import aiohttp
import logging

logger = logging.getLogger(__name__)

class NewsService:
    def __init__(self):
        self.cryptopanic_url = "https://cryptopanic.com/api/v1/posts/?auth_token=public&public=true"

    async def get_latest_news(self, coin: str = None, limit: int = 5) -> list:
        url = self.cryptopanic_url
        if coin:
            url += f"&currencies={coin.upper().replace('USDT', '')}"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=10) as resp:
                    if resp.status != 200:
                        logger.error(f"News API error HTTP {resp.status}")
                        return []

                    data = await resp.json()
                    results = data.get("results", [])
                    news_items = []

                    for item in results[:limit]:
                        title = item.get("title", "")
                        url_link = item.get("url", "")
                        published_at = item.get("published_at", "")[:16].replace("T", " ")
                        votes = item.get("votes", {})
                        
                        bullish = votes.get("positive", 0) + votes.get("liked", 0)
                        bearish = votes.get("negative", 0) + votes.get("disliked", 0)

                        if bullish > bearish:
                            sentiment = "🟢 Bullish"
                        elif bearish > bullish:
                            sentiment = "🔴 Bearish"
                        else:
                            sentiment = "⚪ Neutral"

                        news_items.append({
                            "title": title,
                            "url": url_link,
                            "time": published_at,
                            "sentiment": sentiment,
                            "source": item.get("domain", "CryptoPanic")
                        })

                    return news_items

            except Exception as e:
                logger.error(f"Error fetching news: {e}")
                return []

    def format_news_report(self, news_items: list, coin: str = None) -> str:
        if not news_items:
            return "❌ **No recent news found for this symbol.**"

        header = f"📰 **Latest Crypto News ({coin.upper()})**\n\n" if coin else "📰 **Latest Market News**\n\n"
        body = ""

        for idx, news in enumerate(news_items, 1):
            body += (
                f"{idx}. **[{news['title']}]({news['url']})**\n"
                f"   • Sentiment: `{news['sentiment']}` | Source: `{news['source']}`\n"
                f"   • Time: `{news['time']}`\n\n"
            )

        return header + body

news_service = NewsService()