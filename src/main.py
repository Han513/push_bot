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
from templates import format_message

# 導入自定義模型和數據庫函數
import models

# 載入環境變數
load_dotenv(override=True)

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
        bot_app.add_handler(CommandHandler("push", push))
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

# def format_message(data: Dict) -> str:
#     """將加密貨幣數據格式化為消息"""
#     try:
#         contract_security = json.loads(data['contract_security'])
#         socials = json.loads(data['socials'])
#     except (json.JSONDecodeError, KeyError) as e:
#         logger.error(f"JSON 解析錯誤: {e}")
#         contract_security = {}
#         socials = {}

#     contract_security_str = (
#         f"- 权限：[{ '✅' if contract_security.get('authority', False) else '❌'}]  "
#         f"貔貅: [{ '✅' if contract_security.get('rug_pull', False) else '❌'}]  "
#         f"烧池子 [{ '✅' if contract_security.get('burn_pool', False) else '❌'}]  "
#         f"黑名单 [{ '✅' if contract_security.get('blacklist', False) else '❌'}]"
#     )

#     # 構建推特搜索鏈接
#     token_address = data.get('token_address', '')
#     twitter_search_url = f"https://x.com/search?q={token_address}&src=typed_query"
#     twitter_search_link = f"<a href='{twitter_search_url}'>👉查推特</a>"

#     # 構建社交媒體鏈接 - 整体变成可点击链接
#     twitter_part = "推特❌"
#     if socials.get('twitter', False) and socials.get('twitter_url'):
#         twitter_part = f"<a href='{socials['twitter_url']}'>推特✅</a>"

#     website_part = "官网❌"
#     if socials.get('website', False) and socials.get('website_url'):
#         website_part = f"<a href='{socials['website_url']}'>官网✅</a>"

#     telegram_part = f"电报{'✅' if socials.get('telegram', False) else '❌'}"

#     socials_str = f"🔗 {twitter_part} || {website_part} || {telegram_part} || {twitter_search_link}"

#     dev_status_line = ""
#     if data.get('dev_status_display') and data.get('dev_status_display') != '--':
#         dev_status_line = f"- {data.get('dev_status_display')}\n"

#     # 構建可複製的 token_address
#     copyable_address = f"<code>{token_address}</code>"

#     message = (
#         f"🟢 [MOONX] 🟢 新币上线 / 异动播报 🪙  :\n"
#         f"├ ${data.get('token_symbol', 'Unknown')} - {data.get('chain', 'Unknown')}\n"
#         f"├ {copyable_address}\n"
#         f"💊 当前市值：{data.get('market_cap_display', '--')}\n"
#         f"💰 当前价格：$ {data.get('price_display', '--')}\n"
#         f"👬 持币人：{data.get('holders_display', '--')}\n"
#         f"⏳ 开盘时间： [{data.get('launch_time_display', '--')}] \n"        
#         f"——————————————————\n"
#         f"🔍 链上监控\n"
#         f"聪明钱 {data.get('total_addr_amount', '0')} 笔买入 (15分钟内)\n"
#         f"合约安全：\n"
#         f"{contract_security_str}\n"        
#         f"💰 开发者：\n"
#         f"{dev_status_line}"
#         f"- 开发者余额：{data.get('dev_wallet_balance_display', '--')} SOL \n"
#         f"- Top10占比：{data.get('top10_holding_display', '--')}%\n"
#         f"🌐 社交与工具\n{socials_str}\n"
#         f"——————————————————\n"
#         f"🚨 MOONX 社区提示\n"
#         f"- 防范Rug Pull，务必验证合约权限与流动性锁仓。\n"
#         f"- 关注社区公告，欢迎分享观点与资讯。\n"
#     )
#     return message

# async def push_to_channel(context: ContextTypes.DEFAULT_TYPE, message: str, crypto_id: Optional[int] = None, session=None) -> bool:
#     """推送消息到指定頻道，带有重试机制"""
#     should_close_session = False
#     if session is None:
#         session = await models.get_session()
#         should_close_session = True

