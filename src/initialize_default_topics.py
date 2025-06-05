import asyncio
import os
from telegram import Bot
from telegram.error import TelegramError
import logging

# 初始化 bot token（可用環境變數）
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7665966441:AAF0D8plssQQA2Ejf4FbZ8fAcHaqeMvgTkM")

# 替換成你的 LANGUAGE_GROUPS 結構
LANGUAGE_GROUPS = {
    "zh": {"low_freq_group_id": "-1002289327992", "low_freq_topic_id": "1"},
}

# 設定 logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def initialize_topic(bot: Bot, lang: str, group_id: str, topic_id: int):
    try:
        # await bot.send_message(
        #     chat_id=group_id,
        #     text=f"🔧 初始化預設主題 topic_id=1（語言: {lang}）",
        #     message_thread_id=topic_id,
        #     disable_notification=True
        # )
        await bot.send_message(
            chat_id='-1002289327992',
            text="測試訊息 from topic 1",
            message_thread_id=1
        )

        logger.info(f"[{lang}] ✅ topic_id=1 初始化成功")
    except TelegramError as e:
        logger.warning(f"[{lang}] ❌ topic_id=1 初始化失敗: {e}")


async def main():
    bot = Bot(token=BOT_TOKEN)
    tasks = []

    for lang, conf in LANGUAGE_GROUPS.items():
        group_id = conf["low_freq_group_id"]
        topic_id = int(conf["low_freq_topic_id"])
        tasks.append(initialize_topic(bot, lang, group_id, topic_id))

    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
