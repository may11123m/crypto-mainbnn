import asyncio
import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

from services.price_service import price_service
from services.search_service import search_service
from services.indicator_service import indicator_service
from services.security_service import security_service
from services.futures_service import futures_service
from services.news_service import news_service
from services.ai_service import ai_service
from services.portfolio_service import portfolio_service
from services.alert_service import alert_service

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ==========================================
# LIST OF COINS (MAJORS, ALTS, MEMES)
# ==========================================
COIN_PAGES = {
    1: {
        "title": "💎 Major & Layer 1s (Page 1/3)",
        "coins": ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "AVAX", "DOT", "NEAR", "SUI", "APT", "LINK"]
    },
    2: {
        "title": "🚀 Alts, L2 & AI (Page 2/3)",
        "coins": ["ARB", "OP", "MATIC", "RENDER", "FET", "INJ", "TIA", "SEI", "ATOM", "FTM", "ALGO", "STX"]
    },
    3: {
        "title": "🔥 Memes & High Volatility (Page 3/3)",
        "coins": ["DOGE", "SHIB", "PEPE", "FLOKI", "WIF", "BONK", "POPCAT", "MEME", "ORDI", "1000SATS", "BOME", "NOT"]
    }
}

# --- تابع کمکی حذف خودکار پیام‌ها ---
async def auto_delete_msg(chat_id: int, message_id: int, delay: int = 180):
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass

# --- سرور وب برای زنده نگه داشتن ربات روی Render ---
async def handle_health_check(request):
    return web.Response(text="Bot is online and running!")

# --- حلقه پس‌زمینه بررسی هشدارهای قیمت ---
async def check_alerts_loop():
    while True:
        try:
            alerts = await alert_service.get_alerts_all() if hasattr(alert_service, 'get_alerts_all') else []
            for alert in alerts:
                data = await price_service.get_crypto_price(alert['symbol'])
                if "error" in data:
                    continue

                current_price = data['price']
                triggered = False

                if alert['condition'] == "ABOVE" and current_price >= alert['target_price']:
                    triggered = True
                elif alert['condition'] == "BELOW" and current_price <= alert['target_price']:
                    triggered = True

                if triggered:
                    msg_text = (
                        f"🚨 **PRICE ALERT TRIGGERED!** 🚨\n\n"
                        f"💎 **Token:** `{alert['symbol']}`\n"
                        f"🎯 **Target Price:** `${alert['target_price']:,.4f}`\n"
                        f"💵 **Current Price:** `${current_price:,.4f}`\n"
                        f"📊 **Condition:** Price went `{alert['condition']}` target!"
                    )
                    try:
                        await bot.send_message(chat_id=alert['user_id'], text=msg_text, parse_mode="Markdown")
                        await alert_service.remove_alert(alert['user_id'], alert['id'])
                    except Exception as err:
                        logger.error(f"Failed to send alert to {alert['user_id']}: {err}")

        except Exception as e:
            logger.error(f"Error in alert monitoring loop: {e}")

        await asyncio.sleep(30)

# ==========================================
# KEYBOARD BUILDERS
# ==========================================

def get_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📈 Technical & AI Analysis", callback_data="nav_analysis:1"),
            InlineKeyboardButton(text="⚡ Futures Metrics", callback_data="nav_futures:1")
        ],
        [
            InlineKeyboardButton(text="📰 Latest News", callback_data="nav_news:all"),
            InlineKeyboardButton(text="🛡️ Contract Audit", callback_data="nav_audit")
        ],
        [
            InlineKeyboardButton(text="💼 Portfolio Tracker", callback_data="nav_portfolio"),
            InlineKeyboardButton(text="🔔 Price Alerts", callback_data="nav_alerts")
        ],
        [
            InlineKeyboardButton(text="📊 Live Market Prices", callback_data="nav_prices:1")
        ]
    ])