#     try:
#         if not CHANNEL_ID:
#             logger.error("未設置頻道 ID，無法推送消息")
#             return False

#         # 從消息中提取 token_address
#         token_address = None
#         for line in message.split('\n'):
#             if '<code>' in line and '</code>' in line:
#                 # 提取 <code> 標籤中的內容
#                 start = line.find('<code>') + 6
#                 end = line.find('</code>')
#                 token_address = line[start:end].strip()
#                 break

#         # 構建交易鏈接
#         trade_url = f"https://www.bydfi.com/en/moonx/solana/token?address={token_address}"
#         keyboard = [
#             [
#                 InlineKeyboardButton("⚡️一键交易⬆️", url=trade_url),
#                 InlineKeyboardButton("👉查K线⬆️", url=trade_url)
#             ]
#         ]
#         reply_markup = InlineKeyboardMarkup(keyboard)

#         # 添加重試機制
#         max_retries = 3
#         retry_delay = 2
#         success = False
#         error_message = None

#         for attempt in range(max_retries):
#             try:
#                 # 使用 Bot 類直接創建實例，不設置額外的超時參數
#                 bot = Bot(token=BOT_TOKEN)

#                 # 發送消息
#                 await bot.send_message(
#                     chat_id=CHANNEL_ID,
#                     text=message,
#                     reply_markup=reply_markup,
#                     parse_mode='HTML'
#                 )

#                 logger.info(f"消息已發送到頻道 {CHANNEL_ID}")
#                 success = True
#                 break  # 成功發送，跳出重試循環

#             except (NetworkError, TimedOut) as e:
#                 # 網絡錯誤，等待一段時間後重試
#                 error_message = f"網絡錯誤: {str(e)}"
#                 logger.warning(f"第 {attempt+1} 次嘗試發送消息失敗: {error_message}，等待 {retry_delay} 秒後重試")
#                 await asyncio.sleep(retry_delay)
#                 retry_delay *= 2  # 指數退避策略

#             except RetryAfter as e:
#                 # API 限流，等待指定的時間後重試
#                 retry_after = e.retry_after
#                 error_message = f"API 限流，需要等待 {retry_after} 秒"
#                 logger.warning(f"第 {attempt+1} 次嘗試發送消息失敗: {error_message}")
#                 await asyncio.sleep(retry_after)

#             except Exception as e:
#                 # 其他錯誤
#                 error_message = str(e)
#                 logger.error(f"無法發送消息到頻道 {CHANNEL_ID}: {error_message}")
#                 break  # 非預期錯誤，不重試

#         # 記錄推送歷史
#         await models.add_push_history(
#             session,
#             message_content=message,
#             chat_ids=json.dumps([CHANNEL_ID]),
#             crypto_id=crypto_id,
#             status="success" if success else "failed",
#             error_message=error_message
#         )
#         await session.commit()
#         return success
#     except Exception as e:
#         logger.error(f"推送過程中發生錯誤: {e}")
#         await session.rollback()
#         return False
#     finally:
#         if should_close_session:
#             await session.close()

