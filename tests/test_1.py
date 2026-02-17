from decimal import Decimal

import pytest

@pytest.skip
def test_filter(extracted_transaction):
    test_txn = extracted_transaction(orig_amount = Decimal("11.5"))
    assert test_txn.counterparty.lower() == "brewdog pub"
    assert test_txn.orig_amount == 11.50

