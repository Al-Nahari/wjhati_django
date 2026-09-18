from venv import logger
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from apis.models import Bonus
from .models import Transaction, Transfer, Wallet

@receiver(post_save, sender=Bonus)
def handle_bonus_creation(sender, instance, created, **kwargs):
    if not created or instance.processed:
        return

    try:
        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(user=instance.user)
            wallet.credit(instance.amount)
            instance.processed = True
            instance.save(update_fields=['processed'])
    except Wallet.DoesNotExist:
        raise ObjectDoesNotExist(f"المستخدم {instance.user.username} ليس لديه محفظة")

@receiver(post_save, sender=Transaction)
def update_wallet_balance(sender, instance, created, **kwargs):
    if not created:
        return

    wallet = instance.wallet
    try:
        with transaction.atomic():
            if instance.transaction_type == 'charge':
                wallet.credit(instance.amount)
            elif instance.transaction_type in ['withdraw', 'payment']:
                wallet.debit(instance.amount)
    except Exception as e:
        raise

@receiver(post_save, sender=Transfer)
def auto_process_transfer(sender, instance, created, **kwargs):
    if created:
        try:
            instance.process_transfer()
        except Exception as e:
            logger.error(f"فشل في معالجة التحويل {instance.id}: {e}")
