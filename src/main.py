import os
import json
import httpx
import logging
import hashlib
import time
import asyncio
import traceback
from typing import Dict, Optional
from dotenv import load_dotenv
from logging_setup import setup_logging
import redis
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, ContextTypes, Defaults
from telegram.error import NetworkError, TimedOut, RetryAfter
from templates import format_message, load_templates, format_premium_message
from high_freq_consumer import start_kafka_consumer
from heat_scheduler import start_scheduler, stop_scheduler

# 導入自定義模型和數據庫函數
import models
from utils import get_additional_channels

# 載入環境變數
load_dotenv(override=True)
setup_logging()
logger = logging.getLogger(__name__)

# 從環境變量加載語言群組配置
LANGUAGE_GROUPS = json.loads(os.getenv("LANGUAGE_GROUPS", "{}"))
if not LANGUAGE_GROUPS:
    logger.warning("未設置 LANGUAGE_GROUPS 環境變數，將使用默認配置")

# 日誌輸出已集中到 push_bot/logs，這裡不再額外設定 console handler

# 設置 httpx 的日誌級別為 WARNING，這樣就不會顯示 HTTP 請求日誌
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('telegram').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# 確認環境變數是否正確載入
DATABASE_URI = os.getenv("DATABASE_URI_TELEGRAM")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("ANNOUNCEMENT_CHANNEL_ID")
GROUP_ID = os.getenv("GROUP_ID")
TOPIC_ID = os.getenv("TOPIC_ID")

if not DATABASE_URI or not BOT_TOKEN:
    logger.error("環境變數缺失! 請確認 .env 文件包含 DATABASE_URI_TELEGRAM 和 TELEGRAM_BOT_TOKEN")
    exit(1)

if not CHANNEL_ID:
    logger.warning("未設置 ANNOUNCEMENT_CHANNEL_ID 環境變數，推送消息將無法發送")

if not DATABASE_URI or not BOT_TOKEN:
    logger.error("環境變數缺失! 請確認 .env 文件包含 DATABASE_URI_TELEGRAM 和 TELEGRAM_BOT_TOKEN")
    exit(1)

if not GROUP_ID or not TOPIC_ID:
    logger.warning("未設置 GROUP_ID 或 TOPIC_ID 環境變數，主題推送可能無法正常工作")

# logger.info(f"DATABASE_URI_TELEGRAM: {DATABASE_URI}")
# logger.info(f"GROUP_ID: {GROUP_ID}, TOPIC_ID: {TOPIC_ID}")
# logger.info(f"DATABASE_URI_TELEGRAM: {DATABASE_URI}")
# logger.info(f"ANNOUNCEMENT_CHANNEL_ID: {CHANNEL_ID}")

# 全局 bot 應用實例
bot_app = None

# 本地重複推送去重（僅進程內，避免網絡超時重試造成重複消息）
DEDUP_WINDOW_SECONDS = int(os.getenv("DEDUP_WINDOW_SECONDS", "180"))
_recent_send_keys = {}

def _make_dedupe_key(chat_id: str, thread_id: str, message: str) -> str:
    sha = hashlib.sha256(message.encode("utf-8")).hexdigest()[:16]
    return f"{chat_id}:{thread_id or ''}:{sha}"

def _should_skip_duplicate(key: str) -> bool:
    now = time.time()
    # 清理過期
    expired = [k for k, ts in _recent_send_keys.items() if now - ts > DEDUP_WINDOW_SECONDS]
    for k in expired:
        _recent_send_keys.pop(k, None)
    if key in _recent_send_keys and now - _recent_send_keys[key] <= DEDUP_WINDOW_SECONDS:
        return True
    _recent_send_keys[key] = now
    return False

def init_bot():
    """初始化 bot 應用"""
    global bot_app
    if bot_app is None:
        # 創建 Application 實例 - 嘗試使用其他方式設置超時
        bot_app = (
            Application.builder()
            .token(BOT_TOKEN)
            .build()
        )

        # 註冊命令處理器
        bot_app.add_handler(CommandHandler("start", start))
        bot_app.add_handler(CommandHandler("help", help_command))
        # bot_app.add_handler(CommandHandler("push", push))
        bot_app.add_handler(CommandHandler("test_multilang", test_multilang))
        # 註冊錯誤處理器
        bot_app.add_error_handler(error_handler)

        logger.info("Bot 初始化完成")
    return bot_app

