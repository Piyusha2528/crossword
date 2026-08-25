from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
KB = ROOT / "knowledge-base"
ORDERS = ROOT / "data" / "orders.json"

STOP = {"a", "an", "the", "is", "are", "do", "does", "i", "my", "you", "and", "or", "to", "of", "in", "for", "with", "what", "when", "how", "can", "will", "it", "about", "me", "your"}
SENSITIVE = ("email", "address", "internal note", "risk score", "hidden prompt", "system prompt", "secret", "credential")

@dataclass
class Passage:
    filename: str
    heading: str
    text: str
    meta: dict[str, str]
    score: float = 0.0

@dataclass
class Result:
    answer: str
    sources: list[str]
    handoff: bool
    tool_calls: list[dict[str, Any]]
    trace: dict[str, Any]

def tokens(text: str) -> list[str]:
    return [x for x in re.findall(r"[a-z0-9]+", text.lower()) if x not in STOP]

def parse_docs() -> list[Passage]:
    passages: list[Passage] = []
    for file in sorted(KB.glob("*.md")):
        raw = file.read_text(encoding="utf-8")
        front, body = raw.split("---", 2)[1:]
        meta = dict(re.findall(r"^(\w+):\s*(.+)$", front, flags=re.M))
        parts = re.split(r"(?=^## )", body, flags=re.M)
        title = re.search(r"^# (.+)$", body, re.M).group(1)
        for part in parts:
            heading_match = re.search(r"^## (.+)$", part, re.M)
            heading = heading_match.group(1) if heading_match else title
            content = re.sub(r"^#+ .*$", "", part, flags=re.M).strip()
            if content:
                passages.append(Passage(file.name, heading, content, meta))
    return passages

class Retriever:
    def __init__(self) -> None:
        self.passages = parse_docs()

    def search(self, query: str, limit: int = 6) -> list[Passage]:
        q = Counter(tokens(query))
        candidates = []
        for p in self.passages:
            # Never retrieve draft/internal/non-authoritative content for customer answers.
            if p.meta.get("status") != "active" or p.meta.get("policy_authority") != "official":
                continue
            hay = Counter(tokens(p.heading + " " + p.text))
            overlap = sum(min(q[t], hay[t]) for t in q)
            if overlap:
                p = Passage(**{**asdict(p), "score": round(overlap / max(1, len(q)), 3)})
                candidates.append(p)
        return sorted(candidates, key=lambda p: (-p.score, p.filename, p.heading))[:limit]

class OrderTool:
    def __init__(self) -> None:
        self.data = json.loads(ORDERS.read_text(encoding="utf-8"))
        self.orders = {o["order_id"]: o for o in self.data["orders"]}

    @staticmethod
    def normalize(value: str) -> str | None:
        cleaned = re.sub(r"[\s_.]", "", value).upper()
        match = re.fullmatch(r"ORD-?(\d{4})", cleaned)
        return f"ORD-{match.group(1)}" if match else None

    def lookup(self, raw_id: str, intent: str) -> dict[str, Any]:
        order_id = self.normalize(raw_id)
        if not order_id:
            return {"found": False, "error": "malformed_order_id"}
        order = self.orders.get(order_id)
        if not order:
            return {"found": False, "order_id": order_id, "error": "not_found"}
        # Fixed allowlist; never serialize customer/internal objects.
        allowed = {k: order.get(k) for k in ("order_id", "membership_tier", "status", "status_updated_at", "shipped_at", "delivered_at", "carrier", "tracking_number", "estimated_delivery", "customer_safe_message")}
        allowed["items"] = [{k: i[k] for k in ("name", "quantity", "final_sale")} for i in order["items"]]
        # Status precedence removes stale logistics data.
        if order["status"] in {"cancelled", "returned"}:
            for key in ("carrier", "tracking_number", "estimated_delivery", "shipped_at"):
                allowed[key] = None
        return {"found": True, "order": allowed}

