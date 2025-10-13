import os
import asyncio
import logging
from typing import List, Dict, Optional, Any, Set

import aiohttp
from dotenv import load_dotenv
from logging_setup import setup_logging
import time
import random


# 載入環境變數
load_dotenv(override=True)
setup_logging()

logger = logging.getLogger(__name__)


# Elasticsearch 設定（可透過環境變數覆蓋）
ES_BASE_URL = os.getenv("ES_BASE_URL", "http://es-sg-2ci4eq22t0001gfig.elasticsearch.aliyuncs.com:9200")
ES_INDEX = os.getenv("ES_INDEX", "web3_tokens")
ES_USERNAME = os.getenv("ES_USERNAME", "elastic")
ES_PASSWORD = os.getenv("ES_PASSWORD", "J4U#dh8Kd1Fz")

# 查詢設定
ES_QUERY_SIZE = int(os.getenv("ES_QUERY_SIZE", "500"))
ES_SORT_FIELD = os.getenv("ES_SORT_FIELD", "heat_score.m5")
ES_SORT_ORDER = os.getenv("ES_SORT_ORDER", "desc")

# 定時任務間隔（秒）
# 若未指定單一定時間隔，將在 [3h,5h] 之間隨機
FETCH_INTERVAL_SECONDS = int(os.getenv("HOT_TOKEN_FETCH_INTERVAL_SECONDS", "60"))
FETCH_MIN_SECONDS = int(os.getenv("HOT_TOKEN_FETCH_MIN_SECONDS", str(3 * 3600)))
FETCH_MAX_SECONDS = int(os.getenv("HOT_TOKEN_FETCH_MAX_SECONDS", str(5 * 3600)))
DETAIL_MAX_TOKENS_PER_CYCLE = int(os.getenv("DETAIL_MAX_TOKENS_PER_CYCLE", "100"))
DETAIL_CONCURRENCY = int(os.getenv("DETAIL_CONCURRENCY", "10"))

# 本地/服務 API 設定（對 /api/tg_push_premium 發送）
API_SCHEME = os.getenv("API_SCHEME", "http")
API_HOST = os.getenv("API_HOST", "push-bot-api.chain")
API_PORT = int(os.getenv("API_PORT", "5011"))
API_PUSH_PATH = os.getenv("API_PUSH_PATH", "/api/tg_push_premium")

# 排除的代幣地址（原生、穩定幣、部分老幣等）
EXCLUDED_ADDRESSES = {
    # WSOL, SOL, USDC, USDT, JUP, USD1
    "So11111111111111111111111111111111111111112",
    "So11111111111111111111111111111111111111111",
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
    "27G8MtK7VtTcCHkpASjSDdkWWYfoqT6ggEuKidVJidD4",
    "USD1ttGY1N17NEEHLmELoaybftRBUSErhqYiQzvEmuB",
}

# 推送狀態（記憶體內維持）：每個地址已推送的最高等級，以及第一次推送時間
_push_lock: asyncio.Lock = asyncio.Lock()
_address_to_max_tier: Dict[str, int] = {}
_address_to_first_push_ts: Dict[str, float] = {}
_UNIQUE_TOKENS_PER_HOUR_LIMIT = int(os.getenv("UNIQUE_TOKENS_PER_HOUR_LIMIT", "2"))
RECENT_TOKEN_DAYS = int(os.getenv("RECENT_TOKEN_DAYS", "7"))
_inflight_addresses: Set[str] = set()
_push_gate_lock: asyncio.Lock = asyncio.Lock()
_next_push_earliest_ts: float = 0.0

# 推送抖動間隔（兩次推送之間的隨機間距），避免同時間集中推送
PUSH_MIN_INTERVAL_SECONDS = int(os.getenv("PUSH_MIN_INTERVAL_SECONDS", "60"))
PUSH_MAX_INTERVAL_SECONDS = int(os.getenv("PUSH_MAX_INTERVAL_SECONDS", "180"))
REFRESH_BEFORE_PUSH = os.getenv("REFRESH_BEFORE_PUSH", "1") == "1"

