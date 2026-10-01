import aiohttp
import logging
from config import BINANCE_FUTURES_URL

logger = logging.getLogger(__name__)

class FuturesService:
    async def get_futures_data(self, symbol: str) -> dict:
        symbol_formatted = symbol.upper().replace("USDT", "") + "USDT"

        async with aiohttp.ClientSession() as session:
            try:
                funding_url = f"{BINANCE_FUTURES_URL}/premiumIndex?symbol={symbol_formatted}"
                async with session.get(funding_url, timeout=10) as resp:
                    if resp.status != 200:
                        return {"error": f"Symbol {symbol_formatted} not found in Futures market."}
                    funding_data = await resp.json()

                mark_price = float(funding_data.get("markPrice", 0))
                last_funding_rate = float(funding_data.get("lastFundingRate", 0)) * 100

                oi_url = f"{BINANCE_FUTURES_URL}/openInterest?symbol={symbol_formatted}"
                async with session.get(oi_url, timeout=10) as resp:
                    oi_data = await resp.json() if resp.status == 200 else {}

                open_interest = float(oi_data.get("openInterest", 0))
                open_interest_usd = open_interest * mark_price

                ls_url = f"{BINANCE_FUTURES_URL}/globalLongShortAccountRatio?symbol={symbol_formatted}&period=5m&limit=1"
                async with session.get(ls_url, timeout=10) as resp:
                    ls_data = await resp.json() if resp.status == 200 else []

                long_short_ratio = 1.0
                long_pct = 50.0
                short_pct = 50.0

                if isinstance(ls_data, list) and len(ls_data) > 0:
                    latest_ls = ls_data[0]
                    long_short_ratio = float(latest_ls.get("longShortRatio", 1.0))
                    long_pct = float(latest_ls.get("longAccount", 0.5)) * 100
                    short_pct = float(latest_ls.get("shortAccount", 0.5)) * 100

                if last_funding_rate > 0.03:
                    funding_signal = "🔥 High Bullish Demand (Overheated - Long Liquidation Risk)"
                elif last_funding_rate < -0.01:
                    funding_signal = "❄️ High Bearish Pressure (Short Squeeze Potential)"
                else:
                    funding_signal = "⚖️ Neutral / Balanced Market"

                return {
                    "symbol": symbol_formatted,
                    "mark_price": mark_price,
                    "funding_rate": last_funding_rate,
                    "funding_signal": funding_signal,
                    "open_interest_usd": open_interest_usd,
                    "long_short_ratio": long_short_ratio,
                    "long_pct": long_pct,
                    "short_pct": short_pct
                }

            except Exception as e:
                logger.error(f"Error fetching futures data for {symbol}: {e}")
                return {"error": "Failed to retrieve futures market data."}

    def format_futures_report(self, data: dict) -> str:
        if "error" in data:
            return f"❌ **Futures Data Error:**\n{data['error']}"

        funding_emoji = "🔴" if data['funding_rate'] > 0.03 else ("🟢" if data['funding_rate'] < 0 else "⚪")

        report = (
            f"⚡ **Futures Metrics: {data['symbol']}**\n\n"
            f"💵 **Mark Price:** `${data['mark_price']:,.2f}`\n\n"
            f"{funding_emoji} **Funding Rate (8h):** `{data['funding_rate']:+.4f}%`\n"
            f"📌 **Market Sentiment:** `{data['funding_signal']}`\n\n"
            f"💧 **Open Interest (USD):** `${data['open_interest_usd']:,.0f}`\n"
            f"⚖️ **Long / Short Ratio:** `{data['long_short_ratio']:.2f}`\n"
            f"• **Long Accounts:** `{data['long_pct']:.1f}%` 🟢\n"
            f"• **Short Accounts:** `{data['short_pct']:.1f}%` 🔴\n\n"
            f"⚠️ *Not financial advice*"
        )
        return report

futures_service = FuturesService()