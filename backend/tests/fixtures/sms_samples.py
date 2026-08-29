"""Representative Indian bank SMS shapes used across the parser tests.

Samples are modelled on the message formats the platform targets. Amounts,
account digits and references are fabricated.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.shared.enums import BusinessType, TransactionDirection


@dataclass(frozen=True)
class SmsSample:
    """One message plus what a correct parse should produce."""

    label: str
    sender: str
    message_text: str
    expected_parser: str
    expected_amount: Decimal
    expected_direction: TransactionDirection
    expected_bank: str | None = None
    expected_last_four: str | None = None
    expected_merchant: str | None = None
    expected_reference: str | None = None
    expected_timestamp: datetime | None = None
    expected_business_type: BusinessType | None = None


TRANSACTIONAL_SAMPLES: tuple[SmsSample, ...] = (
    SmsSample(
        label="hdfc_upi_debit",
        sender="VK-HDFCBK",
        message_text=(
            "Rs.70.00 debited from A/C XXXX0452 at SmartQ on 02-06-26 10:00. "
            "Avl Bal Rs.12,345.67. Ref 998877"
        ),
        expected_parser="hdfc",
        expected_amount=Decimal("70.00"),
        expected_direction=TransactionDirection.DEBIT,
        expected_bank="HDFC",
        expected_last_four="0452",
        expected_merchant="SmartQ",
        expected_reference="998877",
        expected_timestamp=datetime(2026, 6, 2, 10, 0),
        expected_business_type=BusinessType.EXPENSE,
    ),
    SmsSample(
        label="icici_upi_debit",
        sender="AD-ICICIB",
        message_text=(
            "INR 249.00 debited from ICICI Bank Account XX1234 on 15-06-2026. "
            "Info: UPI/SWIGGY/412233445566. Available Balance INR 5,432.10"
        ),
        expected_parser="icici",
        expected_amount=Decimal("249.00"),
        expected_direction=TransactionDirection.DEBIT,
        expected_bank="ICICI",
        expected_last_four="1234",
        expected_timestamp=datetime(2026, 6, 15, 0, 0),
        expected_business_type=BusinessType.EXPENSE,
    ),
    SmsSample(
        label="sbi_salary_credit",
        sender="JD-SBIINB",
        message_text=(
            "Dear Customer, Rs.85,000.00 credited to A/c XXXXX7788 on 30-06-2026 "
            "towards SALARY JUN 2026. Ref no 555444333. Avl Bal Rs.1,02,345.00 -SBI"
        ),
        expected_parser="sbi",
        expected_amount=Decimal("85000.00"),
        expected_direction=TransactionDirection.CREDIT,
        expected_bank="SBI",
        expected_last_four="7788",
        expected_reference="555444333",
        expected_timestamp=datetime(2026, 6, 30, 0, 0),
        expected_business_type=BusinessType.INCOME,
    ),
    SmsSample(
        label="hdfc_credit_card_spend",
        sender="VM-HDFCBK",
        message_text=(
            "Rs 1,899.50 spent on HDFC Bank Credit Card xx9012 at AMAZON on "
            "12-06-2026 18:45. Not you? Call 18002586161"
        ),
        expected_parser="hdfc",
        expected_amount=Decimal("1899.50"),
        expected_direction=TransactionDirection.DEBIT,
        expected_bank="HDFC",
        expected_last_four="9012",
        expected_merchant="AMAZON",
        expected_timestamp=datetime(2026, 6, 12, 18, 45),
        expected_business_type=BusinessType.EXPENSE,
    ),
    SmsSample(
        label="icici_atm_withdrawal",
        sender="AD-ICICIB",
        message_text=(
            "INR 5,000.00 withdrawn from ICICI Bank ATM Card XX4321 on 08-06-2026 "
            "14:20. Avl Bal INR 22,100.00"
        ),
        expected_parser="icici",
        expected_amount=Decimal("5000.00"),
        expected_direction=TransactionDirection.DEBIT,
        expected_bank="ICICI",
        expected_last_four="4321",
        expected_timestamp=datetime(2026, 6, 8, 14, 20),
        expected_business_type=BusinessType.TRANSFER,
    ),
    SmsSample(
        label="generic_refund_credit",
        sender="AX-AXISBK",
        message_text=(
            "Rs.499.00 credited to A/c XX5566 on 20-06-2026 as refund from "
            "FLIPKART. Ref: RFND12345"
        ),
        expected_parser="generic",
        expected_amount=Decimal("499.00"),
        expected_direction=TransactionDirection.CREDIT,
        expected_bank=None,
        expected_last_four="5566",
        expected_reference="RFND12345",
        expected_timestamp=datetime(2026, 6, 20, 0, 0),
        expected_business_type=BusinessType.REFUND,
    ),
    SmsSample(
        label="upi_vpa_debit",
        sender="VK-HDFCBK",
        message_text=(
            "Rs.150 debited from A/c XX0452 to VPA swiggy@icici on 03-06-2026. "
            "UPI Ref 412233445566"
        ),
        expected_parser="hdfc",
        expected_amount=Decimal("150.00"),
        expected_direction=TransactionDirection.DEBIT,
        expected_bank="HDFC",
        expected_last_four="0452",
        expected_timestamp=datetime(2026, 6, 3, 0, 0),
    ),
    SmsSample(
        label="emi_debit",
        sender="VK-HDFCBK",
        message_text=(
            "Rs.12,500.00 debited from A/c XX0452 towards EMI on 05-06-2026. "
            "Ref 778899"
        ),
        expected_parser="hdfc",
        expected_amount=Decimal("12500.00"),
        expected_direction=TransactionDirection.DEBIT,
        expected_bank="HDFC",
        expected_last_four="0452",
        expected_reference="778899",
        expected_business_type=BusinessType.EMI,
    ),
)


NON_TRANSACTIONAL_SAMPLES: tuple[tuple[str, str, str], ...] = (
    (
        "otp",
        "VM-HDFCBK",
        "123456 is your OTP for a transaction of Rs.2,500 on HDFC Bank Card "
        "xx9012. Do not share it with anyone.",
    ),
    (
        "credit_card_due",
        "VM-HDFCBK",
        "Your HDFC Bank Credit Card xx9012 statement for Jun 2026 is Rs.15,430.00, "
        "due on 05-07-2026.",
    ),
    (
        "marketing",
        "AD-ICICIB",
        "You are pre-approved for a personal loan of Rs.5,00,000 at attractive "
        "rates. Apply now!",
    ),
    (
        "scheduled_debit_notice",
        "JD-SBIINB",
        "Rs.2,000.00 will be debited from A/c XXXXX7788 on 01-07-2026 towards "
        "your SIP.",
    ),
    (
        "upi_collect_request",
        "VK-HDFCBK",
        "SWIGGY is requesting money Rs.250.00 from your A/c XX0452. "
        "Approve in your UPI app.",
    ),
)


UNPARSEABLE_SAMPLES: tuple[tuple[str, str, str], ...] = (
    ("no_amount", "VK-HDFCBK", "Your A/c XX0452 has been updated successfully."),
    (
        "no_direction",
        "AD-ICICIB",
        "Transaction of INR 500.00 on card XX1234 processed reference 12345.",
    ),
)
