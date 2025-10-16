from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from django.utils.text import slugify


class FundProvider(models.Model):
    """Companies that offer mutual funds and ETFs."""

    name = models.CharField(max_length=255, unique=True, help_text="Provider name (e.g., Vanguard, TD, RBC)")
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    website = models.URLField(blank=True, help_text="Provider website URL")
    description = models.TextField(blank=True, help_text="Brief description of the provider")
    logo = models.ImageField(upload_to="funds/providers/", blank=True, null=True, help_text="Provider logo")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Fund Provider"
        verbose_name_plural = "Fund Providers"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            original_slug = self.slug
            counter = 1
            while FundProvider.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Fund(models.Model):
    """
    Represents both mutual funds and ETFs for comparison purposes.
    High MER mutual funds vs low-fee index ETFs.
    """

    FUND_TYPE_CHOICES = [
        ("MUTUAL_FUND", "Mutual Fund"),
        ("ETF", "Exchange-Traded Fund (ETF)"),
    ]

    ASSET_CLASS_CHOICES = [
        ("EQUITY", "Equity"),
        ("BONDS", "Bonds / Fixed Income"),
        ("BALANCED", "Balanced"),
        ("MONEY_MARKET", "Money Market"),
        ("REAL_ESTATE", "Real Estate / REITs"),
        ("COMMODITIES", "Commodities"),
        ("ALTERNATIVE", "Alternative"),
    ]

    GEOGRAPHIC_FOCUS_CHOICES = [
        ("CANADIAN", "Canadian"),
        ("US", "United States"),
        ("INTERNATIONAL", "International (Ex North America)"),
        ("GLOBAL", "Global"),
        ("EMERGING", "Emerging Markets"),
        ("REGIONAL", "Regional / Specific Country"),
    ]

    # Basic Information
    name = models.CharField(max_length=255, help_text="Full fund name")
    ticker = models.CharField(
        max_length=20, unique=True, db_index=True, help_text="Ticker symbol (e.g., VFV, VGRO, TDB902)"
    )
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    provider = models.ForeignKey(FundProvider, on_delete=models.CASCADE, related_name="funds")
    fund_type = models.CharField(max_length=20, choices=FUND_TYPE_CHOICES, db_index=True)
    description = models.TextField(blank=True, help_text="Fund description and investment strategy")

    # Fee Structure
    mer = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Management Expense Ratio (MER) as percentage (e.g., 2.50 for 2.5%)",
    )
    front_load = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text="Front-end load fee as percentage (e.g., 5.00 for 5%)",
    )
    back_load = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text="Back-end load / DSC fee as percentage (e.g., 5.00 for 5%)",
    )
    transaction_fee = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0.00,
        help_text="Transaction fee in dollars (e.g., 9.99)",
    )

    # Classification
    asset_class = models.CharField(max_length=20, choices=ASSET_CLASS_CHOICES, db_index=True)
    geographic_focus = models.CharField(max_length=20, choices=GEOGRAPHIC_FOCUS_CHOICES, db_index=True)

    # Performance (as percentages, e.g., 10.5 for 10.5% return)
    ytd_return = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True, help_text="Year-to-date return (%)"
    )
    one_year_return = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True, help_text="1-year return (%)"
    )
    three_year_return = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True, help_text="3-year annualized return (%)"
    )
    five_year_return = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True, help_text="5-year annualized return (%)"
    )
    ten_year_return = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True, help_text="10-year annualized return (%)"
    )

    # Fund Details
    inception_date = models.DateField(null=True, blank=True, help_text="Date the fund was created")
    aum = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Assets Under Management in millions (e.g., 1500.00 for $1.5B)",
    )
    minimum_investment = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Minimum investment amount in dollars",
    )

    # Metadata
    last_data_update = models.DateField(null=True, blank=True, help_text="Date when performance data was last updated")
    data_source_url = models.URLField(blank=True, help_text="URL to fund's official page or data source")
    is_active = models.BooleanField(default=True, help_text="Whether the fund is still available for investment")

    # PostgreSQL full-text search vector
    search_vector = SearchVectorField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Fund"
        verbose_name_plural = "Funds"
        ordering = ["ticker"]
        indexes = [
            GinIndex(fields=["search_vector"], name="fund_search_idx"),
            models.Index(fields=["fund_type", "asset_class"], name="fund_type_class_idx"),
            models.Index(fields=["mer"], name="fund_mer_idx"),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = f"{self.ticker}-{slugify(self.name)}"[:250]
            self.slug = base_slug
            original_slug = self.slug
            counter = 1
            while Fund.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    def get_total_cost_percentage(self):
        """
        Calculate the total annual cost as a percentage.
        Includes MER but excludes one-time loads.
        """
        return float(self.mer)

    def calculate_fee_impact(self, initial_investment, years, annual_return=7.0):
        """
        Calculate the impact of fees over time compared to a zero-fee investment.

        Args:
            initial_investment: Initial investment amount in dollars
            years: Number of years to project
            annual_return: Expected annual return before fees (default 7%)

        Returns:
            dict with projection data including final values and total fees paid
        """
        annual_return_decimal = annual_return / 100
        mer_decimal = float(self.mer) / 100

        # Calculate with fees
        value_with_fees = initial_investment
        total_fees_paid = 0

        for year in range(years):
            gross_return = value_with_fees * annual_return_decimal
            fees = value_with_fees * mer_decimal
            value_with_fees = value_with_fees + gross_return - fees
            total_fees_paid += fees

        # Calculate without fees (0% MER)
        value_without_fees = initial_investment * ((1 + annual_return_decimal) ** years)

        # Fee impact
        fee_impact = value_without_fees - value_with_fees

        return {
            "final_value_with_fees": round(value_with_fees, 2),
            "final_value_without_fees": round(value_without_fees, 2),
            "total_fees_paid": round(total_fees_paid, 2),
            "fee_impact": round(fee_impact, 2),
            "fee_impact_percentage": round((fee_impact / value_without_fees) * 100, 2),
        }

    def __str__(self):
        return f"{self.ticker} - {self.name}"


class PerformanceHistory(models.Model):
    """
    Track historical NAV (Net Asset Value) and returns for funds over time.
    Useful for generating performance charts.
    """

    fund = models.ForeignKey(Fund, on_delete=models.CASCADE, related_name="performance_history")
    date = models.DateField(db_index=True, help_text="Date of the NAV reading")
    nav = models.DecimalField(max_digits=10, decimal_places=4, help_text="Net Asset Value")
    daily_return = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True, help_text="Daily return percentage"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Performance History"
        verbose_name_plural = "Performance Histories"
        ordering = ["-date"]
        unique_together = [["fund", "date"]]
        indexes = [
            models.Index(fields=["fund", "-date"], name="fund_date_idx"),
        ]

    def __str__(self):
        return f"{self.fund.ticker} - {self.date}: ${self.nav}"
