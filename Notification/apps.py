import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class NotificationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Notification'

    def ready(self):
        try:
            import Notification.signals  # noqa: F401
        except Exception:
            logger.exception("❌ Failed to load Notification signals")
