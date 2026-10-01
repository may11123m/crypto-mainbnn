import aiosqlite
import logging

logger = logging.getLogger(__name__)

class PortfolioService:
    def __init__(self, db_path: str = "bot_database.db"):
        self.db_path = db_path

    async def init_db(self):
        """
        ایجاد جدول پورتفولیو در دیتابیس در صورت عدم وجود
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS portfolio (
                    user_id INTEGER,
                    symbol TEXT,
                    amount REAL,
                    buy_price REAL,
                    PRIMARY KEY (user_id, symbol)
                )
            """)
            await db.commit()

    async def add_asset(self, user_id: int, symbol: str, amount: float, buy_price: float) -> bool:
        """
        افزودن یا به‌روزرسانی یک دارایی در پورتفولیوی کاربر
        """
        symbol_clean = symbol.upper().replace("USDT", "")
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO portfolio (user_id, symbol, amount, buy_price)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(user_id, symbol) DO UPDATE SET
                        amount = amount + excluded.amount,
                        buy_price = excluded.buy_price
                """, (user_id, symbol_clean, amount, buy_price))
                await db.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding asset for user {user_id}: {e}")
            return False

    async def get_portfolio(self, user_id: int) -> list:
        """
        دریافت تمام دارایی‌های ثبت‌شده برای کاربر
        """
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT symbol, amount, buy_price FROM portfolio WHERE user_id = ?", (user_id,)) as cursor:
                rows = await cursor.fetchall()
                return [{"symbol": row[0], "amount": row[1], "buy_price": row[2]} for row in rows]

    async def remove_asset(self, user_id: int, symbol: str) -> bool:
        """
        حذف یک دارایی از پورتفولیو
        """
        symbol_clean = symbol.upper().replace("USDT", "")
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("DELETE FROM portfolio WHERE user_id = ? AND symbol = ?", (user_id, symbol_clean))
                await db.commit()
            return True
        except Exception as e:
            logger.error(f"Error removing asset for user {user_id}: {e}")
            return False

    def format_portfolio_report(self, items: list, current_prices: dict) -> str:
        """
        قالب‌بندی گزارش پورتفولیو و محاسبه PnL (سود/زیان)
        """
        if not items:
            return "💼 **Your Portfolio is empty.**\nUse `/add <symbol> <amount> <buy_price>` to add assets."

        total_value_usd = 0.0
        total_cost_usd = 0.0
        details = ""

        for item in items:
            symbol = item['symbol']
            amount = item['amount']
            buy_price = item['buy_price']
            current_price = current_prices.get(symbol, buy_price)

            value = amount * current_price
            cost = amount * buy_price
            pnl = value - cost
            pnl_pct = ((current_price - buy_price) / buy_price * 100) if buy_price > 0 else 0.0

            total_value_usd += value
            total_cost_usd += cost

            pnl_emoji = "🟢" if pnl >= 0 else "🔴"
            details += (
                f"🪙 **{symbol}**\n"
                f"   • Amount: `{amount:,.4f}` | Avg Buy: `${buy_price:,.2f}`\n"
                f"   • Current Price: `${current_price:,.2f}`\n"
                f"   • Value: `${value:,.2f}` | PnL: `{pnl_emoji} {pnl_pct:+.2f}% (${pnl:+.2f})`\n\n"
            )

        total_pnl = total_value_usd - total_cost_usd
        total_pnl_pct = ((total_value_usd - total_cost_usd) / total_cost_usd * 100) if total_cost_usd > 0 else 0.0
        overall_emoji = "🟢" if total_pnl >= 0 else "🔴"

        report = (
            f"💼 **Portfolio Summary**\n\n"
            f"💰 **Total Value:** `${total_value_usd:,.2f}`\n"
            f"📊 **Total PnL:** `{overall_emoji} {total_pnl_pct:+.2f}% (${total_pnl:+.2f})`\n\n"
            f"📋 **Asset Breakdown:**\n"
            f"{details}"
        )
        return report

portfolio_service = PortfolioService()