def get_coins_keyboard(action_prefix: str, page: int = 1):
    page_data = COIN_PAGES.get(page, COIN_PAGES[1])
    coins = page_data["coins"]
    
    # ساخت گرید ۳ ستونه از ارزها
    grid = []
    row = []
    for coin in coins:
        row.append(InlineKeyboardButton(text=f"🪙 {coin}", callback_data=f"{action_prefix}:{coin}"))
        if len(row) == 3:
            grid.append(row)
            row = []
    if row:
        grid.append(row)
        
    # دکمه‌های صفحه‌بندی
    prev_page = 3 if page == 1 else page - 1
    next_page = 1 if page == 3 else page + 1
    
    nav_row = [
        InlineKeyboardButton(text="◀️ Prev", callback_data=f"page_{action_prefix}:{prev_page}"),
        InlineKeyboardButton(text=f"📄 {page}/3", callback_data="noop"),
        InlineKeyboardButton(text="Next ▶️", callback_data=f"page_{action_prefix}:{next_page}")
    ]
    grid.append(nav_row)
    grid.append([InlineKeyboardButton(text="🔙 Main Menu", callback_data="nav_main")])
    
    return InlineKeyboardMarkup(inline_keyboard=grid)

def get_report_keyboard(refresh_callback: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Refresh Data", callback_data=refresh_callback),
            InlineKeyboardButton(text="🔙 Main Menu", callback_data="nav_main")
        ]
    ])

# ==========================================
# COMMAND HANDLERS
# ==========================================

@dp.message(Command("start"))
async def start_handler(message: Message):
    welcome_text = (
        "🌐 **CryptoPulse Pro v2 & AI Intelligence**\n\n"
        "Welcome! Select an option from the menu below or send direct commands:\n\n"
        "• Send ticker (`BTC`, `ETH`, `PEPE`) for **Instant Price**\n"
        "• `ta btc` - **Technical & AI Analysis**\n"
        "• `ft btc` - **Futures Funding & OI**\n"
        "• `check 0x...` - **Smart Contract Audit**\n"
        "• `/news` - **Real-time Crypto News**\n"
        "• `/portfolio` or `/add btc 0.5 65000` - **Portfolio**\n"
        "• `alert btc 65000` or `/myalerts` - **Price Alerts**"
    )
    msg = await message.answer(welcome_text, parse_mode="Markdown", reply_markup=get_main_keyboard())
    asyncio.create_task(auto_delete_msg(msg.chat.id, msg.message_id, 300))

# --- Text Commands ---
@dp.message(Command("analyze"))
@dp.message(F.text.lower().startswith("ta "))
async def handle_ai_analysis(message: Message):
    symbol = message.text.split()[1].upper() if message.text.startswith("/analyze") else message.text.lower().replace("ta ", "").strip().upper()
    if not symbol:
        await message.answer("⚠️ **Usage:** `ta btc` or `/analyze btc`", parse_mode="Markdown")
        return

    msg = await message.answer(f"🔄 Analyzing **{symbol}** market metrics & technicals...")
    report = await run_analysis_logic(symbol)
    await msg.edit_text(report, parse_mode="Markdown", reply_markup=get_report_keyboard(f"do_ta:{symbol}"))
    asyncio.create_task(auto_delete_msg(msg.chat.id, msg.message_id, 180))

@dp.message(Command("futures"))
@dp.message(F.text.lower().startswith("ft "))
async def handle_futures(message: Message):
    symbol = message.text.split()[1].upper() if message.text.startswith("/futures") else message.text.lower().replace("ft ", "").strip().upper()
    if not symbol:
        await message.answer("⚠️ **Usage:** `ft btc` or `/futures btc`", parse_mode="Markdown")
        return

    msg = await message.answer(f"📈 Fetching Futures metrics for **{symbol}**...")
    report = await run_futures_logic(symbol)
    await msg.edit_text(report, parse_mode="Markdown", reply_markup=get_report_keyboard(f"do_ft:{symbol}"))
    asyncio.create_task(auto_delete_msg(msg.chat.id, msg.message_id, 120))