# 加密貨幣數據處理
def fetch_crypto_data() -> Dict:
    """從 API 獲取加密貨幣數據"""
    # 模擬從 API 拉取數據
    data = {
        "token_symbol": "BBL(BBL Sheep)",
        "chain": "Solana",
        "token_address": "GKuH7SzV6mYc3RmAsYF7sit7QMfK6oj1c1BP59hQpump",
        "market_cap": 540700,
        "price": 0.00067,
        "holders": 234,
        "launch_time": "2015.12.01 01:23:55",
        "smart_money_activity": "15分钟内3名聪明钱交易",
        "contract_security": json.dumps({
            "authority": False,
            "rug_pull": False,
            "burn_pool": False,
            "blacklist": True
        }),
        "top10_holding": 23.17,
        "dev_holding_at_launch": 10.12,
        "dev_holding_current": 23.12,
        "dev_wallet_balance": 3.12,
        "socials": json.dumps({
            "twitter": False,
            "website": True,
            "telegram": True,
            "twitter_search": True
        })
    }
    return data

async def push_to_channel(
    context: ContextTypes.DEFAULT_TYPE,
    message: str,
    crypto_id: Optional[int] = None,
    session=None,
    language: str = "en",
    target_chat_id: Optional[str] = None,
    target_group_id: Optional[str] = None,
    target_topic_id: Optional[str] = None,
    max_send_retries: int = 3,
    token_address_override: Optional[str] = None,
) -> bool:
    """推送消息到指定頻道或主題，带有重试机制"""
    should_close_session = False
    if session is None:
        session = await models.get_session()
        should_close_session = True

    try:
        # 解析目標對象（優先使用顯式參數，其次環境變數，最後默認頻道）
        USE_TOPIC = False
        resolved_chat_id = None
        resolved_topic_id = None

        if target_chat_id:
            resolved_chat_id = target_chat_id
            USE_TOPIC = False
        else:
            # 允許傳入 group+topic 的顯式目標
            group_raw_id = target_group_id or os.getenv("GROUP_ID")
            topic_id = target_topic_id or os.getenv("TOPIC_ID")
            USE_TOPIC = bool(group_raw_id and topic_id)
            if USE_TOPIC:
                if str(group_raw_id).startswith("-100"):
                    resolved_chat_id = str(group_raw_id)
                else:
                    resolved_chat_id = f"-100{group_raw_id}"
                resolved_topic_id = str(topic_id)
                logger.info(f"使用主題模式，目標群組 ID: {resolved_chat_id}, 主題 ID: {resolved_topic_id}")
            else:
                resolved_chat_id = CHANNEL_ID
                logger.info(f"使用頻道模式，目標頻道 ID: {resolved_chat_id}")
        
        if not resolved_chat_id:
            logger.error("未設置頻道 ID 或群組 ID，無法推送消息")
            return False

        # 去重：在發送前做本地去重，防止網路超時導致重試重複
        dedupe_key = _make_dedupe_key(resolved_chat_id, resolved_topic_id if USE_TOPIC else None, message)
        if _should_skip_duplicate(dedupe_key):
            logger.info(f"跳過重複消息（去重命中） chat={resolved_chat_id} thread={resolved_topic_id if USE_TOPIC else ''}")
            return True

        # 取得 token_address（優先使用透傳參數，其次從訊息解析）
        token_address = (token_address_override or '').strip() or None
        if token_address is None:
            for line in message.split('\n'):
                if '<code>' in line and '</code>' in line:
                    # 提取 <code> 標籤中的內容
                    start = line.find('<code>') + 6
                    end = line.find('</code>')
                    token_address = line[start:end].strip()
                    break

        # 分佈式冪等：同一 chat/thread 在 TTL 內只發一次（優先以 token，否則以 message hash）
        try:
            REDIS_HOST = os.getenv("REDIS_HOST")
            if REDIS_HOST:
                r = getattr(push_to_channel, "_redis_client", None)
                if r is None:
                    r = redis.Redis(
                        host=REDIS_HOST,
                        port=int(os.getenv("REDIS_PORT", "6379")),
                        password=os.getenv("REDIS_PASSWORD"),
                        db=int(os.getenv("REDIS_DB", "0")),
                        decode_responses=True,
                        socket_timeout=2,
                    )
                    setattr(push_to_channel, "_redis_client", r)
                chat_dedupe_ttl = int(os.getenv("CHAT_DEDUP_TTL_SECONDS", "300"))
                # 使用 token_address 作為主鍵，缺失時退回 message hash
                if token_address:
                    unique_id = token_address
                    chat_key = f"chatpush:idemp:{resolved_chat_id}:{resolved_topic_id or '0'}:{token_address}"
                else:
                    # Fallback：以 message hash 去重，避免模板偶發缺少 <code>
                    msg_hash = hashlib.sha256(message.encode("utf-8")).hexdigest()[:16]
                    unique_id = msg_hash
                    chat_key = f"chatpush:msghash:{resolved_chat_id}:{resolved_topic_id or '0'}:{msg_hash}"
                # 已發布標記（僅在成功後設置），用於避免同一次呼叫內因網路超時而二次發送
                published_key = f"chatpush:published:{resolved_chat_id}:{resolved_topic_id or '0'}:{unique_id}"
                # message_id 緩存鍵（成功後設置）
                msgid_key = f"chatpush:msgid:{resolved_chat_id}:{resolved_topic_id or '0'}:{unique_id}"
                # 若已發布，直接略過
                try:
                    if r.exists(published_key):
                        logger.info(
                            f"跳過重複消息（已發布標記命中） chat={resolved_chat_id} thread={resolved_topic_id if USE_TOPIC else ''} key={published_key}"
                        )
                        return True
                except Exception:
                    pass
                # 任務級冪等：短時間內相同 chat/thread+token 僅允許一次入場
                if not r.set(name=chat_key, value="1", nx=True, ex=chat_dedupe_ttl):
                    logger.info(
                        f"跳過重複消息（Redis 冪等命中） chat={resolved_chat_id} thread={resolved_topic_id if USE_TOPIC else ''} key={chat_key}"
                    )
                    return True
        except Exception:
            # 忽略 Redis 失敗，繼續後續流程
            pass

        # 構建交易鏈接
        trade_url = f"https://www.bydfi.com/en/moonx/solana/token?address={token_address}"

        # 根據語言獲取按鈕文本
        templates = load_templates()
        lang_templates = templates.get(language, templates.get("en"))
        trade_button_text = lang_templates.get("trade_button", "⚡️一键交易⬆️")
        chart_button_text = lang_templates.get("chart_button", "👉查K线⬆️")

        keyboard = [
            [
                InlineKeyboardButton(trade_button_text, url=trade_url),
                InlineKeyboardButton(chart_button_text, url=trade_url)
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # 添加重試機制（premium 可降低重試次數以避免偶發重複）
        max_retries = max(1, int(max_send_retries))
        retry_delay = 2
        success = False
        error_message = None

        for attempt in range(max_retries):
            try:
                # 使用 Bot 類直接創建實例
                bot = Bot(token=BOT_TOKEN)

                # 準備發送參數
                message_params = {
                    'chat_id': resolved_chat_id,
                    'text': message,
                    'reply_markup': reply_markup,
                    'parse_mode': 'HTML'
                }
                
                # 如果使用主題模式，添加主題 ID
                if USE_TOPIC:
                    message_params['message_thread_id'] = int(resolved_topic_id)
                
                # 發送消息
                sent_msg = await bot.send_message(**message_params)

                log_message = f"消息已發送到{'主題 ' + resolved_topic_id + ' 在群組 ' + resolved_chat_id if USE_TOPIC else '頻道 ' + resolved_chat_id}"
                # logger.info(log_message)
                # 發送成功後，打上已發布標記，避免因隨後的超時/網路錯誤而重複發送
                try:
                    if REDIS_HOST:
                        # 使用前面計算的 published_key；若未定義則臨時生成一次
                        if 'published_key' not in locals():
                            ident = token_address or hashlib.sha256(message.encode("utf-8")).hexdigest()[:16]
                            published_key = f"chatpush:published:{resolved_chat_id}:{resolved_topic_id or '0'}:{ident}"
                        r = getattr(push_to_channel, "_redis_client", None)
                        if r is not None:
                            r.set(name=published_key, value="1", ex=chat_dedupe_ttl)
                            # 緩存 message_id 以供之後重試檢查
                            try:
                                msg_id_val = getattr(sent_msg, 'message_id', None)
                                if msg_id_val is not None:
                                    if 'msgid_key' not in locals():
                                        ident = token_address or hashlib.sha256(message.encode("utf-8")).hexdigest()[:16]
                                        msgid_key = f"chatpush:msgid:{resolved_chat_id}:{resolved_topic_id or '0'}:{ident}"
                                    r.set(name=msgid_key, value=str(msg_id_val), ex=chat_dedupe_ttl)
                            except Exception:
                                pass
                except Exception:
                    pass
                success = True
                break  # 成功發送，跳出重試循環

            except (NetworkError, TimedOut) as e:
                # 網絡錯誤，等待一段時間後重試
                error_message = f"網絡錯誤: {str(e)}"
                target_desc = f"主題 {resolved_topic_id} 在群組 {resolved_chat_id}" if USE_TOPIC else f"頻道 {resolved_chat_id}"
                logger.warning(f"第 {attempt+1} 次嘗試發送消息失敗[{target_desc}]: {error_message}，等待 {retry_delay} 秒後重試")
                # 若前一次其實已成功送達（但回應超時），則已發布標記會存在，此時直接停止重試避免重複
                try:
                    if REDIS_HOST:
                        if 'published_key' not in locals():
                            ident = token_address or hashlib.sha256(message.encode("utf-8")).hexdigest()[:16]
                            published_key = f"chatpush:published:{resolved_chat_id}:{resolved_topic_id or '0'}:{ident}"
                        if 'msgid_key' not in locals():
                            ident = token_address or hashlib.sha256(message.encode("utf-8")).hexdigest()[:16]
                            msgid_key = f"chatpush:msgid:{resolved_chat_id}:{resolved_topic_id or '0'}:{ident}"
                        r = getattr(push_to_channel, "_redis_client", None)
                        if r is not None and (r.exists(published_key) or r.exists(msgid_key)):
                            logger.info(f"檢測到已發布（published/msgid）標記，停止重試以避免重複：{published_key} | {msgid_key}")
                            success = True
                            break
                except Exception:
                    pass
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # 指數退避策略

            except RetryAfter as e:
                # API 限流，等待指定的時間後重試
                retry_after = e.retry_after
                error_message = f"API 限流，需要等待 {retry_after} 秒"
                target_desc = f"主題 {resolved_topic_id} 在群組 {resolved_chat_id}" if USE_TOPIC else f"頻道 {resolved_chat_id}"
                logger.warning(f"第 {attempt+1} 次嘗試發送消息失敗[{target_desc}]: {error_message}")
                await asyncio.sleep(retry_after)

            except Exception as e:
                # 其他錯誤
                error_message = str(e)
                target_desc = f"{'主題 ' + (resolved_topic_id or '') + ' 在群組 ' + resolved_chat_id if USE_TOPIC else '頻道 ' + resolved_chat_id}"
                logger.error(f"無法發送消息到{target_desc}: {error_message}")
                break  # 非預期錯誤，不重試

        # 記錄推送歷史
        chat_id_for_history = f"{target_chat_id}_{TOPIC_ID}" if USE_TOPIC else target_chat_id
        await models.add_push_history(
            session,
            message_content=message,
            chat_ids=json.dumps([chat_id_for_history]),
            crypto_id=crypto_id,
            status="success" if success else "failed",
            error_message=error_message
        )
        # 立即提交，避免長事務
        await session.commit()
        return success
    except Exception as e:
        logger.error(f"推送過程中發生錯誤: {e}")
        await session.rollback()
        return False
    finally:
        if should_close_session:
            try:
                await session.close()
            except Exception:
                pass

async def push_to_all_language_channels(context: ContextTypes.DEFAULT_TYPE, crypto_data: Dict, session=None, is_low_frequency: bool = False) -> Dict[str, bool]:
    """並發向所有語言主題與額外頻道推送加密貨幣資訊。"""
    results: Dict[str, bool] = {}
    language_groups = json.loads(os.getenv("LANGUAGE_GROUPS", "{}"))

    # 構造併發任務
    send_jobs = []  # (key, coroutine)
    visited_targets = set()  # 去重目標: "chat_id:thread_id"

    def normalize_chat(group_id: Optional[str]) -> Optional[str]:
        if not group_id:
            return None
        gid = str(group_id)
        return gid if gid.startswith("-100") else f"-100{gid}"

    # 1) 多語言主題
    for language, target in language_groups.items():
        if is_low_frequency:
            group_id = target.get("low_freq_group_id") or target.get("group_id")
            topic_id = target.get("low_freq_topic_id") or target.get("topic_id")
        else:
            group_id = target.get("high_freq_group_id") or target.get("group_id")
            topic_id = target.get("high_freq_topic_id") or target.get("topic_id")
        if not group_id or not topic_id:
            # 無有效目標，跳過
            results[language] = False
            continue
        norm_chat = normalize_chat(group_id)
        target_key = f"{norm_chat}:{topic_id}"
        if target_key in visited_targets:
            # 同一輪內去重，避免 premium 情況下同一 chat/thread 重覆
            continue
        visited_targets.add(target_key)
        msg = format_premium_message(crypto_data, language) if is_low_frequency else format_message(crypto_data, language)
        send_jobs.append((language, push_to_channel(
            context,
            msg,
            crypto_data.get("id"),
            session=None,  # 避免共享 session 併發問題
            language=language,
            target_group_id=group_id,
            target_topic_id=topic_id,
            max_send_retries=(1 if is_low_frequency else 3),
            token_address_override=str(crypto_data.get("token_address") or crypto_data.get("contract_address") or "").strip(),
        )))

    # 2) 額外頻道（API）
    additional_channels = await get_additional_channels()
    logger.info(f"additional_channels fetched: high={len(additional_channels.get('high_freq', []))}, low={len(additional_channels.get('low_freq', []))}")
    extra_type = "low_freq" if is_low_frequency else "high_freq"
    extra_channels = additional_channels.get(extra_type, [])
    for channel in extra_channels:
        try:
            if isinstance(channel, dict):
                group_id = channel.get("group_id")
                topic_id = channel.get("topic_id")
                lang = (channel.get("language") or "en").lower()
                if group_id and topic_id:
                    norm_chat = normalize_chat(group_id)
                    target_key = f"{norm_chat}:{topic_id}"
                    if target_key in visited_targets:
                        # 與語言主題重疊時去重
                        logger.info(f"skip duplicate extra channel target in same round: {target_key}")
                        continue
                    visited_targets.add(target_key)
                    msg = format_premium_message(crypto_data, lang) if is_low_frequency else format_message(crypto_data, lang)
                    key = f"extra_{group_id}_{topic_id}"
                    send_jobs.append((key, push_to_channel(
                        context,
                        msg,
                        crypto_data.get("id"),
                        session=None,
                        language=lang,
                        target_group_id=group_id,
                        target_topic_id=topic_id,
                        max_send_retries=(1 if is_low_frequency else 3),
                        token_address_override=str(crypto_data.get("token_address") or crypto_data.get("contract_address") or "").strip(),
                    )))
            else:
                # 非字典，視為直接 chat_id
                chat_id = str(channel)
                lang = "en"
                target_key = f"{chat_id}:0"
                if target_key in visited_targets:
                    logger.info(f"skip duplicate direct chat target in same round: {target_key}")
                    continue
                visited_targets.add(target_key)
                msg = format_premium_message(crypto_data, lang) if is_low_frequency else format_message(crypto_data, lang)
                key = f"extra_{chat_id}"
                send_jobs.append((key, push_to_channel(
                    context,
                    msg,
                    crypto_data.get("id"),
                    session=None,
                    language=lang,
                    target_chat_id=chat_id,
                    max_send_retries=(1 if is_low_frequency else 3),
                    token_address_override=str(crypto_data.get("token_address") or crypto_data.get("contract_address") or "").strip(),
                )))
        except Exception:
            # 忽略單一構建錯誤
            continue

    # 併發執行
    if send_jobs:
        keys = [k for k, _ in send_jobs]
        coros = [c for _, c in send_jobs]
        results_list = await asyncio.gather(*coros, return_exceptions=True)
        for k, r in zip(keys, results_list):
            results[k] = (False if isinstance(r, Exception) else bool(r))

    # 總結
    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    logger.info(f"多語言+額外頻道推送完成(並發): 成功 {success_count}/{total_count}")
    return results

async def test_multilang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """測試多語言推送"""
    await update.message.reply_text("正在測試多語言推送...")

    try:
        # 使用測試數據
        data = fetch_crypto_data()
        
        # 創建會話
        session = await models.get_session()
        try:
            # 儲存測試數據
            crypto_id = await models.add_crypto_info(session, data)
            if crypto_id is None:
                await update.message.reply_text("❌ 無法儲存測試數據，測試中止。")
                return
            
            # 設置 ID
            data["id"] = crypto_id
            
            # 推送到所有語言主題
            results = await push_to_all_language_channels(context, data, session)
            
            # 報告結果
            success_languages = [lang for lang, success in results.items() if success]
            failed_languages = [lang for lang, success in results.items() if not success]
            
            if failed_languages:
                await update.message.reply_text(
                    f"⚠️ 多語言推送測試結果:\n"
                    f"✅ 成功語言: {', '.join(success_languages)}\n"
                    f"❌ 失敗語言: {', '.join(failed_languages)}"
                )
            else:
                await update.message.reply_text(
                    f"✅ 多語言推送測試成功! 已推送到這些語言: {', '.join(success_languages)}"
                )
                
        except Exception as e:
            logger.error(f"測試多語言推送時發生錯誤: {e}")
            await session.rollback()
            await update.message.reply_text(f"❌ 測試失敗: {str(e)}")
        finally:
            await session.close()
    except Exception as e:
        logger.error(f"測試命令處理錯誤: {e}")
        await update.message.reply_text(f"❌ 測試失敗: {str(e)}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """處理 /start 命令"""
    await update.message.reply_text(
        "👋 Welcome to MoonX Crypto Bots!\n\n"
        "🔹 Questions or feedback? Reach out to the admin."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """處理 /help 命令"""
    await update.message.reply_text(
        "📚 MOONX 機器人指令說明：\n\n"
        "/start - 查看歡迎訊息\n"
        "/help - 顯示此幫助訊息\n"
        # "/push - 推送最新加密貨幣資訊到公告頻道\n\n"
        "⚠️ 注意：推送功能僅限授權用戶使用。"
    )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """處理所有 Telegram 錯誤"""
    error = context.error

    try:
        # 獲取錯誤的追溯信息
        tb_list = traceback.format_exception(None, error, error.__traceback__)
        tb_string = ''.join(tb_list)

        # 記錄錯誤信息
        logger.error(f"發生異常: {error}")
        logger.error(f"完整的追溯信息:\n{tb_string}")

        # 如果 update 存在，通知用戶
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text("抱歉，處理您的請求時發生錯誤。")
    except Exception as e:
        logger.error(f"處理錯誤時發生異常: {e}")

async def main():
    """主函數"""
    try:
        # 初始化 bot
        global bot_app
        bot_app = init_bot()

        # 啟動 Bot
        logger.info("Bot 開始初始化...")
        await bot_app.initialize()
        logger.info("Bot 初始化完成，正在啟動...")
        await bot_app.start()
        logger.info("Bot 啟動完成，開始輪詢...")

        # 啟動熱度排程（背景任務）
        try:
            await start_scheduler()
        except Exception as e:
            logger.error(f"啟動熱度排程失敗: {e}")

        # 啟動輪詢並保持運行，設置更穩健的參數
        polling_options = {
            'drop_pending_updates': True,
            'allowed_updates': ['message', 'callback_query']
        }

        # 啟動輪詢
        await bot_app.updater.start_polling(**polling_options)
        logger.info("Bot 輪詢已啟動")

        # 啟動 Kafka 高頻消費任務
        try:
            await start_kafka_consumer()
        except Exception as e:
            logger.error(f"啟動 Kafka 高頻消費任務失敗: {e}")

        # 使用事件等待機制來保持運行
        stop_event = asyncio.Event()

        # 等待直到收到停止信號
        await stop_event.wait()

    except Exception as e:
        logger.error(f"Bot 運行時發生錯誤: {e}")
        logger.error(traceback.format_exc())
    finally:
        logger.info("正在停止 Bot...")
        try:
            # 停止熱度排程
            try:
                await stop_scheduler()
            except Exception as e:
                logger.error(f"停止熱度排程時發生錯誤: {e}")

            if bot_app and hasattr(bot_app.updater, 'running') and bot_app.updater.running:
                logger.info("正在停止輪詢...")
                await bot_app.updater.stop()

            if bot_app:
                logger.info("正在停止 bot...")
                await bot_app.stop()
                logger.info("正在關閉 bot...")
                await bot_app.shutdown()
                logger.info("Bot 已完全停止")
        except Exception as e:
            logger.error(f"停止 Bot 時發生錯誤: {e}")
            logger.error(traceback.format_exc())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("收到停止信號，Bot 正在停止...")
