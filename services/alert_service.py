import aiosqlite
import logging

logger = logging.getLogger(__name__)

class AlertService:
    def __init__(self, db_path: str = "bot_database.db"):
        self.db_path = db_path

    async def init_db(self):
        """
        ایجاد جدول هشدارها در دیتابیس
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    symbol TEXT,
                    target_price REAL,
                    condition TEXT,
                    is_active INTEGER DEFAULT 1
                )
            """)
            await db.commit()

    async def add_alert(self, user_id: int, symbol: str, target_price: float, condition: str = "ABOVE") -> bool:
        """
        ثبت یک هشدار قیمت جدید برای کاربر
        """
        symbol_clean = symbol.upper().replace("USDT", "")
        condition_clean = condition.upper()
        
        if condition_clean not in ["ABOVE", "BELOW"]:
            condition_clean = "ABOVE"

        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO alerts (user_id, symbol, target_price, condition)
                    VALUES (?, ?, ?, ?)
                """, (user_id, symbol_clean, target_price, condition_clean))
                await db.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding alert for user {user_id}: {e}")
            return False

    async def get_alerts(self, user_id: int) -> list:
        """
        دریافت تمام هشدارهای فعال یک کاربر مشخص
        """
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT id, symbol, target_price, condition FROM alerts WHERE user_id = ? AND is_active = 1",
                (user_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [
                    {"id": row[0], "symbol": row[1], "target_price": row[2], "condition": row[3]}
                    for row in rows
                ]

    async def get_alerts_all(self) -> list:
        """
        دریافت تمام هشدارهای فعال سیستم برای حلقه پس‌زمینه (check_alerts_loop)
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT id, user_id, symbol, target_price, condition FROM alerts WHERE is_active = 1"
                ) as cursor:
                    rows = await cursor.fetchall()
                    return [
                        {
                            "id": row[0],
                            "user_id": row[1],
                            "symbol": row[2],
                            "target_price": row[3],
                            "condition": row[4]
                        }
                        for row in rows
                    ]
        except Exception as e:
            logger.error(f"Error fetching all active alerts: {e}")
            return []

    async def remove_alert(self, user_id: int, alert_id: int) -> bool:
        """
        حذف یک هشدار براساس شناسه (ID)
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("DELETE FROM alerts WHERE id = ? AND user_id = ?", (alert_id, user_id))
                await db.commit()
            return True
        except Exception as e:
            logger.error(f"Error removing alert {alert_id}: {e}")
            return False

    def format_alerts_report(self, items: list) -> str:
        """
        قالب‌بندی لیست هشدارها برای نمایش در تلگرام
        """
        if not items:
            return "🔔 **No Active Price Alerts.**\nUse `alert <symbol> <target_price>` to set one."

        details = ""
        for item in items:
            cond_emoji = "📈" if item['condition'] == "ABOVE" else "📉"
            details += f"• ID `{item['id']}` | **{item['symbol']}** {cond_emoji} `${item['target_price']:,.2f}` ({item['condition']})\n"

        report = (
            f"🔔 **Your Active Price Alerts**\n\n"
            f"{details}\n"
            f"💡 *To delete an alert:* `/delalert <id>`"
        )
        return report

alert_service = AlertService()