@dp.message(Command("audit"))
@dp.message(F.text.lower().startswith("check "))
async def handle_security_check(message: Message):
    address = message.text.split()[1] if message.text.startswith("/audit") else message.text.lower().replace("check ", "").strip()
    if not address:
        await message.answer("⚠️ **Usage:** `check 0x...` or `/audit 0x...`", parse_mode="Markdown")
        return

    msg = await message.answer(f"🛡️ Auditing contract address **`{address[:10]}...`**...")
    audit_data = await security_service.check_token_security(address)
    report = security_service.format_security_report(audit_data)
    await msg.edit_text(report, parse_mode="Markdown", reply_markup=get_report_keyboard("nav_main"))
    asyncio.create_task(auto_delete_msg(msg.chat.id, msg.message_id, 180))

@dp.message(Command("news"))
async def handle_news(message: Message):
    parts = message.text.split()
    coin = parts[1] if len(parts) > 1 else "all"
    items = await news_service.get_latest_news(coin=None if coin == "all" else coin)
    report = news_service.format_news_report(items, coin=None if coin == "all" else coin)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Refresh News", callback_data=f"do_news:{coin}")],
        [InlineKeyboardButton(text="🔙 Main Menu", callback_data="nav_main")]
    ])
    msg = await message.answer(report, parse_mode="Markdown", disable_web_page_preview=True, reply_markup=kb)
    asyncio.create_task(auto_delete_msg(msg.chat.id, msg.message_id, 180))

@dp.message(Command("portfolio"))
async def handle_portfolio(message: Message):
    report = await run_portfolio_logic(message.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Refresh Portfolio", callback_data="do_portfolio")],
        [InlineKeyboardButton(text="🔙 Main Menu", callback_data="nav_main")]
    ])
    msg = await message.answer(report, parse_mode="Markdown", reply_markup=kb)
    asyncio.create_task(auto_delete_msg(msg.chat.id, msg.message_id, 120))

@dp.message(Command("add"))
async def handle_add_portfolio(message: Message):
    parts = message.text.split()
    if len(parts) < 4:
        await message.answer("⚠️ **Usage:** `/add <symbol> <amount> <buy_price>`\nExample: `/add btc 0.5 65000`", parse_mode="Markdown")
        return
    try:
        symbol, amount, buy_price = parts[1], float(parts[2]), float(parts[3])
        success = await portfolio_service.add_asset(message.from_user.id, symbol, amount, buy_price)
        text = f"✅ Added `{amount}` **{symbol.upper()}** at `${buy_price:,.2f}` to portfolio." if success else "❌ Failed to add asset."
    except ValueError:
        text = "❌ Invalid numbers provided."
    msg = await message.answer(text, parse_mode="Markdown")
    asyncio.create_task(auto_delete_msg(msg.chat.id, msg.message_id, 60))

@dp.message(F.text.lower().startswith("alert "))
async def handle_set_alert(message: Message):
    parts = message.text.strip().split()
    if len(parts) < 3:
        await message.answer("❌ **Usage:** `alert <symbol> <target_price>`\nExample: `alert btc 65000`", parse_mode="Markdown")
        return
    symbol = parts[1].upper()
    try:
        target_price = float(parts[2])
    except ValueError:
        await message.answer("❌ Invalid target price.")
        return

    data = await price_service.get_crypto_price(symbol)
    if "error" in data:
        await message.answer(f"❌ Symbol **'{symbol}'** not found.")
        return

    current_price = data['price']
    condition = "ABOVE" if target_price > current_price else "BELOW"
    success = await alert_service.add_alert(message.from_user.id, symbol, target_price, condition)
    cond_emoji = "📈" if condition == "ABOVE" else "📉"

    text = (
        f"✅ **Price Alert Set Successfully!**\n\n"
        f"🪙 **Token:** `{symbol}`\n"
        f"💵 **Current Price:** `${current_price:,.4f}`\n"
        f"🎯 **Target Price:** `${target_price:,.4f}`\n"
        f"{cond_emoji} **Trigger:** When price goes `{condition}` target."
    ) if success else "❌ Failed to set alert."

    msg = await message.answer(text, parse_mode="Markdown")
    asyncio.create_task(auto_delete_msg(msg.chat.id, msg.message_id, 60))

