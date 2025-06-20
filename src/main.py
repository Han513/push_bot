import os
import json
import httpx
import logging
import asyncio
import traceback
from typing import Dict, Optional
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, ContextTypes, Defaults
from telegram.error import NetworkError, TimedOut, RetryAfter
from templates import format_message, load_templates, format_premium_message

# 導入自定義模型和數據庫函數
import models
from utils import get_additional_channels

# 載入環境變數
load_dotenv(override=True)

# 從環境變量加載語言群組配置
LANGUAGE_GROUPS = json.loads(os.getenv("LANGUAGE_GROUPS", "{}"))
if not LANGUAGE_GROUPS:
    logger.warning("未設置 LANGUAGE_GROUPS 環境變數，將使用默認配置")

# 設置日誌
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler()  # 只輸出到控制台
    ]
)

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

logger.info(f"DATABASE_URI_TELEGRAM: {DATABASE_URI}")
logger.info(f"GROUP_ID: {GROUP_ID}, TOPIC_ID: {TOPIC_ID}")
logger.info(f"DATABASE_URI_TELEGRAM: {DATABASE_URI}")
logger.info(f"ANNOUNCEMENT_CHANNEL_ID: {CHANNEL_ID}")

# 全局 bot 應用實例
bot_app = None

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

async def push_to_channel(context: ContextTypes.DEFAULT_TYPE, message: str, crypto_id: Optional[int] = None, session=None, language: str = "zh") -> bool:
    """推送消息到指定頻道或主題，带有重试机制"""
    should_close_session = False
    if session is None:
        session = await models.get_session()
        should_close_session = True

    try:
        # 檢查是否有主題設置
        GROUP_RAW_ID = os.getenv("GROUP_ID")
        TOPIC_ID = os.getenv("TOPIC_ID")
        USE_TOPIC = GROUP_RAW_ID and TOPIC_ID
        
        # 決定使用哪種模式
        if USE_TOPIC:
            # 添加 -100 前綴，除非已經有前綴
            if GROUP_RAW_ID.startswith("-100"):
                target_chat_id = GROUP_RAW_ID
            else:
                target_chat_id = f"-100{GROUP_RAW_ID}"
            logger.info(f"使用主題模式，目標群組 ID: {target_chat_id}, 主題 ID: {TOPIC_ID}")
        else:
            target_chat_id = CHANNEL_ID
            logger.info(f"使用頻道模式，目標頻道 ID: {target_chat_id}")
        
        if not target_chat_id:
            logger.error("未設置頻道 ID 或群組 ID，無法推送消息")
            return False

        # 從消息中提取 token_address
        token_address = None
        for line in message.split('\n'):
            if '<code>' in line and '</code>' in line:
                # 提取 <code> 標籤中的內容
                start = line.find('<code>') + 6
                end = line.find('</code>')
                token_address = line[start:end].strip()
                break

        # 構建交易鏈接
        trade_url = f"https://www.bydfi.com/en/moonx/solana/token?address={token_address}"

        # 根據語言獲取按鈕文本
        templates = load_templates()
        lang_templates = templates.get(language, templates.get("zh"))
        trade_button_text = lang_templates.get("trade_button", "⚡️一键交易⬆️")
        chart_button_text = lang_templates.get("chart_button", "👉查K线⬆️")

        keyboard = [
            [
                InlineKeyboardButton(trade_button_text, url=trade_url),
                InlineKeyboardButton(chart_button_text, url=trade_url)
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # 添加重試機制
        max_retries = 3
        retry_delay = 2
        success = False
        error_message = None

        for attempt in range(max_retries):
            try:
                # 使用 Bot 類直接創建實例
                bot = Bot(token=BOT_TOKEN)

                # 準備發送參數
                message_params = {
                    'chat_id': target_chat_id,
                    'text': message,
                    'reply_markup': reply_markup,
                    'parse_mode': 'HTML'
                }
                
                # 如果使用主題模式，添加主題 ID
                if USE_TOPIC:
                    message_params['message_thread_id'] = int(TOPIC_ID)
                
                # 發送消息
                await bot.send_message(**message_params)

                log_message = f"消息已發送到{'主題 ' + TOPIC_ID + ' 在群組 ' + target_chat_id if USE_TOPIC else '頻道 ' + target_chat_id}"
                logger.info(log_message)
                success = True
                break  # 成功發送，跳出重試循環

            except (NetworkError, TimedOut) as e:
                # 網絡錯誤，等待一段時間後重試
                error_message = f"網絡錯誤: {str(e)}"
                logger.warning(f"第 {attempt+1} 次嘗試發送消息失敗: {error_message}，等待 {retry_delay} 秒後重試")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # 指數退避策略

            except RetryAfter as e:
                # API 限流，等待指定的時間後重試
                retry_after = e.retry_after
                error_message = f"API 限流，需要等待 {retry_after} 秒"
                logger.warning(f"第 {attempt+1} 次嘗試發送消息失敗: {error_message}")
                await asyncio.sleep(retry_after)

            except Exception as e:
                # 其他錯誤
                error_message = str(e)
                target_desc = f"{'主題 ' + TOPIC_ID + ' 在群組 ' + target_chat_id if USE_TOPIC else '頻道 ' + target_chat_id}"
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
        await session.commit()
        return success
    except Exception as e:
        logger.error(f"推送過程中發生錯誤: {e}")
        await session.rollback()
        return False
    finally:
        if should_close_session:
            await session.close()

async def push_to_all_language_channels(context: ContextTypes.DEFAULT_TYPE, crypto_data: Dict, session=None, is_low_frequency: bool = False) -> Dict[str, bool]:
    """同時向所有語言主題推送加密貨幣資訊，支持高频和低频信号，並推送到額外頻道（僅一次，中文模板）"""
    results = {}
    language_groups = json.loads(os.getenv("LANGUAGE_GROUPS", "{}"))
    should_close_session = False
    if session is None:
        session = await models.get_session()
        should_close_session = True
    try:
        original_group_id = os.getenv("GROUP_ID")
        original_topic_id = os.getenv("TOPIC_ID")
        # 1. 多語言主題推送
        for language, target in language_groups.items():
            try:
                if is_low_frequency:
                    group_id = target.get("low_freq_group_id") or target.get("group_id")
                    topic_id = target.get("low_freq_topic_id") or target.get("topic_id")
                else:
                    group_id = target.get("high_freq_group_id") or target.get("group_id")
                    topic_id = target.get("high_freq_topic_id") or target.get("topic_id")
                if group_id:
                    os.environ["GROUP_ID"] = group_id
                if topic_id:
                    os.environ["TOPIC_ID"] = topic_id
                message = format_premium_message(crypto_data, language) if is_low_frequency else format_message(crypto_data, language)
                success = await push_to_channel(
                    context,
                    message,
                    crypto_data.get("id"),
                    session,
                    language=language
                )
                results[language] = success
                logger.info(f"向 {language} 主題推送{'低频' if is_low_frequency else '高频'}信號: {'成功' if success else '失敗'}")
            except Exception as e:
                logger.error(f"向 {language} 主題推送{'低频' if is_low_frequency else '高频'}信號時發生錯誤: {e}")
                results[language] = False
        # 2. 額外頻道推送（只推送一次，中文模板）
        additional_channels = await get_additional_channels()
        extra_type = "low_freq" if is_low_frequency else "high_freq"
        extra_channels = additional_channels.get(extra_type, [])
        if extra_channels:
            message = format_premium_message(crypto_data, "zh") if is_low_frequency else format_message(crypto_data, "zh")
            for channel in extra_channels:
                try:
                    if isinstance(channel, dict):
                        os.environ["GROUP_ID"] = channel["group_id"]
                        os.environ["TOPIC_ID"] = channel["topic_id"]
                        channel_id = f"{channel['group_id']}_{channel['topic_id']}"
                    else:
                        channel_id = str(channel)
                        os.environ["GROUP_ID"] = channel_id
                        if "TOPIC_ID" in os.environ:
                            del os.environ["TOPIC_ID"]
                    success = await push_to_channel(context, message, crypto_data.get("id"), session, language="zh")
                    results[f"extra_{channel_id}"] = success
                    logger.info(f"向額外頻道 {channel_id} 推送{'低频' if is_low_frequency else '高频'}信號: {'成功' if success else '失敗'}")
                except Exception as e:
                    logger.error(f"向額外頻道 {channel_id} 推送時發生錯誤: {e}")
                    results[f"extra_{channel_id}"] = False
        # 恢復原始環境變數
        if original_group_id:
            os.environ["GROUP_ID"] = original_group_id
        else:
            if "GROUP_ID" in os.environ:
                del os.environ["GROUP_ID"]
        if original_topic_id:
            os.environ["TOPIC_ID"] = original_topic_id
        else:
            if "TOPIC_ID" in os.environ:
                del os.environ["TOPIC_ID"]
        await session.commit()
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        logger.info(f"多語言+額外頻道推送完成: 成功 {success_count}/{total_count}")
        return results
    except Exception as e:
        logger.error(f"多語言推送過程中發生錯誤: {e}")
        await session.rollback()
        return {"error": str(e)}
    finally:
        if should_close_session:
            await session.close()

# Bot 命令處理函數
# async def push(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     """手動觸發推送加密貨幣信息到所有語言主題的命令"""
#     await update.message.reply_text("正在獲取加密貨幣數據並推送到所有語言主題...")

#     try:
#         # 獲取加密貨幣數據
#         data = fetch_crypto_data()

#         # 創建會話
#         session = await models.get_session()
#         try:
#             # 儲存加密貨幣資訊
#             crypto_id = await models.add_crypto_info(session, data)
#             if crypto_id is None:
#                 await update.message.reply_text("❌ 無法儲存加密貨幣資訊，推送中止。")
#                 return

#             # 設置 ID 用於多語言推送
#             data["id"] = crypto_id

#             # 推送到所有語言主題
#             results = await push_to_all_language_channels(context, data, session)

#             # 檢查結果
#             if "error" in results:
#                 await update.message.reply_text(f"❌ 推送過程中發生錯誤: {results['error']}")
#             else:
#                 success_count = sum(1 for success in results.values() if success)
#                 total_count = len(results)
#                 if success_count == total_count:
#                     await update.message.reply_text(f"✅ 成功推送到所有 {total_count} 個語言主題！")
#                 else:
#                     await update.message.reply_text(f"⚠️ 部分推送失敗: 成功 {success_count}/{total_count} 個語言主題。請檢查日誌。")

#         except Exception as e:
#             logger.error(f"數據庫操作錯誤: {e}")
#             await session.rollback()
#             await update.message.reply_text(f"❌ 推送失敗: {str(e)}")
#         finally:
#             await session.close()
#     except Exception as e:
#         logger.error(f"推送命令處理錯誤: {e}")
#         await update.message.reply_text(f"❌ 推送失敗: {str(e)}")

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
        "👋 歡迎使用 MOONX 加密貨幣資訊機器人！\n\n"
        # "🔹 使用 /push 命令可以推送最新的加密貨幣資訊到公告頻道\n\n"
        "有任何問題或建議，請聯繫管理員。"
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

        # 啟動輪詢並保持運行，設置更穩健的參數
        polling_options = {
            'drop_pending_updates': True,
            'allowed_updates': ['message', 'callback_query']
        }

        # 啟動輪詢
        await bot_app.updater.start_polling(**polling_options)
        logger.info("Bot 輪詢已啟動")

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