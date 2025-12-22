from django.db import models


class LighthouseAudit(models.Model):
    url = models.CharField(max_length=500, help_text="URL that was audited")
    performance_score = models.IntegerField(help_text="Performance score (0-100)")
    accessibility_score = models.IntegerField(help_text="Accessibility score (0-100)")
    best_practices_score = models.IntegerField(help_text="Best Practices score (0-100)")
    seo_score = models.IntegerField(help_text="SEO score (0-100)")
    audit_date = models.DateTimeField(auto_now_add=True, help_text="When the audit was run")
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional Lighthouse data")

    class Meta:
        ordering = ["-audit_date"]
        indexes = [
            models.Index(fields=["-audit_date"]),
            models.Index(fields=["url", "-audit_date"]),
        ]
        verbose_name = "Lighthouse Audit"
        verbose_name_plural = "Lighthouse Audits"

    def __str__(self):
        return f"Audit for {self.url} on {self.audit_date.strftime('%Y-%m-%d %H:%M')}"

    @property
    def average_score(self):
        return round(
            (self.performance_score + self.accessibility_score + self.best_practices_score + self.seo_score) / 4
        )

    @property
    def color_class(self):
        avg = self.average_score
        if avg >= 90:
            return "success"
        elif avg >= 70:
            return "warning"
        else:
            return "danger"
