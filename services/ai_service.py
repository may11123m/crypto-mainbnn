import aiohttp
import logging
import os

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.model = os.getenv("AI_MODEL", "gpt-3.5-turbo")
        self.api_url = "https://api.openai.com/v1/chat/completions"

    async def analyze_market_data(self, symbol: str, spot_data: dict, ta_data: dict, futures_data: dict) -> str:
        symbol_clean = symbol.upper().replace("USDT", "")

        if not self.api_key:
            return self._generate_fallback_analysis(symbol_clean, spot_data, ta_data, futures_data)

        prompt = f"""
        You are a senior Cryptocurrency Analyst. Analyze the following real-time data for {symbol_clean} and provide a concise, professional analysis in English.

        Market Metrics:
        - Symbol: {symbol_clean}
        - Spot Price: ${spot_data.get('price', 0)}
        - 24h Change: {spot_data.get('change_24h', 0)}%
        - Technical Score: {ta_data.get('score', 5)}/10
        - RSI (14): {ta_data.get('rsi', 50)} ({ta_data.get('rsi_status', 'Neutral')})
        - Futures Funding Rate: {futures_data.get('funding_rate', 0)}%
        - Long/Short Ratio: {futures_data.get('long_short_ratio', 1.0)}

        Please respond in English using clear Markdown formatting with:
        1. 🤖 **Market Overview Summary**
        2. 🎯 **Key Drivers & Risk Factors**
        3. 💡 **Suggested Trading Strategy**
        """

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a professional cryptocurrency trading advisor."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(self.api_url, json=payload, headers=headers, timeout=12) as resp:
                    if resp.status == 200:
                        res_data = await resp.json()
                        return res_data['choices'][0]['message']['content']
                    else:
                        logger.error(f"AI API HTTP Error {resp.status}")
                        return self._generate_fallback_analysis(symbol_clean, spot_data, ta_data, futures_data)
            except Exception as e:
                logger.error(f"AI Service Exception: {e}")
                return self._generate_fallback_analysis(symbol_clean, spot_data, ta_data, futures_data)

    def _generate_fallback_analysis(self, symbol: str, spot_data: dict, ta_data: dict, futures_data: dict) -> str:
        score = ta_data.get('score', 5)
        rsi = ta_data.get('rsi', 50)
        funding = futures_data.get('funding_rate', 0)
        change_24h = spot_data.get('change_24h', 0)

        if score >= 7 and rsi < 70:
            bias = "🟢 Strong Bullish Momentum"
            strategy = "Market momentum is overall positive. Buyers are in control; dips toward support levels may present entry opportunities."
        elif score <= 3 or rsi > 70:
            bias = "🔴 Overbought / High Risk"
            strategy = "Price is in overbought territory or under heavy selling pressure. High risk of pullbacks or choppy sideways price action."
        else:
            bias = "⚪ Neutral / Ranging Market"
            strategy = "Market lacks clear directional trend. Buyers and sellers are balanced. Waiting for a breakout is recommended."

        funding_note = ""
        if funding > 0.03:
            funding_note = "\n⚠️ **Futures Warning:** Funding rate is significantly high; elevated risk of Long position liquidations."
        elif funding < -0.01:
            funding_note = "\n⚡ **Futures Signal:** Short sentiment is heavy; potential Short Squeeze rally."

        analysis = (
            f"🤖 **AI Smart Market Synthesis: {symbol}**\n\n"
            f"📈 **Overall Bias:** `{bias}`\n"
            f"📊 **Technical Score:** `{score} / 10`\n"
            f"💵 **24h Change:** `{change_24h:+.2f}%`\n\n"
            f"💡 **Analysis & Suggested Strategy:**\n"
            f"{strategy}{funding_note}\n\n"
            f"⚠️ *Algorithmic market synthesis. Not direct financial advice.*"
        )
        return analysis

ai_service = AIService()