# 條件閥值（可用環境變數覆蓋）
# 新規則：
#  - 市值 ≥ 2M 且 5分成交筆數 ≥ 300 且 5分成交額 ≥ $80k
#  - 市值 ≥ 5M 且 5分成交筆數 ≥ 800 且 5分成交額 ≥ $150k
TIER1_TXNS = int(os.getenv("TIER1_TXNS", "300"))
TIER1_VOL_USD = float(os.getenv("TIER1_VOL_USD", "80000"))
TIER2_TXNS = int(os.getenv("TIER2_TXNS", "800"))
TIER2_VOL_USD = float(os.getenv("TIER2_VOL_USD", "150000"))
TIER3_TXNS = int(os.getenv("TIER3_TXNS", "800"))
TIER3_VOL_USD = float(os.getenv("TIER3_VOL_USD", "150000"))

# 背景任務引用
_scheduler_task: Optional[asyncio.Task] = None


def _build_search_url() -> str:
    return f"{ES_BASE_URL.rstrip('/')}/{ES_INDEX}/_search"


def _build_payload() -> Dict:
    return {
        "query": {"match_all": {}},
        "sort": [{ES_SORT_FIELD: {"order": ES_SORT_ORDER}}],
        "size": ES_QUERY_SIZE,
        "_source": [
            "symbol",
            "name",
            "address",
            "heat_score",
            "price_usd",
            "market_cap_usd",
        ],
    }


async def fetch_hot_tokens(session: aiohttp.ClientSession) -> List[Dict]:
    """查詢熱度表，返回 hits 陣列（保持原順序）。"""
    url = _build_search_url()
    payload = _build_payload()
    try:
        async with session.post(url, json=payload, auth=aiohttp.BasicAuth(ES_USERNAME, ES_PASSWORD), timeout=aiohttp.ClientTimeout(total=20)) as resp:
            if resp.status != 200:
                text = await resp.text()
                logger.error(f"查詢熱度表失敗: HTTP {resp.status}, body={text[:500]}")
                return []
            data = await resp.json()
            return data.get("hits", {}).get("hits", [])
    except Exception as e:
        logger.error(f"請求熱度表發生異常: {e}")
        return []


def _is_bsc_doc(doc_id: str) -> bool:
    return isinstance(doc_id, str) and doc_id.startswith("BSC_")


def _is_solana_doc(doc_id: str) -> bool:
    return isinstance(doc_id, str) and doc_id.startswith("SOLANA_")


def extract_solana_addresses(hits: List[Dict]) -> List[str]:
    """由熱度表 hits 依序萃取 SOLANA 的 address，跳過 BSC，並去重保持順序。"""
    addresses: List[str] = []
    seen: Set[str] = set()
    for item in hits:
        doc_id = item.get("_id", "")
        if _is_bsc_doc(doc_id):
            # 跳過 BSC
            continue
        if not _is_solana_doc(doc_id):
            # 目前只收集 SOLANA
            continue
        src = item.get("_source", {}) or {}
        address = src.get("address")
        if address:
            addr = str(address)
            if addr not in seen:
                seen.add(addr)
                addresses.append(addr)
    return addresses


async def get_top_solana_addresses(limit: Optional[int] = None) -> List[str]:
    """對外函數：取得按熱度排序的 SOLANA address 清單。"""
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        hits = await fetch_hot_tokens(session)
        addresses = extract_solana_addresses(hits)
        if limit is not None and limit > 0:
            return addresses[:limit]
        return addresses


def _build_detail_payload(address: str) -> Dict[str, Any]:
    # 依照用戶提供的查詢格式，按 address + network 精準查詢
    return {
        "query": {
            "bool": {
                "must": [
                    {"term": {"address": address}},
                    {"term": {"network": "SOLANA"}},
                ]
            }
        },
        "size": 1,
    }


async def fetch_token_detail(session: aiohttp.ClientSession, address: str) -> Optional[Dict[str, Any]]:
    """查詢單一 SOLANA token 詳細資料，返回 _source。失敗返回 None。"""
    url = _build_search_url()
    payload = _build_detail_payload(address)
    try:
        async with session.post(
            url,
            json=payload,
            auth=aiohttp.BasicAuth(ES_USERNAME, ES_PASSWORD),
            timeout=aiohttp.ClientTimeout(total=20),
        ) as resp:
            if resp.status != 200:
                text = await resp.text()
                logger.error(
                    f"查詢 token 詳情失敗: address={address}, HTTP {resp.status}, body={text[:300]}"
                )
                return None
            data = await resp.json()
            hits = data.get("hits", {}).get("hits", [])
            if not hits:
                return None
            return hits[0].get("_source") or None
    except Exception as e:
        logger.error(f"請求 token 詳情發生異常: address={address}, err={e}")
        return None