@dp.message(Command("myalerts"))
async def handle_my_alerts(message: Message):
    report = await run_alerts_logic(message.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Refresh Alerts", callback_data="do_alerts")],
        [InlineKeyboardButton(text="🔙 Main Menu", callback_data="nav_main")]
    ])
    msg = await message.answer(report, parse_mode="Markdown", reply_markup=kb)
    asyncio.create_task(auto_delete_msg(msg.chat.id, msg.message_id, 120))

@dp.message(Command("delalert"))
async def handle_del_alert(message: Message):
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("❌ **Usage:** `/delalert <alert_id>`", parse_mode="Markdown")
        return
    alert_id = int(parts[1])
    success = await alert_service.remove_alert(message.from_user.id, alert_id)
    text = f"🗑️ Alert ID `{alert_id}` removed." if success else "❌ Alert not found."
    msg = await message.answer(text, parse_mode="Markdown")
    asyncio.create_task(auto_delete_msg(msg.chat.id, msg.message_id, 60))

# ==========================================
# INTERACTIVE CALLBACK QUERY HANDLERS
# ==========================================

@dp.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery):
    await callback.answer()

@dp.callback_query(F.data == "nav_main")
async def cb_nav_main(callback: CallbackQuery):
    await callback.answer()
    welcome_text = (
        "🌐 **CryptoPulse Pro v2 Main Menu**\n\n"
        "Select an option below to perform real-time crypto operations:"
    )
    await callback.message.edit_text(welcome_text, parse_mode="Markdown", reply_markup=get_main_keyboard())

# --- Navigation & Coin Grid Pickers ---
@dp.callback_query(F.data.startswith("nav_analysis:"))
@dp.callback_query(F.data.startswith("page_do_ta:"))
async def cb_nav_analysis(callback: CallbackQuery):
    await callback.answer()
    page = int(callback.data.split(":")[1])
    page_title = COIN_PAGES[page]["title"]
    await callback.message.edit_text(
        f"📊 **Select Coin for Technical & AI Analysis**\n*{page_title}*\n\nClick any coin below to run instant analysis:",
        parse_mode="Markdown",
        reply_markup=get_coins_keyboard("do_ta", page)
    )

@dp.callback_query(F.data.startswith("nav_futures:"))
@dp.callback_query(F.data.startswith("page_do_ft:"))
async def cb_nav_futures(callback: CallbackQuery):
    await callback.answer()
    page = int(callback.data.split(":")[1])
    page_title = COIN_PAGES[page]["title"]
    await callback.message.edit_text(
        f"⚡ **Select Coin for Futures Metrics**\n*{page_title}*\n\nClick any coin below to view Open Interest & Funding Rates:",
        parse_mode="Markdown",
        reply_markup=get_coins_keyboard("do_ft", page)
    )

@dp.callback_query(F.data.startswith("nav_prices:"))
@dp.callback_query(F.data.startswith("page_do_price:"))
async def cb_nav_prices(callback: CallbackQuery):
    await callback.answer()
    page = int(callback.data.split(":")[1])
    page_title = COIN_PAGES[page]["title"]
    await callback.message.edit_text(
        f"📊 **Live Market Overview**\n*{page_title}*\n\nClick a coin to fetch live spot price & 24h change:",
        parse_mode="Markdown",
        reply_markup=get_coins_keyboard("do_price", page)
    )

@dp.callback_query(F.data == "nav_audit")
async def cb_nav_audit(callback: CallbackQuery):
    await callback.answer()
    text = (
        "🛡️ **Smart Contract Security Audit**\n\n"
        "Send the contract address directly in chat:\n"
        "Example: `check 0x1f9840a85d5af5bf1d1762f925bdaddc4201f984`\n\n"
        "Supported Chains: Ethereum, BSC, Arbitrum, Polygon, Solana, Avalanche."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Main Menu", callback_data="nav_main")]])
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)

# --- Action Callbacks with Real-Time Fetching & Refresh ---

async def run_analysis_logic(symbol: str) -> str:
    spot_data = await price_service.get_crypto_price(symbol)
    ta_data = await indicator_service.analyze_symbol(symbol, interval="1h") if hasattr(indicator_service, 'analyze_symbol') else {}
    futures_data = await futures_service.get_futures_data(symbol)

    return await ai_service.analyze_market_data(
        symbol=symbol,
        spot_data=spot_data if "error" not in spot_data else {},
        ta_data=ta_data if "error" not in ta_data else {},
        futures_data=futures_data if "error" not in futures_data else {}
    )

