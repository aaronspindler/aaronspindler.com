"""
Crypto model - represents cryptocurrencies and tokens.
"""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from .asset import Asset


class Crypto(Asset):
    """
    Represents a cryptocurrency or token.

    Extends Asset base model with crypto-specific fields.
    """

    class Blockchain(models.TextChoices):
        """Blockchain networks."""

        BITCOIN = "BTC", "Bitcoin"
        ETHEREUM = "ETH", "Ethereum"
        BINANCE_SMART_CHAIN = "BSC", "Binance Smart Chain"
        SOLANA = "SOL", "Solana"
        CARDANO = "ADA", "Cardano"
        POLYGON = "MATIC", "Polygon"
        AVALANCHE = "AVAX", "Avalanche"
        POLKADOT = "DOT", "Polkadot"
        COSMOS = "ATOM", "Cosmos"
        ARBITRUM = "ARB", "Arbitrum"
        OPTIMISM = "OP", "Optimism"
        BASE = "BASE", "Base"
        OTHER = "OTHER", "Other"

    class TokenType(models.TextChoices):
        """Type of crypto asset."""

        COIN = "COIN", "Native Coin"
        TOKEN = "TOKEN", "Token"
        STABLECOIN = "STABLE", "Stablecoin"
        DEFI = "DEFI", "DeFi Token"
        NFT = "NFT", "NFT Collection"
        GOVERNANCE = "GOV", "Governance Token"
        WRAPPED = "WRAPPED", "Wrapped Token"
        OTHER = "OTHER", "Other"

    class ConsensusMechanism(models.TextChoices):
        """Consensus mechanism used."""

        PROOF_OF_WORK = "POW", "Proof of Work"
        PROOF_OF_STAKE = "POS", "Proof of Stake"
        DELEGATED_POS = "DPOS", "Delegated Proof of Stake"
        PROOF_OF_AUTHORITY = "POA", "Proof of Authority"
        PROOF_OF_HISTORY = "POH", "Proof of History"
        HYBRID = "HYBRID", "Hybrid"
        OTHER = "OTHER", "Other"

    # Blockchain and type
    blockchain = models.CharField(
        max_length=10,
        choices=Blockchain.choices,
        db_index=True,
        help_text="Primary blockchain network",
    )
    token_type = models.CharField(
        max_length=10,
        choices=TokenType.choices,
        default=TokenType.COIN,
        db_index=True,
        help_text="Type of crypto asset",
    )

    # Contract details
    contract_address = models.CharField(
        max_length=255,
        blank=True,
        help_text="Smart contract address (for tokens)",
    )

    # Supply information
    max_supply = models.DecimalField(
        max_digits=30,
        decimal_places=8,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00000001"))],
        help_text="Maximum supply (if capped)",
    )
    circulating_supply = models.DecimalField(
        max_digits=30,
        decimal_places=8,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00000001"))],
        help_text="Current circulating supply",
    )

    # Market data
    market_cap_rank = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text="Market capitalization ranking",
    )

    # Technical details
    consensus_mechanism = models.CharField(
        max_length=10,
        choices=ConsensusMechanism.choices,
        blank=True,
        help_text="Consensus mechanism used",
    )

    class Meta:
        db_table = "feefifofunds_crypto"
        verbose_name = "Cryptocurrency"
        verbose_name_plural = "Cryptocurrencies"
        ordering = ["market_cap_rank", "ticker"]
        indexes = [
            models.Index(fields=["blockchain", "token_type"]),
            models.Index(fields=["market_cap_rank"]),
        ]

    @property
    def supply_percentage(self) -> Decimal | None:
        """Calculate percentage of max supply in circulation."""
        if self.circulating_supply and self.max_supply and self.max_supply > 0:
            return (self.circulating_supply / self.max_supply) * 100
        return None

    @property
    def is_capped(self) -> bool:
        """Check if supply is capped."""
        return self.max_supply is not None and self.max_supply > 0
