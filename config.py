import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
PORT = int(os.getenv("PORT", 8080))

# API Endpoints
BINANCE_API_URL = "https://api.binance.com/api/v3"
BINANCE_FUTURES_URL = "https://fapi.binance.com/fapi/v1"
GOPLUS_API_URL = "https://api.gopluslabs.io/api/v1"
DEXSCREENER_API_URL = "https://api.dexscreener.com/latest/dex"

# General Settings
AUTO_DELETE_DELAY = 180  # حذف خودکار پیام‌ها پس از ۳ دقیقه (به ثانیه)