def _compute_market_cap_usd(src: Dict[str, Any]) -> float:
    market_cap = src.get("market_cap_usd")
    try:
        market_cap_val = float(market_cap) if market_cap is not None else 0.0
    except Exception:
        market_cap_val = 0.0
    if market_cap_val > 0:
        return market_cap_val
    # 次級回退：fdv_usd
    try:
        fdv_val = float(src.get("fdv_usd")) if src.get("fdv_usd") is not None else 0.0
    except Exception:
        fdv_val = 0.0
    if fdv_val > 0:
        return fdv_val
    # fallback = price_usd * total_supply
    price = src.get("price_usd")
    total_supply = src.get("total_supply")
    try:
        price_val = float(price) if price is not None else 0.0
    except Exception:
        price_val = 0.0
    try:
        supply_val = float(total_supply) if total_supply is not None else 0.0
    except Exception:
        supply_val = 0.0
    return price_val * supply_val


def _get_m5_total_txns(src: Dict[str, Any]) -> int:
    market_info = src.get("market_info") or {}
    val = market_info.get("m5_total_txns")
    try:
        return int(val) if val is not None else 0
    except Exception:
        try:
            return int(float(val))
        except Exception:
            return 0


def _get_m5_volume_usd(src: Dict[str, Any]) -> float:
    """嘗試從多個可能欄位讀取 5 分鐘成交額（美元）"""
    market_info = src.get("market_info") or {}
    candidate_keys = [
        "m5_volume_usd",
        "m5_total_usd",
        "m5_usd",
        "m5_volume",
        "m5_amount_usd",
    ]
    for key in candidate_keys:
        if key in market_info and market_info.get(key) is not None:
            try:
                return float(market_info.get(key) or 0)
            except Exception:
                continue
    return 0.0


def evaluate_token_tiers(src: Dict[str, Any]) -> List[str]:
    """依需求判斷三檔條件（市值 + 5分鐘成交筆數 + 5分鐘成交額），返回命中的 tier 名稱列表。"""
    # 僅評估最近 N 天內創建的代幣
    created_at_ms = src.get("created_at") or 0
    try:
        created_at_ms_val = int(created_at_ms)
    except Exception:
        created_at_ms_val = 0
    if created_at_ms_val <= 0:
        return []
    recent_window_ms = RECENT_TOKEN_DAYS * 24 * 3600 * 1000
    if (int(_now_ts() * 1000) - created_at_ms_val) > recent_window_ms:
        return []

    market_cap = _compute_market_cap_usd(src)
    m5_txns = _get_m5_total_txns(src)
    m5_volume = _get_m5_volume_usd(src)

    tiers = [
        ("TIER_1", 2_000_000, TIER1_TXNS, TIER1_VOL_USD),
        ("TIER_2", 5_000_000, TIER2_TXNS, TIER2_VOL_USD),
    ]
    matched: List[str] = []
    for name, cap_thr, tx_thr, vol_thr in tiers:
        if market_cap >= cap_thr and m5_txns >= tx_thr and m5_volume >= vol_thr:
            matched.append(name)
    return matched


def _tier_from_market_cap(market_cap: float) -> int:
    if market_cap >= 5_000_000:
        return 2
    if market_cap >= 2_000_000:
        return 1
    return 0


def _now_ts() -> float:
    return time.time()


def _within_last_hour(ts: float) -> bool:
    return (_now_ts() - ts) < 3600


async def _await_push_slot() -> None:
    """全局推送閘：確保推送之間存在隨機時間間距，讓時間軸更自然。"""
    global _next_push_earliest_ts
    wait_seconds = 0.0
    async with _push_gate_lock:
        now = _now_ts()
        if now < _next_push_earliest_ts:
            wait_seconds = _next_push_earliest_ts - now
        # 為下一次推送安排新的最早時間點（加入隨機抖動）
        interval = random.randint(
            min(PUSH_MIN_INTERVAL_SECONDS, PUSH_MAX_INTERVAL_SECONDS),
            max(PUSH_MIN_INTERVAL_SECONDS, PUSH_MAX_INTERVAL_SECONDS),
        )
        base = max(_next_push_earliest_ts, now)
        _next_push_earliest_ts = base + interval
    if wait_seconds > 0:
        await asyncio.sleep(wait_seconds)


