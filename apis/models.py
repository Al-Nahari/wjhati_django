from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator, FileExtensionValidator
from django.core.exceptions import ValidationError
from django.db.models.signals import post_delete
from django.dispatch import receiver
import uuid

User = get_user_model()
# ============================
# نموذج أساسي للوقت
# ============================
class BaseModel(models.Model):
    """
    نموذج أساسي يحتوي على حقول تتبع وقت الإنشاء والتحديث.
    """
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاريخ الإنشاء"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("تاريخ التحديث"))

    class Meta:
        abstract = True
        ordering = ['-created_at']


# ============================
# نموذج العميل
# ============================
class Client(BaseModel):
    """
    يمثل بيانات العميل المربوطة بحساب المستخدم (نموذج المستخدم الافتراضي).
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='client',
        verbose_name=_("المستخدم")
    )
    phone_number = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_("رقم الهاتف"),
        validators=[
            RegexValidator(
                regex=r'^\+?\d{9,15}$',
                message=_("يجب أن يُدخل رقم هاتف صالح.")
            )
        ]
    )
    device_id = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("معرف الجهاز"))
    status = models.BooleanField(default=True, verbose_name=_("الحالة"))
    status_del = models.BooleanField(default=False, verbose_name=_("محذوف"))
    city = models.CharField(max_length=50, verbose_name=_("المدينة"))

    class Meta:
        db_table = 'clients'
        verbose_name = _("عميل")
        verbose_name_plural = _("العملاء")
        indexes = [
            models.Index(fields=['city']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.city}"


# ============================
# نموذج المركبة
# ============================
class Vehicle(BaseModel):
    """
    يمثل المركبة مع بياناتها الأساسية مثل النوع واللوحة والموديل.
    """
    VEHICLE_TYPES = (
        ('sedan', _("سيدان")),
        ('suv', _("SUV")),
        ('van', _("فان")),
        ('truck', _("شاحنة")),
    )
    
    model = models.CharField(max_length=100, verbose_name=_("الموديل"))
    plate_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_("رقم اللوحة")
    )
    color = models.CharField(max_length=30, verbose_name=_("اللون"))
    capacity = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name=_("السعة")
    )
    vehicle_type = models.CharField(
        max_length=20,
        choices=VEHICLE_TYPES,
        default='sedan',
        verbose_name=_("نوع المركبة")
    )
    manufacture_year = models.IntegerField(
        verbose_name=_("سنة الصنع"),
        null=True,
        blank=True
    )
    inspection_expiry = models.DateField(
        verbose_name=_("انتهاء الفحص الفني"),
        null=True,
        blank=True
    )
    status = models.BooleanField(default=True, verbose_name=_("الحالة"))

    class Meta:
        db_table = 'vehicles'
        verbose_name = _("مركبة")
        verbose_name_plural = _("المركبات")
        indexes = [
            models.Index(fields=['vehicle_type']),
            models.Index(fields=['plate_number']),
        ]

    def __str__(self):
        return f"{self.get_vehicle_type_display()} - {self.plate_number}"


# ============================
# نموذج السائق
# ============================
class Driver(BaseModel):
    """
    يمثل بيانات السائق مع معلومات الرخصة والمركبات المرتبطة والتقييم.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='driver',
        verbose_name=_("المستخدم")
    )
    phone_number = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_("رقم الهاتف"),
        validators=[
            RegexValidator(
                regex=r'^\+?\d{9,15}$',
                message=_("يجب أن يُدخل رقم هاتف صالح.")
            )
        ]
    )
    where_location = models.CharField(max_length=255, verbose_name=_("وين"))
    license_number = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("رقم الرخصة")
    )
    vehicles = models.ManyToManyField(
        Vehicle,
        related_name='drivers',
        verbose_name=_("المركبات")
    )
    rating = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)],
        verbose_name=_("التقييم")
    )
    total_trips = models.IntegerField(default=0, verbose_name=_("إجمالي الرحلات"))
    is_available = models.BooleanField(default=True, verbose_name=_("متاح للرحلات"))

    class Meta:
        verbose_name = _("سائق")
        verbose_name_plural = _("السائقون")
        indexes = [
            models.Index(fields=['rating']),
            models.Index(fields=['is_available']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.license_number}"

    def update_rating(self):
        """
        تحديث التقييم بناءً على متوسط التقييمات المتلقاة.
        يجب استدعاء هذه الدالة بعد إضافة تقييم جديد.
        """
        ratings = self.ratings.all()
        if ratings.exists():
            avg = sum(r.rating for r in ratings) / ratings.count()
            self.rating = round(avg, 2)
            self.save()


# ============================
# نموذج الرحلة
# ============================


class Trip(models.Model):
    """
    يمثل الرحلة مع تفاصيل مثل نقطة الانطلاق، وجهة الوصول، السائق، وغيرها.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', _('قيد الانتظار')
        IN_PROGRESS = 'in_progress', _('قيد التنفيذ')
        FULL = 'full', _('مكتملة')
        COMPLETED = 'completed', _('منتهية')
        CANCELLED = 'cancelled', _('ملغية')

    from_location = models.CharField(max_length=255, verbose_name=_("من"))
    to_location = models.CharField(max_length=255, verbose_name=_("إلى"))
    departure_time = models.DateTimeField(verbose_name=_("وقت المغادرة"))
    estimated_duration = models.DurationField(
        null=True, blank=True, verbose_name=_("المدة المتوقعة")
    )
    distance_km = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_("المسافة (كم)")
    )
    available_seats = models.IntegerField(default=0, verbose_name=_("عدد المقاعد المتاحة"))
    price_per_seat = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_("السعر لكل مقعد")
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name=_("الحالة")
    )
    driver = models.ForeignKey(
        'Driver',
        on_delete=models.CASCADE,
        related_name='trips',
        verbose_name=_("السائق")
    )
    vehicle = models.ForeignKey(
        'Vehicle',
        on_delete=models.CASCADE,
        related_name='trips',
        verbose_name=_("المركبة"),
        null=False
    )
    route_coordinates = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("إحداثيات المسار"),
        help_text=_("تنسيق JSON لإحداثيات المسار (خط الطول والعرض)")
    )

    class Meta:
        verbose_name = _("رحلة")
        verbose_name_plural = _("الرحلات")
        indexes = [
            models.Index(fields=['departure_time']),
            models.Index(fields=['status']),
        ]
        ordering = ['-departure_time']

    def update_availability(self):
        """تحديث عدد المقاعد المتاحة وحالة الرحلة."""
        total_booked = sum(
            len(booking.seats) if isinstance(booking.seats, list) else 0
            for booking in self.bookings.all()
        )
        vehicle = self.driver.vehicles.first() if self.driver else None
        if vehicle:
            self.available_seats = vehicle.capacity - total_booked
        else:
            self.available_seats = 0  # إذا لم يوجد مركبة

        if self.available_seats <= 0 and self.status != self.Status.FULL:
            self.status = self.Status.FULL
        elif self.available_seats > 0 and self.status == self.Status.FULL:
            self.status = self.Status.PENDING

        self.save(update_fields=['available_seats', 'status'])

    def clean(self):
        """التحقق من صحة البيانات قبل الحفظ"""
        vehicle = getattr(self.driver, 'vehicle', None)

        if vehicle:
            if self.available_seats > vehicle.capacity:
                raise ValidationError({
                    'available_seats': 'لا يمكن أن تكون المقاعد المتاحة أكثر من سعة المركبة'
                })

        if self.price_per_seat is not None and self.price_per_seat <= 0:
            raise ValidationError({
                'price_per_seat': 'يجب أن يكون السعر قيمة موجبة'
            })

    def save(self, *args, **kwargs):
        """تجاوز دالة الحفظ لتطبيق القيود المنطقية قبل التخزين"""
        self.clean()
        # تم إزالة منع التعديل أثناء التنفيذ للسماح بتعديل البيانات
        super().save(*args, **kwargs)

class TripLog(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)
    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True)
    total_requests = models.IntegerField()
    total_bookings = models.IntegerField()
    total_deliveries = models.IntegerField()
    passengers_count = models.IntegerField()
    total_weight = models.FloatField()
    created_at = models.DateTimeField()


# ============================
# نموذج الحجز للرحلات
# ============================

class Booking(models.Model):
    """
    يمثل حجز رحلة من قبل العميل مع تفاصيل المقاعد والسعر.
    """
    class Status(models.TextChoices):
        PENDING = 'pending', _("قيد الانتظار")
        CONFIRMED = 'confirmed', _("مؤكد")
        COMPLETED = 'completed', _("مكتمل")
        CANCELLED = 'cancelled', _("ملغى")

    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name='bookings',
        verbose_name=_("الرحلة")
    )
    customer = models.ForeignKey(
        # افترض أن لديك نموذج Client معرف مسبقاً
        'Client',
        on_delete=models.CASCADE,
        related_name='bookings',
        verbose_name=_("العميل")
    )
    seats = models.JSONField(
        default=list,
        verbose_name=_("المقاعد المحجوزة"),
        help_text=_("قائمة بأرقام/أسماء المقاعد المحددة")
    )
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("المبلغ الإجمالي")
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("الحالة")
    )

    class Meta:
        verbose_name = _("حجز")
        verbose_name_plural = _("الحجوزات")
        indexes = [
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.customer.user.username} - {self.trip} ({len(self.seats)} مقاعد)"


# ============================
# نموذج تقييم الرحلة
# ============================
class Rating(BaseModel):
    """
    يمثل تقييم العميل للسائق بعد الرحلة.
    """
    RATING_CHOICES = [
        (1, '★☆☆☆☆'),
        (2, '★★☆☆☆'),
        (3, '★★★☆☆'),
        (4, '★★★★☆'),
        (5, '★★★★★'),
    ]

    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name='ratings',
        verbose_name=_("الرحلة")
    )
    rated_by = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        verbose_name=_("المقيّم")
    )
    driver = models.ForeignKey(
        Driver,
        on_delete=models.CASCADE,
        related_name='ratings',
        verbose_name=_("السائق")
    )
    rating = models.IntegerField(
        choices=RATING_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name=_("التقييم")
    )
    comment = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("تعليق")
    )

    class Meta:
        verbose_name = _("تقييم")
        verbose_name_plural = _("التقييمات")
        unique_together = ('trip', 'rated_by')
        indexes = [
            models.Index(fields=['rating']),
        ]

    def __str__(self):
        return f"{self.rated_by.user.username} → {self.driver.user.username} ({self.rating}/5)"


# ============================
# نموذج المحادثة والدردشة
# ============================




class Chat(BaseModel):
    participants = models.ManyToManyField(
        User,
        related_name='chats'
    )
    last_message = models.ForeignKey(
        'Message',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )

    class Meta:
        verbose_name = "محادثة"
        verbose_name_plural = "المحادثات"
        unique_together = ['id']  # لمنع التكرار على مستوى الكود
        indexes = [
            models.Index(fields=['updated_at']),
        ]

    def __str__(self):
        other = self.participants.exclude(id=self.last_message.sender.id if self.last_message else None).first()
        return f"محادثة مع {other.username if other else '...'}"

    def update_last_message(self):
        last_msg = self.messages.order_by('-created_at').first()
        Chat.objects.filter(id=self.id).update(
            last_message=last_msg,
            updated_at=last_msg.created_at if last_msg else self.updated_at
        )

class Message(BaseModel):
    chat = models.ForeignKey(
        Chat,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name="المحادثة"
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_messages',
        verbose_name="المرسل"
    )
    content = models.TextField(verbose_name="المحتوى", blank=True, null=True)
    attachment = models.FileField(
        upload_to='chat_attachments/%Y/%m/%d/',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'gif', 'pdf', 'mp3', 'mp4'])],
        null=True,
        blank=True
    )
    is_read = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.chat.update_last_message()

    def __str__(self):
        return f"{self.sender.username}: {self.content[:30] if self.content else '📎 مرفق'}"

# ============================
# نموذج تذاكر الدعم الفني
# ============================
class SupportTicket(BaseModel):
    """
    يمثل تذكرة دعم فني مع تحديد أولوية الحالة والسائق المعني (إذا وُجد).
    """
    STATUS_CHOICES = [
        ('open', _("مفتوح")),
        ('in_progress', _("قيد المتابعة")),
        ('resolved', _("تم الحل")),
        ('closed', _("مغلق")),
    ]

    PRIORITY_CHOICES = [
        ('low', _("منخفض")),
        ('medium', _("متوسط")),
        ('high', _("عالي")),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='tickets',
        verbose_name=_("المستخدم")
    )
    subject = models.CharField(max_length=255, verbose_name=_("الموضوع"))
    message = models.TextField(verbose_name=_("الرسالة"))
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='open',
        verbose_name=_("الحالة")
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium',
        verbose_name=_("الأولوية")
    )
    assigned_to = models.ForeignKey(
        Driver,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tickets',
        verbose_name=_("مُعيّن إلى")
    )

    class Meta:
        verbose_name = _("تذكرة دعم")
        verbose_name_plural = _("تذاكر الدعم")
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}: {self.subject} ({self.get_status_display()})"



# ============================
# نموذج خطط الاشتراك
# ============================
class SubscriptionPlan(BaseModel):
    """
    يمثل خطة الاشتراك الشهرية مع تفاصيل السعر والمدة والحد الأقصى للرحلات.
    """
    name = models.CharField(max_length=100, verbose_name=_("اسم الخطة"))
    description = models.TextField(verbose_name=_("الوصف"))
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("السعر الشهري")
    )
    duration_days = models.IntegerField(
        verbose_name=_("المدة بالأيام"),
        help_text=_("عدد أيام سريان الاشتراك")
    )
    max_trips = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_("الحد الأقصى للرحلات"),
        help_text=_("إذا كان غير محدد، عدد الرحلات غير محدود")
    )
    is_active = models.BooleanField(default=True, verbose_name=_("نشطة"))

    class Meta:
        verbose_name = _("خطة اشتراك")
        verbose_name_plural = _("خطط الاشتراك")
        ordering = ['price']

    def __str__(self):
        return f"{self.name} ({self.price} SAR)"


# ============================
# نموذج الاشتراك
# ============================
class Subscription(BaseModel):
    """
    يمثل اشتراك السائق في إحدى الخطط.
    """
    driver = models.ForeignKey(
        Driver,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name=_("السائق")
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.CASCADE,
        verbose_name=_("الخطة")
    )
    start_date = models.DateField(verbose_name=_("تاريخ البدء"))
    end_date = models.DateField(verbose_name=_("تاريخ الانتهاء"))
    is_active = models.BooleanField(default=True, verbose_name=_("نشط"))
    remaining_trips = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_("الرحلات المتبقية")
    )

    class Meta:
        verbose_name = _("اشتراك")
        verbose_name_plural = _("الاشتراكات")
        indexes = [
            models.Index(fields=['end_date']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.driver.user.username} - {self.plan}"


# ============================
# نموذج المكافآت
# ============================

class Bonus(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bonuses', verbose_name=_("المستخدم"))
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("المبلغ"))
    reason = models.CharField(
        max_length=255,
        choices=[
            ('referral', _("مكافأة إحالة")),
            ('promotion', _("عرض ترويجي")),
            ('other', _("أخرى")),
        ],
        default='other',
        verbose_name=_("السبب")
    )
    expiration_date = models.DateField(null=True, blank=True, verbose_name=_("تاريخ الانتهاء"))
    processed = models.BooleanField(default=False, verbose_name=_("معالجة"))

    def __str__(self):
        return f"{self.user.username} - {self.amount} ريال ({self.get_reason_display()})"

    class Meta:
        verbose_name = _("مكافأة")
        verbose_name_plural = _("المكافآت")
        indexes = [models.Index(fields=['expiration_date'])]

# ============================
# نموذج محطات توقف الرحلة
# ============================

class TripStop(models.Model):
    """
    يمثل محطة توقف خلال الرحلة مع ترتيبها ووقت الوصول المتوقع.
    """
    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name='stops',
        verbose_name=_("الرحلة")
    )
    location = models.CharField(max_length=255, verbose_name=_("الموقع"))
    order = models.PositiveIntegerField(verbose_name=_("ترتيب المحطة"))
    arrival_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("وقت الوصول المتوقع")
    )

    class Meta:
        db_table = 'trip_stops'
        verbose_name = _("محطة توقف")
        verbose_name_plural = _("محطات التوقف")
        ordering = ['order']
        unique_together = ('trip', 'order')

    def __str__(self):
        return f"{self.trip} - {self.location} ({self.order})"

# ============================
# نموذج شحنات تسليم العناصر
# ============================
class ItemDelivery(BaseModel):
    """
    يمثل شحنة لتوصيل عنصر مع تفاصيل الوزن، التأمين وكود الشحنة.
    """
    class Status(models.TextChoices):
        PENDING = 'pending', _("قيد الانتظار")
        IN_TRANSIT = 'in_transit', _("قيد النقل")
        DELIVERED = 'delivered', _("تم التسليم")
        CANCELLED = 'cancelled', _("ملغاة")

    trip = models.ForeignKey(
        'Trip',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deliveries',
        verbose_name=_("الرحلة")
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_deliveries',
        verbose_name=_("المرسل")
    )
    receiver_name = models.CharField(max_length=255, verbose_name=_("اسم المستلم"))
    receiver_phone = models.CharField(max_length=20, verbose_name=_("هاتف المستلم"))
    item_description = models.TextField(verbose_name=_("وصف الشحنة"))
    weight = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("الوزن (كجم)")
    )
    insurance_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("مبلغ التأمين")
    )
    delivery_code = models.CharField(
        max_length=10,
        verbose_name=_("كود الشحنة")
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("الحالة")
    )

    class Meta:
        verbose_name = _("شحنة")
        verbose_name_plural = _("الشحنات")
        indexes = [
            models.Index(fields=['delivery_code']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"شحنة #{self.delivery_code} - {self.get_status_display()}"


# ============================
# نموذج الحجز المسبق (CasheBooking)
# ============================

class CasheBooking(models.Model):
    """
    يمثل حجز مسبق للرحلة مع تفاصيل المواقع ووقت المغادرة وعدد الركاب.
    """
    class Status(models.TextChoices):
        PENDING = 'pending', _("قيد الانتظار")
        ACCEPTED = 'accepted', _("مقبول")
        FAILED = 'failed', _("فشل")  # التأكد من وجود هذا التعريف
        CANCELLED = 'cancelled', _("ملغى")

    user = models.ForeignKey(
        # افترض أن لديك نموذج Client معرف مسبقاً
        'Client',
        on_delete=models.CASCADE,
        related_name='cashe_bookings',
        verbose_name=_("المستخدم")
    )
    from_location = models.CharField(max_length=255, verbose_name=_("من"))
    to_location = models.CharField(max_length=255, verbose_name=_("إلى"))
    departure_time = models.DateTimeField(verbose_name=_("وقت المغادرة"))
    passengers = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name=_("عدد الركاب")
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("الحالة")
    )
    notes = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("ملاحظات إضافية")
    )

    class Meta:
        verbose_name = _("حجز مسبق")
        verbose_name_plural = _("الحجوزات المسبقة")
        indexes = [
            models.Index(fields=['departure_time']),
        ]

    def __str__(self):
        return f"حجز مسبق #{self.id} - {self.user.user.username}"


# ============================
# نموذج طلب توصيل مسبق (CasheItemDelivery)
# ============================
class CasheItemDelivery(BaseModel):
    """
    يمثل طلب توصيل مسبق لعنصر مع تحديد إذا ما كان عاجلًا.
    """
    class Status(models.TextChoices):
        PENDING = 'pending', _("قيد الانتظار")
        ACCEPTED = 'accepted', _("مقبول")
        IN_PROGRESS = 'in_progress', _("قيد التوصيل")
        DELIVERED = 'delivered', _("تم التسليم")
        CANCELLED = 'cancelled', _("ملغى")

    user = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='cashe_deliveries',
        verbose_name=_("المستخدم")
    )
    from_location = models.CharField(max_length=255, verbose_name=_("من"))
    to_location = models.CharField(max_length=255, verbose_name=_("إلى"))
    receiver_name = models.CharField(max_length=255, verbose_name=_("اسم المستلم"))
    receiver_phone = models.CharField(max_length=20, verbose_name=_("هاتف المستلم"))
    item_description = models.TextField(verbose_name=_("وصف الشحنة"))
    weight = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("الوزن (كجم)")
    )
    urgent = models.BooleanField(default=False, verbose_name=_("عاجل"))
    insurance_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("مبلغ التأمين")
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("الحالة")
    )

    class Meta:
        verbose_name = _("طلب توصيل مسبق")
        verbose_name_plural = _("طلبات التوصيل المسبقة")
        indexes = [
            models.Index(fields=['urgent']),
        ]

    def __str__(self):
        return f"طلب توصيل #{self.id} - {self.user.user.username}"
