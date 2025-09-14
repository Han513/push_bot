import os
import json
import logging
import aiohttp
from typing import Dict, List
from dotenv import load_dotenv

# 設置日誌
logger = logging.getLogger(__name__)

# 載入環境變數
load_dotenv(override=True)

# 從環境變量加載配置
SOCIALS_API_URL = os.getenv("SOCIALS_API_URL", "http://127.0.0.1:5002/admin/telegram/social/socials")

async def get_additional_channels() -> Dict[str, List[Dict[str, str]]]:
    """
    從社交API獲取額外的頻道信息
    返回格式: {
        "high_freq": [{"group_id": "xxx", "topic_id": "xxx", "language": "en"}, ...],
        "low_freq": [{"group_id": "xxx", "topic_id": "xxx", "language": "en"}, ...]
    }
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(SOCIALS_API_URL) as response:
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
                    social_group = user_data.get("socialGroup")
                    # 語言標準化：如 es_ES -> es；為空或 None 時使用 en
                    raw_lang = user_data.get("lang")
                    language = "en"
                    if raw_lang:
                        try:
                            language_part = str(raw_lang).split("_")[0].lower()
                            if language_part:
                                language = language_part
                        except Exception:
                            language = "en"
                    if not social_group:
                        continue
                        
                    for chat in user_data.get("chats", []):
                        if not chat.get("enable", False):
                            continue
                            
                        chat_name = chat.get("name", "")
                        chat_id = chat.get("chatId")
                        
                        if "WEB3 Signal - High Freq" in chat_name:
                            high_freq_channels.append({
                                "group_id": social_group,
                                "topic_id": chat_id,
                                "language": language
                            })
                        elif "WEB3 Signal – Low Freq" in chat_name:
                            low_freq_channels.append({
                                "group_id": social_group,
                                "topic_id": chat_id,
                                "language": language
                            })
                
                return {
                    "high_freq": high_freq_channels,
                    "low_freq": low_freq_channels
                }
    except Exception as e:
        logger.error(f"獲取額外頻道信息時發生錯誤: {e}")
        return {"high_freq": [], "low_freq": []} 