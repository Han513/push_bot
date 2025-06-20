import os
import logging
import asyncio
from typing import Dict, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.sql import text
from sqlalchemy.future import select
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# 設置日誌
logger = logging.getLogger(__name__)

# 初始化資料庫
Base = declarative_base()

# 時區設置
TZ_UTC8 = timezone(timedelta(hours=8))

_wallets_cache = {
    "kol_wallets": set(),                  # KOL地址集合
    "smart_wallets": set(),                # 一般聰明錢地址集合 (is_smart_wallet=True)
    "high_value_smart_wallets": set(),     # 高淨值聰明錢地址集合 (is_smart_wallet=True and win_rate_30d>70)
    "smart_wallets_win_rate": {},          # address: win_rate_30d 字典
    "last_update": None
}
_CACHE_EXPIRE_SECONDS = 24 * 60 * 60  # 24小時

def get_utc8_time():
    """獲取 UTC+8 當前時間"""
    return datetime.now(TZ_UTC8).replace(tzinfo=None)

class PushHistory(Base):
    __tablename__ = 'push_history'
    __table_args__ = {'schema': 'dex_query_v1'}

    id = Column(Integer, primary_key=True, comment='ID')
    message_content = Column(Text, nullable=False, comment='推送消息內容')
    chat_ids = Column(Text, nullable=False, comment='推送到的頻道 ID 列表（JSON 格式）')
    push_time = Column(DateTime, nullable=False, default=get_utc8_time, comment='推送時間')
    crypto_id = Column(Integer, nullable=True, comment='關聯的加密貨幣資訊 ID')
    status = Column(String(50), nullable=False, default='success', comment='推送狀態（success/failed）')
    error_message = Column(Text, nullable=True, comment='錯誤訊息（如果推送失敗）')

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class CryptoInfo(Base):
    __tablename__ = 'crypto_info'
    __table_args__ = {'schema': 'dex_query_v1'}

    id = Column(Integer, primary_key=True, comment='ID')
    token_name = Column(String(255), nullable=False, comment='代幣名稱')
    chain = Column(String(50), nullable=False, comment='區塊鏈類型')
    contract_address = Column(String(255), nullable=False, comment='合約地址')
    market_cap = Column(Float, nullable=True, comment='當前市值 (USD)')
    price = Column(Float, nullable=True, comment='當前價格 (USD)')
    holders = Column(Integer, nullable=True, comment='持幣人數')
    launch_time = Column(DateTime, nullable=True, comment='開盤時間')
    smart_money_activity = Column(String(255), nullable=True, comment='聰明錢動向')
    contract_security = Column(Text, nullable=True, comment='合約安全資訊（JSON 格式）')
    top10_holding = Column(Float, nullable=True, comment='Top10 持幣占比 (%)')
    dev_holding_at_launch = Column(Float, nullable=True, comment='開發者開盤持幣量 (%)')
    dev_holding_current = Column(Float, nullable=True, comment='開發者當前持幣量 (%)')
    dev_wallet_balance = Column(Float, nullable=True, comment='開發者錢包餘額 (SOL)')
    socials = Column(Text, nullable=True, comment='社交媒體資訊（JSON 格式）')
    created_at = Column(DateTime, nullable=False, default=get_utc8_time, comment='創建時間')
    updated_at = Column(DateTime, nullable=False, default=get_utc8_time, onupdate=get_utc8_time, comment='更新時間')

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
    
class Wallet(Base):
    __tablename__ = 'wallet'
    __table_args__ = {'schema': 'dex_query_v1'}

    id = Column(Integer, primary_key=True, comment='ID')
    address = Column(String(100), nullable=False, unique=True, comment='錢包地址')
    balance = Column(Float, nullable=True, comment='錢包餘額')
    balance_USD = Column(Float, nullable=True, comment='錢包餘額 (USD)')
    chain = Column(String(50), nullable=False, comment='區塊鏈類型')
    tag = Column(String(50), nullable=True, comment='標籤')
    twitter_name = Column(String(50), nullable=True, comment='X名稱')
    twitter_username = Column(String(50), nullable=True, comment='X用戶名')
    is_smart_wallet = Column(Boolean, nullable=True, comment='是否為聰明錢包')
    wallet_type = Column(Integer, nullable=True, comment='0:一般聰明錢，1:pump聰明錢，2:moonshot聰明錢')
    asset_multiple = Column(Float, nullable=True, comment='資產翻倍數(到小數第1位)')
    token_list = Column(Text, nullable=True, comment='用户最近交易的三种代币信息')
    win_rate_30d = Column(Float, nullable=True, comment='30日勝率') 
    update_time = Column(DateTime, nullable=False, default=get_utc8_time, comment='更新時間')
    last_transaction_time = Column(Integer, nullable=True, comment='最後活躍時間')
    is_active = Column(Boolean, nullable=True, comment='是否還是聰明錢')

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

# 全局變數
engine = None
Session = None

# 資料庫初始化函數
def init_db(database_uri):
    """初始化數據庫連接"""
    global engine, Session
    
    # 創建資料庫引擎
    engine = create_async_engine(database_uri, echo=False, future=True)
    
    # 創建會話工廠
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    logger.info("初始化數據庫完成")
    return engine, Session

# 獲取會話的函數
async def get_session():
    """獲取一個新的數據庫會話"""
    async_session = Session()
    return async_session

