from django.db.models import Q

INTERVAL_CHOICES = [
        ('5M', '5 Minutes'),
        ('3M', '3 Minutes'),
        ('1M', '1 Minute'),
        ('30S', '30 Seconds'),
]

def get_interval_choices(interval):
    return INTERVAL_CHOICES[:next((i for i, choice in enumerate(INTERVAL_CHOICES) if choice[0] == interval), len(INTERVAL_CHOICES)) + 1]
