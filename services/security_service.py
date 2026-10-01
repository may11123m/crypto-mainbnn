import aiohttp
import logging
from config import GOPLUS_API_URL

logger = logging.getLogger(__name__)

class SecurityService:
    def __init__(self):
        self.chain_mapping = {
            "1": "Ethereum",
            "56": "BNB Chain (BSC)",
            "137": "Polygon",
            "42161": "Arbitrum",
            "10": "Optimism",
            "43114": "Avalanche",
            "8453": "Base"
        }

    async def check_token_security(self, contract_address: str, chain_id: str = "56") -> dict:
        contract_clean = contract_address.strip().lower()
        url = f"{GOPLUS_API_URL}/token_security/{chain_id}?contract_addresses={contract_clean}"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=10) as resp:
                    if resp.status != 200:
                        logger.error(f"GoPlus API Error HTTP {resp.status}")
                        return {"error": "Unable to query Security API."}

                    data = await resp.json()

                    if data.get("code") != 0 or not data.get("result"):
                        if chain_id != "1":
                            return await self.check_token_security(contract_clean, chain_id="1")
                        return {"error": "Invalid contract address or unsupported network."}

                    result_dict = data.get("result", {})
                    token_data = result_dict.get(contract_clean, {})

                    if not token_data:
                        return {"error": "No security data found for this contract address."}

                    token_name = token_data.get("token_name", "Unknown")
                    token_symbol = token_data.get("token_symbol", "UNKNOWN")
                    is_honeypot = token_data.get("is_honeypot", "0") == "1"
                    buy_tax = float(token_data.get("buy_tax", 0)) * 100
                    sell_tax = float(token_data.get("sell_tax", 0)) * 100
                    is_open_source = token_data.get("is_open_source", "0") == "1"
                    is_proxy = token_data.get("is_proxy", "0") == "1"
                    can_take_back_ownership = token_data.get("can_take_back_ownership", "0") == "1"
                    is_mintable = token_data.get("is_mintable", "0") == "1"
                    owner_address = token_data.get("owner_address", "No Owner / Renounced")

                    risk_score = 0
                    risk_factors = []

                    if is_honeypot:
                        risk_score += 100
                        risk_factors.append("🚨 **Honeypot Detected!** Token cannot be sold.")

                    if buy_tax > 10 or sell_tax > 10:
                        risk_score += 30
                        risk_factors.append(f"⚠️ **High Tax:** Buy {buy_tax:.1f}% / Sell {sell_tax:.1f}%")

                    if not is_open_source:
                        risk_score += 40
                        risk_factors.append("⚠️ **Unverified Code:** Contract source code is not verified on explorer.")

                    if is_proxy:
                        risk_score += 20
                        risk_factors.append("⚙️ **Proxy Contract:** Contract logic can be modified dynamically.")

                    if is_mintable:
                        risk_score += 20
                        risk_factors.append("🪙 **Mintable:** New tokens can be minted without limit.")

                    if can_take_back_ownership:
                        risk_score += 30
                        risk_factors.append("🔑 **Owner Reclaim:** Creator can reclaim ownership.")

                    if risk_score == 0:
                        status = "🟢 Low Risk (Safe)"
                    elif risk_score < 50:
                        status = "🟡 Medium Risk"
                    else:
                        status = "🔴 HIGH RISK / DANGEROUS"

                    chain_name = self.chain_mapping.get(str(chain_id), f"Chain ID {chain_id}")

                    return {
                        "name": token_name,
                        "symbol": token_symbol,
                        "chain": chain_name,
                        "contract": contract_clean,
                        "status": status,
                        "risk_score": risk_score,
                        "is_honeypot": "YES ❌" if is_honeypot else "NO ✅",
                        "buy_tax": f"{buy_tax:.1f}%",
                        "sell_tax": f"{sell_tax:.1f}%",
                        "is_open_source": "YES ✅" if is_open_source else "NO ⚠️",
                        "owner": owner_address,
                        "risk_factors": risk_factors
                    }

            except Exception as e:
                logger.error(f"Error checking security for {contract_address}: {e}")
                return {"error": "Error connecting to on-chain security service."}

    def format_security_report(self, data: dict) -> str:
        if "error" in data:
            return f"❌ **Audit Failed:**\n{data['error']}"

        risk_list_text = "\n".join([f"• {r}" for r in data['risk_factors']]) if data['risk_factors'] else "• No critical risk factors detected."

        report = (
            f"🛡️ **Smart Contract Audit: {data['name']} ({data['symbol']})**\n"
            f"🌐 **Network:** `{data['chain']}`\n\n"
            f"📊 **Overall Safety:** `{data['status']}`\n"
            f"🧪 **Honeypot Check:** `{data['is_honeypot']}`\n"
            f"💸 **Buy Tax:** `{data['buy_tax']}` | **Sell Tax:** `{data['sell_tax']}`\n"
            f"📜 **Source Code Verified:** `{data['is_open_source']}`\n"
            f"👤 **Owner:** `{data['owner'][:12]}...{data['owner'][-6:]}`\n\n"
            f"🚨 **Risk Analysis Factors:**\n"
            f"{risk_list_text}\n\n"
            f"📝 **Contract:**\n`{data['contract']}`\n\n"
            f"⚠️ *Not financial advice*"
        )
        return report

security_service = SecurityService()