async def _post_premium_push(session: aiohttp.ClientSession, payload: Dict[str, Any]) -> bool:
    url = f"{API_SCHEME}://{API_HOST}:{API_PORT}{API_PUSH_PATH}"
    try:
        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                return True
            text = await resp.text()
            logger.error(f"推送失敗: HTTP {resp.status}, body={text[:300]}")
            return False
    except Exception as e:
        logger.error(f"推送請求異常: {e}")
        return False


async def try_push_token(session: aiohttp.ClientSession, src: Dict[str, Any]) -> bool:
    address: str = src.get("address") or ""
    if not address or address in EXCLUDED_ADDRESSES:
        if address in EXCLUDED_ADDRESSES:
            logger.debug(f"推送跳過: address 在排除清單")
        return False

    # 可選：推送前刷新一次詳情，確保價格/市值使用最新數據
    if REFRESH_BEFORE_PUSH:
        try:
            latest = await fetch_token_detail(session, address)
            if latest:
                src = latest
        except Exception:
            pass

    market_cap = _compute_market_cap_usd(src)
    target_level = _tier_from_market_cap(market_cap)
    if target_level <= 0:
        logger.debug(
            f"推送跳過: 市值不足 address={address}, market_cap_usd={market_cap:.2f}"
        )
        return False

    # 新增：根據級別校驗 5 分鐘成交筆數與成交額
    m5_txns = _get_m5_total_txns(src)
    m5_volume = _get_m5_volume_usd(src)
    need = {
        1: (TIER1_TXNS, TIER1_VOL_USD),
        2: (TIER2_TXNS, TIER2_VOL_USD),
        3: (TIER3_TXNS, TIER3_VOL_USD),
    }
    req_txns, req_vol = need.get(target_level, (0, 0.0))
    if m5_txns < req_txns or m5_volume < req_vol:
        logger.debug(
            f"推送跳過: 5m條件不足 address={address}, level={target_level}, txns={m5_txns}/{req_txns}, vol=${m5_volume:.0f}/${req_vol:.0f}"
        )
        return False

    # 速率限制：1小時內最多推送2個不同代幣
    async with _push_lock:
        # 若該地址正在推送中，避免重複推送
        if address in _inflight_addresses:
            logger.debug(f"推送跳過: address={address} 正在推送中")
            return False
        # 清理過期的一小時窗口
        recent_tokens = [a for a, ts in _address_to_first_push_ts.items() if _within_last_hour(ts)]
        unique_recent = set(recent_tokens)

        # 升級策略：只能向更高等級推送；最高到2級
        prev_level = _address_to_max_tier.get(address, 0)
        if prev_level >= 2:
            logger.debug(f"推送跳過: 已達最高等級2 address={address}")
            return
        if target_level <= prev_level:
            logger.debug(
                f"推送跳過: 無升級 address={address}, prev_level={prev_level}, target_level={target_level}"
            )
            return

        # 如果從未推送過該地址，檢查 1 小時內的唯一代幣限制
        if address not in _address_to_first_push_ts:
            if len(unique_recent) >= _UNIQUE_TOKENS_PER_HOUR_LIMIT:
                # 超過速率限制，跳過本次
                logger.info(
                    f"推送跳過: 速率限制 一小時已推送 {len(unique_recent)} 個代幣，限制={_UNIQUE_TOKENS_PER_HOUR_LIMIT}，address={address}"
                )
                return False
            _address_to_first_push_ts[address] = _now_ts()

        # 準備 payload
        # 轉秒
        created_at_ms = src.get("created_at") or 0
        try:
            created_at_ms_val = int(created_at_ms)
        except Exception:
            created_at_ms_val = 0
        created_at_sec = created_at_ms_val // 1000 if created_at_ms_val > 0 else 0
        # 價格若缺失/為 0，傳遞 None 讓下游自行回退（避免顯示為 0）
        raw_price = src.get("price_usd")
        try:
            price_usd = float(raw_price) if raw_price not in (None, "", 0, 0.0, "0", "0.0") else None
        except Exception:
            price_usd = None

        payload = {
            "token_address": address,
            "chain": "SOLANA",
            "market_cap_level": target_level,
            "open_time": created_at_sec,
            "token_price": price_usd,
        }
        # 標記 in-flight，避免併發重複
        _inflight_addresses.add(address)

    # 發送推送（不在鎖內）
    # 全局節流：避免同時間集中推送
    await _await_push_slot()
    ok = await _post_premium_push(session, payload)
    # 解除 in-flight 並根據結果更新狀態
    async with _push_lock:
        _inflight_addresses.discard(address)
        if ok:
            _address_to_max_tier[address] = target_level
            logger.info(
                f"已推送: address={address}, level={target_level}, market_cap_usd={market_cap:.2f}"
            )
            return True
    return False