@dp.callback_query(F.data.startswith("do_ta:"))
async def cb_do_ta(callback: CallbackQuery):
    symbol = callback.data.split(":")[1]
    await callback.answer(f"Analyzing {symbol}...")
    await callback.message.edit_text(f"⏳ Generating Technical & AI Analysis for **{symbol}**...", parse_mode="Markdown")
    
    report = await run_analysis_logic(symbol)
    await callback.message.edit_text(report, parse_mode="Markdown", reply_markup=get_report_keyboard(f"do_ta:{symbol}"))

async def run_futures_logic(symbol: str) -> str:
    ft_data = await futures_service.get_futures_data(symbol)
    return futures_service.format_futures_report(ft_data)

@dp.callback_query(F.data.startswith("do_ft:"))
async def cb_do_ft(callback: CallbackQuery):
    symbol = callback.data.split(":")[1]
    await callback.answer(f"Fetching Futures for {symbol}...")
    await callback.message.edit_text(f"⏳ Fetching Futures Funding & OI for **{symbol}**...", parse_mode="Markdown")
    
    report = await run_futures_logic(symbol)
    await callback.message.edit_text(report, parse_mode="Markdown", reply_markup=get_report_keyboard(f"do_ft:{symbol}"))

@dp.callback_query(F.data.startswith("do_price:"))
async def cb_do_price(callback: CallbackQuery):
    symbol = callback.data.split(":")[1]
    await callback.answer(f"Fetching Price for {symbol}...")
    
    cex_data = await price_service.get_crypto_price(symbol)
    if "error" not in cex_data:
        change_emoji = "🟢" if cex_data.get('change_24h', 0) >= 0 else "🔴"
        response = (
            f"📊 **{cex_data['symbol']} Price Overview**\n\n"
            f"💵 **Price:** `${cex_data['price']:,.4f}`\n"
            f"{change_emoji} **24h Change:** `{cex_data.get('change_24h', 0):+.2f}%`\n"
            f"📈 **24h High:** `${cex_data.get('high_24h', 0):,.4f}`\n"
            f"📉 **24h Low:** `${cex_data.get('low_24h', 0):,.4f}`\n"
            f"💰 **24h Volume:** `${cex_data.get('volume', 0):,.2f}`\n\n"
            f"⚠️ *Not financial advice*"
        )
        await callback.message.edit_text(response, parse_mode="Markdown", reply_markup=get_report_keyboard(f"do_price:{symbol}"))

@dp.callback_query(F.data.startswith("nav_news"))
@dp.callback_query(F.data.startswith("do_news:"))
async def cb_do_news(callback: CallbackQuery):
    await callback.answer("Updating News...")
    coin = callback.data.split(":")[1] if ":" in callback.data else "all"
    
    items = await news_service.get_latest_news(coin=None if coin == "all" else coin)
    report = news_service.format_news_report(items, coin=None if coin == "all" else coin)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Refresh News", callback_data=f"do_news:{coin}")],
        [InlineKeyboardButton(text="🔙 Main Menu", callback_data="nav_main")]
    ])
    await callback.message.edit_text(report, parse_mode="Markdown", disable_web_page_preview=True, reply_markup=kb)

async def run_portfolio_logic(user_id: int) -> str:
    items = await portfolio_service.get_portfolio(user_id)
    current_prices = {}
    for item in items:
        p_data = await price_service.get_crypto_price(item['symbol'])
        if "error" not in p_data:
            current_prices[item['symbol']] = p_data['price']
    return portfolio_service.format_portfolio_report(items, current_prices)

@dp.callback_query(F.data == "nav_portfolio")
@dp.callback_query(F.data == "do_portfolio")
async def cb_do_portfolio(callback: CallbackQuery):
    await callback.answer("Loading Portfolio...")
    report = await run_portfolio_logic(callback.from_user.id)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Refresh Portfolio", callback_data="do_portfolio")],
        [InlineKeyboardButton(text="➕ How to Add: /add btc 0.5 65000", callback_data="noop")],
        [InlineKeyboardButton(text="🔙 Main Menu", callback_data="nav_main")]
    ])
    await callback.message.edit_text(report, parse_mode="Markdown", reply_markup=kb)

