from django.contrib import admin
from .models import (
    Client, Vehicle, Driver, Trip, Booking, Rating,
    Chat, Message, SupportTicket,
    SubscriptionPlan, Subscription, Bonus, TripStop, ItemDelivery,
    CasheBooking, CasheItemDelivery
)
# Wallet/Transaction/Transfer انتقلت إلى تطبيق Transaction، وNotification/FCMToken
# إلى تطبيق Notification؛ سجلاتها الآن في admin.py الخاص بكل تطبيق.

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('user', 'city', 'status', 'status_del', 'device_id', 'created_at')
    search_fields = ('user__username', 'city', 'device_id')
    list_filter = ('status', 'city')

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('model', 'plate_number', 'color', 'capacity', 'vehicle_type', 'manufacture_year', 'status')
    search_fields = ('plate_number', 'model')
    list_filter = ('vehicle_type', 'status')

@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ('user', 'license_number', 'rating', 'total_trips', 'is_available', 'where_location')
    search_fields = ('user__username', 'license_number')
    list_filter = ('is_available',)

@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ('from_location', 'to_location', 'departure_time', 'estimated_duration', 'available_seats', 'status', 'driver')
    search_fields = ('from_location', 'to_location', 'driver__user__username')
    list_filter = ('departure_time', 'status')
    readonly_fields = ('route_coordinates',)

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('trip', 'customer', 'seats', 'total_price', 'status')
    search_fields = ('customer__user__username', 'trip__from_location', 'trip__to_location')
    list_filter = ('status',)

@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('trip', 'rated_by', 'driver', 'rating', 'comment')
    search_fields = ('rated_by__user__username', 'driver__user__username')
    list_filter = ('rating',)

@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ('id', 'updated_at')
    search_fields = ('participants__username',)
    list_filter = ()

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('chat', 'sender', 'content', 'is_read', 'created_at')
    search_fields = ('sender__username', 'content')
    list_filter = ('is_read',)

@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('user', 'subject', 'status', 'priority', 'created_at')
    search_fields = ('user__username', 'subject')
    list_filter = ('status', 'priority')

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'duration_days', 'max_trips', 'is_active', 'created_at')
    search_fields = ('name',)
    list_filter = ('is_active',)

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('driver', 'plan', 'start_date', 'end_date', 'is_active', 'remaining_trips')
    search_fields = ('driver__user__username', 'plan__name')
    list_filter = ('is_active', 'end_date')

@admin.register(Bonus)
class BonusAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'reason', 'expiration_date', 'created_at')
    search_fields = ('user__username', 'reason')
    list_filter = ('expiration_date',)

@admin.register(TripStop)
class TripStopAdmin(admin.ModelAdmin):
    list_display = ('trip', 'location', 'order', 'arrival_time')
    search_fields = ('trip__from_location', 'location')
    list_filter = ('order',)

@admin.register(ItemDelivery)
class ItemDeliveryAdmin(admin.ModelAdmin):
    list_display = ('trip', 'sender', 'receiver_name', 'weight', 'status', 'delivery_code')
    search_fields = ('receiver_name', 'delivery_code', 'sender__username')
    list_filter = ('status',)

@admin.register(CasheBooking)
class CasheBookingAdmin(admin.ModelAdmin):
    list_display = ('user', 'from_location', 'to_location', 'departure_time', 'passengers', 'status')
    search_fields = ('user__user__username', 'from_location', 'to_location')
    list_filter = ('departure_time', 'status')

@admin.register(CasheItemDelivery)
class CasheItemDeliveryAdmin(admin.ModelAdmin):
    list_display = ('user', 'from_location', 'to_location', 'item_description', 'weight', 'urgent', 'status', 'created_at')
    search_fields = ('user__user__username', 'from_location', 'to_location')
    list_filter = ('urgent', 'status')
