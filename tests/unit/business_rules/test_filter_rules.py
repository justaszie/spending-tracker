import pytest

from app.business_rules.filter_rules import get_filter_rules, is_own_account_transfer
from app.core.project_types import TransactionType


class TestOWnAccountTranfer:
    @pytest.mark.parametrize(
        "counterparty",
        [
            "justas zieminykas",
            "to Justas Žieminykas",
            "to usd",
            "justas Zieminykas",
        ],
    )
    def test_positive_match(self, extracted_transaction, counterparty):
        transaction = extracted_transaction(counterparty=counterparty)
        assert is_own_account_transfer(transaction)

    @pytest.mark.parametrize(
        "counterparty",
        [
            "John Zieminykas",
            "JUSTAS WHATEVER",
            "Elvis Presley",
        ],
    )
    def test_no_match(self, extracted_transaction, counterparty):
        transaction = extracted_transaction(counterparty=counterparty)
        assert not is_own_account_transfer(transaction)


class TestAllRulesCovered:
    @pytest.fixture(scope="class")
    def active_rules(self):
        return get_filter_rules()

    def test_filters_own_account_transfers(self, extracted_transaction, active_rules):
        transaction = extracted_transaction(counterparty="JUSTAS ZIEMINYKAS")
        assert any(not rule_fn(transaction) for rule_fn in active_rules)

    def test_filters_cash_withdrawals(self, extracted_transaction, active_rules):
        transaction = extracted_transaction(type=TransactionType.CASH_WITHDRAWAL)
        assert any(not rule_fn(transaction) for rule_fn in active_rules)

    def test_no_filter_applied(self, extracted_transaction, active_rules):
        transaction = extracted_transaction(
            type=TransactionType.CARD_PAYMENT,
            counterparty="Tesco Express",
        )
        assert all(rule_fn(transaction) for rule_fn in active_rules)
