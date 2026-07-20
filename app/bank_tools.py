from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.mock_bank_data import MOCK_ACCOUNTS


class TransactionsInput(BaseModel):
    limit: int = Field(default=5, description="Max number of recent transactions to return.")


class BlockCardInput(BaseModel):
    card_id: str = Field(description="The card_id to block, as returned by get_card_status.")


def build_bank_tools(account_id: str) -> list[StructuredTool]:
    """Build tool instances bound to a single account_id, so the model can
    never query or act on another customer's data -- account_id comes from
    the authenticated request, not from anything the LLM can control."""

    account = MOCK_ACCOUNTS.get(account_id)

    def get_balance() -> str:
        """Get the current account balance and currency for the customer."""
        if not account:
            return f"No account found for account_id={account_id}."
        return f"Balance: {account['balance']:.2f} {account['currency']} ({account['account_type']} account)."

    def get_recent_transactions(limit: int = 5) -> str:
        """Get the customer's most recent transactions, newest first."""
        if not account:
            return f"No account found for account_id={account_id}."
        txns = account["transactions"][:limit]
        if not txns:
            return "No transactions found."
        lines = [f"{t['date']}: {t['description']} ({t['amount']:+.2f} {account['currency']})" for t in txns]
        return "\n".join(lines)

    def get_card_status() -> str:
        """Get the status (active/blocked) of the customer's cards."""
        if not account:
            return f"No account found for account_id={account_id}."
        cards = account["cards"]
        if not cards:
            return "No cards on file."
        lines = [f"card_id={c['card_id']} ending in {c['last4']}: {c['status']}" for c in cards]
        return "\n".join(lines)

    def block_card(card_id: str) -> str:
        """Block one of the customer's cards, e.g. because it was lost or stolen."""
        if not account:
            return f"No account found for account_id={account_id}."
        for card in account["cards"]:
            if card["card_id"] == card_id:
                card["status"] = "blocked"
                return f"Card {card_id} has been blocked."
        return f"No card with card_id={card_id} found on this account."

    return [
        StructuredTool.from_function(func=get_balance, name="get_balance"),
        StructuredTool.from_function(
            func=get_recent_transactions, name="get_recent_transactions", args_schema=TransactionsInput
        ),
        StructuredTool.from_function(func=get_card_status, name="get_card_status"),
        StructuredTool.from_function(func=block_card, name="block_card", args_schema=BlockCardInput),
    ]
