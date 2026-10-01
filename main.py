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

# --- تابع کمکی حذف خودکار پیام‌ها ---
async def auto_delete_msg(chat_id: int, message_id: int, delay: int = 120):
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

# --- منوی شیشه‌ای اصلی ---
def get_main_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📈 Market Analysis", callback_data="menu_analysis"),
            InlineKeyboardButton(text="⚡ Futures Metrics", callback_data="menu_futures")
        ],
        [
            InlineKeyboardButton(text="🛡️ Contract Audit", callback_data="menu_audit"),
            InlineKeyboardButton(text="📰 Crypto News", callback_data="menu_news")
        ],
        [
            InlineKeyboardButton(text="💼 Portfolio", callback_data="menu_portfolio"),
            InlineKeyboardButton(text="🔔 Price Alerts", callback_data="menu_alerts")
        ]
    ])
    return keyboard

# --- Handlers ---

@dp.message(Command("start"))
async def start_handler(message: Message):
    welcome_text = (
        "🌐 **CryptoPulse Pro v2 & AI Intelligence**\n\n"
        "Select an option below or send commands directly:\n"
        "• Send symbol (`BTC`, `ETH`) for **Price Overview**\n"
        "• `ta btc` or `/analyze btc` - **Technical & AI Analysis**\n"
        "• `ft btc` or `/futures btc` - **Futures Funding & OI**\n"
        "• `check 0x...` or `/audit 0x...` - **Security Audit**\n"
        "• `/news [coin]` - **Latest Crypto News**\n"
        "• `/portfolio` or `/add btc 0.5 65000` - **Portfolio Tracker**\n"
        "• `alert btc 65000` or `/myalerts` - **Price Alerts**"
    )
    msg = await message.answer(welcome_text, parse_mode="Markdown", reply_markup=get_main_keyboard())
    asyncio.create_task(auto_delete_msg(msg.chat.id, msg.message_id, 300))

# --- AI & Market Analysis Handler ---
@dp.message(Command("analyze"))
@dp.message(F.text.lower().startswith("ta "))
async def handle_ai_analysis(message: Message):
    if message.text.startswith("/analyze"):
        parts = message.text.split()
        symbol = parts[1].upper() if len(parts) > 1 else ""
    else:
        symbol = message.text.lower().replace("ta ", "").strip().upper()

    if not symbol:
        await message.answer("⚠️ **Usage:** `ta btc` or `/analyze btc`", parse_mode="Markdown")
        return

    msg = await message.answer(f"🔄 Analyzing **{symbol}** market metrics & technicals...")

    spot_data = await price_service.get_crypto_price(symbol)
    ta_data = await indicator_service.analyze_symbol(symbol, interval="1h") if hasattr(indicator_service, 'analyze_symbol') else {}
    futures_data = await futures_service.get_futures_data(symbol)

    report = await ai_service.analyze_market_data(
        symbol=symbol,
        spot_data=spot_data if "error" not in spot_data else {},
        ta_data=ta_data if "error" not in ta_data else {},
        futures_data=futures_data if "error" not in futures_data else {}
    )

    await msg.edit_text(report, parse_mode="Markdown")
    asyncio.create_task(auto_delete_msg(msg.chat.id, msg.message_id, 180))

# --- Futures Data Handler ---
@dp.message(Command("futures"))
@dp.message(F.text.lower().startswith("ft "))
async def handle_futures(message: Message):
    if message.text.startswith("/futures"):
        parts = message.text.split()
        symbol = parts[1].upper() if len(parts) > 1 else ""
    else:
        symbol = message.text.lower().replace("ft ", "").strip().upper()

    if not symbol:
        await message.answer("⚠️ **Usage:** `ft btc` or `/futures btc`", parse_mode="Markdown")
        return

    msg = await message.answer(f"📈 Fetching Futures metrics for **{symbol}**...")
    ft_data = await futures_service.get_futures_data(symbol)
    report = futures_service.format_futures_report(ft_data)

    await msg.edit_text(report, parse_mode="Markdown")
    asyncio.create_task(auto_delete_msg(msg.chat.id, msg.message_id, 120))

# --- Security Audit Handler ---
@dp.message(Command("audit"))
@dp.message(F.text.lower().startswith("check "))
async def handle_security_check(message: Message):
    if message.text.startswith("/audit"):
        parts = message.text.split()
        address = parts[1] if len(parts) > 1 else ""
    else:
        address = message.text.lower().replace("check ", "").strip()

    if not address:
        await message.answer("⚠️ **Usage:** `check 0x...` or `/audit 0x...`", parse_mode="Markdown")
        return

    msg = await message.answer(f"🛡️ Auditing contract address **`{address[:10]}...`**...")
    audit_data = await security_service.check_token_security(address)
    report = security_service.format_security_report(audit_data)

    await msg.edit_text(report, parse_mode="Markdown")
    asyncio.create_task(auto_delete_msg(msg.chat.id, msg.message_id, 180))

