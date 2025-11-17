import os
import sys
import pytest
from unittest.mock import Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.library_service import (
    pay_late_fees,
    refund_late_fee_payment,
)
from services.payment_service import PaymentGateway




# ---------------- pay_late_fees() ----------------

def test_pay_late_fees_successful_payment(mocker):
    # Stubs: provide fake late fee + book data
    mocker.patch(
        'services.library_service.calculate_late_fee_for_book',
        return_value={'fee_amount': 5.00, 'days_overdue': 3, 'status': 'Overdue'}
    )
    mocker.patch(
        'services.library_service.get_book_by_id',
        return_value={'id': 1, 'title': 'Clean Code', 'available_copies': 0, 'total_copies': 3}
    )

    # Mock: verify gateway interaction
    gateway = Mock(spec=PaymentGateway)
    gateway.process_payment.return_value = (True, 'txn_123', 'Processed OK')

    success, message, txn = pay_late_fees('123456', 1, gateway)

    assert success is True
    assert 'payment successful' in message.lower()
    assert txn == 'txn_123'

    gateway.process_payment.assert_called_once()
    gateway.process_payment.assert_called_with(
        patron_id='123456',
        amount=5.00,
        description="Late fees for 'Clean Code'",
    )


def test_pay_late_fees_payment_declined(mocker):
    mocker.patch(
        'services.library_service.calculate_late_fee_for_book',
        return_value={'fee_amount': 7.50, 'days_overdue': 9, 'status': 'Overdue'}
    )
    mocker.patch(
        'services.library_service.get_book_by_id',
        return_value={'id': 2, 'title': 'Refactoring'}
    )

    gateway = Mock(spec=PaymentGateway)
    gateway.process_payment.return_value = (False, '', 'Card declined')

    success, message, txn = pay_late_fees('123456', 2, gateway)

    assert success is False
    assert 'payment failed' in message.lower()
    assert 'declined' in message.lower()
    assert txn is None

    gateway.process_payment.assert_called_once()
    gateway.process_payment.assert_called_with(
        patron_id='123456',
        amount=7.50,
        description="Late fees for 'Refactoring'",
    )


def test_pay_late_fees_invalid_patron_id_not_called():
    # Validation fails early; gateway must not be called
    gateway = Mock(spec=PaymentGateway)

    success, message, txn = pay_late_fees('12A456', 1, gateway)

    assert success is False
    assert 'invalid patron id' in message.lower()
    assert txn is None
    gateway.process_payment.assert_not_called()


def test_pay_late_fees_zero_fee_not_called(mocker):
    mocker.patch(
        'services.library_service.calculate_late_fee_for_book',
        return_value={'fee_amount': 0.0, 'days_overdue': 0, 'status': 'Not overdue'}
    )
    mocker.patch(
        'services.library_service.get_book_by_id',
        return_value={'id': 1, 'title': 'No Fee Book'}
    )

    gateway = Mock(spec=PaymentGateway)

    success, message, txn = pay_late_fees('123456', 1, gateway)

    assert success is False
    assert 'no late fees' in message.lower()
    assert txn is None
    gateway.process_payment.assert_not_called()


def test_pay_late_fees_network_error_handling(mocker):
    mocker.patch(
        'services.library_service.calculate_late_fee_for_book',
        return_value={'fee_amount': 4.25, 'days_overdue': 2, 'status': 'Overdue'}
    )
    mocker.patch(
        'services.library_service.get_book_by_id',
        return_value={'id': 3, 'title': 'Domain-Driven Design'}
    )

    gateway = Mock(spec=PaymentGateway)
    gateway.process_payment.side_effect = Exception('Network error')

    success, message, txn = pay_late_fees('123456', 3, gateway)

    assert success is False
    assert 'payment processing error' in message.lower()
    assert 'network error' in message.lower()
    assert txn is None
    gateway.process_payment.assert_called_once()


# ---------------- refund_late_fee_payment() ----------------

def test_refund_late_fee_payment_success():
    gateway = Mock(spec=PaymentGateway)
    gateway.refund_payment.return_value = (True, 'Refund processed')

    success, message = refund_late_fee_payment('txn_abc123', 10.0, gateway)

    assert success is True
    assert 'refund' in message.lower()
    gateway.refund_payment.assert_called_once_with('txn_abc123', 10.0)


@pytest.mark.parametrize('bad_txn', ['', 'abc', None])
def test_refund_late_fee_payment_invalid_transaction_id_not_called(bad_txn):
    gateway = Mock(spec=PaymentGateway)

    success, message = refund_late_fee_payment(bad_txn, 5.0, gateway)

    assert success is False
    assert 'invalid transaction id' in message.lower()
    gateway.refund_payment.assert_not_called()


@pytest.mark.parametrize('bad_amount', [-1.0, 0.0, 16.0])
def test_refund_late_fee_payment_invalid_amounts_not_called(bad_amount):
    gateway = Mock(spec=PaymentGateway)

    success, message = refund_late_fee_payment('txn_valid_001', bad_amount, gateway)

    assert success is False
    if bad_amount <= 0:
        assert 'greater than 0' in message.lower()
    else:
        assert 'exceeds maximum' in message.lower()

    gateway.refund_payment.assert_not_called()
