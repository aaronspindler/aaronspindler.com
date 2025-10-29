"""
SavingsAccount model - represents savings accounts, CDs, and money market accounts.
"""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from .asset import Asset


class SavingsAccount(Asset):
    """
    Represents a savings account, CD, or money market account.

    Extends Asset base model with savings account-specific fields.
    """

    class AccountType(models.TextChoices):
        """Type of savings account."""

        SAVINGS = "SAVINGS", "Savings Account"
        HYSA = "HYSA", "High-Yield Savings Account"
        MONEY_MARKET = "MM", "Money Market Account"
        CD = "CD", "Certificate of Deposit"
        CHECKING = "CHECKING", "Interest-Bearing Checking"
        OTHER = "OTHER", "Other"

    # Account details
    institution_name = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Financial institution name",
    )
    account_type = models.CharField(
        max_length=10,
        choices=AccountType.choices,
        default=AccountType.SAVINGS,
        db_index=True,
        help_text="Type of account",
    )

    # Account terms
    minimum_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Minimum balance requirement",
    )
    term_length_months = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text="Term length in months (for CDs)",
    )

    # Insurance and protection
    fdic_insured = models.BooleanField(
        default=True,
        help_text="FDIC insured (or equivalent)",
    )

    class Meta:
        db_table = "feefifofunds_savings"
        verbose_name = "Savings Account"
        verbose_name_plural = "Savings Accounts"
        ordering = ["institution_name", "account_type"]
        indexes = [
            models.Index(fields=["institution_name", "account_type"]),
            models.Index(fields=["account_type"]),
        ]

    def __str__(self) -> str:
        """String representation."""
        return f"{self.institution_name} - {self.get_account_type_display()}"

    @property
    def is_cd(self) -> bool:
        """Check if this is a CD."""
        return self.account_type == self.AccountType.CD

    @property
    def term_years(self) -> float | None:
        """Get term length in years."""
        if self.term_length_months:
            return self.term_length_months / 12.0
        return None
