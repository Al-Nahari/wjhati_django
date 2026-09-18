import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class TransactionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Transaction'

    def ready(self):
        try:
            import Transaction.signals  # noqa: F401
        except Exception:
            logger.exception("❌ Failed to load Transaction signals")
