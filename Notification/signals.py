
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

import Notification
from apis.tasks import send_fcm_notification

@receiver(post_save, sender=Notification)
def on_notification_created(sender, instance, created, **kwargs):
    if created:
        # ترسل الإشعار مباشرة بعد إنشاء السجل
        send_fcm_notification(
            user=instance.user,
            title=instance.title,
            message=instance.message,
            data={
                "notification_type": getattr(instance, "notification_type", ""),
                "related_object_id": getattr(instance, "related_object_id", "")
            }
        )