async def run_alerts_logic(user_id: int) -> str:
    alerts = await alert_service.get_alerts(user_id)
    return alert_service.format_alerts_report(alerts)

@dp.callback_query(F.data == "nav_alerts")
@dp.callback_query(F.data == "do_alerts")
async def cb_do_alerts(callback: CallbackQuery):
    await callback.answer("Loading Alerts...")
    report = await run_alerts_logic(callback.from_user.id)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Refresh Alerts", callback_data="do_alerts")],
        [InlineKeyboardButton(text="➕ How to Set: alert btc 65000", callback_data="noop")],
        [InlineKeyboardButton(text="🔙 Main Menu", callback_data="nav_main")]
    ])
    await callback.message.edit_text(report, parse_mode="Markdown", reply_markup=kb)

# --- Search Fallback Handler (CEX + DEX) ---
@dp.message(F.text)
async def handle_search(message: Message):
    query = message.text.strip()
    if query.startswith("/"):
        return

    msg = await message.answer(f"🔍 Fetching price data for **'{query}'**...")

    cex_data = await price_service.get_crypto_price(query)
    if "error" not in cex_data:
        change_emoji = "🟢" if cex_data.get('change_24h', 0) >= 0 else "🔴"
        response = (
            f"📊 **{cex_data['symbol']} Price Overview**\n\n"
            f"💵 **Price:** `${cex_data['price']:,.4f}`\n"
            f"{change_emoji} **24h Change:** `{cex_data.get('change_24h', 0):+.2f}%`\n"
            f"📈 **24h High:** `${cex_data.get('high_24h', 0):,.4f}`\n"
            f"📉 **24h Low:** `${cex_data.get('low_24h', 0):,.4f}`\n"
            f"💰 **24h Volume:** `${cex_data.get('volume', 0):,.2f}`\n\n"
            f"💡 *Tip: Try 'ta {cex_data['symbol']}' or 'alert {cex_data['symbol']} 65000'*\n"
            f"⚠️ *Not financial advice*"
        )
        await msg.edit_text(response, parse_mode="Markdown", reply_markup=get_report_keyboard(f"do_price:{cex_data['symbol']}"))
        asyncio.create_task(auto_delete_msg(msg.chat.id, msg.message_id, 120))
        return

    dex_results = await search_service.search_token(query) if hasattr(search_service, 'search_token') else []
    if not dex_results:
        await msg.edit_text(f"❌ No matching token found for **'{query}'**.")
        asyncio.create_task(auto_delete_msg(msg.chat.id, msg.message_id, 30))
        return

    first = dex_results[0]
    change_emoji = "🟢" if first.get('change_24h', 0) >= 0 else "🔴"
    response = (
        f"🌐 **{first['name']} ({first['symbol']})**\n"
        f"🔗 **Chain:** `{first['chain']}` | **DEX:** `{first['dex']}`\n\n"
        f"💵 **Price:** `${first['price_usd']:,.6f}`\n"
        f"{change_emoji} **24h Change:** `{first['change_24h']:+.2f}%`\n"
        f"💧 **Liquidity:** `${first['liquidity']:,.2f}`\n"
        f"📝 **Contract:**\n`{first['contract']}`\n\n"
        f"⚠️ *Not financial advice*"
    )
    await msg.edit_text(response, parse_mode="Markdown", reply_markup=get_report_keyboard("nav_main"))
    asyncio.create_task(auto_delete_msg(msg.chat.id, msg.message_id, 120))

# --- Main App Entrypoint ---
async def main():
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN missing in .env file!")
        return

    await portfolio_service.init_db()
    await alert_service.init_db()

    asyncio.create_task(check_alerts_loop())

    app = web.Application()
    app.router.add_get("/", handle_health_check)
    runner = web.WebRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    logger.info(f"🌐 Health server running on port {port}")
    logger.info("🚀 CryptoPulse Pro Bot is online!")

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