# 資料庫表創建函數
async def create_schema_if_not_exists():
    """創建 schema 如果不存在"""
    schema_name = 'tg_smartmoney'
    
    async with engine.connect() as conn:
        # 檢查 schema 是否存在
        result = await conn.execute(text(f"SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = '{schema_name}')"))
        schema_exists = result.scalar()
        
        if not schema_exists:
            logger.info(f"創建 schema '{schema_name}'")
            await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
            await conn.commit()
            logger.info(f"Schema '{schema_name}' 已創建")
        else:
            logger.info(f"Schema '{schema_name}' 已存在")

async def create_tables():
    """創建所有資料表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("所有資料表已創建")

async def add_crypto_info(session, crypto_data: Dict) -> Optional[int]:
    """將加密貨幣資訊添加到資料庫並返回 ID"""
    try:
        await session.execute(text("SET search_path TO dex_query_v1;"))
        # 處理 launch_time
        launch_time = crypto_data.get("launch_time")
        if isinstance(launch_time, str):
            try:
                # 嘗試將日期字符串轉換為 datetime 對象
                launch_time = datetime.strptime(launch_time, "%Y.%m.%d %H:%M:%S")
            except ValueError:
                launch_time = None
        
        new_crypto = CryptoInfo(
            token_name=crypto_data.get("token_symbol", ""),
            chain=crypto_data.get("chain", ""),
            contract_address=crypto_data.get("contract_address", ""),
            market_cap=crypto_data.get("market_cap", 0.0),
            price=crypto_data.get("price", 0.0),
            holders=crypto_data.get("holders", 0),
            launch_time=launch_time,
            smart_money_activity=crypto_data.get("smart_money_activity", ""),
            contract_security=crypto_data.get("contract_security", "{}"),
            top10_holding=crypto_data.get("top10_holding", 0.0),
            dev_holding_at_launch=crypto_data.get("dev_holding_at_launch", 0.0),
            dev_holding_current=crypto_data.get("dev_holding_current", 0.0),
            dev_wallet_balance=crypto_data.get("dev_wallet_balance", 0.0),
            socials=crypto_data.get("socials", "{}"),
            created_at=get_utc8_time(),
            updated_at=get_utc8_time()
        )
        session.add(new_crypto)
        await session.flush()  # 確保 ID 被生成
        logger.info(f"添加加密貨幣資訊: {crypto_data['token_symbol']}")
        return new_crypto.id
    except Exception as e:
        logger.error(f"添加加密貨幣資訊時發生錯誤: {str(e)}")
        return None

async def add_push_history(session, message_content: str, chat_ids: str, crypto_id: int = None, status: str = "success", error_message: str = None) -> bool:
    """記錄推送歷史"""
    try:
        new_history = PushHistory(
            message_content=message_content,
            chat_ids=chat_ids,
            crypto_id=crypto_id,
            push_time=get_utc8_time(),
            status=status,
            error_message=error_message
        )
        session.add(new_history)
        logger.info(f"添加推送歷史記錄，加密貨幣 ID: {crypto_id}")
        return True
    except Exception as e:
        logger.error(f"添加推送歷史時發生錯誤: {str(e)}")
        return False
    
async def refresh_wallets_cache():
    """從資料庫查詢KOL、一般聰明錢、高淨值聰明錢，並更新快取"""
    async with await get_session() as session:
        await session.execute(text("SET search_path TO dex_query_v1;"))
        result = await session.execute(
            select(Wallet.address).where(Wallet.tag == 'kol')
        )
        kol_wallets = set(row[0] for row in result.fetchall())
        # 查所有聰明錢
        result = await session.execute(
            select(Wallet.address, Wallet.win_rate_30d).where(Wallet.is_smart_wallet == True)
        )
        smart_wallets = {row[0]: row[1] for row in result.fetchall()}
        # 高淨值聰明錢
        high_value_smart_wallets = set(addr for addr, win_rate in smart_wallets.items() if win_rate and win_rate > 70)
    # 更新快取
    print(f"更新快取: {len(kol_wallets)}, {len(smart_wallets)}, {len(high_value_smart_wallets)}")
    _wallets_cache["kol_wallets"] = kol_wallets
    _wallets_cache["smart_wallets"] = set(smart_wallets.keys())
    _wallets_cache["high_value_smart_wallets"] = high_value_smart_wallets
    _wallets_cache["smart_wallets_win_rate"] = smart_wallets  # address: win_rate
    _wallets_cache["last_update"] = datetime.now()

async def get_cached_wallets(force_refresh=False):
    """獲取KOL、一般聰明錢、高淨值聰明錢快取，必要時自動刷新"""
    now = datetime.now()
    if (
        force_refresh or
        _wallets_cache["last_update"] is None or
        (now - _wallets_cache["last_update"]).total_seconds() > _CACHE_EXPIRE_SECONDS
    ):
        await refresh_wallets_cache()
    return (
        _wallets_cache["kol_wallets"],
        _wallets_cache["smart_wallets"],
        _wallets_cache["high_value_smart_wallets"],
        _wallets_cache["smart_wallets_win_rate"]
    )

async def main():
    """主函數，用於初始化資料庫和創建表"""
    
    # 從環境變數獲取資料庫 URI
    database_uri = os.getenv("DATABASE_URI_TELEGRAM")
    if not database_uri:
        logger.error("未設置 DATABASE_URI_TELEGRAM 環境變數")
        return
    
    print("初始化資料庫")
    # 初始化資料庫連接
    init_db(database_uri)
    
    # 創建 schema 和表
    await create_schema_if_not_exists()
    await create_tables()
    
    print("資料庫初始化完成，所有表已創建")

# 在模塊導入時初始化資料庫
load_dotenv(override=True)
database_uri = os.getenv("DATABASE_URI_TELEGRAM")
if database_uri:
    init_db(database_uri)
else:
    logger.error("未設置 DATABASE_URI_TELEGRAM 環境變數")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())