import os
import json
import asyncio
import logging
from typing import Optional

import aiohttp
from aiokafka import AIOKafkaConsumer
from dotenv import load_dotenv
from logging_setup import setup_logging


load_dotenv(override=True)
setup_logging()
logger = logging.getLogger(__name__)


# Kafka 配置（使用環境變數可覆蓋）
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
_topics_env = os.getenv("KAFKA_TOPICS") or os.getenv("KAFKA_TOPIC") or "web3_trade_events"
KAFKA_TOPICS = [t.strip() for t in _topics_env.split(",") if t.strip()]
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "byd-high-freq-consumer")
KAFKA_SECURITY_PROTOCOL = os.getenv("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT")  # 或 SASL_SSL
KAFKA_SASL_MECHANISM = os.getenv("KAFKA_SASL_MECHANISM")  # e.g. PLAIN
KAFKA_SASL_USERNAME = os.getenv("KAFKA_SASL_USERNAME")
KAFKA_SASL_PASSWORD = os.getenv("KAFKA_SASL_PASSWORD")
KAFKA_AUTO_OFFSET_RESET = os.getenv("KAFKA_AUTO_OFFSET_RESET", "latest")

# 需要關注的事件 type
TARGET_EVENT_TYPE = "com.zeroex.web3.core.event.data.PoolMigrateEvent"

# API 配置（複用本地 API 的端口）
API_SCHEME = os.getenv("API_SCHEME", "http")
API_HOST = os.getenv("API_HOST", "push-bot-api.chain")
API_PORT = int(os.getenv("API_PORT", "5011"))


_consumer_task: Optional[asyncio.Task] = None


async def _post_tg_push(session: aiohttp.ClientSession, token_address: str, network: str) -> None:
    url = f"{API_SCHEME}://{API_HOST}:{API_PORT}/api/tg_push"
    payload = {"token_address": token_address, "chain": network}
    try:
        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                text = await resp.text()
                logger.error(f"tg_push 失敗: HTTP {resp.status}, body={text[:300]}")
            else:
                logger.info(f"已提交高頻推送請求: {token_address} ({network})")
    except Exception as e:
        logger.error(f"請求 /api/tg_push 異常: {e}")


def _build_consumer(loop: asyncio.AbstractEventLoop) -> AIOKafkaConsumer:
    kwargs = {
        "loop": loop,
        "bootstrap_servers": KAFKA_BOOTSTRAP_SERVERS,
        "group_id": KAFKA_GROUP_ID,
        "enable_auto_commit": True,
        "auto_offset_reset": KAFKA_AUTO_OFFSET_RESET,
        "security_protocol": KAFKA_SECURITY_PROTOCOL,
    }
    if KAFKA_SECURITY_PROTOCOL.upper() != "PLAINTEXT":
        if KAFKA_SASL_MECHANISM:
            kwargs["sasl_mechanism"] = KAFKA_SASL_MECHANISM
        if KAFKA_SASL_USERNAME is not None:
            kwargs["sasl_plain_username"] = KAFKA_SASL_USERNAME
        if KAFKA_SASL_PASSWORD is not None:
            kwargs["sasl_plain_password"] = KAFKA_SASL_PASSWORD
    return AIOKafkaConsumer(*KAFKA_TOPICS, **kwargs)


async def _consume_loop() -> None:
    while True:
        loop = asyncio.get_running_loop()
        consumer = _build_consumer(loop)
        try:
            await consumer.start()
            logger.info(
                f"Kafka 高頻消費啟動：topics={KAFKA_TOPICS}, group={KAFKA_GROUP_ID}, servers={KAFKA_BOOTSTRAP_SERVERS}"
            )

            http_timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=http_timeout) as session:
                async for msg in consumer:
                    try:
                        payload = msg.value
                        if isinstance(payload, (bytes, bytearray)):
                            payload = payload.decode("utf-8", errors="ignore")
                        data = json.loads(payload)

                        event = data.get("event") or data
                        event_type = event.get("type") or data.get("type")
                        if event_type != TARGET_EVENT_TYPE:
                            continue

                        token_address = (
                            (event.get("tokenAddress") or event.get("token_address") or "").strip()
                        )
                        network = (event.get("network") or "").strip() or "SOLANA"
                        if not token_address:
                            continue

                        logger.info(
                            f"收到 PoolMigrateEvent: token={token_address}, network={network}, partition={msg.partition}, offset={msg.offset}"
                        )
                        await _post_tg_push(session, token_address, network)
                    except json.JSONDecodeError:
                        logger.warning("忽略不可解析的消息負載（非 JSON）")
                    except Exception as e:
                        logger.error(f"處理消息異常: {e}")
        except asyncio.CancelledError:
            # 任務被取消，正常退出
            raise
        except Exception as e:
            logger.error(f"高頻消費循環發生異常，3秒後重啟: {e}", exc_info=True)
        finally:
            try:
                await consumer.stop()
                logger.info("Kafka 高頻消費已停止")
            except Exception:
                pass
        await asyncio.sleep(3)


async def start_kafka_consumer() -> None:
    global _consumer_task
    if _consumer_task and not _consumer_task.done():
        logger.info("Kafka 高頻消費任務已在運行，跳過啟動")
        return
    _consumer_task = asyncio.create_task(_consume_loop())
    logger.info("Kafka 高頻消費任務已啟動 (background task)")


async def stop_kafka_consumer() -> None:
    global _consumer_task
    if _consumer_task:
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass
        _consumer_task = None
        logger.info("Kafka 高頻消費任務已停止")


