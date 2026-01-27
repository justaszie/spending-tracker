import pytest
from app.filters import is_own_account_transfer

def test_filter():
    is_own_account_transfer('abc')