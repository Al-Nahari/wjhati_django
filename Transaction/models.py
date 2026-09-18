

import uuid
from django.db import models
from apis.models import BaseModel, User
from django.utils.translation import gettext_lazy as _


class Wallet(BaseModel):
    CURRENCY_CHOICES = (('YE', 'ريال يمني'),)

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet', verbose_name=_("المستخدم"))
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name=_("الرصيد"))
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='YE', verbose_name=_("العملة"))
    is_locked = models.BooleanField(default=False, verbose_name=_("محظورة"))

    def credit(self, amount):
        if amount > 0:
            self.balance += amount
            self.save(update_fields=['balance'])

    def debit(self, amount):
        if amount > 0 and self.balance >= amount:
            self.balance -= amount
            self.save(update_fields=['balance'])
        else:
            raise ValueError(_("رصيد غير كافٍ."))

    def __str__(self):
        return f"{self.user.username} - {self.balance} {self.currency}"

    class Meta:
        verbose_name = _("محفظة")
        verbose_name_plural = _("المحافظ")



class Transfer(BaseModel):
    class Status(models.TextChoices):
        PENDING = 'pending', _("قيد الانتظار")
        COMPLETED = 'completed', _("مكتمل")
        CANCELLED = 'cancelled', _("ملغى")
        FAILED = 'failed', _("فشل")

    from_wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transfers_sent', verbose_name=_("محفظة المرسل"))
    to_wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transfers_received', verbose_name=_("محفظة المستقبل"))
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name=_("المبلغ"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name=_("الحالة"))
    transfer_code = models.CharField(max_length=10, unique=True, verbose_name=_("رمز التحويل"))

    def save(self, *args, **kwargs):
        if not self.transfer_code:
            self.transfer_code = str(uuid.uuid4()).split('-')[0].upper()
        super().save(*args, **kwargs)

    def process_transfer(self):
        if self.status != self.Status.PENDING:
            raise ValueError(_("لا يمكن معالجة تحويل غير قيد الانتظار."))

        if self.from_wallet.balance < self.amount:
            self.status = self.Status.FAILED
            self.save(update_fields=['status'])
            raise ValueError(_("رصيد المرسل غير كافٍ."))

        self.from_wallet.debit(self.amount)
        self.to_wallet.credit(self.amount)
        self.status = self.Status.COMPLETED
        self.save(update_fields=['status'])

    def __str__(self):
        return f"تحويل {self.amount} من {self.from_wallet.user.username} إلى {self.to_wallet.user.username}"

    class Meta:
        verbose_name = _("تحويل مالي")
        verbose_name_plural = _("التحويلات المالية")
        indexes = [
            models.Index(fields=['transfer_code']),
            models.Index(fields=['status']),
        ]



class Transaction(BaseModel):
    TRANSACTION_TYPES = [
        ('charge', _("شحن")),
        ('transfer', _("تحويل")),
        ('withdraw', _("سحب")),
        ('payment', _("دفع")),
        ('refund', _("استرداد")),
    ]

    class Status(models.TextChoices):
        PENDING = 'pending', _("قيد الانتظار")
        COMPLETED = 'completed', _("مكتمل")
        CANCELLED = 'cancelled', _("ملغى")
        FAILED = 'failed', _("فشل")

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions', verbose_name=_("المحفظة"))
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES, verbose_name=_("نوع العملية"))
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name=_("المبلغ"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name=_("الحالة"))
    reference_number = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name=_("رقم المرجع"))
    description = models.TextField(blank=True, null=True, verbose_name=_("الوصف"))
    metadata = models.JSONField(default=dict, blank=True, verbose_name=_("بيانات إضافية"))

    def save(self, *args, **kwargs):
        if not self.reference_number:
            self.reference_number = str(uuid.uuid4()).split('-')[0].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.amount} {self.wallet.currency}"

    class Meta:
        verbose_name = _("عملية")
        verbose_name_plural = _("العمليات")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['transaction_type']),
            models.Index(fields=['status']),
        ]
