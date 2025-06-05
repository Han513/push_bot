# 在一個新的文件，例如 templates.py
import json
import os
import logging
from typing import Dict, Optional
import time

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
            ),
            "trade_button": "⚡️One-Click Trade⬆️",
            "chart_button": "👉View Chart⬆️"
        },
        "ko": {
            "coin_announcement": (
                "🟢 [MOONX] 🟢 새 코인 알림 / 활동 보고서 🪙 :\n"
                "├ ${token_symbol} - {chain}\n"
                "├ {token_address}\n"
                "💊 현재 시가총액：{market_cap_display}\n"
                # ... 韓文模板內容
            ),
            "trade_button": "⚡️원클릭 거래⬆️",
            "chart_button": "👉차트 보기⬆️"
        },
        "zh": {
            "coin_announcement": (
                "🟢 [MOONX] 🟢 新幣上線 / 異動播報 🪙 :\n"
                "├ ${token_symbol} - {chain}\n"
                "├ {token_address}\n"
                "💊 當前市值：{market_cap_display}\n"
                # ... 中文模板內容
            ),
            "trade_button": "⚡️一鍵交易⬆️",
            "chart_button": "👉查看K線⬆️"
        },
        "ch": {
            "title": "🟢 [MoonX] 🟢 新幣上線 / 異動播報 🪙 ：",
            "token_info": "├ ${0} ({1}) - {2}",
            "market_cap": "💊 當前市值：{0}",
            "price": "💰 當前價格：{0}",
            "holders": "👬 持幣人數：{0}",
            "launch_time": "⏳ 開盤時間：[{0}]",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 鏈上監控",
            "smart_money": "🤏 聰明錢動向：15 分鐘內有 {0} 筆聰明錢交易",
            "contract_security": "代幣檢測：",
            "security_item": "• 權限：[{0}] 貔貅：[{1}] 燒池子：[{2}] 黑明單：[{3}]",
            "dev_info": "開發者：",
            "dev_status": "• 開盤持有量：{0}",
            "dev_balance": "• 開發者錢包餘額：{0} SOL",
            "top10_holding": "• Top10 占比：{0}%",
            "social_info": "相關：",
            "social_links": "🔗 推特博主：{0} || 官方網站：{1} || 電報群：{2} || 推特搜尋：{3}",
            "community_tips": "⚠️ 風險提示：\n• 加密貨幣投資風險極高，請務必DYOR (Do Your Own Research)\n• 請勿FOMO (Fear of Missing Out)，理性投資\n• 請小心Rug Pull (捲款跑路) 及其他詐騙行為\nMoonX 社群提醒：\n• 請關注社群公告，掌握最新資訊\n• 歡迎在社群中分享您的觀點與分析",
            "trade_button": "⚡️一鍵交易⬆️",
            "chart_button": "👉查看K線⬆️"
        },
        "ru": {
            "title": "🟢 [MoonX] 🟢 Новая монета / Рыночное уведомление 🪙:",
            "token_info": "├ ${0} ({1}) – {2}",
            "market_cap": "💊 Рыночная капитализация: {0}",
            "price": "💰 Текущая цена: {0}",
            "holders": "👬 Владельцев: {0}",
            "launch_time": "⏳ Время запуска: [{0}]",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 Мониторинг блокчейна",
            "smart_money": "🤏 Активность смарт-денег: {0} сделки за последние 15 минут",
            "contract_security": "Аудит:",
            "security_item": "• Права: [{0}] Ханипот: [{1}] Пул сжигания: [{2}] Чёрный список: [{3}]",
            "dev_info": "Информация о разработчике:",
            "dev_status": "• Первоначальные активы: {0}",
            "dev_balance": "• Баланс кошелька разработчика: {0} SOL",
            "top10_holding": "• Доля топ-10 держателей: {0}%",
            "social_info": "Ссылки:",
            "social_links": "🔗 Twitter-инфлюенсер: {0} || Офиц. сайт: {1} || Telegram: {2} || Поиск в X: {3}",
            "community_tips": "⚠️ Предупреждение о рисках:\n • Инвестиции в криптовалюты крайне рискованны. Всегда проводите собственный анализ (DYOR)\n • Избегайте FOMO (Fear of Missing Out) – инвестируйте обдуманно\n • Будьте осторожны с Rug Pull и другими мошенническими схемами\nСообщество MoonX напоминает:\n • Следите за новостями в чате для актуальных обновлений\n • Делитесь своим мнением и аналитикой в группе",
            "trade_button": "⚡️Быстрая Торговля⬆️",
            "chart_button": "👉Проверить График⬆️"
        },
        "id": {
            "title": "🟢 [MoonX] 🟢 Listing Baru / Peringatan Pasar🪙:",
            "token_info": "├ ${0} ({1}) – {2}",
            "market_cap": "💊 Mcap Saat Ini: {0}",
            "price": "💰 Harga Saat Ini: {0}",
            "holders": "👬 Holder: {0}",
            "launch_time": "⏳ Waktu Mulai: [{0}]",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 Pemantauan On-chain",
            "smart_money": "🤏 Tren Smart Money: {0} perdagangan smart money dalam 15 menit terakhir",
            "contract_security": "Audit:",
            "security_item": "• Izin: [{0}] Honeypot: [{1}] Burn Pool: [{2}] Daftar Hitam: [{3}]",
            "dev_info": "Info Pengembang:",
            "dev_status": "• Kepemilikan Awal: {0}",
            "dev_balance": "• Saldo Dompet Pengembang: {0} SOL",
            "top10_holding": "• Pembagian Top 10 Holder : {0}%",
            "social_info": "Terkait:",
            "social_links": "🔗 Twitter Influencer: {0} || Situs Web Resmi: {1} || Telegram: {2} || Search X: {3}",
            "community_tips": "⚠️ Peringatan Risiko:\n• Investasi aset kripto sangat berisiko. Selalu DYOR (Do Your Own Research)\n• Hindari FOMO (Fear of Missing Out) - Berinvestasi secara rasional\n• Waspada terhadap Rug Pulls dan taktik penipuan lainnya\nPengingat Komunitas MoonX:\n• Nantikan pengumuman komunitas untuk pembaruan terbaru\n• Jangan ragu untuk membagikan insight dan analisis Anda di grup",
            "trade_button": "⚡️Perdagangan Cepat⬆️",
            "chart_button": "👉Lihat Grafik⬆️"
        },
        "ja": {
            "title": "🟢【MoonX】🟢 新規上場 / マーケットアラート 🪙",
            "token_info": "├ ${0}（{1}）– {2}",
            "market_cap": "💊 現在の時価総額：{0}",
            "price": "💰 現在価格：{0}",
            "holders": "👬 保有者数：{0}人",
            "launch_time": "⏳ 開始日時：［{0}］",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 オンチェーン監視",
            "smart_money": "🤏 スマートマネーの動向：過去15分間にスマートマネーによる取引が{0}件",
            "contract_security": "セキュリティ監査：",
            "security_item": " • パーミッション（許可）：[{0}] ハニーポット：[{1}]焼却プール：[{2}]ブラックリスト：[{3}]",
            "dev_info": "開発者情報：",
            "dev_status": "• 初期保有率：{0}",
            "dev_balance": "• 開発者ウォレット残高：{0} SOL",
            "top10_holding": "• トップ10ホルダーの保有率：{0}%",
            "social_info": "関連リンク：",
            "social_links": "🔗 Twitterインフルエンサー：{0} || 公式サイト：{1} ||  Telegram：{2} ||  X（旧Twitter）で検索 {3}",
            "community_tips": "⚠️ リスク警告：\n • 仮想通貨投資は非常に高リスクです。必ずご自身で調査（DYOR）を行ってください\n • FOMO（乗り遅れる恐怖）に注意して、冷静に投資を行いましょう\n • ラグプル（詐欺的な資金引き抜き）やその他の詐欺手口にも注意\nMoonXコミュニティからのリマインダー：\n • 最新情報はコミュニティの発表をチェック！\n • ご自身の分析や見解も、グループで気軽にシェアしてください",
            "trade_button": "⚡️クイック取引⬆️",
            "chart_button": "👉チャート確認⬆️"
        },
        "pt": {
            "title": "🟢 [MoonX] 🟢 Nova Listagem / Alerta de Mercado 🪙",
            "token_info": "├ ${0} ({1}) – {2}",
            "market_cap": "💊 Valor de Mercado Atual: {0}",
            "price": "💰 Preço Atual: {0}",
            "holders": "👬 Detentores: {0}",
            "launch_time": "⏳ Início: [{0}]",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 Monitoramento On-chain",
            "smart_money": "🤏 Tendência de Smart Money: {0} transações de smart money nos últimos 15 minutos",
            "contract_security": "Audit:",
            "security_item": "• Permissões: [{0}] Honeypot: [{1}] Pool de Queima: [{2}] Lista Negra: [{3}]",
            "dev_info": "Informações do Desenvolvedor:",
            "dev_status": "• Participação Inicial: {0}",
            "dev_balance": "• Saldo da Carteira Dev: {0} SOL",
            "top10_holding": "• Participação dos 10 Maiores Detentores: {0}%",
            "social_info": "Relacionados:",
            "social_links": "🔗 Influenciador no Twitter: {0} || Site Oficial: {1} || Telegram: {2} || Buscar no X: {3}",
            "community_tips": "⚠️ Aviso de Risco:\n • Investimentos em criptomoedas são extremamente arriscados. Sempre faça sua própria pesquisa (DYOR)\n • Evite o FOMO (medo de ficar de fora) – Invista com racionalidade\n • Fique atento a rug pulls e outras táticas de golpe\nLembrete da Comunidade MoonX:\n • Acompanhe os anúncios da comunidade para as atualizações mais recentes\n • Sinta-se à vontade para compartilhar suas análises e opiniões no grupo",
            "trade_button": "⚡️Comércio Rápido⬆️",
            "chart_button": "👉Ver Gráfico⬆️"
        },
        "fr": {
            "title": "🟢 [MoonX] 🟢 Nouvelle Cotation / Alerte Marché 🪙",
            "token_info": "├ ${0} ({1}) – {2}",
            "market_cap": "💊 Capitalisation boursière actuelle : {0}",
            "price": "💰 Prix actuel : {0}",
            "holders": "👬 Nombre de détenteurs : {0}",
            "launch_time": "⏳ Heure de lancement : [{0}]",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 Surveillance On-chain",
            "smart_money": "🤏 Tendance Smart Money : {0} transactions de smart money au cours des 15 dernières minutes",
            "contract_security": "Audit :",
            "security_item": "• Permissions : [{0}] Honeypot : [{1}] Burn Pool : [{2}] Liste noire : [{3}]",
            "dev_info": "Informations sur le développeur :",
            "dev_status": "• Possession initiale : {0}",
            "dev_balance": "• Solde du portefeuille développeur : {0} SOL",
            "top10_holding": "• Part détenue par le Top 10 : {0}%",
            "social_info": "Liens associés :",
            "social_links": "🔗 Influenceur Twitter : {0} || Site officiel : {1} || Telegram : {2} || Recherche sur X : {3}",
            "community_tips": "⚠️ Avertissement sur les risques :\n • Les investissements en cryptomonnaie sont extrêmement risqués. Faites toujours vos propres recherches (DYOR).\n • Évitez le FOMO (peur de rater une opportunité) – Investissez de manière rationnelle.\n • Méfiez-vous des Rug Pulls et autres arnaques.\nRappel à la communauté MoonX :\n • Restez à l'écoute des annonces de la communauté pour les dernières mises à jour.\n • N'hésitez pas à partager vos analyses et observations dans le groupe.",
            "trade_button": "⚡️Commerce Rapide⬆️",
            "chart_button": "👉Voir Graphique⬆️"
        },
        "es": {
            "title": "🟢 [MoonX] 🟢 Nueva Lista / Alerta de Mercado 🪙:",
            "token_info": "├ ${0} ({1}) – {2}",
            "market_cap": "💊 Capitalización de Mercado Actual: {0}",
            "price": "💰 Precio Actual: {0}",
            "holders": "👬 Holders: {0}",
            "launch_time": "⏳ Hora de Inicio: [{0}]",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 Monitoreo On-chain",
            "smart_money": "🤏 Tendencia de Smart Money: {0} operaciones de smart money en los últimos 15 minutos",
            "contract_security": "Auditoría:",
            "security_item": "• Permisos: [{0}] Honeypot: [{1}] Burn Pool: [{2}] Lista negra: [{3}]",
            "dev_info": "Info del Desarrollador:",
            "dev_status": "• Tenencia inicial: {0}",
            "dev_balance": "• Balance del wallet del dev: {0} SOL",
            "top10_holding": "• Participación del Top 10 de holders: {0}%",
            "social_info": "Relacionado:",
            "social_links": "🔗 Twitter Influencer: {0} || Sitio Web Oficial: {1} || Telegram: {2} || Buscar en X: {3}",
            "community_tips": "⚠️ Advertencia de Riesgo:\n • Las inversiones en criptomonedas son extremadamente riesgosas. Siempre haz tu propia investigación (DYOR)\n • Evita el FOMO (miedo a quedarse fuera) – Invierte racionalmente\n • Cuidado con los rug pulls y otras estafas\nRecordatorio de la Comunidad MoonX:\n • Mantente atento a los anuncios de la comunidad para conocer las últimas actualizaciones\n • Siéntete libre de compartir tus análisis e ideas en el grupo",
            "trade_button": "⚡️Comercio Rápido⬆️",
            "chart_button": "👉Ver Gráfico⬆️"
        },
        "tr": {
            "title": "🟢 [MoonX] 🟢 Yeni Listeleme / Pazar Uyarısı 🪙:",
            "token_info": "├ ${0} ({1}) – {2}",
            "market_cap": "💊 Mevcut Piyasa Değeri: {0}",
            "price": "💰 Mevcut Fiyat: {0}",
            "holders": "👬 Sahipler: {0}",
            "launch_time": "⏳ Başlangıç Zamanı: [{0}]",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 Zincir Üzeri İzleme",
            "smart_money": "🤏 Akıllı Para Trendi: Son 15 dakikada {0} akıllı para işlemi",
            "contract_security": "Denetim:",
            "security_item": "• İzinler: [{0}] Honeypot: [{1}] Burn Pool: [{2}] Blacklist: [{3}]",
            "dev_info": "Geliştirici Bilgisi:",
            "dev_status": "• Başlangıç Sahipliği: {0}",
            "dev_balance": "• Geliştirici Cüzdan Bakiyesi: {0} SOL",
            "top10_holding": "• İlk 10 Sahibin Payı: {0}%",
            "social_info": "İlgili:",
            "social_links": "🔗 Twitter Etkileyici: {0} || Resmi Web Sitesi: {1} || Telegram: {2} || X'te ara: {3}",
            "community_tips": "⚠️ Risk Uyarısı:\n • Kripto para yatırımları son derece risklidir. Her zaman DYOR (Kendi Araştırmanızı Yapın)\n • FOMO (Kaçırma Korkusu)dan kaçının – Mantıklı bir şekilde yatırım yapın\n • Rug Pull ve diğer dolandırıcılık taktiklerine karşı dikkatli olun\nMoonX Topluluk Hatırlatması:\n • En son güncellemeler için topluluk duyurularını takip edin\n • Grup içinde görüşlerinizi ve analizlerinizi paylaşmaktan çekinmeyin",
            "trade_button": "⚡️Hızlı İşlem⬆️",
            "chart_button": "👉Grafiği Kontrol Et⬆️"
        },
        "de": {
            "title": "🟢 [MoonX] 🟢 Neue Listung / Marktmitteilung 🪙:",
            "token_info": "├ ${0} ({1}) – {2}",
            "market_cap": "💊 Aktuelle Marktkapitalisierung: {0}",
            "price": "💰 Aktueller Preis: {0}",
            "holders": "👬 Halter: {0}",
            "launch_time": "⏳ Startzeit: [{0}]",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 On-Chain-Überwachung",
            "smart_money": "🤏 Smart-Money-Trend: {0} Smart-Money-Transaktionen in den letzten 15 Minuten",
            "contract_security": "Prüfung:",
            "security_item": "• Berechtigungen: [{0}] Honeypot: [{1}] Burn Pool: [{2}] Blacklist: [{3}]",
            "dev_info": "Entwicklerinformationen:",
            "dev_status": "• Anfänglicher Halteanteil: {0}",
            "dev_balance": "• Entwickler-Wallet-Guthaben: {0} SOL",
            "top10_holding": "• Anteil der Top-10-Halter: {0}%",
            "social_info": "Zugehörige Links:",
            "social_links": "🔗 Twitter-Influencer: {0} || Offizielle Website: {1} || Telegram: {2} || Suche auf X: {3}",
            "community_tips": "⚠️ Risikowarnung:\n• Kryptowährungsinvestitionen sind extrem riskant. Führen Sie immer Ihre eigene Recherche durch (DYOR)\n• Vermeiden Sie FOMO (Fear of Missing Out) – Investieren Sie rational\n• Seien Sie vorsichtig bei Rug Pulls und anderen Betrugsmethoden\nMoonX Community Erinnerung:\n• Bleiben Sie auf dem Laufenden mit Community-Ankündigungen für die neuesten Updates\n• Teilen Sie gerne Ihre Erkenntnisse und Analysen in der Gruppe",
            "trade_button": "⚡️Schnellhandel⬆️",
            "chart_button": "👉Chart Prüfen⬆️"
        },
        "it": {
            "title": "🟢 [MoonX] 🟢 Nuovo Inserimento / Allerta Mercato 🪙",
            "token_info": "├ ${0} ({1}) – {2}",
            "market_cap": "💊 Capitalizzazione di Mercato Attuale: {0}",
            "price": "💰 Prezzo Attuale: {0}",
            "holders": "👬 Detentori: {0}",
            "launch_time": "⏳ Orario di Lancio: [{0}]",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 Monitoraggio On-chain",
            "smart_money": "🤏 Trend Smart Money: {0} transazioni smart money negli ultimi 15 minuti",
            "contract_security": "Verifica:",
            "security_item": "• Permessi: [{0}] Honeypot: [{1}] Burn Pool: [{2}] Lista Nera: [{3}]",
            "dev_info": "Informazioni Sviluppatore:",
            "dev_status": "• Possesso Iniziale: {0}",
            "dev_balance": "• Saldo Wallet Sviluppatore: {0} SOL",
            "top10_holding": "• Quota Top 10 Detentori: {0}%",
            "social_info": "Collegamenti:",
            "social_links": "🔗 Influencer Twitter: {0} || Sito Ufficiale: {1} || Telegram: {2} || Cerca su X: {3}",
            "community_tips": "⚠️ Avviso di Rischio:\n• Gli investimenti in criptovalute sono estremamente rischiosi. Fai sempre le tue ricerche (DYOR)\n• Evita il FOMO (Fear of Missing Out) - Investi razionalmente\n• Attenzione ai Rug Pull e altre tattiche di truffa\nPromemoria della Comunità MoonX:\n• Segui gli annunci della comunità per gli ultimi aggiornamenti\n• Condividi liberamente le tue analisi e idee nel gruppo",
            "trade_button": "⚡️Trading Rapido⬆️",
            "chart_button": "👉Controlla Grafico⬆️"
        },
        "ar": {
            "title": "🟢 [MoonX] 🟢 إدراج جديد / تنبيه السوق 🪙",
            "token_info": "├ ${0} ({1}) – {2}",
            "market_cap": "💊 القيمة السوقية الحالية: {0}",
            "price": "💰 السعر الحالي: {0}",
            "holders": "👬 المالكين: {0}",
            "launch_time": "⏳ وقت الإطلاق: [{0}]",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 مراقبة السلسلة",
            "smart_money": "🤏 اتجاه الأموال الذكية: {0} معاملة ذكية في آخر 15 دقيقة",
            "contract_security": "المراجعة:",
            "security_item": "• الصلاحيات: [{0}] مصيدة العسل: [{1}] حوض الحرق: [{2}] القائمة السوداء: [{3}]",
            "dev_info": "معلومات المطور:",
            "dev_status": "• الحيازة الأولية: {0}",
            "dev_balance": "• رصيد محفظة المطور: {0} SOL",
            "top10_holding": "• حصة أكبر 10 مالكين: {0}%",
            "social_info": "روابط ذات صلة:",
            "social_links": "🔗 مؤثر تويتر: {0} | | الموقع الرسمي: {1} | | | تيليجرام {2} | | بحث X: {3}",
            "community_tips": "⚠️ تحذير المخاطر:\n -و الاستثمارات في العملات الرقمية محفوفة بالمخاطر. DYOR (قم دائمًا بالبحث بنفسك)\n • تجنب FOMO (الخوف من فقدان الفرصة) - استثمر بعقلانية\n • احترس من العمليات الاحتيالية مثل \" عملية السحب على البساط (Rug Pulls)\" وأساليب الاحتيال الأخرى\nتذكير من مجتمع MoonX:\n • ترقبوا إعلانات المجتمع للاطلاع على آخر التحديثات\n • لا تتردد في مشاركة أفكارك وتحليلاتك في المجموعة",
            "trade_button": "⚡️تداول سريع⬆️",
            "chart_button": "👉تحقق من الرسم البياني⬆️"
        },
        "fa": {
            "title": "🟢 [MoonX] 🟢 لیست جدید / هشدار بازار 🪙",
            "token_info": "├ ${0} ({1}) – {2}",
            "market_cap": "💊 ارزش بازار فعلی: {0}",
            "price": "💰 قیمت فعلی: {0}",
            "holders": "👬 دارندگان: {0}",
            "launch_time": "⏳ زمان شروع: [{0}]",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 نظارت زنجیره‌ای",
            "smart_money": "🤏 روند پول هوشمند: {0} معامله پول هوشمند در 15 دقیقه گذشته",
            "contract_security": "بازرسی:",
            "security_item": "• مجوزها: [{0}] هانی‌پات: [{1}] استخر سوزاندن: [{2}] لیست سیاه: [{3}]",
            "dev_info": "اطلاعات توسعه‌دهنده:",
            "dev_status": "• مالکیت اولیه: {0}",
            "dev_balance": "• موجودی کیف پول توسعه‌دهنده: {0} SOL",
            "top10_holding": "• سهم 10 دارنده برتر: {0}%",
            "social_info": "لینک‌های مرتبط:",
            "social_links": "🔗 اینفلوئنسر توییتر: {0} || وب‌سایت رسمی: {1} || تلگرام: {2} || جستجو در X: {3}",
            "community_tips": "⚠️ هشدار ریسک:\n • سرمایه‌گذاری در ارزهای دیجیتال بسیار پرخطر است. همیشه تحقیقات خود را انجام دهید (DYOR)\n • از FOMO (ترس از دست دادن) اجتناب کنید - منطقی سرمایه‌گذاری کنید\n • مراقب Rug Pull و سایر تکنیک‌های کلاهبرداری باشید\nیادآوری جامعه MoonX:\n • برای آخرین به‌روزرسانی‌ها به اعلان‌های جامعه توجه کنید\n • در گروه آزادانه تحلیل‌ها و ایده‌های خود را به اشتراک بگذارید",
            "trade_button": "⚡️معامله سریع⬆️",
            "chart_button": "👉بررسی نمودار⬆️"
        },
        "vn": {
            "title": "🟢 [MoonX] 🟢 Niêm yết Mới / Biến Động Thị Trường 🪙:",
            "token_info": "├ ${0} ({1}) – {2}",
            "market_cap": "💊 Vốn hóa thị trường hiện tại: {0}",
            "price": "💰 Giá hiện tại: {0}",
            "holders": "👬 Số lượng người nắm giữ: {0}",
            "launch_time": "⏳ Thời gian khởi tạo: [{0}]",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 Giám sát On-chain",
            "smart_money": "🤏 Xu hướng Smart Money: {0} giao dịch từ ví thông minh trong 15 phút qua",
            "contract_security": "Kiểm toán:",
            "security_item": "• Quyền truy cập: [{0}] Honeypot: [{1}] Burn Pool: [{2}] Danh sách đen: [{3}]",
            "dev_info": "Thông tin nhà phát triển:",
            "dev_status": "• Sở hữu ban đầu: {0}",
            "dev_balance": "• Số dư ví Dev: {0} SOL",
            "top10_holding": "• Tỷ lệ nắm giữ của Top 10: {0}%",
            "social_info": "Liên quan:",
            "social_links": "🔗 Twitter Influencer: {0} || Website chính thức: {1} || Telegram: {2} || Tìm trên Twitter: {3}",
            "community_tips": "⚠️ Cảnh báo rủi ro:\n • Đầu tư tiền mã hóa có độ rủi ro rất cao. Luôn tự nghiên cứu (DYOR)\n • Tránh tâm lý FOMO (sợ bỏ lỡ) – Hãy đầu tư một cách lý trí\n • Cẩn thận với Rug Pull và các hình thức lừa đảo khác\nNhắc nhở từ cộng đồng MoonX:\n • Theo dõi thông báo cộng đồng để cập nhật mới nhất\n • Thoải mái chia sẻ nhận định và phân tích của bạn trong nhóm",
            "trade_button": "⚡️Giao Dịch Nhanh⬆️",
            "chart_button": "👉Kiểm Tra Biểu Đồ⬆️"
        },
        
        # 精選信號模板
        "premium": {
            "zh": {
                "title": "MoonX 精選信號",
                "token_info": "🚀 代幣：{0}（{1}）",
                "price": "💰 價格：${0}",
                "contract": "📌 合約：{0}",
                "market_cap_alert": "⚙️ {0}次預警 ⚠️ 市值達到 {1}",
                "launch_time": "⏰ 開盤時間：{0}",
                "token_check": "📝 代幣檢測：燒池子 {0} | 權限 {1} | TOP10 {2}% {3} | 貔貅 {4}",
                "links": "🔗 MoonX K線：{0}\n🔍 X討論：{1}",
                "highlight_tags": "🔥 亮點：{0}",
                "divider": ""
            },
            "en": {
                "title": "MoonX Featured Signal",
                "token_info": "🚀 Token: {0} ({1})",
                "price": "💰 Price: ${0}",
                "contract": "📌 Contract: {0}",
                "market_cap_alert": "⚙️ {0} Warning ⚠️ MCap reached {1}",
                "launch_time": "⏰ Start Time: {0}",
                "token_check": "📝 Audit: Burn Pool {0} | Permission {1} | TOP10 {2}% {3} | Honeypot {4}",
                "links": "🔗 MoonX Chart: {0}\n🔍 X Discussion: {1}",
                "highlight_tags": "🔥 Highlights: {0}",
                "divider": ""
            },
            "ru": {
                "title": "MoonX Рекомендованный сигнал",
                "token_info": "🚀 Токен: {0} ({1})",
                "price": "💰 Цена: ${0}",
                "contract": "📌 Контракт: {0}",
                "market_cap_alert": "⚙️ Уведомление: Предупреждение {0} ⚠️ Р. Кап. {1}",
                "launch_time": "⏰ Время старта: {0}",
                "token_check": "📝 Аудит: Пул сжигания {0} | Права доступа {1} | ТОП10 {2}% {3} | Honeypot {4}",
                "links": "🔗 График MoonX: {0}\n🔍 Обсуждение в X: {1}",
                "highlight_tags": "🔥 Выделенные метки: {0}",
                "divider": ""
            },
            "id": {
                "title": "Sinyal Unggulan MoonX",
                "token_info": "🚀 Token: {0} ({1})",
                "price": "💰 Harga: ${0}",
                "contract": "📌 Kontrak: {0}",
                "market_cap_alert": "⚙️ Alert: Peringatan {0} ⚠️ MCap mencapai {1}",
                "launch_time": "⏰ Waktu Mulai: {0}",
                "token_check": "📝 Audit: Burn Pool {0} | Permission {1} | TOP10 {2}% {3} | Honeypot {4}",
                "links": "🔗 MoonX Chart: {0}\n🔍 X Diskusi: {1}",
                "highlight_tags": "🔥 Key Highlights: {0}",
                "divider": ""
            },
            "ja": {
                "title": "MoonX 注目シグナル",
                "token_info": "🚀 トークン: {0}（{1}）",
                "price": "💰 価格: ${0}",
                "contract": "📌 コントラクト: {0}",
                "market_cap_alert": "⚙️ アラート: 第{0}警告 ⚠️ MCapが{1}に到達",
                "launch_time": "⏰ 開始時間: {0}",
                "token_check": "📝 セキュリティ監査: Burn Pool {0} | パーミッション {1} | 上位10アドレスの保有率 {2}% {3} | ハニーポット対策 {4}",
                "links": "🔗 MoonX チャート: {0}\n🔍 X（旧Twitter）での議論: {1}",
                "highlight_tags": "🔥 注目マーク: {0}",
                "divider": ""
            },
            "pt": {
                "title": "Sinal em Destaque da MoonX",
                "token_info": "🚀 Token: {0} ({1})",
                "price": "💰 Preço: ${0}",
                "contract": "📌 Contrato: {0}",
                "market_cap_alert": "⚙️ Alerta: {0} Aviso ⚠️ MCap atingiu {1}",
                "launch_time": "⏰ Tempo de Início: {0}",
                "token_check": "📝 Audit: Burn Pool {0} | Permissões {1} | TOP10 {2}% {3} | Honeypot {4}",
                "links": "🔗 Gráfico MoonX: {0}\n🔍 Discussão no X (Twitter): {1}",
                "highlight_tags": "🔥 Principais Destaques: {0}",
                "divider": ""
            },
            "fr": {
                "title": "Signal en vedette sur MoonX",
                "token_info": "🚀 Token : {0} ({1})",
                "price": "💰 Prix : ${0}",
                "contract": "📌 Contrat : {0}",
                "market_cap_alert": "⚙️ Alerte : {0} alerte ⚠️ MCap atteint {1}",
                "launch_time": "⏰ Heure de lancement : {0}",
                "token_check": "📝 Audit : Burn Pool {0} | Permissions {1} | TOP10 détient {2}% {3} | Honeypot {4}",
                "links": "🔗 Graphique MoonX : {0}\n🔍 Discussion sur X : {1}",
                "highlight_tags": "🔥 Points forts : {0}",
                "divider": ""
            },
            "es": {
                "title": "MoonX Signal Destacado",
                "token_info": "🚀 Token: {0} ({1})",
                "price": "💰 Precio: ${0}",
                "contract": "📌 Contrato: {0}",
                "market_cap_alert": "⚙️ Alerta: {0} Aviso ⚠️ MCap alcanzó {1}",
                "launch_time": "⏰ Hora de Inicio: {0}",
                "token_check": "📝 Auditoría: Burn Pool {0} | Permiso {1} | TOP10 {2}% {3} | Honeypot {4}",
                "links": "🔗 Gráfico de MoonX: {0}\n🔍 Discusión en X: {1}",
                "highlight_tags": "🔥 Aspectos Clave: {0}",
                "divider": ""
            },
            "tr": {
                "title": "MoonX Öne Çıkan Sinyal",
                "token_info": "🚀 Token: {0} ({1})",
                "price": "💰 Fiyat: ${0}",
                "contract": "📌 Kontrat: {0}",
                "market_cap_alert": "⚙️ Uyarı: {0} Uyarı ⚠️ MCap {1}'ye ulaştı",
                "launch_time": "⏰ Başlangıç Zamanı: {0}",
                "token_check": "📝 Denetim: Yakım Havuzu {0} | Yetki {1} | TOP10 {2}% {3} | Honeypot {4}",
                "links": "🔗 MoonX Grafiği: {0}\n🔍 X Tartışması: {1}",
                "highlight_tags": "🔥 Temel Noktalar: {0}",
                "divider": ""
            },
            "de": {
                "title": "MoonX Vorgestelltes Signal",
                "token_info": "🚀 Token: {0} ({1})",
                "price": "💰 Preis: ${0}",
                "contract": "📌 Vertrag: {0}",
                "market_cap_alert": "⚙️ Alarm: {0} Warnung ⚠️ MCap hat {1} erreicht",
                "launch_time": "⏰ Startzeit: {0}",
                "token_check": "📝 Prüfung: Burn-Pool {0} | Berechtigungen {1} | TOP10 {2}% {3} | Honeypot {4}",
                "links": "🔗 MoonX-Chart: {0}\n🔍 X-Diskussion: {1}",
                "highlight_tags": "🔥 Wichtige Punkte: {0}",
                "divider": ""
            },
            "it": {
                "title": "Segnale in Evidenza MoonX",
                "token_info": "🚀 Token: {0} ({1})",
                "price": "💰 Prezzo: ${0}",
                "contract": "📌 Contratto: {0}",
                "market_cap_alert": "⚙️ Avviso: {0} Avvertimento ⚠️ MCap raggiunta {1}",
                "launch_time": "⏰ Ora di Lancio: {0}",
                "token_check": "📝 Controllo: Pool di Burn {0} | Permessi {1} | TOP10 {2}% {3} | Honeypot {4}",
                "links": "🔗 Grafico MoonX: {0}\n🔍 Discussione su X: {1}",
                "highlight_tags": "🔥 Punti Chiave: {0}",
                "divider": ""
            },
            "ar": {
                "title": "إشارة مميزة من MoonX",
                "token_info": "🚀 الرمز: {0} ({1})",
                "price": "💰 السعر: ${0}",
                "contract": "📌 العقد: {0}",
                "market_cap_alert": "⚙️ التنبيه: التحذير {0} ⚠️ MCap وصلت إلى {1}",
                "launch_time": "⏰ وقت البدء: {0}",
                "token_check": "📝 التدقيق: مجموعة الحرق {0} | الأذونات {1} | أفضل 10: {2}% {3} | فخ العسل {4}",
                "links": "🔗 رسم بياني من MoonX: {0}\n🔍 نقاش X: {1}",
                "highlight_tags": "🔥 أبرز الأحداث: {0}",
                "divider": ""
            },
            "fa": {
                "title": "سیگنال ویژه MoonX",
                "token_info": "🚀 نشانه: {0} ({1})",
                "price": "💰 قیمت: ${0}",
                "contract": "📌 قرارداد: {0}",
                "market_cap_alert": "⚙️ هشدار: {0} هشدار ⚠️ MCap به {1} رسید",
                "launch_time": "⏰ زمان شروع: {0}",
                "token_check": "📝 ممیزی: استخر سوختگی {0} | مجوز {1} | TOP10 {2}% {3} | هانی پات {4}",
                "links": "🔗 نمودار MoonX: {0}\n🔍 X بحث: {1}",
                "highlight_tags": "🔥 نکات برجسته کلیدی: {0}",
                "divider": ""
            },
            "vn": {
                "title": "MoonX - Tín Hiệu Nổi Bật",
                "token_info": "🚀 Token: {0} ({1})",
                "price": "💰 Giá: ${0}",
                "contract": "📌 Hợp đồng: {0}",
                "market_cap_alert": "⚙️ Lưu ý: Cảnh báo lần {0} ⚠️ Vốn hóa đạt {1}",
                "launch_time": "⏰ Thời gian mở giao dịch: {0}",
                "token_check": "📝 Kiểm tra Token: Burn Pool: {0} | Quyền truy cập: {1} | Top 10 nắm giữ: {2}% {3} | Honeypot {4}",
                "links": "🔗 MoonX (K-line): {0}\n🔍 Thảo luận trên X: {1}",
                "highlight_tags": "🔥 Tín hiệu: {0}",
                "divider": ""
            }
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
            "title": "🟢 [MoonX] 🟢 New Listing / Market Alert 🪙:",
            "token_info": "├ ${0} - {1}\n├ {2}",
            "market_cap": "💊 Current Market Cap: {0}",
            "price": "💰 Current Price: $ {0}",
            "holders": "👬 Holders: {0}",
            "launch_time": "⏳ Start Time: [{0}]",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 On-chain Monitoring",
            "smart_money": "🤏 Smart Money Trend: {0} smart money trades in the last 15 minutes",
            "contract_security": "Audit:",
            "security_item": "• Permissions: [{0}] Honeypot: [{1}] Burn Pool: [{2}] Blacklist: [{3}]",
            "dev_info": "Developer Info:",
            "dev_status": "• Initial Holding: {0}",
            "dev_balance": "• Dev Wallet Balance: {0} SOL",
            "top10_holding": "• Top 10 Holder Share: {0}%",
            "social_info": "🌐 Related:",
            "social_links": "Twitter Influencer: {0} || Official Website: {1} || Telegram: {2} || Search X: {3}",
            "community_tips": "⚠️ Risk Warning:\n • Cryptocurrency investments are extremely risky. Always DYOR (Do Your Own Research)\n • Avoid FOMO (Fear of Missing Out) – Invest rationally\n • Watch out for Rug Pulls and other scam tactics\nMoonX Community Reminder:\n • Stay tuned to community announcements for the latest updates\n • Feel free to share your insights and analysis in the group"
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
            "smart_money": "스마트 머니 {0건 구매 (15분 이내)",
            "contract_security": "컨트랙트 보안:",
            "security_item": "- 권한: [{0}]  러그풀: [{1}]  LP소각: [{2}]  블랙리스트: [{3}]",
            "dev_info": "💰 개발자:",
            "dev_status": "- {0}",
            "dev_balance": "- 개발자 잔액: {0} SOL",
            "top10_holding": "- 상위10 보유율: {0}%",
            "social_info": "🌐 소셜 및 도구",
            "social_links": "{0}",
            "community_tips": "🚨 MOONX 커뮤니티 팁\n- 컨트랙트 권한 및 유동성 잠금을 확인하여 러그풀을 방지하세요.\n- 커뮤니티 공지를 확인하고 인사이트를 공유하세요."
        },
        "ch": {
            "title": "🟢 [MoonX] 🟢 新幣上線 / 異動播報 🪙 ：",
            "token_info": "├ ${0} ({1}) – {2}",
            "market_cap": "💊 當前市值：{0}",
            "price": "💰 當前價格：{0}",
            "holders": "👬 持幣人數：{0}",
            "launch_time": "⏳ 開盤時間：[{0}]",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 鏈上監控",
            "smart_money": "🤏 聰明錢動向：15 分鐘內有 {0} 筆聰明錢交易",
            "contract_security": "代幣檢測：",
            "security_item": "• 權限：[{0}] 貔貅：[{1}] 燒池子：[{2}] 黑明單：[{3}]",
            "dev_info": "開發者：",
            "dev_status": "• 開盤持有量：{0}",
            "dev_balance": "• 開發者錢包餘額：{0} SOL",
            "top10_holding": "• Top10 占比：{0}%",
            "social_info": "相關：",
            "social_links": "{0}",
            "community_tips": "⚠️ 風險提示：\n• 加密貨幣投資風險極高，請務必DYOR (Do Your Own Research)\n• 請勿FOMO (Fear of Missing Out)，理性投資\n• 請小心Rug Pull (捲款跑路) 及其他詐騙行為\nMoonX 社群提醒：\n• 請關注社群公告，掌握最新資訊\n• 歡迎在社群中分享您的觀點與分析"
        },
        "ru": {
            "title": "🟢 [MoonX] 🟢 Новая монета / Рыночное уведомление 🪙:",
            "token_info": "├ ${0} ({1}) – {2}",
            "market_cap": "💊 Рыночная капитализация: {0}",
            "price": "💰 Текущая цена: {0}",
            "holders": "👬 Владельцев: {0}",
            "launch_time": "⏳ Время запуска: [{0}]",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 Мониторинг блокчейна",
            "smart_money": "🤏 Активность смарт-денег: {0} сделки за последние 15 минут",
            "contract_security": "Аудит:",
            "security_item": "• Права: [{0}] Ханипот: [{1}] Пул сжигания: [{2}] Чёрный список: [{3}]",
            "dev_info": "Информация о разработчике:",
            "dev_status": "• Первоначальные активы: {0}",
            "dev_balance": "• Баланс кошелька разработчика: {0} SOL",
            "top10_holding": "• Доля топ-10 держателей: {0}%",
            "social_info": "Ссылки:",
            "social_links": "{0}",
            "community_tips": "⚠️ Предупреждение о рисках:\n • Инвестиции в криптовалюты крайне рискованны. Всегда проводите собственный анализ (DYOR)\n • Избегайте FOMO (Fear of Missing Out) – инвестируйте обдуманно\n • Будьте осторожны с Rug Pull и другими мошенническими схемами\nСообщество MoonX напоминает:\n • Следите за новостями в чате для актуальных обновлений\n • Делитесь своим мнением и аналитикой в группе"
        },
        "id": {
            "title": "🟢 [MoonX] 🟢 Listing Baru / Peringatan Pasar🪙:",
            "token_info": "├ ${0} ({1}) – {2}",
            "market_cap": "💊 Mcap Saat Ini: {0}",
            "price": "💰 Harga Saat Ini: {0}",
            "holders": "👬 Holder: {0}",
            "launch_time": "⏳ Waktu Mulai: [{0}]",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 Pemantauan On-chain",
            "smart_money": "🤏 Tren Smart Money: {0} perdagangan smart money dalam 15 menit terakhir",
            "contract_security": "Audit:",
            "security_item": "• Izin: [{0}] Honeypot: [{1}] Burn Pool: [{2}] Daftar Hitam: [{3}]",
            "dev_info": "Info Pengembang:",
            "dev_status": "• Kepemilikan Awal: {0}",
            "dev_balance": "• Saldo Dompet Pengembang: {0} SOL",
            "top10_holding": "• Pembagian Top 10 Holder : {0}%",
            "social_info": "Terkait:",
            "social_links": "{0}",
            "community_tips": "⚠️ Peringatan Risiko:\n• Investasi aset kripto sangat berisiko. Selalu DYOR (Do Your Own Research)\n• Hindari FOMO (Fear of Missing Out) - Berinvestasi secara rasional\n• Waspada terhadap Rug Pulls dan taktik penipuan lainnya\nPengingat Komunitas MoonX:\n• Nantikan pengumuman komunitas untuk pembaruan terbaru\n• Jangan ragu untuk membagikan insight dan analisis Anda di grup"
        },
        "ja": {
            "title": "🟢【MoonX】🟢 新規上場 / マーケットアラート 🪙",
            "token_info": "├ ${0} - {1}\n├ {2}",
            "market_cap": "💊 現在の時価総額：{0}",
            "price": "💰 現在価格：{0}",
            "holders": "👬 保有者数：{0}人",
            "launch_time": "⏳ 開始日時：［{0}］",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 オンチェーン監視",
            "smart_money": "🤏 スマートマネーの動向：過去15分間にスマートマネーによる取引が{0}件",
            "contract_security": "セキュリティ監査：",
            "security_item": " • パーミッション（許可）：[{0}] ハニーポット：[{1}]焼却プール：[{2}]ブラックリスト：[{3}]",
            "dev_info": "開発者情報：",
            "dev_status": "• 初期保有率：{0}",
            "dev_balance": "• 開発者ウォレット残高：{0} SOL",
            "top10_holding": "• トップ10ホルダーの保有率：{0}%",
            "social_info": "関連リンク：",
            "social_links": "{0}",
            "community_tips": "⚠️ リスク警告：\n • 仮想通貨投資は非常に高リスクです。必ずご自身で調査（DYOR）を行ってください\n • FOMO（乗り遅れる恐怖）に注意して、冷静に投資を行いましょう\n • ラグプル（詐欺的な資金引き抜き）やその他の詐欺手口にも注意\nMoonXコミュニティからのリマインダー：\n • 最新情報はコミュニティの発表をチェック！\n • ご自身の分析や見解も、グループで気軽にシェアしてください"
        },
        "pt": {
            "title": "🟢 [MoonX] 🟢 Nova Listagem / Alerta de Mercado 🪙",
            "token_info": "├ ${0} - {1}\n├ {2}",
            "market_cap": "💊 Valor de Mercado Atual: {0}",
            "price": "💰 Preço Atual: {0}",
            "holders": "👬 Detentores: {0}",
            "launch_time": "⏳ Início: [{0}]",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 Monitoramento On-chain",
            "smart_money": "🤏 Tendência de Smart Money: {0} transações de smart money nos últimos 15 minutos",
            "contract_security": "Audit:",
            "security_item": "• Permissões: [{0}] Honeypot: [{1}] Pool de Queima: [{2}] Lista Negra: [{3}]",
            "dev_info": "Informações do Desenvolvedor:",
            "dev_status": "• Participação Inicial: {0}",
            "dev_balance": "• Saldo da Carteira Dev: {0} SOL",
            "top10_holding": "• Participação dos 10 Maiores Detentores: {0}%",
            "social_info": "Relacionados:",
            "social_links": "{0}",
            "community_tips": "⚠️ Aviso de Risco:\n • Investimentos em criptomoedas são extremamente arriscados. Sempre faça sua própria pesquisa (DYOR)\n • Evite o FOMO (medo de ficar de fora) – Invista com racionalidade\n • Fique atento a rug pulls e outras táticas de golpe\nLembrete da Comunidade MoonX:\n • Acompanhe os anúncios da comunidade para as atualizações mais recentes\n • Sinta-se à vontade para compartilhar suas análises e opiniões no grupo"
        },
        "fr": {
            "title": "🟢 [MoonX] 🟢 Nouvelle Cotation / Alerte Marché 🪙",
            "token_info": "├ ${0} - {1}\n├ {2}",
            "market_cap": "💊 Capitalisation boursière actuelle : {0}",
            "price": "💰 Prix actuel : {0}",
            "holders": "👬 Nombre de détenteurs : {0}",
            "launch_time": "⏳ Heure de lancement : [{0}]",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 Surveillance On-chain",
            "smart_money": "🤏 Tendance Smart Money : {0} transactions de smart money au cours des 15 dernières minutes",
            "contract_security": "Audit :",
            "security_item": "• Permissions : [{0}] Honeypot : [{1}] Burn Pool : [{2}] Liste noire : [{3}]",
            "dev_info": "Informations sur le développeur :",
            "dev_status": "• Possession initiale : {0}",
            "dev_balance": "• Solde du portefeuille développeur : {0} SOL",
            "top10_holding": "• Part détenue par le Top 10 : {0}%",
            "social_info": "Liens associés :",
            "social_links": "🔗 Influenceur Twitter : {0} || Site officiel : {1} || Telegram : {2} || Recherche sur X : {3}",
            "community_tips": "⚠️ Avertissement sur les risques :\n • Les investissements en cryptomonnaie sont extrêmement risqués. Faites toujours vos propres recherches (DYOR).\n • Évitez le FOMO (peur de rater une opportunité) – Investissez de manière rationnelle.\n • Méfiez-vous des Rug Pulls et autres arnaques.\nRappel à la communauté MoonX :\n • Restez à l'écoute des annonces de la communauté pour les dernières mises à jour.\n • N'hésitez pas à partager vos analyses et observations dans le groupe.",
            "trade_button": "⚡️Commerce Rapide⬆️",
            "chart_button": "👉Voir Graphique⬆️"
        },
        "es": {
            "title": "🟢 [MoonX] 🟢 Nueva Lista / Alerta de Mercado 🪙:",
            "token_info": "├ ${0} - {1}\n├ {2}",
            "market_cap": "💊 Capitalización de Mercado Actual: {0}",
            "price": "💰 Precio Actual: {0}",
            "holders": "👬 Holders: {0}",
            "launch_time": "⏳ Hora de Inicio: [{0}]",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 Monitoreo On-chain",
            "smart_money": "🤏 Tendencia de Smart Money: {0} operaciones de smart money en los últimos 15 minutos",
            "contract_security": "Auditoría:",
            "security_item": "• Permisos: [{0}] Honeypot: [{1}] Burn Pool: [{2}] Lista negra: [{3}]",
            "dev_info": "Info del Desarrollador:",
            "dev_status": "• Tenencia inicial: {0}",
            "dev_balance": "• Balance del wallet del dev: {0} SOL",
            "top10_holding": "• Participación del Top 10 de holders: {0}%",
            "social_info": "Relacionado:",
            "social_links": "🔗 Twitter Influencer: {0} || Sitio Web Oficial: {1} || Telegram: {2} || Buscar en X: {3}",
            "community_tips": "⚠️ Advertencia de Riesgo:\n • Las inversiones en criptomonedas son extremadamente riesgosas. Siempre haz tu propia investigación (DYOR)\n • Evita el FOMO (miedo a quedarse fuera) – Invierte racionalmente\n • Cuidado con los rug pulls y otras estafas\nRecordatorio de la Comunidad MoonX:\n • Mantente atento a los anuncios de la comunidad para conocer las últimas actualizaciones\n • Siéntete libre de compartir tus análisis e ideas en el grupo",
            "trade_button": "⚡️Comercio Rápido⬆️",
            "chart_button": "👉Ver Gráfico⬆️"
        },
        "tr": {
            "title": "🟢 [MoonX] 🟢 Yeni Listeleme / Pazar Uyarısı 🪙:",
            "token_info": "├ ${0} - {1}\n├ {2}",
            "market_cap": "💊 Mevcut Piyasa Değeri: {0}",
            "price": "💰 Mevcut Fiyat: {0}",
            "holders": "👬 Sahipler: {0}",
            "launch_time": "⏳ Başlangıç Zamanı: [{0}]",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 Zincir Üzeri İzleme",
            "smart_money": "🤏 Akıllı Para Trendi: Son 15 dakikada {0} akıllı para işlemi",
            "contract_security": "Denetim:",
            "security_item": "• İzinler: [{0}] Honeypot: [{1}] Burn Pool: [{2}] Blacklist: [{3}]",
            "dev_info": "Geliştirici Bilgisi:",
            "dev_status": "• Başlangıç Sahipliği: {0}",
            "dev_balance": "• Geliştirici Cüzdan Bakiyesi: {0} SOL",
            "top10_holding": "• İlk 10 Sahibin Payı: {0}%",
            "social_info": "İlgili:",
            "social_links": "🔗 Twitter Etkileyici: {0} || Resmi Web Sitesi: {1} || Telegram: {2} || X'te ara: {3}",
            "community_tips": "⚠️ Risk Uyarısı:\n • Kripto para yatırımları son derece risklidir. Her zaman DYOR (Kendi Araştırmanızı Yapın)\n • FOMO (Kaçırma Korkusu)dan kaçının – Mantıklı bir şekilde yatırım yapın\n • Rug Pull ve diğer dolandırıcılık taktiklerine karşı dikkatli olun\nMoonX Topluluk Hatırlatması:\n • En son güncellemeler için topluluk duyurularını takip edin\n • Grup içinde görüşlerinizi ve analizlerinizi paylaşmaktan çekinmeyin",
            "trade_button": "⚡️Hızlı İşlem⬆️",
            "chart_button": "👉Grafiği Kontrol Et⬆️"
        },
        "de": {
            "title": "🟢 [MoonX] 🟢 Neue Listung / Marktmitteilung 🪙:",
            "token_info": "├ ${0} ({1}) – {2}",
            "market_cap": "💊 Aktuelle Marktkapitalisierung: {0}",
            "price": "💰 Aktueller Preis: {0}",
            "holders": "👬 Halter: {0}",
            "launch_time": "⏳ Startzeit: [{0}]",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 On-Chain-Überwachung",
            "smart_money": "🤏 Smart-Money-Trend: {0} Smart-Money-Transaktionen in den letzten 15 Minuten",
            "contract_security": "Prüfung:",
            "security_item": "• Berechtigungen: [{0}] Honeypot: [{1}] Burn Pool: [{2}] Blacklist: [{3}]",
            "dev_info": "Entwicklerinformationen:",
            "dev_status": "• Anfänglicher Halteanteil: {0}",
            "dev_balance": "• Entwickler-Wallet-Guthaben: {0} SOL",
            "top10_holding": "• Anteil der Top-10-Halter: {0}%",
            "social_info": "Zugehörige Links:",
            "social_links": "🔗 Twitter-Influencer: {0} || Offizielle Website: {1} || Telegram: {2} || Suche auf X: {3}",
            "community_tips": "⚠️ Risikohinweis:\n• Kryptowährungsinvestitionen sind extrem riskant. Führen Sie stets eigene Recherchen durch (DYOR).\n• Vermeiden Sie FOMO (Fear of Missing Out) – Investieren Sie rational.\n• Achten Sie auf Rug Pulls und andere Betrugsmethoden.\nHinweis der MoonX-Community:\n• Bleiben Sie über Community-Ankündigungen auf dem Laufenden.\n• Teilen Sie gerne Ihre Erkenntnisse und Analysen in der Gruppe.",
            "trade_button": "⚡️Schnellhandel⬆️",
            "chart_button": "👉Chart Prüfen⬆️"
        },
        "it": {
            "title": "🟢 [MoonX] 🟢 Nuove Inserzioni / Avviso di Mercato 🪙:",
            "token_info": "├ ${0} ({1}) – {2}",
            "market_cap": "💊 Cap di Mercato Attuale: {0}",
            "price": "💰 Prezzo Attuale: {0}",
            "holders": "👬 Detentori: {0}",
            "launch_time": "⏳ Ora di Inizio: [{0}]",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 Monitoraggio On-chain",
            "smart_money": "🤏 Trend Smart Money: {0} azioni di trading di Smart Money negli ultimi 15 minuti",
            "contract_security": "Controllo:",
            "security_item": "• Permessi: [{0}] Honeypot: [{1}] Pool di Burn: [{2}] Blacklist: [{3}]",
            "dev_info": "Informazioni sullo Sviluppatore:",
            "dev_status": "• Detenzione Iniziale: {0}",
            "dev_balance": "• Saldo del Wallet dello Sviluppatore: {0} SOL",
            "top10_holding": "• Quota dei Primi 10 Detentori: {0}%",
            "social_info": "Correlato:",
            "social_links": "🔗 Influencer su Twitter: {0} || Sito Ufficiale: {1} || Telegram: {2} || Cerca X: {3}",
            "community_tips": "⚠️ Avviso di Rischio:\n• Gli investimenti in criptovalute sono estremamente rischiosi. Fai sempre le tue ricerche (DYOR)\n• Evita il FOMO (Paura di Perdere un'Opportunità) – Investi in modo razionale\n• Fai attenzione ai Rug Pulls e ad altre tattiche fraudolente\nPromemoria della Comunità MoonX:\n• Resta aggiornato sugli annunci della comunità per le ultime novità\n• Sentiti libero di condividere le tue intuizioni e analisi nel gruppo",
            "trade_button": "⚡️Trading Rapido⬆️",
            "chart_button": "👉Controlla Grafico⬆️"
        },
        "ar": {
            "title": "🟢 [MoonX] 🟢 قائمة جديدة / تنبيه السوق 🟢:",
            "token_info": "├ ${0} ({1}) – {2}",
            "market_cap": "💊 القيمة السوقية الحالية: {0}",
            "price": "💰 السعر الحالي: {0}",
            "holders": "👬 حاملو السندات: {0}",
            "launch_time": "⏳ وقت البدء: [{0}]",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 مراقبة البلوكتشين",
            "smart_money": "🤏 اتجاه المال الذكي: {0} تداولات أموال ذكية في آخر 15 دقيقة",
            "contract_security": ":التدقيق",
            "security_item": "• الأذونات: [{0}] نقطة التداوُل: [{1}] مجموعة الحرق: [{2}] قائمة الحرق: [{3}]",
            "dev_info": "معلومات المطور:",
            "dev_status": "• الحيازة الأولية {0}",
            "dev_balance": "• رصيد محفظة المطور: {0} سول",
            "top10_holding": "• أفضل 10 حائزين على أعلى 10 حصص {0}%",
            "social_info": "🔗 ذات صلة",
            "social_links": "مؤثر تويتر: {0} | | الموقع الرسمي: {1} | | | تيليجرام {2} | | بحث X: {3}",
            "community_tips": "⚠️ تحذير من المخاطر:\n -و الاستثمارات في العملات الرقمية محفوفة بالمخاطر. DYOR (قم دائمًا بالبحث بنفسك)\n • تجنب FOMO (الخوف من فقدان الفرصة) - استثمر بعقلانية\n • احترس من العمليات الاحتيالية مثل \" عملية السحب على البساط (Rug Pulls)\" وأساليب الاحتيال الأخرى\nتذكير من مجتمع MoonX:\n • ترقبوا إعلانات المجتمع للاطلاع على آخر التحديثات\n • لا تتردد في مشاركة أفكارك وتحليلاتك في المجموعة"
        },
        "fa": {
            "title": "🟢 [MoonX] 🟢 لیست جدید / هشدار بازار 🪙:",
            "token_info": "├ ${0} ({1}) - {2}",
            "market_cap": "💊 ارزش بازار فعلی: {0}",
            "price": "💰 قیمت فعلی: {0}",
            "holders": "👬 دارندگان: {0}",
            "launch_time": "⏳ زمان شروع: [{0}]",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 نظارت زنجیره‌ای",
            "smart_money": "🤏 ترند پول هوشمند: {0} معامله پول هوشمند در 15 دقیقه گذشته",
            "contract_security": "بررسی امنیت:",
            "security_item": "• مجوزها: [{0}] هانی پات: [{1}] استخر سوختگی: [{2}] لیست سیاه: [{3}]",
            "dev_info": "اطلاعات توسعه دهنده:",
            "dev_status": "• برگزاری اولیه: {0}",
            "dev_balance": "• موجودی کیف پول توسعه دهنده: {0} SOL",
            "top10_holding": "• 10 سهم برتر: {0}%",
            "social_info": "مرتبط:",
            "social_links": "🔗 اینفلوئنسر توییتر: {0} || وب سایت رسمی: {1} || تلگرام: {2} || جستجوی X: {3}",
            "community_tips": "⚠️ هشدار خطر:\n • سرمایه گذاری در ارزهای دیجیتال بسیار پرخطر است. همیشه DYOR (خودت تحقیق کن)\n • اجتناب از FOMO (ترس از دست دادن) - سرمایه گذاری منطقی\n • مراقب قالیچه ها و دیگر تاکتیک های کلاهبرداری باشید\nیادآوری انجمن MoonX:\n • برای اطلاع از آخرین به روز رسانی ها منتظر اطلاعیه های انجمن باشید\n • با خیال راحت بینش و تحلیل خود را در گروه به اشتراک بگذارید"
        },
        "vn": {
            "title": "🟢 [MoonX] 🟢 Niêm yết Mới / Biến Động Thị Trường 🪙:",
            "token_info": "├ ${0} ({1}) – {2}",
            "market_cap": "💊 Vốn hóa thị trường hiện tại: {0}",
            "price": "💰 Giá hiện tại: {0}",
            "holders": "👬 Số lượng người nắm giữ: {0}",
            "launch_time": "⏳ Thời gian khởi tạo: [{0}]",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 Giám sát On-chain",
            "smart_money": "🤏 Xu hướng Smart Money: {0} giao dịch từ ví thông minh trong 15 phút qua",
            "contract_security": "Kiểm toán:",
            "security_item": "• Quyền truy cập: [{0}] Honeypot: [{1}] Burn Pool: [{2}] Danh sách đen: [{3}]",
            "dev_info": "Thông tin nhà phát triển:",
            "dev_status": "• Sở hữu ban đầu: {0}",
            "dev_balance": "• Số dư ví Dev: {0} SOL",
            "top10_holding": "• Tỷ lệ nắm giữ của Top 10: {0}%",
            "social_info": "Liên quan:",
            "social_links": "🔗 Twitter Influencer: {0} || Website chính thức: {1} || Telegram: {2} || Tìm trên Twitter: {3}",
            "community_tips": "⚠️ Cảnh báo rủi ro:\n • Đầu tư tiền mã hóa có độ rủi ro rất cao. Luôn tự nghiên cứu (DYOR)\n • Tránh tâm lý FOMO (sợ bỏ lỡ) – Hãy đầu tư một cách lý trí\n • Cẩn thận với Rug Pull và các hình thức lừa đảo khác\nNhắc nhở từ cộng đồng MoonX:\n • Theo dõi thông báo cộng đồng để cập nhật mới nhất\n • Thoải mái chia sẻ nhận định và phân tích của bạn trong nhóm",
            "trade_button": "⚡️Giao Dịch Nhanh⬆️",
            "chart_button": "👉Kiểm Tra Biểu Đồ⬆️"
        },
        
        # 精選信號模板
        "premium": {
            "zh": {
                "title": "MoonX 精選信號",
                "token_info": "🚀 代幣：{0}（{1}）",
                "price": "💰 價格：${0}",
                "contract": "📌 合約：{0}",
                "market_cap_alert": "⚙️ {0}次預警 ⚠️ 市值達到 {1}",
                "launch_time": "⏰ 開盤時間：{0}",
                "token_check": "📝 代幣檢測：燒池子 {0} | 權限 {1} | TOP10 {2}% {3} | 貔貅 {4}",
                "links": "🔗 MoonX K線：{0}\n🔍 X討論：{1}",
                "highlight_tags": "🔥 亮點：{0}",
                "divider": ""
            },
            "en": {
                "title": "MoonX Featured Signal",
                "token_info": "🚀 Token: {0} ({1})",
                "price": "💰 Price: ${0}",
                "contract": "📌 Contract: {0}",
                "market_cap_alert": "⚙️ {0} Warning ⚠️ MCap reached {1}",
                "launch_time": "⏰ Start Time: {0}",
                "token_check": "📝 Audit: Burn Pool {0} | Permission {1} | TOP10 {2}% {3} | Honeypot {4}",
                "links": "🔗 MoonX Chart: {0}\n🔍 X Discussion: {1}",
                "highlight_tags": "🔥 Highlights: {0}",
                "divider": ""
            },
            "ru": {
                "title": "MoonX Рекомендованный сигнал",
                "token_info": "🚀 Токен: {0} ({1})",
                "price": "💰 Цена: ${0}",
                "contract": "📌 Контракт: {0}",
                "market_cap_alert": "⚙️ Уведомление: Предупреждение {0} ⚠️ Р. Кап. {1}",
                "launch_time": "⏰ Время старта: {0}",
                "token_check": "📝 Аудит: Пул сжигания {0} | Права доступа {1} | ТОП10 {2}% {3} | Honeypot {4}",
                "links": "🔗 График MoonX: {0}\n🔍 Обсуждение в X: {1}",
                "highlight_tags": "🔥 Выделенные метки: {0}",
                "divider": ""
            },
            "id": {
                "title": "Sinyal Unggulan MoonX",
                "token_info": "🚀 Token: {0} ({1})",
                "price": "💰 Harga: ${0}",
                "contract": "📌 Kontrak: {0}",
                "market_cap_alert": "⚙️ Alert: Peringatan {0} ⚠️ MCap mencapai {1}",
                "launch_time": "⏰ Waktu Mulai: {0}",
                "token_check": "📝 Audit: Burn Pool {0} | Permission {1} | TOP10 {2}% {3} | Honeypot {4}",
                "links": "🔗 MoonX Chart: {0}\n🔍 X Diskusi: {1}",
                "highlight_tags": "🔥 Key Highlights: {0}",
                "divider": ""
            },
            "ja": {
                "title": "MoonX 注目シグナル",
                "token_info": "🚀 トークン: {0}（{1}）",
                "price": "💰 価格: ${0}",
                "contract": "📌 コントラクト: {0}",
                "market_cap_alert": "⚙️ アラート: 第{0}警告 ⚠️ MCapが{1}に到達",
                "launch_time": "⏰ 開始時間: {0}",
                "token_check": "📝 セキュリティ監査: Burn Pool {0} | パーミッション {1} | 上位10アドレスの保有率 {2}% {3} | ハニーポット対策 {4}",
                "links": "🔗 MoonX チャート: {0}\n🔍 X（旧Twitter）での議論: {1}",
                "highlight_tags": "🔥 注目マーク: {0}",
                "divider": ""
            },
            "pt": {
                "title": "Sinal em Destaque da MoonX",
                "token_info": "🚀 Token: {0} ({1})",
                "price": "💰 Preço: ${0}",
                "contract": "📌 Contrato: {0}",
                "market_cap_alert": "⚙️ Alerta: {0} Aviso ⚠️ MCap atingiu {1}",
                "launch_time": "⏰ Tempo de Início: {0}",
                "token_check": "📝 Audit: Burn Pool {0} | Permissões {1} | TOP10 {2}% {3} | Honeypot {4}",
                "links": "🔗 Gráfico MoonX: {0}\n🔍 Discussão no X (Twitter): {1}",
                "highlight_tags": "🔥 Principais Destaques: {0}",
                "divider": ""
            },
            "fr": {
                "title": "Signal en vedette sur MoonX",
                "token_info": "🚀 Token : {0} ({1})",
                "price": "💰 Prix : ${0}",
                "contract": "📌 Contrat : {0}",
                "market_cap_alert": "⚙️ Alerte : {0} alerte ⚠️ MCap atteint {1}",
                "launch_time": "⏰ Heure de lancement : {0}",
                "token_check": "📝 Audit : Burn Pool {0} | Permissions {1} | TOP10 détient {2}% {3} | Honeypot {4}",
                "links": "🔗 Graphique MoonX : {0}\n🔍 Discussion sur X : {1}",
                "highlight_tags": "🔥 Points forts : {0}",
                "divider": ""
            },
            "es": {
                "title": "MoonX Signal Destacado",
                "token_info": "🚀 Token: {0} ({1})",
                "price": "💰 Precio: ${0}",
                "contract": "📌 Contrato: {0}",
                "market_cap_alert": "⚙️ Alerta: {0} Aviso ⚠️ MCap alcanzó {1}",
                "launch_time": "⏰ Hora de Inicio: {0}",
                "token_check": "📝 Auditoría: Burn Pool {0} | Permiso {1} | TOP10 {2}% {3} | Honeypot {4}",
                "links": "🔗 Gráfico de MoonX: {0}\n🔍 Discusión en X: {1}",
                "highlight_tags": "🔥 Aspectos Clave: {0}",
                "divider": ""
            },
            "tr": {
                "title": "MoonX Öne Çıkan Sinyal",
                "token_info": "🚀 Token: {0} ({1})",
                "price": "💰 Fiyat: ${0}",
                "contract": "📌 Kontrat: {0}",
                "market_cap_alert": "⚙️ Uyarı: {0} Uyarı ⚠️ MCap {1}'ye ulaştı",
                "launch_time": "⏰ Başlangıç Zamanı: {0}",
                "token_check": "📝 Denetim: Yakım Havuzu {0} | Yetki {1} | TOP10 {2}% {3} | Honeypot {4}",
                "links": "🔗 MoonX Grafiği: {0}\n🔍 X Tartışması: {1}",
                "highlight_tags": "🔥 Temel Noktalar: {0}",
                "divider": ""
            },
            "de": {
                "title": "MoonX Vorgestelltes Signal",
                "token_info": "🚀 Token: {0} ({1})",
                "price": "💰 Preis: ${0}",
                "contract": "📌 Vertrag: {0}",
                "market_cap_alert": "⚙️ Alarm: {0} Warnung ⚠️ MCap hat {1} erreicht",
                "launch_time": "⏰ Startzeit: {0}",
                "token_check": "📝 Prüfung: Burn-Pool {0} | Berechtigungen {1} | TOP10 {2}% {3} | Honeypot {4}",
                "links": "🔗 MoonX-Chart: {0}\n🔍 X-Diskussion: {1}",
                "highlight_tags": "🔥 Wichtige Punkte: {0}",
                "divider": ""
            },
            "it": {
                "title": "Segnale in Evidenza MoonX",
                "token_info": "🚀 Token: {0} ({1})",
                "price": "💰 Prezzo: ${0}",
                "contract": "📌 Contratto: {0}",
                "market_cap_alert": "⚙️ Avviso: {0} Avvertimento ⚠️ MCap raggiunta {1}",
                "launch_time": "⏰ Ora di Lancio: {0}",
                "token_check": "📝 Controllo: Pool di Burn {0} | Permessi {1} | TOP10 {2}% {3} | Honeypot {4}",
                "links": "🔗 Grafico MoonX: {0}\n🔍 Discussione su X: {1}",
                "highlight_tags": "🔥 Punti Chiave: {0}",
                "divider": ""
            },
            "ar": {
                "title": "إشارة مميزة من MoonX",
                "token_info": "🚀 الرمز: {0} ({1})",
                "price": "💰 السعر: ${0}",
                "contract": "📌 العقد: {0}",
                "market_cap_alert": "⚙️ التنبيه: التحذير {0} ⚠️ MCap وصلت إلى {1}",
                "launch_time": "⏰ وقت البدء: {0}",
                "token_check": "📝 التدقيق: مجموعة الحرق {0} | الأذونات {1} | أفضل 10: {2}% {3} | فخ العسل {4}",
                "links": "🔗 رسم بياني من MoonX: {0}\n🔍 نقاش X: {1}",
                "highlight_tags": "🔥 أبرز الأحداث: {0}",
                "divider": ""
            },
            "fa": {
                "title": "سیگنال ویژه MoonX",
                "token_info": "🚀 نشانه: {0} ({1})",
                "price": "💰 قیمت: ${0}",
                "contract": "📌 قرارداد: {0}",
                "market_cap_alert": "⚙️ هشدار: {0} هشدار ⚠️ MCap به {1} رسید",
                "launch_time": "⏰ زمان شروع: {0}",
                "token_check": "📝 ممیزی: استخر سوختگی {0} | مجوز {1} | TOP10 {2}% {3} | هانی پات {4}",
                "links": "🔗 نمودار MoonX: {0}\n🔍 X بحث: {1}",
                "highlight_tags": "🔥 نکات برجسته کلیدی: {0}",
                "divider": ""
            },
            "vn": {
                "title": "MoonX - Tín Hiệu Nổi Bật",
                "token_info": "🚀 Token: {0} ({1})",
                "price": "💰 Giá: ${0}",
                "contract": "📌 Hợp đồng: {0}",
                "market_cap_alert": "⚙️ Lưu ý: Cảnh báo lần {0} ⚠️ Vốn hóa đạt {1}",
                "launch_time": "⏰ Thời gian mở giao dịch: {0}",
                "token_check": "📝 Kiểm tra Token: Burn Pool: {0} | Quyền truy cập: {1} | Top 10 nắm giữ: {2}% {3} | Honeypot {4}",
                "links": "🔗 MoonX (K-line): {0}\n🔍 Thảo luận trên X: {1}",
                "highlight_tags": "🔥 Tín hiệu: {0}",
                "divider": ""
            }
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
            "title": "🟢 [MoonX] 🟢 New Listing / Market Alert 🪙:",
            "token_info": "├ ${0} - {1}\n├ {2}",
            "market_cap": "💊 Current Market Cap: {0}",
            "price": "💰 Current Price: $ {0}",
            "holders": "👬 Holders: {0}",
            "launch_time": "⏳ Start Time: [{0}]",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 On-chain Monitoring",
            "smart_money": "🤏 Smart Money Trend: {0} smart money trades in the last 15 minutes",
            "contract_security": "Audit:",
            "security_item": "• Permissions: [{0}] Honeypot: [{1}] Burn Pool: [{2}] Blacklist: [{3}]",
            "dev_info": "Developer Info:",
            "dev_status": "• Initial Holding: {0}",
            "dev_balance": "• Dev Wallet Balance: {0} SOL",
            "top10_holding": "• Top 10 Holder Share: {0}%",
            "social_info": "🌐 Related:",
            "social_links": "Twitter Influencer: {0} || Official Website: {1} || Telegram: {2} || Search X: {3}",
            "community_tips": "⚠️ Risk Warning:\n • Cryptocurrency investments are extremely risky. Always DYOR (Do Your Own Research)\n • Avoid FOMO (Fear of Missing Out) – Invest rationally\n • Watch out for Rug Pulls and other scam tactics\nMoonX Community Reminder:\n • Stay tuned to community announcements for the latest updates\n • Feel free to share your insights and analysis in the group"
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
            "smart_money": "스마트 머니 {0건 구매 (15분 이내)",
            "contract_security": "컨트랙트 보안:",
            "security_item": "- 권한: [{0}]  러그풀: [{1}]  LP소각: [{2}]  블랙리스트: [{3}]",
            "dev_info": "💰 개발자:",
            "dev_status": "- {0}",
            "dev_balance": "- 개발자 잔액: {0} SOL",
            "top10_holding": "- 상위10 보유율: {0}%",
            "social_info": "🌐 소셜 및 도구",
            "social_links": "{0}",
            "community_tips": "🚨 MOONX 커뮤니티 팁\n- 컨트랙트 권한 및 유동성 잠금을 확인하여 러그풀을 방지하세요.\n- 커뮤니티 공지를 확인하고 인사이트를 공유하세요."
        },
        "ch": {
            "title": "🟢 [MoonX] 🟢 新幣上線 / 異動播報 🪙 ：",
            "token_info": "├ ${0} ({1}) – {2}",
            "market_cap": "💊 當前市值：{0}",
            "price": "💰 當前價格：{0}",
            "holders": "👬 持幣人數：{0}",
            "launch_time": "⏳ 開盤時間：[{0}]",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 鏈上監控",
            "smart_money": "🤏 聰明錢動向：15 分鐘內有 {0} 筆聰明錢交易",
            "contract_security": "代幣檢測：",
            "security_item": "• 權限：[{0}] 貔貅：[{1}] 燒池子：[{2}] 黑明單：[{3}]",
            "dev_info": "開發者：",
            "dev_status": "• 開盤持有量：{0}",
            "dev_balance": "• 開發者錢包餘額：{0} SOL",
            "top10_holding": "• Top10 占比：{0}%",
            "social_info": "相關：",
            "social_links": "{0}",
            "community_tips": "⚠️ 風險提示：\n• 加密貨幣投資風險極高，請務必DYOR (Do Your Own Research)\n• 請勿FOMO (Fear of Missing Out)，理性投資\n• 請小心Rug Pull (捲款跑路) 及其他詐騙行為\nMoonX 社群提醒：\n• 請關注社群公告，掌握最新資訊\n• 歡迎在社群中分享您的觀點與分析"
        },
        "ru": {
            "title": "🟢 [MoonX] 🟢 Новая монета / Рыночное уведомление 🪙:",
            "token_info": "├ ${0} ({1}) – {2}",
            "market_cap": "💊 Рыночная капитализация: {0}",
            "price": "💰 Текущая цена: {0}",
            "holders": "👬 Владельцев: {0}",
            "launch_time": "⏳ Время запуска: [{0}]",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 Мониторинг блокчейна",
            "smart_money": "🤏 Активность смарт-денег: {0} сделки за последние 15 минут",
            "contract_security": "Аудит:",
            "security_item": "• Права: [{0}] Ханипот: [{1}] Пул сжигания: [{2}] Чёрный список: [{3}]",
            "dev_info": "Информация о разработчике:",
            "dev_status": "• Первоначальные активы: {0}",
            "dev_balance": "• Баланс кошелька разработчика: {0} SOL",
            "top10_holding": "• Доля топ-10 держателей: {0}%",
            "social_info": "Ссылки:",
            "social_links": "{0}",
            "community_tips": "⚠️ Предупреждение о рисках:\n • Инвестиции в криптовалюты крайне рискованны. Всегда проводите собственный анализ (DYOR)\n • Избегайте FOMO (Fear of Missing Out) – инвестируйте обдуманно\n • Будьте осторожны с Rug Pull и другими мошенническими схемами\nСообщество MoonX напоминает:\n • Следите за новостями в чате для актуальных обновлений\n • Делитесь своим мнением и аналитикой в группе"
        },
        "id": {
            "title": "🟢 [MoonX] 🟢 Listing Baru / Peringatan Pasar🪙:",
            "token_info": "├ ${0} ({1}) – {2}",
            "market_cap": "💊 Mcap Saat Ini: {0}",
            "price": "💰 Harga Saat Ini: {0}",
            "holders": "👬 Holder: {0}",
            "launch_time": "⏳ Waktu Mulai: [{0}]",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 Pemantauan On-chain",
            "smart_money": "🤏 Tren Smart Money: {0} perdagangan smart money dalam 15 menit terakhir",
            "contract_security": "Audit:",
            "security_item": "• Izin: [{0}] Honeypot: [{1}] Burn Pool: [{2}] Daftar Hitam: [{3}]",
            "dev_info": "Info Pengembang:",
            "dev_status": "• Kepemilikan Awal: {0}",
            "dev_balance": "• Saldo Dompet Pengembang: {0} SOL",
            "top10_holding": "• Pembagian Top 10 Holder : {0}%",
            "social_info": "Terkait:",
            "social_links": "{0}",
            "community_tips": "⚠️ Peringatan Risiko:\n• Investasi aset kripto sangat berisiko. Selalu DYOR (Do Your Own Research)\n• Hindari FOMO (Fear of Missing Out) - Berinvestasi secara rasional\n• Waspada terhadap Rug Pulls dan taktik penipuan lainnya\nPengingat Komunitas MoonX:\n• Nantikan pengumuman komunitas untuk pembaruan terbaru\n• Jangan ragu untuk membagikan insight dan analisis Anda di grup"
        },
        "ja": {
            "title": "🟢【MoonX】🟢 新規上場 / マーケットアラート 🪙",
            "token_info": "├ ${0} - {1}\n├ {2}",
            "market_cap": "💊 現在の時価総額：{0}",
            "price": "💰 現在価格：{0}",
            "holders": "👬 保有者数：{0}人",
            "launch_time": "⏳ 開始日時：［{0}］",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 オンチェーン監視",
            "smart_money": "🤏 スマートマネーの動向：過去15分間にスマートマネーによる取引が{0}件",
            "contract_security": "セキュリティ監査：",
            "security_item": " • パーミッション（許可）：[{0}] ハニーポット：[{1}]焼却プール：[{2}]ブラックリスト：[{3}]",
            "dev_info": "開発者情報：",
            "dev_status": "• 初期保有率：{0}",
            "dev_balance": "• 開発者ウォレット残高：{0} SOL",
            "top10_holding": "• トップ10ホルダーの保有率：{0}%",
            "social_info": "関連リンク：",
            "social_links": "{0}",
            "community_tips": "⚠️ リスク警告：\n • 仮想通貨投資は非常に高リスクです。必ずご自身で調査（DYOR）を行ってください\n • FOMO（乗り遅れる恐怖）に注意して、冷静に投資を行いましょう\n • ラグプル（詐欺的な資金引き抜き）やその他の詐欺手口にも注意\nMoonXコミュニティからのリマインダー：\n • 最新情報はコミュニティの発表をチェック！\n • ご自身の分析や見解も、グループで気軽にシェアしてください"
        },
        "pt": {
            "title": "🟢 [MoonX] 🟢 Nova Listagem / Alerta de Mercado 🪙",
            "token_info": "├ ${0} - {1}\n├ {2}",
            "market_cap": "💊 Valor de Mercado Atual: {0}",
            "price": "💰 Preço Atual: {0}",
            "holders": "👬 Detentores: {0}",
            "launch_time": "⏳ Início: [{0}]",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 Monitoramento On-chain",
            "smart_money": "🤏 Tendência de Smart Money: {0} transações de smart money nos últimos 15 minutos",
            "contract_security": "Audit:",
            "security_item": "• Permissões: [{0}] Honeypot: [{1}] Pool de Queima: [{2}] Lista Negra: [{3}]",
            "dev_info": "Informações do Desenvolvedor:",
            "dev_status": "• Participação Inicial: {0}",
            "dev_balance": "• Saldo da Carteira Dev: {0} SOL",
            "top10_holding": "• Participação dos 10 Maiores Detentores: {0}%",
            "social_info": "Relacionados:",
            "social_links": "{0}",
            "community_tips": "⚠️ Aviso de Risco:\n • Investimentos em criptomoedas são extremamente arriscados. Sempre faça sua própria pesquisa (DYOR)\n • Evite o FOMO (medo de ficar de fora) – Invista com racionalidade\n • Fique atento a rug pulls e outras táticas de golpe\nLembrete da Comunidade MoonX:\n • Acompanhe os anúncios da comunidade para as atualizações mais recentes\n • Sinta-se à vontade para compartilhar suas análises e opiniões no grupo"
        },
        "fr": {
            "title": "🟢 [MoonX] 🟢 Nouvelle Cotation / Alerte Marché 🪙",
            "token_info": "├ ${0} - {1}\n├ {2}",
            "market_cap": "💊 Capitalisation boursière actuelle : {0}",
            "price": "💰 Prix actuel : {0}",
            "holders": "👬 Nombre de détenteurs : {0}",
            "launch_time": "⏳ Heure de lancement : [{0}]",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 Surveillance On-chain",
            "smart_money": "🤏 Tendance Smart Money : {0} transactions de smart money au cours des 15 dernières minutes",
            "contract_security": "Audit :",
            "security_item": "• Permissions : [{0}] Honeypot : [{1}] Burn Pool : [{2}] Liste noire : [{3}]",
            "dev_info": "Informations sur le développeur :",
            "dev_status": "• Possession initiale : {0}",
            "dev_balance": "• Solde du portefeuille développeur : {0} SOL",
            "top10_holding": "• Part détenue par le Top 10 : {0}%",
            "social_info": "Liens associés :",
            "social_links": "🔗 Influenceur Twitter : {0} || Site officiel : {1} || Telegram : {2} || Recherche sur X : {3}",
            "community_tips": "⚠️ Avertissement sur les risques :\n • Les investissements en cryptomonnaie sont extrêmement risqués. Faites toujours vos propres recherches (DYOR).\n • Évitez le FOMO (peur de rater une opportunité) – Investissez de manière rationnelle.\n • Méfiez-vous des Rug Pulls et autres arnaques.\nRappel à la communauté MoonX :\n • Restez à l'écoute des annonces de la communauté pour les dernières mises à jour.\n • N'hésitez pas à partager vos analyses et observations dans le groupe.",
            "trade_button": "⚡️Commerce Rapide⬆️",
            "chart_button": "👉Voir Graphique⬆️"
        },
        "es": {
            "title": "🟢 [MoonX] 🟢 Nueva Lista / Alerta de Mercado 🪙:",
            "token_info": "├ ${0} - {1}\n├ {2}",
            "market_cap": "💊 Capitalización de Mercado Actual: {0}",
            "price": "💰 Precio Actual: {0}",
            "holders": "👬 Holders: {0}",
            "launch_time": "⏳ Hora de Inicio: [{0}]",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 Monitoreo On-chain",
            "smart_money": "🤏 Tendencia de Smart Money: {0} operaciones de smart money en los últimos 15 minutos",
            "contract_security": "Auditoría:",
            "security_item": "• Permisos: [{0}] Honeypot: [{1}] Burn Pool: [{2}] Lista negra: [{3}]",
            "dev_info": "Info del Desarrollador:",
            "dev_status": "• Tenencia inicial: {0}",
            "dev_balance": "• Balance del wallet del dev: {0} SOL",
            "top10_holding": "• Participación del Top 10 de holders: {0}%",
            "social_info": "Relacionado:",
            "social_links": "🔗 Twitter Influencer: {0} || Sitio Web Oficial: {1} || Telegram: {2} || Buscar en X: {3}",
            "community_tips": "⚠️ Advertencia de Riesgo:\n • Las inversiones en criptomonedas son extremadamente riesgosas. Siempre haz tu propia investigación (DYOR)\n • Evita el FOMO (miedo a quedarse fuera) – Invierte racionalmente\n • Cuidado con los rug pulls y otras estafas\nRecordatorio de la Comunidad MoonX:\n • Mantente atento a los anuncios de la comunidad para conocer las últimas actualizaciones\n • Siéntete libre de compartir tus análisis e ideas en el grupo",
            "trade_button": "⚡️Comercio Rápido⬆️",
            "chart_button": "👉Ver Gráfico⬆️"
        },
        "tr": {
            "title": "🟢 [MoonX] 🟢 Yeni Listeleme / Pazar Uyarısı 🪙:",
            "token_info": "├ ${0} - {1}\n├ {2}",
            "market_cap": "💊 Mevcut Piyasa Değeri: {0}",
            "price": "💰 Mevcut Fiyat: {0}",
            "holders": "👬 Sahipler: {0}",
            "launch_time": "⏳ Başlangıç Zamanı: [{0}]",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 Zincir Üzeri İzleme",
            "smart_money": "🤏 Akıllı Para Trendi: Son 15 dakikada {0} akıllı para işlemi",
            "contract_security": "Denetim:",
            "security_item": "• İzinler: [{0}] Honeypot: [{1}] Burn Pool: [{2}] Blacklist: [{3}]",
            "dev_info": "Geliştirici Bilgisi:",
            "dev_status": "• Başlangıç Sahipliği: {0}",
            "dev_balance": "• Geliştirici Cüzdan Bakiyesi: {0} SOL",
            "top10_holding": "• İlk 10 Sahibin Payı: {0}%",
            "social_info": "İlgili:",
            "social_links": "🔗 Twitter Etkileyici: {0} || Resmi Web Sitesi: {1} || Telegram: {2} || X'te ara: {3}",
            "community_tips": "⚠️ Risk Uyarısı:\n • Kripto para yatırımları son derece risklidir. Her zaman DYOR (Kendi Araştırmanızı Yapın)\n • FOMO (Kaçırma Korkusu)dan kaçının – Mantıklı bir şekilde yatırım yapın\n • Rug Pull ve diğer dolandırıcılık taktiklerine karşı dikkatli olun\nMoonX Topluluk Hatırlatması:\n • En son güncellemeler için topluluk duyurularını takip edin\n • Grup içinde görüşlerinizi ve analizlerinizi paylaşmaktan çekinmeyin",
            "trade_button": "⚡️Hızlı İşlem⬆️",
            "chart_button": "👉Grafiği Kontrol Et⬆️"
        },
        "de": {
            "title": "🟢 [MoonX] 🟢 Neue Listung / Marktmitteilung 🪙:",
            "token_info": "├ ${0} ({1}) – {2}",
            "market_cap": "💊 Aktuelle Marktkapitalisierung: {0}",
            "price": "💰 Aktueller Preis: {0}",
            "holders": "👬 Halter: {0}",
            "launch_time": "⏳ Startzeit: [{0}]",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 On-Chain-Überwachung",
            "smart_money": "🤏 Smart-Money-Trend: {0} Smart-Money-Transaktionen in den letzten 15 Minuten",
            "contract_security": "Prüfung:",
            "security_item": "• Berechtigungen: [{0}] Honeypot: [{1}] Burn Pool: [{2}] Blacklist: [{3}]",
            "dev_info": "Entwicklerinformationen:",
            "dev_status": "• Anfänglicher Halteanteil: {0}",
            "dev_balance": "• Entwickler-Wallet-Guthaben: {0} SOL",
            "top10_holding": "• Anteil der Top-10-Halter: {0}%",
            "social_info": "Zugehörige Links:",
            "social_links": "🔗 Twitter-Influencer: {0} || Offizielle Website: {1} || Telegram: {2} || Suche auf X: {3}",
            "community_tips": "⚠️ Risikohinweis:\n• Kryptowährungsinvestitionen sind extrem riskant. Führen Sie stets eigene Recherchen durch (DYOR).\n• Vermeiden Sie FOMO (Fear of Missing Out) – Investieren Sie rational.\n• Achten Sie auf Rug Pulls und andere Betrugsmethoden.\nHinweis der MoonX-Community:\n• Bleiben Sie über Community-Ankündigungen auf dem Laufenden.\n• Teilen Sie gerne Ihre Erkenntnisse und Analysen in der Gruppe.",
            "trade_button": "⚡️Schnellhandel⬆️",
            "chart_button": "👉Chart Prüfen⬆️"
        },
        "it": {
            "title": "🟢 [MoonX] 🟢 Nuove Inserzioni / Avviso di Mercato 🪙:",
            "token_info": "├ ${0} ({1}) – {2}",
            "market_cap": "💊 Cap di Mercato Attuale: {0}",
            "price": "💰 Prezzo Attuale: {0}",
            "holders": "👬 Detentori: {0}",
            "launch_time": "⏳ Ora di Inizio: [{0}]",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 Monitoraggio On-chain",
            "smart_money": "🤏 Trend Smart Money: {0} azioni di trading di Smart Money negli ultimi 15 minuti",
            "contract_security": "Controllo:",
            "security_item": "• Permessi: [{0}] Honeypot: [{1}] Pool di Burn: [{2}] Blacklist: [{3}]",
            "dev_info": "Informazioni sullo Sviluppatore:",
            "dev_status": "• Detenzione Iniziale: {0}",
            "dev_balance": "• Saldo del Wallet dello Sviluppatore: {0} SOL",
            "top10_holding": "• Quota dei Primi 10 Detentori: {0}%",
            "social_info": "Correlato:",
            "social_links": "🔗 Influencer su Twitter: {0} || Sito Ufficiale: {1} || Telegram: {2} || Cerca X: {3}",
            "community_tips": "⚠️ Avviso di Rischio:\n• Gli investimenti in criptovalute sono estremamente rischiosi. Fai sempre le tue ricerche (DYOR)\n• Evita il FOMO (Paura di Perdere un'Opportunità) – Investi in modo razionale\n• Fai attenzione ai Rug Pulls e ad altre tattiche fraudolente\nPromemoria della Comunità MoonX:\n• Resta aggiornato sugli annunci della comunità per le ultime novità\n• Sentiti libero di condividere le tue intuizioni e analisi nel gruppo",
            "trade_button": "⚡️Trading Rapido⬆️",
            "chart_button": "👉Controlla Grafico⬆️"
        },
        "ar": {
            "title": "🟢 [MoonX] 🟢 قائمة جديدة / تنبيه السوق 🟢:",
            "token_info": "├ ${0} ({1}) – {2}",
            "market_cap": "💊 القيمة السوقية الحالية: {0}",
            "price": "💰 السعر الحالي: {0}",
            "holders": "👬 حاملو السندات: {0}",
            "launch_time": "⏳ وقت البدء: [{0}]",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 مراقبة البلوكتشين",
            "smart_money": "🤏 اتجاه المال الذكي: {0} تداولات أموال ذكية في آخر 15 دقيقة",
            "contract_security": ":التدقيق",
            "security_item": "• الأذونات: [{0}] نقطة التداوُل: [{1}] مجموعة الحرق: [{2}] قائمة الحرق: [{3}]",
            "dev_info": "معلومات المطور:",
            "dev_status": "• الحيازة الأولية {0}",
            "dev_balance": "• رصيد محفظة المطور: {0} سول",
            "top10_holding": "• أفضل 10 حائزين على أعلى 10 حصص {0}%",
            "social_info": "🔗 ذات صلة",
            "social_links": "مؤثر تويتر: {0} | | الموقع الرسمي: {1} | | | تيليجرام {2} | | بحث X: {3}",
            "community_tips": "⚠️ تحذير من المخاطر:\n -و الاستثمارات في العملات الرقمية محفوفة بالمخاطر. DYOR (قم دائمًا بالبحث بنفسك)\n • تجنب FOMO (الخوف من فقدان الفرصة) - استثمر بعقلانية\n • احترس من العمليات الاحتيالية مثل \" عملية السحب على البساط (Rug Pulls)\" وأساليب الاحتيال الأخرى\nتذكير من مجتمع MoonX:\n • ترقبوا إعلانات المجتمع للاطلاع على آخر التحديثات\n • لا تتردد في مشاركة أفكارك وتحليلاتك في المجموعة"
        },
        "fa": {
            "title": "🟢 [MoonX] 🟢 لیست جدید / هشدار بازار 🪙:",
            "token_info": "├ ${0} ({1}) - {2}",
            "market_cap": "💊 ارزش بازار فعلی: {0}",
            "price": "💰 قیمت فعلی: {0}",
            "holders": "👬 دارندگان: {0}",
            "launch_time": "⏳ زمان شروع: [{0}]",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 نظارت زنجیره‌ای",
            "smart_money": "🤏 ترند پول هوشمند: {0} معامله پول هوشمند در 15 دقیقه گذشته",
            "contract_security": "بررسی امنیت:",
            "security_item": "• مجوزها: [{0}] هانی پات: [{1}] استخر سوختگی: [{2}] لیست سیاه: [{3}]",
            "dev_info": "اطلاعات توسعه دهنده:",
            "dev_status": "• برگزاری اولیه: {0}",
            "dev_balance": "• موجودی کیف پول توسعه دهنده: {0} SOL",
            "top10_holding": "• 10 سهم برتر: {0}%",
            "social_info": "مرتبط:",
            "social_links": "🔗 اینفلوئنسر توییتر: {0} || وب سایت رسمی: {1} || تلگرام: {2} || جستجوی X: {3}",
            "community_tips": "⚠️ هشدار خطر:\n • سرمایه گذاری در ارزهای دیجیتال بسیار پرخطر است. همیشه DYOR (خودت تحقیق کن)\n • اجتناب از FOMO (ترس از دست دادن) - سرمایه گذاری منطقی\n • مراقب قالیچه ها و دیگر تاکتیک های کلاهبرداری باشید\nیادآوری انجمن MoonX:\n • برای اطلاع از آخرین به روز رسانی ها منتظر اطلاعیه های انجمن باشید\n • با خیال راحت بینش و تحلیل خود را در گروه به اشتراک بگذارید"
        },
        "vn": {
            "title": "🟢 [MoonX] 🟢 Niêm yết Mới / Biến Động Thị Trường 🪙:",
            "token_info": "├ ${0} ({1}) – {2}",
            "market_cap": "💊 Vốn hóa thị trường hiện tại: {0}",
            "price": "💰 Giá hiện tại: {0}",
            "holders": "👬 Số lượng người nắm giữ: {0}",
            "launch_time": "⏳ Thời gian khởi tạo: [{0}]",
            "divider": "——————————————————",
            "chain_monitoring": "🔍 Giám sát On-chain",
            "smart_money": "🤏 Xu hướng Smart Money: {0} giao dịch từ ví thông minh trong 15 phút qua",
            "contract_security": "Kiểm toán:",
            "security_item": "• Quyền truy cập: [{0}] Honeypot: [{1}] Burn Pool: [{2}] Danh sách đen: [{3}]",
            "dev_info": "Thông tin nhà phát triển:",
            "dev_status": "• Sở hữu ban đầu: {0}",
            "dev_balance": "• Số dư ví Dev: {0} SOL",
            "top10_holding": "• Tỷ lệ nắm giữ của Top 10: {0}%",
            "social_info": "Liên quan:",
            "social_links": "🔗 Twitter Influencer: {0} || Website chính thức: {1} || Telegram: {2} || Tìm trên Twitter: {3}",
            "community_tips": "⚠️ Cảnh báo rủi ro:\n • Đầu tư tiền mã hóa có độ rủi ro rất cao. Luôn tự nghiên cứu (DYOR)\n • Tránh tâm lý FOMO (sợ bỏ lỡ) – Hãy đầu tư một cách lý trí\n • Cẩn thận với Rug Pull và các hình thức lừa đảo khác\nNhắc nhở từ cộng đồng MoonX:\n • Theo dõi thông báo cộng đồng để cập nhật mới nhất\n • Thoải mái chia sẻ nhận định và phân tích của bạn trong nhóm",
            "trade_button": "⚡️Giao Dịch Nhanh⬆️",
            "chart_button": "👉Kiểm Tra Biểu Đồ⬆️"
        },
        
        # 精選信號模板
        "premium": {
            "zh": {
                "title": "MoonX 精選信號",
                "token_info": "🚀 代幣：{0}（{1}）",
                "price": "💰 價格：${0}",
                "contract": "📌 合約：{0}",
                "market_cap_alert": "⚙️ {0}次預警 ⚠️ 市值達到 {1}",
                "launch_time": "⏰ 開盤時間：{0}",
                "token_check": "📝 代幣檢測：燒池子 {0} | 權限 {1} | TOP10 {2}% {3} | 貔貅 {4}",
                "links": "🔗 MoonX K線：{0}\n🔍 X討論：{1}",
                "highlight_tags": "🔥 亮點：{0}",
                "divider": ""
            },
            "en": {
                "title": "MoonX Featured Signal",
                "token_info": "🚀 Token: {0} ({1})",
                "price": "💰 Price: ${0}",
                "contract": "📌 Contract: {0}",
                "market_cap_alert": "⚙️ {0} Warning ⚠️ MCap reached {1}",
                "launch_time": "⏰ Start Time: {0}",
                "token_check": "📝 Audit: Burn Pool {0} | Permission {1} | TOP10 {2}% {3} | Honeypot {4}",
                "links": "🔗 MoonX Chart: {0}\n🔍 X Discussion: {1}",
                "highlight_tags": "🔥 Highlights: {0}",
                "divider": ""
            },
            "ru": {
                "title": "MoonX Рекомендованный сигнал",
                "token_info": "🚀 Токен: {0} ({1})",
                "price": "💰 Цена: ${0}",
                "contract": "📌 Контракт: {0}",
                "market_cap_alert": "⚙️ Уведомление: Предупреждение {0} ⚠️ Р. Кап. {1}",
                "launch_time": "⏰ Время старта: {0}",
                "token_check": "📝 Аудит: Пул сжигания {0} | Права доступа {1} | ТОП10 {2}% {3} | Honeypot {4}",
                "links": "🔗 График MoonX: {0}\n🔍 Обсуждение в X: {1}",
                "highlight_tags": "🔥 Выделенные метки: {0}",
                "divider": ""
            },
            "id": {
                "title": "Sinyal Unggulan MoonX",
                "token_info": "🚀 Token: {0} ({1})",
                "price": "💰 Harga: ${0}",
                "contract": "📌 Kontrak: {0}",
                "market_cap_alert": "⚙️ Alert: Peringatan {0} ⚠️ MCap mencapai {1}",
                "launch_time": "⏰ Waktu Mulai: {0}",
                "token_check": "📝 Audit: Burn Pool {0} | Permission {1} | TOP10 {2}% {3} | Honeypot {4}",
                "links": "🔗 MoonX Chart: {0}\n🔍 X Diskusi: {1}",
                "highlight_tags": "🔥 Key Highlights: {0}",
                "divider": ""
            },
            "ja": {
                "title": "MoonX 注目シグナル",
                "token_info": "🚀 トークン: {0}（{1}）",
                "price": "💰 価格: ${0}",
                "contract": "📌 コントラクト: {0}",
                "market_cap_alert": "⚙️ アラート: 第{0}警告 ⚠️ MCapが{1}に到達",
                "launch_time": "⏰ 開始時間: {0}",
                "token_check": "📝 セキュリティ監査: Burn Pool {0} | パーミッション {1} | 上位10アドレスの保有率 {2}% {3} | ハニーポット対策 {4}",
                "links": "🔗 MoonX チャート: {0}\n🔍 X（旧Twitter）での議論: {1}",
                "highlight_tags": "🔥 注目マーク: {0}",
                "divider": ""
            },
            "pt": {
                "title": "Sinal em Destaque da MoonX",
                "token_info": "🚀 Token: {0} ({1})",
                "price": "💰 Preço: ${0}",
                "contract": "📌 Contrato: {0}",
                "market_cap_alert": "⚙️ Alerta: {0} Aviso ⚠️ MCap atingiu {1}",
                "launch_time": "⏰ Tempo de Início: {0}",
                "token_check": "📝 Audit: Burn Pool {0} | Permissões {1} | TOP10 {2}% {3} | Honeypot {4}",
                "links": "🔗 Gráfico MoonX: {0}\n🔍 Discussão no X (Twitter): {1}",
                "highlight_tags": "🔥 Principais Destaques: {0}",
                "divider": ""
            },
            "fr": {
                "title": "Signal en vedette sur MoonX",
                "token_info": "🚀 Token : {0} ({1})",
                "price": "💰 Prix : ${0}",
                "contract": "📌 Contrat : {0}",
                "market_cap_alert": "⚙️ Alerte : {0} alerte ⚠️ MCap atteint {1}",
                "launch_time": "⏰ Heure de lancement : {0}",
                "token_check": "📝 Audit : Burn Pool {0} | Permissions {1} | TOP10 détient {2}% {3} | Honeypot {4}",
                "links": "🔗 Graphique MoonX : {0}\n🔍 Discussion sur X : {1}",
                "highlight_tags": "🔥 Points forts : {0}",
                "divider": ""
            },
            "es": {
                "title": "MoonX Signal Destacado",
                "token_info": "🚀 Token: {0} ({1})",
                "price": "💰 Precio: ${0}",
                "contract": "📌 Contrato: {0}",
                "market_cap_alert": "⚙️ Alerta: {0} Aviso ⚠️ MCap alcanzó {1}",
                "launch_time": "⏰ Hora de Inicio: {0}",
                "token_check": "📝 Auditoría: Burn Pool {0} | Permiso {1} | TOP10 {2}% {3} | Honeypot {4}",
                "links": "🔗 Gráfico de MoonX: {0}\n🔍 Discusión en X: {1}",
                "highlight_tags": "🔥 Aspectos Clave: {0}",
                "divider": ""
            },
            "tr": {
                "title": "MoonX Öne Çıkan Sinyal",
                "token_info": "🚀 Token: {0} ({1})",
                "price": "💰 Fiyat: ${0}",
                "contract": "📌 Kontrat: {0}",
                "market_cap_alert": "⚙️ Uyarı: {0} Uyarı ⚠️ MCap {1}'ye ulaştı",
                "launch_time": "⏰ Başlangıç Zamanı: {0}",
                "token_check": "📝 Denetim: Yakım Havuzu {0} | Yetki {1} | TOP10 {2}% {3} | Honeypot {4}",
                "links": "🔗 MoonX Grafiği: {0}\n🔍 X Tartışması: {1}",
                "highlight_tags": "🔥 Temel Noktalar: {0}",
                "divider": ""
            },
            "de": {
                "title": "MoonX Vorgestelltes Signal",
                "token_info": "🚀 Token: {0} ({1})",
                "price": "💰 Preis: ${0}",
                "contract": "📌 Vertrag: {0}",
                "market_cap_alert": "⚙️ Alarm: {0} Warnung ⚠️ MCap hat {1} erreicht",
                "launch_time": "⏰ Startzeit: {0}",
                "token_check": "📝 Prüfung: Burn-Pool {0} | Berechtigungen {1} | TOP10 {2}% {3} | Honeypot {4}",
                "links": "🔗 MoonX-Chart: {0}\n🔍 X-Diskussion: {1}",
                "highlight_tags": "🔥 Wichtige Punkte: {0}",
                "divider": ""
            },
            "it": {
                "title": "Segnale in Evidenza MoonX",
                "token_info": "🚀 Token: {0} ({1})",
                "price": "💰 Prezzo: ${0}",
                "contract": "📌 Contratto: {0}",
                "market_cap_alert": "⚙️ Avviso: {0} Avvertimento ⚠️ MCap raggiunta {1}",
                "launch_time": "⏰ Ora di Lancio: {0}",
                "token_check": "📝 Controllo: Pool di Burn {0} | Permessi {1} | TOP10 {2}% {3} | Honeypot {4}",
                "links": "🔗 Grafico MoonX: {0}\n🔍 Discussione su X: {1}",
                "highlight_tags": "🔥 Punti Chiave: {0}",
                "divider": ""
            },
            "ar": {
                "title": "إشارة مميزة من MoonX",
                "token_info": "🚀 الرمز: {0} ({1})",
                "price": "💰 السعر: ${0}",
                "contract": "📌 العقد: {0}",
                "market_cap_alert": "⚙️ التنبيه: التحذير {0} ⚠️ MCap وصلت إلى {1}",
                "launch_time": "⏰ وقت البدء: {0}",
                "token_check": "📝 التدقيق: مجموعة الحرق {0} | الأذونات {1} | أفضل 10: {2}% {3} | فخ العسل {4}",
                "links": "🔗 رسم بياني من MoonX: {0}\n🔍 نقاش X: {1}",
                "highlight_tags": "🔥 أبرز الأحداث: {0}",
                "divider": ""
            },
            "fa": {
                "title": "سیگنال ویژه MoonX",
                "token_info": "🚀 نشانه: {0} ({1})",
                "price": "💰 قیمت: ${0}",
                "contract": "📌 قرارداد: {0}",
                "market_cap_alert": "⚙️ هشدار: {0} هشدار ⚠️ MCap به {1} رسید",
                "launch_time": "⏰ زمان شروع: {0}",
                "token_check": "📝 ممیزی: استخر سوختگی {0} | مجوز {1} | TOP10 {2}% {3} | هانی پات {4}",
                "links": "🔗 نمودار MoonX: {0}\n🔍 X بحث: {1}",
                "highlight_tags": "🔥 نکات برجسته کلیدی: {0}",
                "divider": ""
            },
            "vn": {
                "title": "MoonX - Tín Hiệu Nổi Bật",
                "token_info": "🚀 Token: {0} ({1})",
                "price": "💰 Giá: ${0}",
                "contract": "📌 Hợp đồng: {0}",
                "market_cap_alert": "⚙️ Lưu ý: Cảnh báo lần {0} ⚠️ Vốn hóa đạt {1}",
                "launch_time": "⏰ Thời gian mở giao dịch: {0}",
                "token_check": "📝 Kiểm tra Token: Burn Pool: {0} | Quyền truy cập: {1} | Top 10 nắm giữ: {2}% {3} | Honeypot {4}",
                "links": "🔗 MoonX (K-line): {0}\n🔍 Thảo luận trên X: {1}",
                "highlight_tags": "🔥 Tín hiệu: {0}",
                "divider": ""
            }
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
    twitter_text = {
        "zh": "推特", "en": "Twitter", "ko": "트위터", "ch": "推特", "ru": "Твиттер",
        "id": "Twitter", "ja": "Twitter", "pt": "Twitter", "fr": "Twitter",
        "es": "Twitter", "tr": "Twitter", "de": "Twitter", "it": "Twitter",
        "ar": "تويتر", "fa": "توییتر", "vn": "Twitter"
    }
    website_text = {
        "zh": "官网", "en": "Website", "ko": "웹사이트", "ch": "官網", "ru": "Сайт",
        "id": "Website", "ja": "ウェブサイト", "pt": "Website", "fr": "Site web",
        "es": "Sitio web", "tr": "Web sitesi", "de": "Webseite", "it": "Sito web",
        "ar": "الموقع", "fa": "وب سایت", "vn": "Website"
    }
    telegram_text = {
        "zh": "电报", "en": "Telegram", "ko": "텔레그램", "ch": "電報", "ru": "Телеграм",
        "id": "Telegram", "ja": "Telegram", "pt": "Telegram", "fr": "Telegram",
        "es": "Telegram", "tr": "Telegram", "de": "Telegram", "it": "Telegram",
        "ar": "تيليجرام", "fa": "تلگرام", "vn": "Telegram"
    }
    search_text = {
        "zh": "👉查推特", "en": "👉Search Twitter", "ko": "👉트위터 검색", "ch": "👉查推特", "ru": "👉Поиск в X",
        "id": "👉Cari Twitter", "ja": "👉Xで検索", "pt": "👉Buscar no X", "fr": "👉Rechercher sur X",
        "es": "👉Buscar en X", "tr": "👉X'te ara", "de": "👉Auf X suchen", "it": "👉Cerca su X",
        "ar": "👉البحث في X", "fa": "👉جستجو در X", "vn": "👉Tìm trên Twitter"
    }
    
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
        # dev_status_line,
        *([dev_status_line] if dev_status_line else []),
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

def format_premium_message(data: Dict, language: str = "zh") -> str:
    templates = load_templates()
    premium_templates = templates.get("premium", {})
    if language not in premium_templates:
        language = "zh"
    template = premium_templates[language]

    # 多語言亮點標籤映射
    tag_map = {
        "zh": {
            1: "KOL 地址買入",
            2: "1 小時內吸引 ≥ 3 個高淨值聰明錢地址買入",
            3: "同一聰明錢購買超過10K"
        },
        "en": {
            1: "KOL Address Buy",
            2: "≥ 3 Smart Money Buys in 1h",
            3: "Single Address Bought >10K"
        },
        "ja": {
            1: "KOL アドレスによる購入",
            2: "1 時間以内に 3 件以上のスマートマネー アドレスによる購入",
            3: "同じスマートマネーによる 10K 以上の購入"
        },
        "ru": {
            1: "Покупка адреса KOL",
            2: "≥ 3 покупки адресов умных денег за 1 час",
            3: "Один адрес купил >10K"
        },
        "es": {
            1: "Compra de Dirección KOL",
            2: "≥ 3 Compras de Direcciones Smart Money en 1h",
            3: "Una Dirección Compró >10K"
        },
        "fr": {
            1: "Achat d'adresse KOL",
            2: "≥ 3 adresses Smart Money achètent en 1h",
            3: "Adresse unique achetée >10K"
        },
        "de": {
            1: "KOL Adressenkauf",
            2: "≥ 3 Smart-Money-Käufe in 1h",
            3: "Einzelne Adresse kaufte >10K"
        },
        "it": {
            1: "Acquisto da Indirizzo KOL",
            2: "≥ 3 Acquisti da Indirizzi Smart Money in 1h",
            3: "Un Singolo Indirizzo ha Acquistato >10K"
        },
        "pt": {
            1: "Compra por Endereço de KOL",
            2: "≥ 3 Compras por Endereços de Smart Money em 1h",
            3: "Endereço Único Comprou >10K"
        },
        "tr": {
            1: "KOL Adresi Alımı",
            2: "≥ 1 saat içinde 3 Akıllı Para Adresi Alımı",
            3: "Tek Bir Adres Alımı >10K"
        },
        "ar": {
            1: "شراء من عنوان مؤثر (KOL)",
            2: "≥ 3 عمليات شراء من عناوين المال الذكي خلال ساعة واحدة",
            3: "عنوان واحد نفّذ عملية شراء > 10 آلاف"
        },
        "fa": {
            1: "خرید آدرس KOL",
            2: "≥ ۳ خرید آدرس با اسمارت مانی در ۱ ساعت",
            3: "خرید یک آدرس >10 هزار"
        },
        "id": {
            1: "Alamat Beli KOL",
            2: "≥ 3 Alamat Smart Money Beli dalam 1h",
            3: "Alamat Tunggal Membeli>10K"
        },
        "vi": {
            1: "Ví KOL mua vào",
            2: "≥ 3 ví giá trị ròng cao mua trong 1 giờ",
            3: "Cùng ví Smart Money mua vào >10K"
        }
    }
    # 取得 highlight_tags 的 index
    highlight_tag_codes = data.get("highlight_tag_codes", [])
    lang_tags = tag_map.get(language, tag_map["zh"])
    translated_tags = [lang_tags.get(code, "") for code in highlight_tag_codes if code in lang_tags]

    if translated_tags:
        highlight_line = template.get("highlight_tags", "🔥 亮點標籤：{0}").format("、".join(translated_tags))
    else:
        highlight_line = ""

    # 市值等級
    market_cap_level = data.get('market_cap_level', 1)
    market_cap_levels = {1: "100K", 2: "300K", 3: "500K"}
    market_cap_text = market_cap_levels.get(market_cap_level, "100K")
    
    # 預警次數
    alert_numbers = {
        "zh": {1: "第一", 2: "第二", 3: "第三"},
        "en": {1: "First", 2: "Second", 3: "Third"},
        "ru": {1: "1", 2: "2", 3: "3"},
        "id": {1: "Awal", 2: "Kedua", 3: "Ketiga"},
        "ja": {1: "第1", 2: "第2", 3: "第3"},
        "pt": {1: "Primeiro", 2: "Segundo", 3: "Terceiro"},
        "fr": {1: "Première", 2: "Deuxième", 3: "Troisième"},
        "es": {1: "Primer", 2: "Segundo", 3: "Tercer"},
        "tr": {1: "İlk", 2: "İkinci", 3: "Üçüncü"},
        "de": {1: "Erste", 2: "Zweite", 3: "Dritte"},
        "it": {1: "Primo", 2: "Secondo", 3: "Terzo"},
        "ar": {1: "الأول", 2: "الثاني", 3: "الثالث"},
        "fa": {1: "اولین", 2: "دوم", 3: "سوم"},
        "vn": {1: "đầu", 2: "2", 3: "3"}
    }
    alert_number_text = alert_numbers.get(language, alert_numbers["en"]).get(market_cap_level, alert_numbers["en"][1])
    
    stars = "⭐️" * market_cap_level
    
    # 格式化預警消息
    market_cap_alert_line = template["market_cap_alert"].format(alert_number_text, market_cap_text)
    market_cap_alert_line_with_stars = f"<b>{market_cap_alert_line}{stars}</b>"


    # 合約可複製
    contract_address = data.get('token_address', '--')
    contract_display = f"<code>{contract_address}</code>"

    # MoonX K線、X討論超連結
    moonx_kline_url = f"https://www.bydfi.com/en/moonx/solana/token?address={contract_address}"
    x_search_url = f"https://x.com/search?q={contract_address}&src=typed_query"
    moonx_kline_link = f"<a href='{moonx_kline_url}'>MoonX</a>"
    x_search_link = f"<a href='{x_search_url}'>X</a>"

    # 開盤時長
    if data.get('open_time'):
        try:
            launch_timestamp = int(data['open_time'])
            current_time = int(time.time())
            duration = current_time - launch_timestamp
            days = duration // (24 * 3600)
            hours = (duration % (24 * 3600)) // 3600
            minutes = (duration % 3600) // 60
            if language == 'zh':
                launch_time_display = f"{days}天{hours}小時{minutes}分鐘" if days > 0 else f"{hours}小時{minutes}分鐘" if hours > 0 else f"{minutes}分鐘"
            else:
                launch_time_display = f"{days}d {hours}h {minutes}m" if days > 0 else f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
        except Exception:
            launch_time_display = '--'
    else:
        launch_time_display = '--'

    # 組裝訊息
    message_parts = [
        template["title"],
        template["token_info"].format(data.get('token_name', 'Unknown'), data.get('token_symbol', 'Unknown')),
        template["price"].format(data.get('price_display', '--')),
        template["contract"].format(contract_display),
        template["launch_time"].format(launch_time_display),
        template["token_check"].format(
            '✅' if data.get('burn_pool', False) else '❌',
            '✅' if data.get('authority', False) else '❌',
            data.get('top10_holding_display', '--'),
            '✅' if data.get('top10_holding', 0) else '❌',
            '✅' if data.get('honeypot', False) else '❌'
        ),
        template["links"].format(moonx_kline_link, x_search_link),
        highlight_line,
        "", # Blank line before alert
        "", # Extra blank line to ensure proper spacing
        market_cap_alert_line_with_stars, # 使用新的預警消息行
        template["divider"]
    ]
    message = "\n".join([part for part in message_parts if part])
    return message