# --- News Handler ---
@dp.message(Command("news"))
async def handle_news(message: Message):
    parts = message.text.split()
    coin = parts[1] if len(parts) > 1 else None

    items = await news_service.get_latest_news(coin=coin)
    report = news_service.format_news_report(items, coin=coin)

    msg = await message.answer(report, parse_mode="Markdown", disable_web_page_preview=True)
    asyncio.create_task(auto_delete_msg(msg.chat.id, msg.message_id, 180))

# --- Portfolio Handlers ---
@dp.message(Command("portfolio"))
async def handle_portfolio(message: Message):
    user_id = message.from_user.id
    items = await portfolio_service.get_portfolio(user_id)

    current_prices = {}
    for item in items:
        p_data = await price_service.get_crypto_price(item['symbol'])
        if "error" not in p_data:
            current_prices[item['symbol']] = p_data['price']

    report = portfolio_service.format_portfolio_report(items, current_prices)
    msg = await message.answer(report, parse_mode="Markdown")
    asyncio.create_task(auto_delete_msg(msg.chat.id, msg.message_id, 120))

@dp.message(Command("add"))
async def handle_add_portfolio(message: Message):
    parts = message.text.split()
    if len(parts) < 4:
        await message.answer("⚠️ **Usage:** `/add <symbol> <amount> <buy_price>`\nExample: `/add btc 0.5 65000`", parse_mode="Markdown")
        return

    try:
        symbol = parts[1]
        amount = float(parts[2])
        buy_price = float(parts[3])
        success = await portfolio_service.add_asset(message.from_user.id, symbol, amount, buy_price)
        text = f"✅ Added `{amount}` **{symbol.upper()}** at `${buy_price:,.2f}` to portfolio." if success else "❌ Failed to add asset."
    except ValueError:
        text = "❌ Invalid numbers provided."

    msg = await message.answer(text, parse_mode="Markdown")
    asyncio.create_task(auto_delete_msg(msg.chat.id, msg.message_id, 60))

# --- Alert Handlers ---
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

    if success:
        text = (
            f"✅ **Price Alert Set Successfully!**\n\n"
            f"🪙 **Token:** `{symbol}`\n"
            f"💵 **Current Price:** `${current_price:,.4f}`\n"
            f"🎯 **Target Price:** `${target_price:,.4f}`\n"
            f"{cond_emoji} **Trigger:** When price goes `{condition}` target."
        )
    else:
        text = "❌ Failed to set alert."

    msg = await message.answer(text, parse_mode="Markdown")
    asyncio.create_task(auto_delete_msg(msg.chat.id, msg.message_id, 60))

@dp.message(Command("myalerts"))
async def handle_my_alerts(message: Message):
    alerts = await alert_service.get_alerts(message.from_user.id)
    report = alert_service.format_alerts_report(alerts)
    msg = await message.answer(report, parse_mode="Markdown")
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

# --- Callback Handler برای کلیدهای شیشه‌ای ---
@dp.callback_query()
async def process_callback(callback: CallbackQuery):
    await callback.answer()
    data = callback.data

    if data == "menu_analysis":
        await callback.message.answer("📌 Send `ta btc` or `/analyze btc`", parse_mode="Markdown")
    elif data == "menu_futures":
        await callback.message.answer("📌 Send `ft btc` or `/futures btc`", parse_mode="Markdown")
    elif data == "menu_audit":
        await callback.message.answer("📌 Send `check 0x...` or `/audit 0x...`", parse_mode="Markdown")
    elif data == "menu_news":
        await callback.message.answer("📌 Send `/news` or `/news eth`", parse_mode="Markdown")
    elif data == "menu_portfolio":
        await callback.message.answer("📌 Send `/portfolio` to view, or `/add btc 0.5 65000` to add.", parse_mode="Markdown")
    elif data == "menu_alerts":
        await callback.message.answer("📌 Send `alert btc 65000` or `/myalerts`", parse_mode="Markdown")

# --- Search Handler (CEX + DEX Fallback) ---
@dp.message(F.text)
async def handle_search(message: Message):
    query = message.text.strip()
    if query.startswith("/"):
        return

    msg = await message.answer(f"🔍 Fetching price data for **'{query}'**...")

    # ۱. ابتدا در صرافی متمرکز جستجو می‌شود
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
        await msg.edit_text(response, parse_mode="Markdown")
        asyncio.create_task(auto_delete_msg(msg.chat.id, msg.message_id, 120))
        return

    # ۲. در صورت عدم وجود در CEX، در DEX جستجو می‌شود
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
    await msg.edit_text(response, parse_mode="Markdown")
    asyncio.create_task(auto_delete_msg(msg.chat.id, msg.message_id, 120))

# --- Main App Entrypoint ---
async def main():
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN missing in .env file!")
        return

    # مقداردهی دیتابیس SQLite
    await portfolio_service.init_db()
    await alert_service.init_db()

    # اجرای حلقه پس‌زمینه برای بررسی قیمت هشدارها
    asyncio.create_task(check_alerts_loop())

    # اجرای سرور وب برای پورت هاست (Render Free Tier)
    app = web.Application()
    app.router.add_get("/", handle_health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    logger.info(f"🌐 Health server running on port {port}")
    logger.info("🚀 CryptoPulse Pro Bot with Aiogram is running...")

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())