async def _scheduler_loop() -> None:
    """定時任務：週期性拉取 SOLANA address。"""
    logger.info(
        f"啟動熱度表定時任務：間隔隨機 {FETCH_MIN_SECONDS}~{FETCH_MAX_SECONDS}s，索引 {ES_INDEX}，排序 {ES_SORT_FIELD} {ES_SORT_ORDER}"
    )
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        while True:
            try:
                hits = await fetch_hot_tokens(session)
                addresses = extract_solana_addresses(hits)
                logger.info(
                    f"本次獲取 SOLANA tokens: {len(addresses)}，樣例: {addresses[:5]}"
                )

                # 批次並發處理：若前一批沒有任何成功推送，繼續往下掃描
                sem = asyncio.Semaphore(DETAIL_CONCURRENCY)

                async def process_address(addr: str) -> bool:
                    async with sem:
                        src = await fetch_token_detail(session, addr)
                    if not src:
                        return False
                    matched = evaluate_token_tiers(src)
                    if matched:
                        symbol = src.get("symbol") or ""
                        name = src.get("name") or ""
                        market_cap = _compute_market_cap_usd(src)
                        m5_txns = _get_m5_total_txns(src)
                        m5_volume = _get_m5_volume_usd(src)
                        logger.info(
                            f"命中條件: address={addr}, symbol={symbol}, name={name}, tiers={matched}, market_cap_usd={market_cap:.2f}, m5_total_txns={m5_txns}, m5_volume_usd={m5_volume:.0f}"
                        )
                    # 無論 evaluate 是否命中，最終以 try_push_token 的條件為準
                    pushed = await try_push_token(session, src)
                    return pushed

                # 逐批處理整個清單，直到本輪至少推送一個或全部掃完
                pushed_this_round = 0
                start_index = 0
                total = len(addresses)
                while start_index < total and pushed_this_round == 0:
                    batch = addresses[start_index:start_index + DETAIL_MAX_TOKENS_PER_CYCLE]
                    if not batch:
                        break
                    # 打亂處理順序，讓命中/推送時間更加隨機
                    random.shuffle(batch)
                    results = await asyncio.gather(*(process_address(a) for a in batch))
                    pushed_in_batch = sum(1 for r in results if r)
                    pushed_this_round += pushed_in_batch
                    start_index += DETAIL_MAX_TOKENS_PER_CYCLE

                if pushed_this_round == 0:
                    logger.info("本輪未找到符合推送條件的代幣，已掃描完整清單或達到批次上限")
            except Exception as e:
                logger.error(f"定時任務執行錯誤: {e}")
            # 每輪結束後在 3~5 小時（可用環境變數覆蓋）之間隨機等待
            next_sleep = random.randint(min(FETCH_MIN_SECONDS, FETCH_MAX_SECONDS), max(FETCH_MIN_SECONDS, FETCH_MAX_SECONDS))
            logger.info(f"下一輪抓取將在 {next_sleep} 秒後進行")
            await asyncio.sleep(next_sleep)


async def start_scheduler() -> None:
    """從其他模組啟動定時抓取任務（若已啟動則跳過）。"""
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        logger.info("熱度排程已在運行，跳過重複啟動")
        return
    _scheduler_task = asyncio.create_task(_scheduler_loop())
    logger.info("熱度排程已啟動 (background task)")


async def stop_scheduler() -> None:
    """停止定時抓取任務。"""
    global _scheduler_task
    if _scheduler_task:
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass
        _scheduler_task = None
        logger.info("熱度排程已停止")


def _setup_logging() -> None:
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO,
        handlers=[logging.StreamHandler()],
    )


if __name__ == "__main__":
    _setup_logging()
    try:
        asyncio.run(_scheduler_loop())
    except KeyboardInterrupt:
        logger.info("收到停止訊號，定時任務正在關閉...")