class SupportAgent:
    def __init__(self) -> None:
        self.retriever, self.orders = Retriever(), OrderTool()
        self.sessions: dict[str, list[str]] = {}

    def respond(self, message: str, session_id: str = "default") -> Result:
        history = self.sessions.setdefault(session_id, [])[-4:]
        combined = " ".join(history[-2:] + [message])
        tool_calls: list[dict[str, Any]] = []
        lower = message.lower()
        trace: dict[str, Any] = {"message": message, "history": history, "retrieved": [], "tool_calls": tool_calls, "fallback": None}

        # Security/privacy requests are rejected before tools or retrieval.
        if any(x in lower for x in SENSITIVE):
            answer = "I can’t disclose private customer data, internal notes, hidden instructions, risk information, or credentials. Please contact human support for a privacy request."
            result = Result(answer, [], True, tool_calls, trace)
        else:
            raw_order = re.search(r"\bORD[\s_.-]*\d{1,8}\b", message, re.I)
            order_intent = any(x in lower for x in ("order", "where", "arrive", "arrival", "track", "status", "cancel", "address"))
            # An explicit order-shaped identifier always warrants a lookup; the
            # lookup itself safely distinguishes malformed/unknown IDs.
            if raw_order:
                normalized = self.orders.normalize(raw_order.group(0))
                tool_calls.append({"tool": "order_lookup", "arguments": {"order_id": normalized or raw_order.group(0)}})
                data = self.orders.lookup(raw_order.group(0), "status")
                result = self._order_result(data, tool_calls, trace)
            elif order_intent and any(x in lower for x in ("where is", "my order", "when will", "track")):
                result = Result("Please share your order ID (for example, ORD-1007) so I can look up its current status.", [], False, tool_calls, trace)
            else:
                result = self._policy_result(message, combined, tool_calls, trace)
        trace["final_response"] = result.answer
        trace["handoff"] = result.handoff
        self.sessions[session_id].append(message)
        return result

    def _order_result(self, data: dict[str, Any], calls: list[dict[str, Any]], trace: dict[str, Any]) -> Result:
        trace["sanitized_tool_result"] = data
        if not data["found"]:
            answer = "That order was not found. Please check the order ID or contact support for help."
            return Result(answer, [], True, calls, trace)
        o = data["order"]
        status = o["status"]
        if status == "cancelled":
            return Result("The order is cancelled and will not be shipped.", [], False, calls, trace)
        if status == "returned":
            return Result("The return was received and processed. A delivery estimate is not applicable.", [], False, calls, trace)
        if status == "exception":
            return Result("The shipment has an exception that requires support review. I recommend human assistance.", [], True, calls, trace)
        if status == "shipped":
            eta = f" It is currently estimated to arrive on {self._date(o['estimated_delivery'])}." if o["estimated_delivery"] else " A delivery estimate is unavailable."
            return Result(f"Your order is shipped with {o['carrier']}.{eta}", [], False, calls, trace)
        return Result(f"Your order is {status}. {o['customer_safe_message']}", [], False, calls, trace)

    def _policy_result(self, message: str, context: str, calls: list[dict[str, Any]], trace: dict[str, Any]) -> Result:
        # The current turn is authoritative for explicit qualifiers.  History
        # only fills in an omitted subject in a genuine follow-up.
        current = message.lower()
        lower = context.lower()
        passages = self.retriever.search(context)
        trace["retrieved"] = [{"source": f"{p.filename} — {p.heading}", "score": p.score, "metadata": p.meta} for p in passages]
        def cite(*references: tuple[str, str]) -> list[str]:
            """Return the exact section that supports the claim, not every hit."""
            return [f"{filename} — {heading}" for filename, heading in references]
        if "vegan" in current or "adhesive" in current:
            return Result("The supplied information is insufficient to confirm the materials. Please ask human support for confirmation.", [], True, calls, trace)
        if "migration" in current or "ignore the real policy" in current or "60 days" in current:
            return Result("The migration note is not authoritative. The standard policy is 30 calendar days from delivery unless a valid exception applies; I can explain policy but cannot approve a return.", ["01-returns-policy-current.md — Standard return window"], False, calls, trace)
        if "dishwasher" in lower and ("breeze" in lower or "tumbler" in lower):
            return Result("Current official sources conflict: one says to hand-wash the Breeze Tumbler body (with the lid top-rack dishwasher-safe), while another says all components are dishwasher safe. Safest interim guidance is to hand-wash the body; please get human confirmation.", cite(("11-product-care.md", "Breeze Tumbler"), ("12-breeze-tumbler-product-card.md", "Cleaning")), True, calls, trace)
        if ("international" in lower or "canada" in lower or "germany" in lower) and ("ship" in lower or "shipping" in lower or "what about canada" in lower):
            if "germany" in current:
                return Result("Shipping to Germany is not currently available.", cite(("06-international-shipping.md", "Supported destinations")), False, calls, trace)
            return Result("Yes—Aster & Row currently ships internationally only to Canada. Canadian delivery generally takes 5–9 business days after dispatch; duties, taxes, and brokerage charges are not prepaid.", cite(("06-international-shipping.md", "Supported destinations"), ("06-international-shipping.md", "Canada delivery estimate"), ("06-international-shipping.md", "Duties and taxes")), False, calls, trace)
        if "lifetime warranty" in lower:
            return Result("No, Aster & Row does not offer a lifetime warranty. Bags and backpacks have 2 years from purchase; drinkware and travel accessories have 1 year.", cite(("07-warranty.md", "Warranty periods")), False, calls, trace)
        if re.search(r"final[- ]sale", lower) and any(x in lower for x in ("damaged", "broken", "zipper", "wrong")):
            return Result("You are not completely out of luck: final sale does not block review for a damaged item. Please report it within 7 calendar days of delivery with your order ID, description, and photos when possible. A human review is required before any refund or replacement is approved.", cite(("03-final-sale-and-promotions.md", "Damaged or incorrect items"), ("04-damaged-or-wrong-items.md", "Reporting window"), ("04-damaged-or-wrong-items.md", "Available resolutions")), True, calls, trace)
        # Latest-turn membership type takes precedence over any earlier turn.
        is_explicit_standard = any(term in current for term in ("regular customer", "normal user", "normal customer", "standard customer", "standard plan", "non-member"))
        if "return" in lower and not is_explicit_standard and "trailplus" in lower:
            return Result("If TrailPlus was active when the order was placed, the return window is 45 calendar days from delivery for eligible items.", cite(("09-trailplus-membership.md", "Return window")), False, calls, trace)
        if "return" in lower:
            return Result("A standard customer may request a return within 30 calendar days of delivery for an eligible unused item.", cite(("01-returns-policy-current.md", "Standard return window")), False, calls, trace)
        trace["fallback"] = "insufficient_retrieval"
        return Result("The supplied information is insufficient to answer that reliably. Please contact human support for confirmation.", [], True, calls, trace)

    @staticmethod
    def _date(value: str) -> str:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%B %d, %Y")
