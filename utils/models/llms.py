"""
LLM usage tracking models for monitoring AI/LLM API calls.
"""

from django.db import models

from .mixins import TimestampedModel


class LLMUsage(TimestampedModel):
    """
    Track LLM API usage.

    Attributes:
        prompt: The input prompt sent to the LLM
        response: The response received from the LLM
        created_at: Timestamp when the record was created (from TimestampedModel)
        updated_at: Timestamp when the record was last updated (from TimestampedModel)
    """
    provider = models.CharField(max_length=255, help_text="The provider used for the API call")
    model = models.CharField(max_length=255, help_text="The model used for the API call")
    prompt = models.TextField(help_text="The prompt sent to the LLM")
    response = models.TextField(blank=True, help_text="The response from the LLM")

    class Meta:
        verbose_name = "LLM Usage"
        verbose_name_plural = "LLM Usage Records"
        ordering = ["-created_at"]

    def __str__(self):
        return f"LLM Usage - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

