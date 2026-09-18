from django.contrib import admin

from .models import Transaction, Transfer, Wallet


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'currency', 'is_locked', 'created_at')
    search_fields = ('user__username',)
    list_filter = ('currency', 'is_locked')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'transaction_type', 'amount', 'status', 'reference_number', 'created_at')
    search_fields = ('wallet__user__username', 'transaction_type')
    list_filter = ('transaction_type', 'status')
    readonly_fields = ('reference_number',)


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ('from_wallet', 'to_wallet', 'amount', 'status', 'transfer_code', 'created_at')
    search_fields = ('from_wallet__user__username', 'to_wallet__user__username', 'transfer_code')
    list_filter = ('status',)
