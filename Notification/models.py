from django.utils.translation import gettext_lazy as _

from apis import models


class FCMToken(models.Model):
    user = models.ForeignKey(
        models.User, 
        on_delete=models.CASCADE, 
        related_name='fcm_tokens',
        verbose_name=_("User")
    )
    token = models.CharField(
        max_length=255, 
        unique=True,
        verbose_name=_("FCM Token")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At")
    )
    device_info = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_("Device Information")
    )
    
    class Meta:
        verbose_name = _("FCM Token")
        verbose_name_plural = _("FCM Tokens")
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['user']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.token[:10]}..."


class Notification(models.BaseModel):
    """
    يمثل إشعار للمستخدم بأنشطة مختلفة في النظام.
    """
    user = models.ForeignKey(
        models.User,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_("المستخدم")
    )
    title = models.CharField(max_length=200, verbose_name=_("العنوان"))
    message = models.TextField(verbose_name=_("المحتوى"))
    is_read = models.BooleanField(default=False, verbose_name=_("تم القراءة"))
    notification_type = models.CharField(
        max_length=50,
        choices=[
            ('booking', _("حجز")),
            ('trip', _("رحلة")),
            ('payment', _("دفع")),
            ('system', _("نظام")),
        ],
        default='system',
        verbose_name=_("نوع الإشعار")
    )
    related_object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("معرّف الكائن المرتبط")
    )

    class Meta:
        verbose_name = _("إشعار")
        verbose_name_plural = _("الإشعارات")
        indexes = [
            models.Index(fields=['is_read']),
            models.Index(fields=['notification_type']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.user.username}"
