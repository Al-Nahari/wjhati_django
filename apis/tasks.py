from celery import shared_task
import logging

logger = logging.getLogger(__name__)

@shared_task
def run_trip_scheduler():
    try:
        from django.core.management import call_command

        logger.info("🚀 Running intelligent trip scheduler via Celery...")
        call_command('dbscan_clustering', '--min_cluster_size=3')
        logger.info("✅ Trip scheduler executed successfully.")
    except Exception as e:
        logger.exception("❌ Trip scheduler execution failed")


def send_fcm_notification(user, title, message, data=None):
    from firebase_admin import messaging
    from apis.models import FCMToken
    import apis.firebase  # noqa: F401  # للتأكد من تهيئة Firebase

    tokens = FCMToken.objects.filter(user=user).values_list('token', flat=True)
    if not tokens:
        logger.info("🚫 لا توجد توكنات FCM للمستخدم.")
        return

    # جهّز dict للـ data مع تحويل القيم إلى نص واستبعاد None
    clean_data = {}
    if data:
        for key, value in data.items():
            if value is not None:
                clean_data[key] = str(value)

    for token in tokens:
        msg = messaging.Message(
            notification=messaging.Notification(title=title, body=message),
            token=token,
            data=clean_data,
        )
        try:
            logger.info("🚀 إرسال إشعار عبر Firebase Admin SDK...")
            response = messaging.send(msg)
            logger.info("✅ تم الإرسال: %s", response)
        except Exception:
            logger.exception("❌ فشل إرسال الإشعار")
