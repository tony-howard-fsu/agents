"""In-memory repository for account storage."""

from __future__ import annotations

from exceptions import AccountNotFoundError
from models import Account


class InMemoryAccountRepository:
    def __init__(self) -> None:
        self._accounts: dict[str, Account] = {}

    def add_account(self, account: Account) -> None:
        self._accounts[account.account_id] = account

    def get_account(self, account_id: str) -> Account:
        try:
            return self._accounts[account_id]
        except KeyError as exc:
            raise AccountNotFoundError(f"Account not found: {account_id}") from exc

    def save_account(self, account: Account) -> None:
        if account.account_id not in self._accounts:
            raise AccountNotFoundError(f"Account not found: {account.account_id}")
        self._accounts[account.account_id] = account

    def list_accounts(self) -> list[Account]:
        return list(self._accounts.values())

    def account_exists(self, account_id: str) -> bool:
        return account_id in self._accounts
