from quart import Quart, request, jsonify
import asyncio
import logging
from typing import Dict, Optional, List
from quart_cors import cors
import json
from main import push_to_channel, format_message, init_bot
from models import get_session, add_crypto_info, get_cached_wallets
import os
from dotenv import load_dotenv
import redis
from logging_setup import setup_logging
import aiohttp
from datetime import datetime, timezone, timedelta
import threading
import time
import base58
from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey
from main import push_to_all_language_channels
from utils import get_additional_channels

# 設置日誌
logger = logging.getLogger(__name__)

# 載入環境變數
load_dotenv(override=True)
setup_logging()
CHANNEL_ID = os.getenv("ANNOUNCEMENT_CHANNEL_ID")
SOLSCAN_API_TOKEN = os.getenv("SOLSCAN_API_TOKEN")
INTERNAL_API_URL = os.getenv("INTERNAL_API_URL", "http://moonx.backend:4200")
RPC_URL = os.getenv("RPC_URL")
RPC_URL_BACKUP = os.getenv("RPC_URL_backup")
LOCAL = os.getenv("LOCAL")
SMART_MONEY = os.getenv("SMART_MONEY")
SOCIALS_API_URL = os.getenv("SOCIALS_API_URL", "http://172.31.91.67:5002/admin/telegram/social/socials")

# 請求超時（秒）
ES_REQUEST_TIMEOUT = int(os.getenv("ES_REQUEST_TIMEOUT", "3"))
SOLSCAN_REQUEST_TIMEOUT = int(os.getenv("SOLSCAN_REQUEST_TIMEOUT", "3"))
ES_REQUEST_RETRIES = int(os.getenv("ES_REQUEST_RETRIES", "2"))
SOLSCAN_REQUEST_RETRIES = int(os.getenv("SOLSCAN_REQUEST_RETRIES", "2"))
ES_RETRY_BACKOFF = float(os.getenv("ES_RETRY_BACKOFF", "0.5"))
SOLSCAN_RETRY_BACKOFF = float(os.getenv("SOLSCAN_RETRY_BACKOFF", "0.5"))

# Redis（分佈式冪等）
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
IDEMPOTENCY_TTL_SECONDS = int(os.getenv("IDEMPOTENCY_TTL_SECONDS", "600"))  # 普通推送冪等 10 分鐘
_redis_client: Optional[redis.Redis] = None

def get_redis() -> Optional[redis.Redis]:
    global _redis_client
    if _redis_client is None and REDIS_HOST:
        _redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD,
            db=REDIS_DB,
            decode_responses=True,
            socket_timeout=2,
        )
    return _redis_client

# 創建應用實例
app = Quart(__name__)
app = cors(app, allow_origin="*")

# 用于避免重複處理相同代幣的集合（普通推送去重：一段時間內同一地址只入隊一次）
processed_tokens = set()
processing_lock = asyncio.Lock()

# Premium 推送的等級去重：記錄每個地址已推送的最高等級，只允許更高等級入隊
premium_max_level = {}
premium_lock = asyncio.Lock()

# 存儲任務對象
app_tasks = {}

# 處理隊列資料結構，使用列表代替 asyncio.Queue
token_queue = []
queue_lock = threading.Lock()

