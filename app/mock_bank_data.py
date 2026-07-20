"""In-memory mock data standing in for a bank's core-banking system.

This is a demo/simulation fixture only -- no real money, accounts, or PII.
Keyed by account_id so each customer's data stays isolated.
"""

MOCK_ACCOUNTS: dict[str, dict] = {
    "demo-001": {
        "customer_name": "Alice Silva",
        "account_type": "checking",
        "currency": "USD",
        "balance": 4523.10,
        "cards": [
            {"card_id": "card-001", "last4": "4242", "status": "active"},
        ],
        "transactions": [
            {"date": "2026-07-15", "description": "Grocery Store", "amount": -85.32},
            {"date": "2026-07-12", "description": "Salary Deposit", "amount": 3200.00},
            {"date": "2026-07-10", "description": "Electric Bill", "amount": -120.45},
            {"date": "2026-07-05", "description": "Streaming Subscription", "amount": -15.99},
            {"date": "2026-07-01", "description": "ATM Withdrawal", "amount": -200.00},
        ],
    },
    "demo-002": {
        "customer_name": "Marcus Chen",
        "account_type": "savings",
        "currency": "USD",
        "balance": 18320.55,
        "cards": [
            {"card_id": "card-002", "last4": "8891", "status": "blocked"},
        ],
        "transactions": [
            {"date": "2026-07-14", "description": "Interest Payment", "amount": 12.40},
            {"date": "2026-07-08", "description": "Transfer to Checking", "amount": -500.00},
            {"date": "2026-07-02", "description": "Employer Deposit", "amount": 4000.00},
        ],
    },
    "demo-003": {
        "customer_name": "Priya Nair",
        "account_type": "checking",
        "currency": "USD",
        "balance": 862.47,
        "cards": [
            {"card_id": "card-003", "last4": "1197", "status": "active"},
        ],
        "transactions": [
            {"date": "2026-07-16", "description": "Coffee Shop", "amount": -6.75},
            {"date": "2026-07-13", "description": "Rent Payment", "amount": -950.00},
            {"date": "2026-07-11", "description": "Freelance Payment", "amount": 780.00},
        ],
    },
    "demo-004": {
        "customer_name": "Diego Alvarez",
        "account_type": "savings",
        "currency": "USD",
        "balance": 52410.00,
        "cards": [
            {"card_id": "card-004", "last4": "5560", "status": "active"},
        ],
        "transactions": [
            {"date": "2026-07-15", "description": "Investment Transfer", "amount": -10000.00},
            {"date": "2026-07-09", "description": "Interest Payment", "amount": 84.20},
            {"date": "2026-07-03", "description": "Bonus Deposit", "amount": 5000.00},
        ],
    },
}
