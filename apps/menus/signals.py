from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import MenuItem


MENU_CACHE_PATTERN = "visor:menu:*"


@receiver([post_save, post_delete], sender=MenuItem)
def clear_menu_cache(**kwargs):
    try:
        cache.delete_pattern(MENU_CACHE_PATTERN)
    except Exception:
        cache.clear()