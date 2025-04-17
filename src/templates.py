# 在一個新的文件，例如 templates.py
import json
import os
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# 加載模板
def load_templates():
    """加載不同語言的消息模板"""
    templates = {
        "en": {
            "coin_announcement": (
                "🟢 [MOONX] 🟢 New Coin Alert / Activity Report 🪙 :\n"
                "├ ${token_symbol} - {chain}\n"
                "├ {token_address}\n"
                "💊 Current Market Cap：{market_cap_display}\n"
                # ... 英文模板內容
            )
        },
        "ko": {
            "coin_announcement": (
                "🟢 [MOONX] 🟢 새 코인 알림 / 활동 보고서 🪙 :\n"
                "├ ${token_symbol} - {chain}\n"
                "├ {token_address}\n"
                "💊 현재 시가총액：{market_cap_display}\n"
                # ... 韓文模板內容
            )
        },
        "zh": {
            "coin_announcement": (
                "🟢 [MOONX] 🟢 新币上线 / 异动播报 🪙 :\n"
                "├ ${token_symbol} - {chain}\n"
                "├ {token_address}\n"
                "💊 当前市值：{market_cap_display}\n"
                # ... 中文模板內容
            )
        }
    }
    return templates

def format_message(data: Dict, language: str = "zh") -> str:
    """將加密貨幣數據格式化為消息，支持多語言"""
    # 加載多語言模板
    templates = {
        "zh": {
            "title": "🟢 [MOONX] 🟢 新币上线 / 异动播报 🪙  :",
            "token_info": "├ ${0} - {1}\n├ {2}",
            "market_cap": "💊 当前市值：{0}",
            "price": "💰 当前价格：$ {0}",
            "holders": "👬 持币人：{0}",
            "launch_time": "⏳ 开盘时间： [{0}]",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 链上监控",
            "smart_money": "聪明钱 {0} 笔买入 (15分钟内)",
            "contract_security": "合约安全：",
            "security_item": "- 权限：[{0}]  貔貅: [{1}]  烧池子 [{2}]  黑名单 [{3}]",
            "dev_info": "💰 开发者：",
            "dev_status": "- {0}",
            "dev_balance": "- 开发者余额：{0} SOL",
            "top10_holding": "- Top10占比：{0}%",
            "social_info": "🌐 社交与工具",
            "social_links": "{0}",
            "community_tips": "🚨 MOONX 社区提示\n- 防范Rug Pull，务必验证合约权限与流动性锁仓。\n- 关注社区公告，欢迎分享观点与资讯。"
        },
        "en": {
            "title": "🟢 [MOONX] 🟢 New Coin Listing / Activity Alert 🪙  :",
            "token_info": "├ ${0} - {1}\n├ {2}",
            "market_cap": "💊 Current Market Cap: {0}",
            "price": "💰 Current Price: $ {0}",
            "holders": "👬 Holders: {0}",
            "launch_time": "⏳ Launch Time: [{0}]",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 On-Chain Monitoring",
            "smart_money": "Smart Money {0} buys (within 15 minutes)",
            "contract_security": "Contract Security:",
            "security_item": "- Authority: [{0}]  Rug Pull: [{1}]  Burn LP: [{2}]  Blacklist: [{3}]",
            "dev_info": "💰 Developer:",
            "dev_status": "- {0}",
            "dev_balance": "- Developer Balance: {0} SOL",
            "top10_holding": "- Top10 Holdings: {0}%",
            "social_info": "🌐 Social & Tools",
            "social_links": "{0}",
            "community_tips": "🚨 MOONX Community Tips\n- Prevent Rug Pulls by verifying contract permissions and liquidity locks.\n- Stay updated with community announcements and share your insights."
        },
        "ko": {
            "title": "🟢 [MOONX] 🟢 새 코인 상장 / 활동 알림 🪙  :",
            "token_info": "├ ${0} - {1}\n├ {2}",
            "market_cap": "💊 현재 시가총액: {0}",
            "price": "💰 현재 가격: $ {0}",
            "holders": "👬 홀더 수: {0}",
            "launch_time": "⏳ 출시 시간: [{0}]",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 온체인 모니터링",
            "smart_money": "스마트 머니 {0}건 구매 (15분 이내)",
            "contract_security": "컨트랙트 보안:",
            "security_item": "- 권한: [{0}]  러그풀: [{1}]  LP소각: [{2}]  블랙리스트: [{3}]",
            "dev_info": "💰 개발자:",
            "dev_status": "- {0}",
            "dev_balance": "- 개발자 잔액: {0} SOL",
            "top10_holding": "- 상위10 보유율: {0}%",
            "social_info": "🌐 소셜 및 도구",
            "social_links": "{0}",
            "community_tips": "🚨 MOONX 커뮤니티 팁\n- 컨트랙트 권한 및 유동성 잠금을 확인하여 러그풀을 방지하세요.\n- 커뮤니티 공지를 확인하고 인사이트를 공유하세요."
        }
    }
    
    # 如果沒有該語言的模板，使用默認語言
    if language not in templates:
        language = "zh"  # 默認使用中文
    
    try:
        contract_security = json.loads(data.get('contract_security', '{}'))
        socials = json.loads(data.get('socials', '{}'))
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"JSON 解析錯誤: {e}")
        contract_security = {}
        socials = {}

    # 安全項目格式化
    security_status = templates[language]["security_item"].format(
        '✅' if contract_security.get('authority', False) else '❌',
        '✅' if contract_security.get('rug_pull', False) else '❌',
        '✅' if contract_security.get('burn_pool', False) else '❌',
        '✅' if contract_security.get('blacklist', False) else '❌'
    )

    # 構建推特搜索鏈接 - 根據語言可能有不同的文本
    token_address = data.get('token_address', '')
    twitter_search_url = f"https://x.com/search?q={token_address}&src=typed_query"
    
    # 社交媒體文本 - 根據語言調整
    twitter_text = {"zh": "推特", "en": "Twitter", "ko": "트위터"}
    website_text = {"zh": "官网", "en": "Website", "ko": "웹사이트"}
    telegram_text = {"zh": "电报", "en": "Telegram", "ko": "텔레그램"}
    search_text = {"zh": "👉查推特", "en": "👉Search Twitter", "ko": "👉트위터 검색"}
    
    # 構建社交媒體鏈接
    twitter_part = f"{twitter_text[language]}❌"
    if socials.get('twitter', False) and socials.get('twitter_url'):
        twitter_part = f"<a href='{socials['twitter_url']}'>{twitter_text[language]}✅</a>"

    website_part = f"{website_text[language]}❌"
    if socials.get('website', False) and socials.get('website_url'):
        website_part = f"<a href='{socials['website_url']}'>{website_text[language]}✅</a>"

    telegram_part = f"{telegram_text[language]}{'✅' if socials.get('telegram', False) else '❌'}"
    twitter_search_link = f"<a href='{twitter_search_url}'>{search_text[language]}</a>"

    socials_str = f"🔗 {twitter_part} || {website_part} || {telegram_part} || {twitter_search_link}"

    # 開發者狀態行
    dev_status_line = ""
    if data.get('dev_status_display') and data.get('dev_status_display') != '--':
        dev_status_line = templates[language]["dev_status"].format(data.get('dev_status_display')) + "\n"

    # 構建可複製的 token_address
    copyable_address = f"<code>{token_address}</code>"
    
    # 使用模板構建消息
    template = templates[language]
    
    message_parts = [
        template["title"],
        template["token_info"].format(data.get('token_symbol', 'Unknown'), data.get('chain', 'Unknown'), copyable_address),
        template["market_cap"].format(data.get('market_cap_display', '--')),
        template["price"].format(data.get('price_display', '--')),
        template["holders"].format(data.get('holders_display', '--')),
        template["launch_time"].format(data.get('launch_time_display', '--')),
        template["divider"],
        template["chain_monitoring"],
        template["smart_money"].format(data.get('total_addr_amount', '0')),
        template["contract_security"],
        security_status,
        template["dev_info"],
        dev_status_line,
        template["dev_balance"].format(data.get('dev_wallet_balance_display', '--')),
        template["top10_holding"].format(data.get('top10_holding_display', '--')),
        template["social_info"],
        socials_str,
        template["divider"],
        template["community_tips"]
    ]
    
    # 將所有部分連接成完整消息
    message = "\n".join(message_parts)
    return message