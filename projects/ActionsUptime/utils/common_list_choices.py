
INTERVAL_CHOICES = [
        ('5M', '5 Minutes'),
        ('3M', '3 Minutes'),
        ('1M', '1 Minute'),
        ('30S', '30 Seconds'),
]


def get_interval_choices(interval):
    return INTERVAL_CHOICES[:next((i for i, choice in enumerate(INTERVAL_CHOICES) if choice[0] == interval), len(INTERVAL_CHOICES)) + 1]


def get_region_choices(region_prefixes):
    from django.apps import apps
    LambdaRegion = apps.get_model('utils', 'LambdaRegion')
    if region_prefixes:
        regions = LambdaRegion.objects.filter(code_prefix__in=region_prefixes)
        return [(region.id, region.name) for region in regions]
    return [('', 'Actions Uptime Server')]
