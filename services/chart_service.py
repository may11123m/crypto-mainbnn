import os
import io
import logging
import aiohttp
import pandas as pd
import mplfinance as mpf
from config import BINANCE_API_URL

logger = logging.getLogger(__name__)

class ChartService:
    def __init__(self):
        self.temp_dir = "temp_charts"
        os.makedirs(self.temp_dir, exist_ok=True)

    async def fetch_klines(self, symbol: str, interval: str = "1h", limit: int = 90) -> pd.DataFrame:
        """
        دریافت داده‌های کندل‌استیک از API عمومی بایننس
        """
        symbol_formatted = symbol.upper().replace("USDT", "") + "USDT"
        url = f"{BINANCE_API_URL}/klines?symbol={symbol_formatted}&interval={interval}&limit={limit}"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=10) as resp:
                    if resp.status != 200:
                        logger.error(f"Binance Klines API error HTTP {resp.status} for {symbol_formatted}")
                        return pd.DataFrame()

                    data = await resp.json()
                    if not isinstance(data, list) or len(data) == 0:
                        return pd.DataFrame()

                    # تبدیل داده‌ها به DataFrame
                    df = pd.DataFrame(data, columns=[
                        "open_time", "open", "high", "low", "close", "volume",
                        "close_time", "quote_volume", "trades", "taker_buy_base",
                        "taker_buy_quote", "ignore"
                    ])

                    # تبدیل نوع داده‌ها به عددی
                    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
                    for col in ["open", "high", "low", "close", "volume"]:
                        df[col] = df[col].astype(float)

                    df.set_index("open_time", inplace=True)
                    df.rename(columns={
                        "open": "Open",
                        "high": "High",
                        "low": "Low",
                        "close": "Close",
                        "volume": "Volume"
                    }, inplace=True)

                    return df

            except Exception as e:
                logger.error(f"Error fetching klines for {symbol}: {e}")
                return pd.DataFrame()

    async def generate_chart(self, symbol: str, interval: str = "1h") -> str:
        """
        تولید عکس نمودار کندل‌استیک به همراه اندیکاتورهای EMA 20 و EMA 50
        """
        df = await self.fetch_klines(symbol, interval=interval)
        if df.empty:
            return ""

        # محاسبه اندیکاتورهای نمایی EMA 20 و EMA 50
        df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()

        # استایل شبیه به تریدینگ‌ویو (Binance Dark)
        mc = mpf.make_marketcolors(
            up='#0ecb81',
            down='#f6465d',
            edge='inherit',
            wick='inherit',
            volume='in'
        )

        style = mpf.make_mpf_style(
            base_mpf_style='nightclouds',
            marketcolors=mc,
            gridstyle=':',
            y_on_right=True
        )

        # اضافه‌کردن خطوط اندیکاتور EMA به نمودار
        add_plots = [
            mpf.make_addplot(df['EMA20'], color='#f39c12', width=1.2), # نارنجی
            mpf.make_addplot(df['EMA50'], color='#2980b9', width=1.2)  # آبی
        ]

        file_path = os.path.join(self.temp_dir, f"{symbol.upper()}_{interval}.png")

        # ساخت و ذخیره نمودار
        mpf.plot(
            df,
            type='candle',
            style=style,
            volume=True,
            addplot=add_plots,
            title=f"\n{symbol.upper()} / USDT ({interval.upper()}) - Candlestick Chart",
            savefig=dict(fname=file_path, dpi=150, bbox_inches='tight'),
            figratio=(16, 9),
            figscale=1.1
        )

        return file_path

chart_service = ChartService()