async def push_to_channel(context: ContextTypes.DEFAULT_TYPE, message: str, crypto_id: Optional[int] = None, session=None) -> bool:
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
        keyboard = [
            [
                InlineKeyboardButton("⚡️一键交易⬆️", url=trade_url),
                InlineKeyboardButton("👉查K线⬆️", url=trade_url)
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

async def push_to_all_language_channels(context: ContextTypes.DEFAULT_TYPE, crypto_data: Dict, session=None) -> Dict[str, bool]:
    """同時向所有語言主題推送加密貨幣資訊"""
    results = {}
    
    # 從環境變數加載語言群組配置
    language_groups = json.loads(os.getenv("LANGUAGE_GROUPS", "{}"))
    
    # 如果配置為空，回退到原始頻道
    if not language_groups:
        message = format_message(crypto_data)
        result = await push_to_channel(context, message, crypto_data.get("id"), session)
        return {"default": result}
    
    # 保存會話管理狀態
    should_close_session = False
    if session is None:
        session = await models.get_session()
        should_close_session = True
    
    try:
        # 保存原始環境變數
        original_group_id = os.getenv("GROUP_ID")
        original_topic_id = os.getenv("TOPIC_ID")
        
        # 為每種語言創建并發送消息
        for language, target in language_groups.items():
            try:
                # 臨時設置環境變數為目標語言的頻道/群組
                group_id = target.get("group_id")
                topic_id = target.get("topic_id")
                
                # 使用 os.environ 動態設置環境變數
                if group_id:
                    os.environ["GROUP_ID"] = group_id
                if topic_id:
                    os.environ["TOPIC_ID"] = topic_id
                
                # 格式化該語言的消息
                message = format_message(crypto_data, language)
                
                # 使用現有的 push_to_channel 函數發送消息
                success = await push_to_channel(
                    context, 
                    message, 
                    crypto_data.get("id"), 
                    session
                )
                
                results[language] = success
                logger.info(f"向 {language} 主題推送消息: {'成功' if success else '失敗'}")
                
            except Exception as e:
                logger.error(f"向 {language} 主題推送消息時發生錯誤: {e}")
                results[language] = False
        
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
        
        # 日誌輸出總結
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        logger.info(f"多語言推送完成: 成功 {success_count}/{total_count}")
        
        return results
    except Exception as e:
        logger.error(f"多語言推送過程中發生錯誤: {e}")
        await session.rollback()
        return {"error": str(e)}
    finally:
        if should_close_session:
            await session.close()

# Bot 命令處理函數
async def push(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """手動觸發推送加密貨幣信息到所有語言主題的命令"""
    await update.message.reply_text("正在獲取加密貨幣數據並推送到所有語言主題...")

    try:
        # 獲取加密貨幣數據
        data = fetch_crypto_data()

        # 創建會話
        session = await models.get_session()
        try:
            # 儲存加密貨幣資訊
            crypto_id = await models.add_crypto_info(session, data)
            if crypto_id is None:
                await update.message.reply_text("❌ 無法儲存加密貨幣資訊，推送中止。")
                return

            # 設置 ID 用於多語言推送
            data["id"] = crypto_id

            # 推送到所有語言主題
            results = await push_to_all_language_channels(context, data, session)

            # 檢查結果
            if "error" in results:
                await update.message.reply_text(f"❌ 推送過程中發生錯誤: {results['error']}")
            else:
                success_count = sum(1 for success in results.values() if success)
                total_count = len(results)
                if success_count == total_count:
                    await update.message.reply_text(f"✅ 成功推送到所有 {total_count} 個語言主題！")
                else:
                    await update.message.reply_text(f"⚠️ 部分推送失敗: 成功 {success_count}/{total_count} 個語言主題。請檢查日誌。")

        except Exception as e:
            logger.error(f"數據庫操作錯誤: {e}")
            await session.rollback()
            await update.message.reply_text(f"❌ 推送失敗: {str(e)}")
        finally:
            await session.close()
    except Exception as e:
        logger.error(f"推送命令處理錯誤: {e}")
        await update.message.reply_text(f"❌ 推送失敗: {str(e)}")

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
        "🔹 使用 /push 命令可以推送最新的加密貨幣資訊到公告頻道\n\n"
        "有任何問題或建議，請聯繫管理員。"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """處理 /help 命令"""
    await update.message.reply_text(
        "📚 MOONX 機器人指令說明：\n\n"
        "/start - 查看歡迎訊息\n"
        "/help - 顯示此幫助訊息\n"
        "/push - 推送最新加密貨幣資訊到公告頻道\n\n"
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