async def get_additional_channels() -> Dict[str, List[str]]:
    """
    從社交API獲取額外的頻道信息
    返回格式: {
        "high_freq": ["chat_id1", "chat_id2", ...],
        "low_freq": ["chat_id1", "chat_id2", ...]
    }
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(SOCIALS_API_URL) as response:
                if response.status != 200:
                    logger.error(f"獲取額外頻道信息失敗: {response.status}")
                    return {"high_freq": [], "low_freq": []}
                
                data = await response.json()
                if data.get("code") != 200:
                    logger.error("API返回錯誤狀態碼")
                    return {"high_freq": [], "low_freq": []}
                
                high_freq_channels = []
                low_freq_channels = []
                
                # 遍歷所有用戶的聊天組
                for user_data in data.get("data", []):
                    for chat in user_data.get("chats", []):
                        if not chat.get("enable", False):
                            continue
                            
                        chat_name = chat.get("name", "")
                        chat_id = chat.get("chatId")
                        
                        if "WEB3 Signal - High Freq" in chat_name:
                            high_freq_channels.append(chat_id)
                        elif "WEB3 Signal – Low Freq" in chat_name:
                            low_freq_channels.append(chat_id)
                
                return {
                    "high_freq": high_freq_channels,
                    "low_freq": low_freq_channels
                }
    except Exception as e:
        logger.error(f"獲取額外頻道信息時發生錯誤: {e}")
        return {"high_freq": [], "low_freq": []}

# 心跳任務
async def heartbeat():
    """每10分鐘執行一次的心跳任務"""
    try:
        while True:
            logger.info("API 心跳檢查 - 服務正常運行中")
            await asyncio.sleep(600)  # 10分鐘 = 600秒
    except asyncio.CancelledError:
        logger.info("心跳任務已停止")
        raise

async def token_processor():
    """處理隊列中的代幣任務"""
    try:
        while True:
            task = None
            with queue_lock:
                if token_queue:
                    task = token_queue.pop(0)

            if task:
                # 根據任務類型處理
                if task.get('type') == 'premium':
                    # 處理 premium 類型的任務
                    data = task['data']
                    token_address = data['token_address']
                    chain = data['chain']
                    market_cap_level = data['market_cap_level']
                    open_time = data['open_time']
                    token_price = float(data['token_price'])
                    is_low_frequency = True
                else:
                    # 處理普通類型的任務
                    token_address = task['token_address']
                    chain = task['chain']
                    is_low_frequency = False

                    # 高頻任務：增加分佈式處理柵欄，避免短時間重複處理同一 token
                    try:
                        r = get_redis()
                        if r is not None:
                            hf_key_ttl = max(60, min(600, IDEMPOTENCY_TTL_SECONDS))  # 1~10 分鐘
                            hf_proc_key = f"hf:processing:{chain}:{token_address}"
                            if not r.set(name=hf_proc_key, value="1", nx=True, ex=hf_key_ttl):
                                logger.info(f"跳過高頻重複處理（processing 柵欄命中）: {chain} {token_address}")
                                continue
                    except Exception as e:
                        logger.warning(f"高頻 processing 柵欄設置失敗（略過）：{e}")

                # 檢查是否已經處理過
                should_process = True
                # async with processing_lock:
                #     if token_address in processed_tokens:
                #         logger.info(f"跳過已處理的代幣: {token_address}")
                #         should_process = False
                #     else:
                #         processed_tokens.add(token_address)

                if should_process:
                    logger.info(f"開始處理代幣: chain={chain}, address={token_address}")

                    try:
                        # 根據任務類型選擇不同的處理函數
                        if task.get('type') == 'premium':
                            crypto_data = await fetch_token_info_premium(token_address, token_price)
                        else:
                            crypto_data = await fetch_token_info(token_address)

                        if not crypto_data:
                            logger.error(f"無法獲取代幣信息: {token_address}")
                            continue

                        # 創建會話
                        session = await get_session()
                        try:
                            # 儲存加密貨幣資訊（flush 之後立即提交，避免長事務）
                            crypto_id = await add_crypto_info(session, crypto_data)
                            if crypto_id is None:
                                logger.error(f"無法保存加密貨幣信息: {token_address}")
                                continue

                            # 立即提交並釋放事務，避免 idle in transaction
                            try:
                                await session.commit()
                            except Exception as e:
                                logger.error(f"提交加密貨幣信息時發生錯誤: {e}")
                                await session.rollback()
                                continue

                            # 設置 ID
                            crypto_data["id"] = crypto_id

                            # 如果是 premium 任務，添加額外信息
                            if task.get('type') == 'premium':
                                crypto_data['market_cap_level'] = market_cap_level
                                crypto_data['open_time'] = open_time

                            # 模擬 context 對象
                            class FakeContext:
                                def __init__(self):
                                    self.bot = None

                            # 統一使用 push_to_all_language_channels，根據任務類型設置 is_low_frequency
                            # 插入完成後不再依賴當前資料庫會話，提早關閉以釋放連線
                            try:
                                await session.close()
                            except Exception:
                                pass

                            results = await push_to_all_language_channels(
                                FakeContext(), 
                                crypto_data, 
                                session=None, 
                                is_low_frequency=is_low_frequency
                            )

                            # 檢查結果
                            if "error" in results:
                                logger.error(f"推送過程中發生錯誤: {results['error']}")
                            else:
                                success_count = sum(1 for success in results.values() if success)
                                total_count = len(results)
                                if success_count == total_count:
                                    logger.info(f"成功推送代幣通知: {token_address}")
                                else:
                                    logger.warning(f"部分推送失敗: 成功 {success_count}/{total_count} 個語言群組: {token_address}")

                        except Exception as e:
                            logger.error(f"處理代幣 {token_address} 時發生錯誤: {e}")
                            await session.rollback()
                        finally:
                            # 若前面未能提前關閉，這裡作保險處理
                            try:
                                await session.close()
                            except Exception:
                                pass
                        # 高頻 processing 柵欄：處理完畢後縮短 TTL，避免長時間佔用
                        try:
                            if task.get('type') != 'premium':
                                r = get_redis()
                                if r is not None:
                                    hf_proc_key = f"hf:processing:{chain}:{token_address}"
                                    # 將剩餘 TTL 調整為 30 秒，允許稍後再次處理
                                    r.expire(hf_proc_key, 30)
                        except Exception:
                            pass
                    except Exception as e:
                        logger.error(f"處理代幣任務時發生錯誤: {e}")

            # 休息一下，避免 CPU 佔用過高
            await asyncio.sleep(0.1)

    except asyncio.CancelledError:
        logger.info("代幣處理任務已取消")
        raise
    except Exception as e:
        logger.error(f"代幣處理器發生致命錯誤: {e}")
        raise

# 定期清理已處理代幣的任務
async def cleanup_processed_tokens():
    """每小時清理一次已處理的代幣集合，避免內存泄漏"""
    try:
        while True:
            await asyncio.sleep(3600)  # 每小時執行一次

            async with processing_lock:
                token_count = len(processed_tokens)
                processed_tokens.clear()

            async with premium_lock:
                premium_count = len(premium_max_level)
                premium_max_level.clear()

            logger.info(f"已清理去重集合，普通: {token_count}，premium: {premium_count}")
    except asyncio.CancelledError:
        logger.info("清理任務已取消")
        raise

@app.before_serving
async def startup():
    """在API啟動前啟動心跳任務和代幣處理任務"""
    # 獲取當前事件循環
    loop = asyncio.get_running_loop()

    # 創建並啟動所有後台任務
    app_tasks['heartbeat'] = loop.create_task(heartbeat())
    app_tasks['token_processor'] = loop.create_task(token_processor())
    app_tasks['cleanup'] = loop.create_task(cleanup_processed_tokens())

    logger.info("心跳監控和代幣處理任務已啟動")

@app.after_serving
async def shutdown():
    """在API關閉時清理所有任務"""
    # 取消所有任務
    for name, task in app_tasks.items():
        if not task.done():
            logger.info(f"正在取消任務: {name}")
            task.cancel()

    # 等待所有任務完成
    if app_tasks:
        await asyncio.gather(*app_tasks.values(), return_exceptions=True)
        app_tasks.clear()

    logger.info("所有後台任務已停止")

async def check_token_exists(session: aiohttp.ClientSession, token_address: str) -> bool:
    """檢查代幣是否存在於內部 API"""
    internal_url = f"{INTERNAL_API_URL}/internal/token_info"
    params = {
        "network": "SOLANA",
        "tokenAddress": token_address,
        "brand": "BYD"
    }

    logger.info(f"正在檢查代幣是否存在: {internal_url} with params: {params}")
    try:
        async with session.get(internal_url, params=params) as response:
            if response.status != 200:
                logger.error(f"內部 API 請求失敗: {response.status}")
                return False

            data = await response.json()

            # 如果返回的數據中沒有 data 字段，表示代幣不存在
            if data.get("code") == 200 and not data.get("data"):
                logger.info(f"代幣不存在: {token_address}")
                return False

            return True
    except Exception as e:
        logger.error(f"檢查代幣時發生錯誤: {e}")
        return False

async def fetch_token_info(token_address: str) -> Optional[Dict]:
    """從 Solscan API 和內部 API 獲取代幣信息"""
    async with aiohttp.ClientSession() as session:
        # 從 ES 獲取數據（以 address + SOLANA 精準查詢）
        es_base_url = os.getenv("ES_BASE_URL", "http://es-sg-2ci4eq22t0001gfig.elasticsearch.aliyuncs.com:9200")
        es_index = os.getenv("ES_INDEX", "web3_tokens")
        es_username = os.getenv("ES_USERNAME", "elastic")
        es_password = os.getenv("ES_PASSWORD", "J4U#dh8Kd1Fz")

        es_detail_url = f"{es_base_url.rstrip('/')}/{es_index}/_search"
        es_payload = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"address": token_address}},
                        {"term": {"network": "SOLANA"}},
                    ]
                }
            },
            "size": 1,
        }

        es_source = None
        # 帶重試的 ES 查詢
        es_attempt = 0
        while es_attempt <= ES_REQUEST_RETRIES:
            try:
                async with session.post(
                    es_detail_url,
                    json=es_payload,
                    auth=aiohttp.BasicAuth(es_username, es_password),
                    timeout=aiohttp.ClientTimeout(total=ES_REQUEST_TIMEOUT),
                ) as es_resp:
                    if es_resp.status != 200:
                        logger.warning(f"ES 查詢失敗: HTTP {es_resp.status} (attempt={es_attempt+1}/{ES_REQUEST_RETRIES+1})")
                    else:
                        es_json = await es_resp.json()
                        hits = es_json.get("hits", {}).get("hits", [])
                        if not hits:
                            logger.info(f"ES 未找到代幣: {token_address}")
                        else:
                            es_source = hits[0].get("_source") or None
                            break
            except asyncio.TimeoutError:
                logger.warning(f"ES 查詢超時 {ES_REQUEST_TIMEOUT}s (attempt={es_attempt+1}/{ES_REQUEST_RETRIES+1}): address={token_address}")
            except Exception as e:
                logger.warning(f"查詢 ES 發生錯誤 (attempt={es_attempt+1}/{ES_REQUEST_RETRIES+1}): {e}")
            es_attempt += 1
            if es_attempt <= ES_REQUEST_RETRIES:
                await asyncio.sleep(ES_RETRY_BACKOFF * es_attempt)

        # ES 優先，Solscan 作為備援
        has_twitter = False
        has_website = False
        twitter_url = None
        website_url = None
        dev_wallet_balance = 0.0

        # 風險/Top10/DEV 狀態等（先設預設值）
        risk_items = {}
        top10_holding = None
        top10_holding_display = "--"
        dev_status = None
        dev_status_display = "--"

        # 從 ES 取名/符號
        token_name = (es_source or {}).get("name", "Unknown")
        token_symbol = (es_source or {}).get("symbol", "Unknown")

        # 時間：優先 ES created_at(毫秒)
        created_time = None
        if es_source:
            try:
                created_time = int(int(es_source.get("created_at") or 0) / 1000)
            except Exception:
                created_time = None
        if created_time:
            dt = datetime.fromtimestamp(created_time, tz=timezone.utc)
            dt_utc8 = dt.astimezone(timezone(timedelta(hours=8)))
            formatted_time = dt_utc8.strftime("%Y.%m.%d %H:%M:%S")
            launch_time = dt_utc8.replace(tzinfo=None)
        else:
            formatted_time = "--"
            launch_time = None

        # 市值/價格/持有人：優先 ES
        market_cap = None
        if es_source:
            try:
                es_mc = es_source.get("market_cap_usd")
                if es_mc is not None:
                    mc_val = float(es_mc)
                    market_cap = mc_val if mc_val > 0 else None
            except Exception:
                market_cap = None
            # 若 market_cap_usd 無效，嘗試 fdv_usd
            if market_cap is None:
                try:
                    es_fdv = es_source.get("fdv_usd")
                    if es_fdv is not None:
                        fdv_val = float(es_fdv)
                        market_cap = fdv_val if fdv_val > 0 else None
                except Exception:
                    pass
        price = None
        if es_source:
            try:
                p = es_source.get("price_usd")
                if p is not None:
                    p_val = float(p)
                    price = p_val if p_val > 0 else None
            except Exception:
                price = None
        if (market_cap is None) and price is not None and es_source:
            try:
                supply_es = es_source.get("total_supply") or 0
                mc_calc = float(price) * float(supply_es)
                market_cap = mc_calc if mc_calc > 0 else None
            except Exception:
                pass
        holders = None
        if es_source:
            try:
                raw_h = (es_source.get("holder_info") or {}).get("holder_count")
                if raw_h is not None:
                    h_val = int(raw_h)
                    holders = h_val if h_val > 0 else None
            except Exception:
                holders = None

        # 風險與 Top10/DEV 狀態 from ES
        if es_source:
            security_info = es_source.get("security_info") or {}
            holder_info = es_source.get("holder_info") or {}
            social_info = es_source.get("social_info") or {}
            contract_info = es_source.get("contract_info") or {}

            dev_status = security_info.get("dev_status")
            if dev_status is not None:
                dev_status_map = {0: "DEV持有", 1: "DEV减仓", 2: "DEV加仓", 3: "DEV清仓", 4: "DEV加池子", 5: "DEV烧池子"}
                dev_status_display = dev_status_map.get(dev_status, "--")

            try:
                if holder_info.get("top10_percent") is not None:
                    top10_holding = float(holder_info.get("top10_percent"))
                elif security_info.get("base_top_10_percent") is not None:
                    top10_holding = float(security_info.get("base_top_10_percent"))
                if top10_holding is not None:
                    top10_holding_display = f"{top10_holding:.2f}"
            except (ValueError, TypeError):
                logger.warning("無法解析 top10 百分比")

            try:
                risk_items = {}
                primary_code_map = {
                    "PERMISSION_RENOUNCED": "authority",
                    "OWNER_CANNOT_CHANGE_BALANCE": "authority",
                    "OWNER_CANNOT_PAUSE_TRADING": "authority",
                    "TRANSFER_HOOK": "authority",
                    "NOT_PIKS": "rug_pull",
                    "NO_INFLATION_DUMP": "rug_pull",
                    "TOKEN_CANNOT_SELF_DESTRUCT": "rug_pull",
                    "LP_LOCKED": "burn_pool",
                    "SLIPPAGE_IMMUTABLE": "burn_pool",
                    "NO_BLACKLIST": "blacklist",
                }
                risk_items_list = security_info.get("risk_item", []) or []
                for item in risk_items_list:
                    code = item.get("code")
                    risk_status = item.get("riskStatus")
                    mapped = primary_code_map.get(code)
                    if mapped and risk_status == "PASS":
                        risk_items[mapped] = True
            except Exception as e:
                logger.error(f"處理風險項目時發生錯誤: {e}")

            # 社交 from ES
            try:
                tw = (social_info.get("twitter") or "").strip()
                if tw:
                    has_twitter = True
                    twitter_url = tw if tw.startswith(("http://", "https://")) else f"https://{tw}"
                websites = social_info.get("websites") or []
                if isinstance(websites, list) and websites:
                    has_website = True
                    website_url = websites[0]
                    if not website_url.startswith(("http://", "https://")):
                        website_url = f"https://{website_url}"
            except Exception:
                pass

            # 創建者地址 from ES，用於查餘額
            creator_address = (contract_info.get("creator") or "").strip()
            if creator_address:
                try:
                    dev_wallet_balance = await get_sol_balance(creator_address)
                except Exception as e:
                    logger.error(f"獲取創建者錢包餘額時出錯: {e}")

        # 若仍缺關鍵信息，再調用 Solscan 作備援
        need_solscan = False
        if price is None or market_cap in (None, 0) or holders in (None, 0) or (not has_twitter and not has_website) or token_name == "Unknown" or token_symbol == "Unknown" or launch_time is None:
            need_solscan = True

        if need_solscan:
            # 帶重試的 Solscan 查詢
            sc_attempt = 0
            while sc_attempt <= SOLSCAN_REQUEST_RETRIES:
                try:
                    url = f"https://pro-api.solscan.io/v2.0/token/meta?address={token_address}"
                    headers = {"token": SOLSCAN_API_TOKEN}
                    async with session.get(
                        url,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=SOLSCAN_REQUEST_TIMEOUT),
                    ) as response:
                        if response.status == 200:
                            solscan_data = await response.json()
                            if solscan_data.get("success") and solscan_data.get("data"):
                                sd = solscan_data["data"]
                                # 名稱/符號
                                token_name = token_name if token_name and token_name != "Unknown" else sd.get("name", token_name)
                                token_symbol = token_symbol if token_symbol and token_symbol != "Unknown" else sd.get("symbol", token_symbol)
                                # 價格
                                if price is None and sd.get("price") is not None:
                                    try:
                                        p = float(sd.get("price"))
                                        price = p if p > 0 else None
                                    except Exception:
                                        pass
                                # 市值
                                if market_cap in (None, 0):
                                    mc_val = sd.get("market_cap")
                                    if mc_val is None and sd.get("price") is not None and sd.get("supply") is not None:
                                        try:
                                            mc_val = float(sd.get("price")) * float(sd.get("supply"))
                                        except Exception:
                                            mc_val = None
                                    try:
                                        if mc_val is not None:
                                            mc = float(mc_val)
                                            market_cap = mc if mc > 0 else market_cap
                                    except Exception:
                                        pass
                                # 持有人數
                                if holders in (None, 0):
                                    try:
                                        raw_h = sd.get("holder")
                                        if raw_h is not None:
                                            h = int(raw_h)
                                            holders = h if h > 0 else holders
                                    except Exception:
                                        pass
                                # 社交
                                md = sd.get("metadata") or {}
                                if not has_twitter and md.get("twitter"):
                                    has_twitter = True
                                    twitter_url = md.get("twitter")
                                    if not twitter_url.startswith(("http://", "https://")):
                                        twitter_url = f"https://{twitter_url}"
                                if not has_website and md.get("website"):
                                    has_website = True
                                    website_url = md.get("website")
                                    if not website_url.startswith(("http://", "https://")):
                                        website_url = f"https://{website_url}"
                                # 建立時間
                                if launch_time is None and sd.get("created_time"):
                                    try:
                                        ct = int(sd.get("created_time"))
                                        dt = datetime.fromtimestamp(ct, tz=timezone.utc)
                                        dt_utc8 = dt.astimezone(timezone(timedelta(hours=8)))
                                        formatted_time = dt_utc8.strftime("%Y.%m.%d %H:%M:%S")
                                        launch_time = dt_utc8.replace(tzinfo=None)
                                    except Exception:
                                        pass
                                break
                        else:
                            logger.warning(f"Solscan 備援請求失敗: HTTP {response.status} (attempt={sc_attempt+1}/{SOLSCAN_REQUEST_RETRIES+1})")
                except asyncio.TimeoutError:
                    logger.warning(f"Solscan 查詢超時 {SOLSCAN_REQUEST_TIMEOUT}s (attempt={sc_attempt+1}/{SOLSCAN_REQUEST_RETRIES+1}): address={token_address}")
                except Exception as e:
                    logger.error(f"Solscan 備援調用異常 (attempt={sc_attempt+1}/{SOLSCAN_REQUEST_RETRIES+1}): {e}")
                sc_attempt += 1
                if sc_attempt <= SOLSCAN_REQUEST_RETRIES:
                    await asyncio.sleep(SOLSCAN_RETRY_BACKOFF * sc_attempt)

            # 确保它们都不为空
            if not token_name or token_name.strip() == "":
                token_name = token_symbol  # 使用symbol作为备选
            if not token_symbol or token_symbol.strip() == "":
                token_symbol = token_name  # 使用name作为备选

            # 去除空格
            token_name = token_name.strip()
            token_symbol = token_symbol.strip()

            # 格式化數值顯示（避免科學計數法）
            market_cap_display = "--"
            price_display = "--"
            holders_display = "--"
            dev_wallet_balance_display = "0"

            if market_cap is not None:
                # 格式化市值显示，使用K、M、B表示
                if market_cap >= 1_000_000_000:  # 十亿及以上用B
                    market_cap_display = f"$ {market_cap / 1_000_000_000:.2f}B".rstrip('0').rstrip('.')
                    if market_cap_display.endswith('.'):
                        market_cap_display = market_cap_display[:-1]
                elif market_cap >= 1_000_000:  # 百万及以上用M
                    market_cap_display = f"$ {market_cap / 1_000_000:.2f}M".rstrip('0').rstrip('.')
                    if market_cap_display.endswith('.'):
                        market_cap_display = market_cap_display[:-1]
                elif market_cap >= 10_000:  # 万及以上用K
                    market_cap_display = f"$ {market_cap / 1_000:.2f}K".rstrip('0').rstrip('.')
                    if market_cap_display.endswith('.'):
                        market_cap_display = market_cap_display[:-1]
                else:  # 小于一万直接显示
                    market_cap_display = f"$ {market_cap:,.2f}".rstrip('0').rstrip('.')
                    if market_cap_display.endswith('.'):
                        market_cap_display = market_cap_display[:-1]

            if price is not None:
                # 处理非常小的数字，避免科学计数法
                if price < 0.0001:
                    # 查找第一个非零位
                    str_price = str(price)
                    decimal_places = 8

                    # 对于非常小的数字，寻找第一个非零数字
                    if "e-" in str_price:  # 科学计数法
                        # 提取指数
                        exponent = int(str_price.split("e-")[1])
                        # 设置足够的小数位
                        decimal_places = exponent + 2  # 多显示一两位有效数字

                    price_display = f"{price:.{decimal_places}f}".rstrip('0').rstrip('.')
                    if price_display == "":
                        price_display = "0"
                else:
                    # 一般数字，显示足够的小数位
                    price_display = f"{price:.6f}".rstrip('0').rstrip('.')
                    if price_display == "":
                        price_display = "0"

            if holders is not None:
                # 持幣人數為整數，使用千分位格式
                holders_display = f"{holders:,}"

            if dev_wallet_balance:
                # 開發者錢包餘額，特殊格式化小數點後多個零的情況
                str_balance = str(dev_wallet_balance)
                if '.' in str_balance:
                    integer_part, decimal_part = str_balance.split('.')
                    
                    # 计算小数点后连续的零的个数
                    zero_count = 0
                    for char in decimal_part:
                        if char == '0':
                            zero_count += 1
                        else:
                            break
                    
                    # 如果小数点后有超过3个连续的零
                    if zero_count > 3:
                        # 找到第一个非零数字的位置
                        non_zero_pos = decimal_part.find(next(filter(lambda x: x != '0', decimal_part), ''))
                        if non_zero_pos != -1:
                            # 格式化为 "整数.0{零的数量}非零部分"
                            dev_wallet_balance_display = f"{integer_part}.0{{{zero_count}}}{decimal_part[zero_count:]}"
                        else:
                            # 如果小数部分全是零
                            dev_wallet_balance_display = f"{integer_part}.0"
                    else:
                        # 如果零的数量不多，正常显示两位小数
                        dev_wallet_balance_display = f"{dev_wallet_balance:.2f}"
                else:
                    # 如果没有小数部分
                    dev_wallet_balance_display = f"{dev_wallet_balance:.2f}"

            # 構建社交媒體信息 JSON
            socials_json = {
                "twitter": has_twitter,
                "website": has_website,
                "telegram": False,  # 默認沒有 Telegram
                "twitter_search": True,  # 總是可以搜索 Twitter
                "twitter_url": twitter_url,
                "website_url": website_url
            }
            # ------------------------------------------------聰明錢動態------------------------------------------------
            total_addr_amount = 0
            try:
                async with aiohttp.ClientSession() as smart_money_session:
                    url = f"http://{SMART_MONEY}:5041/robots/smartmoney/tokentrend"
                    payload = {
                        "chain": "SOLANA",
                        "token_addresses": [token_address],
                        "time": 900  # 15分钟
                    }

                    async with smart_money_session.post(url, json=payload) as response:
                        if response.status == 200:
                            smart_money_data = await response.json()
                            if smart_money_data.get("code") == 200 and smart_money_data.get("data"):
                                # 获取第一条数据（因为我们只查询了一个token）
                                token_data = smart_money_data["data"][0]
                                total_addr_amount = str(token_data.get("total_addr_amount", 0))
                                logger.info(f"获取到智能钱数据: {total_addr_amount}名聪明钱")
            except Exception as e:
                logger.error(f"获取智能钱活动时出错: {e}")

            # 最終必備校驗（普通路徑）：必須取得 價格、市值、持幣人數，且都 > 0
            if price is None or market_cap is None or holders is None or price <= 0 or market_cap <= 0 or holders <= 0:
                logger.info(
                    f"跳過推送：缺少關鍵數據 token={token_address}, price={price}, market_cap={market_cap}, holders={holders}"
                )
                return None

            return {
                "token_name": token_name,
                "token_symbol": token_symbol,
                "chain": "Solana",
                "contract_address": token_address,
                # 數據庫存儲值
                "market_cap": market_cap if market_cap is not None else None,
                "price": price if price is not None else None,
                "holders": holders if holders is not None else None,
                "launch_time": launch_time,
                "smart_money_activity": None,
                "top10_holding": top10_holding,
                "dev_status": dev_status,
                "dev_status_display": dev_status_display,
                "dev_wallet_balance": dev_wallet_balance,
                # 顯示值（用於消息格式化）
                "market_cap_display": market_cap_display,
                "price_display": price_display,
                "holders_display": holders_display,
                "launch_time_display": formatted_time,
                "total_addr_amount": total_addr_amount,
                "top10_holding_display": top10_holding_display,
                "dev_holding_at_launch_display": "--",
                "dev_holding_current_display": "--",
                "dev_wallet_balance_display": dev_wallet_balance_display,
                "contract_security": json.dumps({
                    key: risk_items[key]
                    for key in ["authority", "rug_pull", "burn_pool", "blacklist"]
                    if key in risk_items
                }),
                "socials": json.dumps(socials_json),
                "token_address": token_address
            }

async def fetch_token_info_premium(token_address: str, token_price: float) -> Optional[Dict]:
    """從 Solscan API 和內部 API 獲取代幣信息"""
    # 初始化 crypto_data 字典
    crypto_data = {
        "token_name": "",
        "token_symbol": "",
        "chain": "Solana",
        "contract_address": token_address,
        "price": token_price,
        "holders": None,
        "launch_time": None,
        "smart_money_activity": None,
        "top10_holding": None,
        "dev_status": None,
        "dev_status_display": "--",
        "market_cap_display": "--",
        "price_display": "--",
        "holders_display": "--",
        "launch_time_display": "--",
        "total_addr_amount": "0",
        "top10_holding_display": "--",
        "dev_holding_at_launch_display": "--",
        "dev_holding_current_display": "--",
        "dev_wallet_balance_display": "0",
        "contract_security": "{}",
        "socials": "{}",
        "token_address": token_address,
        "highlight_tag_codes": []  # 初始化為空列表
    }

    async with aiohttp.ClientSession() as session:
        # 從 ES 獲取數據（以 address + SOLANA 精準查詢）
        es_base_url = os.getenv("ES_BASE_URL", "http://es-sg-2ci4eq22t0001gfig.elasticsearch.aliyuncs.com:9200")
        es_index = os.getenv("ES_INDEX", "web3_tokens")
        es_username = os.getenv("ES_USERNAME", "elastic")
        es_password = os.getenv("ES_PASSWORD", "J4U#dh8Kd1Fz")

        es_detail_url = f"{es_base_url.rstrip('/')}/{es_index}/_search"
        es_payload = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"address": token_address}},
                        {"term": {"network": "SOLANA"}},
                    ]
                }
            },
            "size": 1,
        }

        es_source = None
        try:
            async with session.post(
                es_detail_url,
                json=es_payload,
                auth=aiohttp.BasicAuth(es_username, es_password),
                timeout=aiohttp.ClientTimeout(total=ES_REQUEST_TIMEOUT),
            ) as es_resp:
                if es_resp.status != 200:
                    logger.warning(f"ES 查詢失敗: HTTP {es_resp.status}，將嘗試 Solscan 補償")
                else:
                    es_json = await es_resp.json()
                    hits = es_json.get("hits", {}).get("hits", [])
                    if not hits:
                        logger.info(f"ES 未找到代幣: {token_address}，將嘗試 Solscan 補償")
                    else:
                        es_source = hits[0].get("_source") or None
        except asyncio.TimeoutError:
            logger.warning(f"ES 查詢超時 {ES_REQUEST_TIMEOUT}s: address={token_address}")
        except Exception as e:
            logger.warning(f"查詢 ES 發生錯誤: {e}，將嘗試 Solscan 補償")

        # 從 Solscan API 獲取基本信息
        url = f"https://pro-api.solscan.io/v2.0/token/meta?address={token_address}"
        headers = {"token": SOLSCAN_API_TOKEN}

        async with session.get(
            url,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=SOLSCAN_REQUEST_TIMEOUT),
        ) as response:
            if response.status != 200:
                logger.error(f"從 Solscan API 獲取數據失敗: {response.status}")
                return None

            solscan_data = await response.json()

            if not solscan_data.get("success") or "data" not in solscan_data:
                logger.error("Solscan API 返回無效數據")
                return None

            token_data = solscan_data["data"]
            
            # 檢查必要字段
            if token_data.get("symbol") is None:
                return None
                
            # 如果沒有 market_cap，嘗試計算
            if token_data.get("market_cap") is None and token_data.get("price") is not None and token_data.get("supply") is not None:
                try:
                    price = float(token_data["price"])
                    supply = float(token_data["supply"])
                    token_data["market_cap"] = price * supply
                except (ValueError, TypeError):
                    logger.error("無法計算市值")
                    return None

            # 獲取社交媒體連結
            has_twitter = False
            has_website = False
            twitter_url = None
            website_url = None

            # 從 metadata 中獲取社交媒體連結
            if "metadata" in token_data and token_data["metadata"]:
                metadata = token_data["metadata"]

                if "twitter" in metadata and metadata["twitter"]:
                    has_twitter = True
                    twitter_url = metadata["twitter"]
                    # 確保 Twitter URL 格式正確
                    if not twitter_url.startswith(("http://", "https://")):
                        twitter_url = f"https://{twitter_url}"

                if "website" in metadata and metadata["website"]:
                    has_website = True
                    website_url = metadata["website"]
                    # 確保 Website URL 格式正確
                    if not website_url.startswith(("http://", "https://")):
                        website_url = f"https://{website_url}"

            # 獲取創建者錢包餘額
            dev_wallet_balance = 0.0
            if "creator" in token_data and token_data["creator"]:
                creator_address = token_data["creator"]
                try:
                    dev_wallet_balance = await get_sol_balance(creator_address)
                except Exception as e:
                    logger.error(f"獲取創建者錢包餘額時出錯: {e}")

            # 處理 ES 數據（替代原先的內部 API）
            risk_items = {}
            top10_holding = None
            top10_holding_display = "--"
            dev_status = None
            dev_status_display = "--"
            if es_source:
                security_info = es_source.get("security_info") or {}
                holder_info = es_source.get("holder_info") or {}

                dev_status = security_info.get("dev_status")
                if dev_status is not None:
                    dev_status_map = {
                        0: "DEV持有",
                        1: "DEV减仓",
                        2: "DEV加仓",
                        3: "DEV清仓",
                        4: "DEV加池子",
                        5: "DEV烧池子"
                    }
                    dev_status_display = dev_status_map.get(dev_status, "--")

                # 優先從 holder_info.top10_percent 取得，若無則嘗試 security_info.base_top_10_percent
                try:
                    if holder_info.get("top10_percent") is not None:
                        top10_holding = float(holder_info.get("top10_percent"))
                    elif security_info.get("base_top_10_percent") is not None:
                        top10_holding = float(security_info.get("base_top_10_percent"))
                    if top10_holding is not None:
                        top10_holding_display = f"{top10_holding:.2f}"
                except (ValueError, TypeError):
                    logger.warning("無法解析 top10 百分比")

                # 轉換 ES 的 risk_item 列表到我們的四類
                try:
                    risk_items = {}
                    primary_code_map = {
                        # 權限/所有權相關
                        "PERMISSION_RENOUNCED": "authority",
                        "OWNER_CANNOT_CHANGE_BALANCE": "authority",
                        "OWNER_CANNOT_PAUSE_TRADING": "authority",
                        "TRANSFER_HOOK": "authority",
                        # 風險/跑路相關
                        "NOT_PIKS": "rug_pull",
                        "NO_INFLATION_DUMP": "rug_pull",
                        "TOKEN_CANNOT_SELF_DESTRUCT": "rug_pull",
                        # 鎖池/滑點不可變 等近似視為 burn_pool 類
                        "LP_LOCKED": "burn_pool",
                        "SLIPPAGE_IMMUTABLE": "burn_pool",
                        # 黑名單
                        "NO_BLACKLIST": "blacklist",
                    }
                    risk_items_list = security_info.get("risk_item", []) or []
                    for item in risk_items_list:
                        code = item.get("code")
                        risk_status = item.get("riskStatus")
                        mapped = primary_code_map.get(code)
                        if mapped:
                            # 任一對應 code PASS 則視為該類 True
                            if risk_status == "PASS":
                                risk_items[mapped] = True
                except Exception as e:
                    logger.error(f"處理風險項目時發生錯誤: {e}")

            # 轉換時間戳為 UTC+8 格式
            created_time = token_data.get("created_time")
            if created_time is None and es_source:
                try:
                    created_time = int(int(es_source.get("created_at") or 0) / 1000)
                except Exception:
                    created_time = None
            if created_time:
                dt = datetime.fromtimestamp(created_time, tz=timezone.utc)
                dt_utc8 = dt.astimezone(timezone(timedelta(hours=8)))
                formatted_time = dt_utc8.strftime("%Y.%m.%d %H:%M:%S")
                launch_time = dt_utc8.replace(tzinfo=None)  # 數據庫存儲用
            else:
                formatted_time = "--"
                launch_time = None

            # 準備顯示和存儲的數據
            market_cap = token_data.get("market_cap")
            # 若 ES 有 market_cap_usd/或 fdv_usd 可用，優先使用；否則再嘗試 price*total_supply
            if (market_cap is None or market_cap == 0) and es_source:
                try:
                    es_mc = es_source.get("market_cap_usd")
                    if es_mc and float(es_mc) > 0:
                        market_cap = float(es_mc)
                    else:
                        es_fdv = es_source.get("fdv_usd")
                        if es_fdv and float(es_fdv) > 0:
                            market_cap = float(es_fdv)
                        else:
                            price_es = es_source.get("price_usd") or 0
                            supply_es = es_source.get("total_supply") or 0
                            market_cap = float(price_es) * float(supply_es)
                except Exception:
                    pass

            # 若上游客戶傳入為 None 或 0，視為缺值，嘗試從 ES 補充；若仍缺，再用 Solscan
            price = None
            try:
                if token_price not in (None, 0, 0.0, "0", "0.0"):
                    price = float(token_price)
            except Exception:
                price = None
            if price is None and es_source:
                try:
                    price = float(es_source.get("price_usd"))
                except Exception:
                    price = None
            # 最後嘗試使用 Solscan 的價格
            if price is None:
                try:
                    sc_price = token_data.get("price")
                    if sc_price not in (None, 0, 0.0, "0", "0.0"):
                        price = float(sc_price)
                except Exception:
                    price = None

            holders = token_data.get("holder")
            if (holders is None or holders == 0) and es_source:
                try:
                    holders = int((es_source.get("holder_info") or {}).get("holder_count", 0))
                except Exception:
                    pass

            token_name = token_data.get("name", "Unknown")
            token_symbol = token_data.get("symbol", "Unknown")

            # 确保它们都不为空
            if not token_name or token_name.strip() == "":
                token_name = token_symbol  # 使用symbol作为备选
            if not token_symbol or token_symbol.strip() == "":
                token_symbol = token_name  # 使用name作为备选

            # 去除空格
            token_name = token_name.strip()
            token_symbol = token_symbol.strip()

            # 格式化數值顯示（避免科學計數法）
            market_cap_display = "--"
            price_display = "--"
            holders_display = "--"
            dev_wallet_balance_display = "0"

            if market_cap is not None:
                # 格式化市值显示，使用K、M、B表示
                if market_cap >= 1_000_000_000:  # 十亿及以上用B
                    market_cap_display = f"$ {market_cap / 1_000_000_000:.2f}B".rstrip('0').rstrip('.')
                    if market_cap_display.endswith('.'):
                        market_cap_display = market_cap_display[:-1]
                elif market_cap >= 1_000_000:  # 百万及以上用M
                    market_cap_display = f"$ {market_cap / 1_000_000:.2f}M".rstrip('0').rstrip('.')
                    if market_cap_display.endswith('.'):
                        market_cap_display = market_cap_display[:-1]
                elif market_cap >= 10_000:  # 万及以上用K
                    market_cap_display = f"$ {market_cap / 1_000:.2f}K".rstrip('0').rstrip('.')
                    if market_cap_display.endswith('.'):
                        market_cap_display = market_cap_display[:-1]
                else:  # 小于一万直接显示
                    market_cap_display = f"$ {market_cap:,.2f}".rstrip('0').rstrip('.')
                    if market_cap_display.endswith('.'):
                        market_cap_display = market_cap_display[:-1]

            if price is not None:
                # 处理非常小的数字，避免科学计数法
                if price < 0.0001:
                    # 查找第一个非零位
                    str_price = str(price)
                    decimal_places = 8

                    # 对于非常小的数字，寻找第一个非零数字
                    if "e-" in str_price:  # 科学计数法
                        # 提取指数
                        exponent = int(str_price.split("e-")[1])
                        # 设置足够的小数位
                        decimal_places = exponent + 2  # 多显示一两位有效数字

                    price_display = f"{price:.{decimal_places}f}".rstrip('0').rstrip('.')
                    if price_display == "":
                        price_display = "0"
                else:
                    # 一般数字，显示足够的小数位
                    price_display = f"{price:.6f}".rstrip('0').rstrip('.')
                    if price_display == "":
                        price_display = "0"

            if holders is not None:
                # 持幣人數為整數，使用千分位格式
                holders_display = f"{holders:,}"

            if dev_wallet_balance:
                # 開發者錢包餘額，特殊格式化小數點後多個零的情況
                str_balance = str(dev_wallet_balance)
                if '.' in str_balance:
                    integer_part, decimal_part = str_balance.split('.')
                    
                    # 计算小数点后连续的零的个数
                    zero_count = 0
                    for char in decimal_part:
                        if char == '0':
                            zero_count += 1
                        else:
                            break
                    
                    # 如果小数点后有超过3个连续的零
                    if zero_count > 3:
                        # 找到第一个非零数字的位置
                        non_zero_pos = decimal_part.find(next(filter(lambda x: x != '0', decimal_part), ''))
                        if non_zero_pos != -1:
                            # 格式化为 "整数.0{零的数量}非零部分"
                            dev_wallet_balance_display = f"{integer_part}.0{{{zero_count}}}{decimal_part[zero_count:]}"
                        else:
                            # 如果小数部分全是零
                            dev_wallet_balance_display = f"{integer_part}.0"
                    else:
                        # 如果零的数量不多，正常显示两位小数
                        dev_wallet_balance_display = f"{dev_wallet_balance:.2f}"
                else:
                    # 如果没有小数部分
                    dev_wallet_balance_display = f"{dev_wallet_balance:.2f}"

            # 構建社交媒體信息 JSON
            socials_json = {
                "twitter": has_twitter,
                "website": has_website,
                "telegram": False,  # 默認沒有 Telegram
                "twitter_search": True,  # 總是可以搜索 Twitter
                "twitter_url": twitter_url,
                "website_url": website_url
            }

            # 最小資訊檢查（premium 與普通一致：價格、市值、持幣都需 > 0）
            if price in (None, 0) or market_cap in (None, 0) or holders in (None, 0):
                logger.info(
                    f"跳過推送：缺少關鍵數據 token={token_address}, price={price}, market_cap={market_cap}, holders={holders}"
                )
                return None

            # 更新 crypto_data 字典
            crypto_data.update({
                "token_name": token_name,
                "token_symbol": token_symbol,
                "price": price if price is not None else None,
                "holders": holders if holders is not None else None,
                "launch_time": launch_time,
                "top10_holding": top10_holding,
                "dev_status": dev_status,
                "dev_status_display": dev_status_display,
                "market_cap_display": market_cap_display,
                "price_display": price_display,
                "holders_display": holders_display,
                "launch_time_display": formatted_time,
                "top10_holding_display": top10_holding_display,
                "dev_wallet_balance_display": dev_wallet_balance_display,
                "contract_security": json.dumps({
                    key: risk_items[key]
                    for key in ["authority", "rug_pull", "burn_pool", "blacklist"]
                    if key in risk_items
                }),
                "socials": json.dumps(socials_json)
            })

            # ------------------------------------------------聰明錢動態------------------------------------------------
            try:
                buy_list = []
                async with aiohttp.ClientSession() as smart_money_session:
                    url = f"http://{SMART_MONEY}:5041/robots/smartmoney/tokentrend"
                    payload = {
                        "chain": "SOLANA",
                        "token_addresses": [token_address],
                        "time": 3600  # 1小時
                    }

                    async with smart_money_session.post(url, json=payload) as response:
                        if response.status == 200:
                            smart_money_data = await response.json()
                            if smart_money_data.get("code") == 200 and smart_money_data.get("data"):
                                token_data = smart_money_data["data"][0]
                                buy_list = token_data.get("buy", [])
                                total_addr_amount = str(token_data.get("total_addr_amount", 0))
                                crypto_data["total_addr_amount"] = total_addr_amount
                                logger.info(f"获取到智能钱数据: {total_addr_amount}名聪明钱")

                kol_wallets, smart_wallets, high_value_smart_wallets, smart_wallets_win_rate = await get_cached_wallets()
                
                # 1. KOL地址买入
                if any(buy['wallet_address'] in kol_wallets for buy in buy_list):
                    crypto_data["highlight_tag_codes"].append(1)
                    logger.info("觸發KOL地址买入標籤")

                # 2. 1小时内吸引≥3个高净值聪明钱地址买入
                high_value_buyers = set(
                    buy['wallet_address'] for buy in buy_list if buy['wallet_address'] in high_value_smart_wallets
                )
                if len(high_value_buyers) >= 3:
                    crypto_data["highlight_tag_codes"].append(2)
                    logger.info("觸發高净值聪明钱地址买入標籤")

                # 3. 同一聪明钱购买超过1万美金
                from collections import defaultdict
                usd_sum = defaultdict(float)
                for buy in buy_list:
                    addr = buy['wallet_address']
                    if addr in smart_wallets:
                        usd_sum[addr] += float(buy.get('wallet_buy_usd', 0))
                if any(total > 10000 for total in usd_sum.values()):
                    crypto_data["highlight_tag_codes"].append(3)
                    logger.info("觸發同一聪明钱购买超过1万美金標籤")

                logger.info(f"最終的亮點標籤代碼: {crypto_data['highlight_tag_codes']}")

            except Exception as e:
                logger.error(f"获取智能钱活动时出错: {e}")
                crypto_data["highlight_tag_codes"] = []

            return crypto_data

@app.route('/api/tg_push', methods=['POST'])
async def tg_push():
    """接收代幣地址並異步觸發推送"""
    try:
        # 獲取請求數據
        data = await request.get_json()
        token_address = data.get('token_address')
        chain = data.get('chain')

        if not token_address:
            return jsonify({
                'status': 'error',
                'message': 'Missing required parameter: token_address'
            }), 400

        if not chain:
            return jsonify({
                'status': 'error',
                'message': 'Missing required parameter: chain'
            }), 400

        # 驗證 chain 參數
        ALLOWED_CHAINS = ['SOLANA', 'BASE', 'ETH', 'BSC', 'TRON']
        if chain not in ALLOWED_CHAINS:
            return jsonify({
                'status': 'error',
                'message': f'Invalid chain parameter. Must be one of: {", ".join(ALLOWED_CHAINS)}'
            }), 400

        # 檢查並標記處理中（去重：入隊即標記）
        async with processing_lock:
            if token_address in processed_tokens:
                logger.info(f"代幣已在處理中: {token_address}")
                return jsonify({
                    'status': 'success',
                    'message': 'Token is already being processed'
                })
            processed_tokens.add(token_address)

        # 分佈式冪等：同一 token_address 在短時間內只允許一個入隊
        try:
            r = get_redis()
            if r is not None:
                idem_key = f"push:idemp:{chain}:{token_address}"
                if not r.set(name=idem_key, value="1", nx=True, ex=IDEMPOTENCY_TTL_SECONDS):
                    logger.info(f"忽略重覆請求（冪等鍵命中）: {chain} {token_address}")
                    return jsonify({'status': 'success', 'message': 'Duplicate ignored by idempotency key'})
        except Exception as e:
            logger.warning(f"Redis 冪等檢查失敗（略過）: {e}")

        # 將任務添加到隊列
        logger.info(f"將代幣添加到處理隊列: chain={chain}, address={token_address}")
        with queue_lock:
            token_queue.append({
                'token_address': token_address,
                'chain': chain
            })

        # 立即返回成功响應
        return jsonify({
            'status': 'success',
            'message': 'Token notification request accepted and queued for processing'
        })

    except Exception as e:
        logger.error(f"API 請求處理錯誤: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# 修改批量添加代幣API
@app.route('/api/tg_push_premium', methods=['POST'])
async def tg_push_premium():
    try:
        data = await request.get_json()
        
        # 驗證必要字段
        required_fields = ['token_address', 'chain', 'market_cap_level', 'open_time', 'token_price']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"缺少必要字段: {field}"}), 400

        address = data.get('token_address')
        level = int(data.get('market_cap_level') or 0)

        # premium 等級去重：僅更高等級允許入隊
        async with premium_lock:
            prev = premium_max_level.get(address, 0)
            if level <= prev:
                logger.info(f"Premium 去重：忽略非升級請求 address={address}, level={level}, prev={prev}")
                return jsonify({'status': 'success', 'message': 'Duplicate (non-upgrade) premium request ignored'})
            premium_max_level[address] = level

        # 分佈式冪等：同一 address+level 在 TTL 內只允許一個 premium 任務
        try:
            r = get_redis()
            if r is not None:
                idem_key = f"premium:idemp:{data.get('chain','SOLANA')}:{address}:{level}"
                if not r.set(name=idem_key, value="1", nx=True, ex=max(IDEMPOTENCY_TTL_SECONDS, 3600)):
                    logger.info(f"忽略重覆 premium 請求（冪等鍵命中）: {address} level={level}")
                    return jsonify({'status': 'success', 'message': 'Duplicate premium ignored by idempotency key'})
        except Exception as e:
            logger.warning(f"Redis 冪等檢查失敗（略過）: {e}")

        # 將任務添加到隊列
        with queue_lock:
            token_queue.append({
                'type': 'premium',
                'data': data
            })

        # 立即返回成功響應
        return jsonify({
            'status': 'success',
            'message': '推送任務已加入隊列'
        })

    except Exception as e:
        logger.error(f"處理請求時發生錯誤: {e}")
        return jsonify({"error": str(e)}), 500

# 獲取處理隊列狀態
@app.route('/api/queue_status', methods=['GET'])
async def queue_status():
    """獲取代幣處理隊列狀態"""
    try:
        with queue_lock:
            queue_size = len(token_queue)

        async with processing_lock:
            processed_count = len(processed_tokens)

        return jsonify({
            'status': 'success',
            'data': {
                'queue_size': queue_size,
                'processed_tokens': processed_count
            }
        })
    except Exception as e:
        logger.error(f"獲取隊列狀態錯誤: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

async def get_sol_balance(wallet_address: str) -> float:
    """
    獲取 SOL 餘額
    :param wallet_address: 錢包地址
    :return: SOL 餘額 (浮點數)
    """
    # 創建 RPC 客戶端
    client = None
    try:
        # 首先嘗試主要 RPC
        client = AsyncClient(RPC_URL)
        pubkey = Pubkey(base58.b58decode(wallet_address))
        balance_response = await client.get_balance(pubkey=pubkey)

        # 從回應中獲取值
        # solders.rpc.responses.GetBalanceResp 格式有所不同
        sol_balance = float(balance_response.value) / 10**9
        # logger.info(f"錢包 {wallet_address} 的 SOL 餘額: {sol_balance}")
        return sol_balance
    except Exception as e:
        logger.error(f"使用主要 RPC 獲取 SOL 餘額時發生異常: {e}")
        try:
            # 嘗試使用備用 RPC
            if client:
                await client.close()
            client = AsyncClient(RPC_URL_BACKUP)
            pubkey = Pubkey(base58.b58decode(wallet_address))
            balance_response = await client.get_balance(pubkey=pubkey)

            # 從回應中獲取值
            sol_balance = float(balance_response.value) / 10**9
            logger.info(f"使用備用 RPC 獲取錢包 {wallet_address} 的 SOL 餘額: {sol_balance}")
            return sol_balance
        except Exception as e:
            logger.error(f"使用備用 RPC 獲取 SOL 餘額時也發生異常: {e}")
            return 0.0
    finally:
        # 確保客戶端連接關閉
        if client:
            try:
                await client.close()
            except Exception:
                pass

async def run_api():
    """運行 Quart API"""
    config = {
        "host": LOCAL,
        # "host": "127.0.0.1",
        "port": 5011,
        "debug": False  # 在生產環境中禁用 debug 模式
    }
    await app.run_task(**config)

if __name__ == '__main__':
    # 設置事件循環策略
    if os.name == 'nt':  # Windows
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # 運行 API
    asyncio.run(run_api())

# 在 api.py 的開頭添加
HIGHLIGHT_TAG_CODES = {
    1: "KOL地址买入",
    2: "1小时内吸引≥3个高净值聪明钱地址买入",
    3: "同一聪明钱购买超过1万美金"
}
