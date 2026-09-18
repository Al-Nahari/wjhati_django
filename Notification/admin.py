from django.contrib import admin

from .models import FCMToken, Notification


@admin.register(FCMToken)
class FCMTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'created_at')
    search_fields = ('user__username', 'token')
    list_filter = ('created_at',)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'is_read', 'notification_type', 'created_at')
    search_fields = ('user__username', 'title')
    list_filter = ('notification_type', 'is_read')
