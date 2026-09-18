import logging
from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User
from django.conf import settings
from apis.tasks import send_fcm_notification
from .models import Booking, Chat, Transaction, Transfer, Bonus, Wallet, CasheBooking, Trip, Notification, FCMToken

logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def create_user_wallet(sender, instance, created, **kwargs):
    if created and not hasattr(instance, 'wallet'):
        Wallet.objects.create(user=instance)


@receiver(post_save, sender=User)
def create_user_chat(sender, instance, created, **kwargs):
    """إنشاء محادثة تلقائية للمستخدم الجديد"""
    if created:
        try:
            chat = Chat.objects.create(title=f"Chat for {instance.username}")
            chat.participants.add(instance)
            logger.info(f"تم إنشاء محادثة جديدة للمستخدم {instance.username}")
        except Exception as e:
            logger.error(f"فشل في إنشاء محادثة للمستخدم {instance.username}: {e}")

@receiver(post_save, sender=Trip)
def mark_driver_unavailable(sender, instance, created, **kwargs):
    if created and instance.driver and instance.status != 'completed':
        instance.driver.is_available = False
        instance.driver.save(update_fields=['is_available'])



@receiver([post_save, post_delete], sender=Booking)
def update_trip_availability(sender, instance, **kwargs):
    instance.trip.update_availability()