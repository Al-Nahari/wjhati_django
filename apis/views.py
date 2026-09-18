import logging

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from rest_framework import generics, mixins, permissions, status, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Bonus, Booking, CasheBooking, CasheItemDelivery, Chat, Client, Driver,
    ItemDelivery, Message, Rating, Subscription,
    SubscriptionPlan, SupportTicket, Trip, TripStop,
    Vehicle,
)
from Notification.models import FCMToken, Notification
from Transaction.models import Transaction, Transfer, Wallet
from .permissions import IsDriverOrStaffOrReadOnly, IsStaffOrReadOnly
from .serializers import (
    BonusSerializer, BookingSerializer, CasheBookingSerializer,
    CasheItemDeliverySerializer, ChatSerializer, ClientSerializer,
    DriverSerializer, ItemDeliverySerializer, MessageSerializer,
    NotificationSerializer, RatingSerializer, RegisterSerializer,
    SubscriptionPlanSerializer, SubscriptionSerializer,
    SupportTicketSerializer, TransactionSerializer, TransferSerializer,
    TripSerializer, TripStopSerializer, UserSerializer, VehicleSerializer,
    WalletSerializer,
)

User = get_user_model()

logger = logging.getLogger(__name__)


# ============================
# المستخدمون
# ============================
class UserViewSet(viewsets.ModelViewSet):
    """
    المشرف يرى كل المستخدمين؛ أي مستخدم آخر يرى حسابه فقط
    (كانت القائمة الكاملة بالبريد الإلكتروني متاحة لأي زائر بلا تسجيل دخول).
    """
    queryset = User.objects.all().order_by('id')
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action in ('create', 'destroy'):
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_staff:
            return qs
        return qs.filter(pk=self.request.user.pk)


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class ClientViewSet(viewsets.ModelViewSet):
    """
    واجهة للتعامل مع بيانات العملاء.
    """
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        جلب بيانات العميل المرتبطة بالمستخدم الحالي.
        """
        user = self.request.user
        if user.is_staff:
            return Client.objects.all()
        if hasattr(user, 'client'):
            return Client.objects.filter(user=user)
        return Client.objects.none()

    def perform_create(self, serializer):
        if hasattr(self.request.user, 'client'):
            raise ValidationError({'detail': 'لديك ملف عميل بالفعل.'})
        serializer.save(user=self.request.user)


# ============================
# المال (قراءة فقط — الرصيد لا يُعدَّل مباشرة من العميل)
# ============================
class WalletViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WalletSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Wallet.objects.all()
        return Wallet.objects.filter(user=user)

    def retrieve(self, request, *args, **kwargs):
        # يبقى السلوك القديم: أي معرّف يُعيد محفظة المستخدم الحالي
        wallet = Wallet.objects.filter(user=request.user).first()
        if wallet:
            serializer = self.get_serializer(wallet)
            return Response(serializer.data)
        return Response({"detail": "المحفظة غير موجودة."}, status=status.HTTP_404_NOT_FOUND)


class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """سجل العمليات المالية. الإنشاء يتم من لوحة الإدارة/بوابة الدفع فقط."""
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return self.queryset
        return self.queryset.filter(wallet__user=self.request.user)


class TransferViewSet(mixins.CreateModelMixin,
                      mixins.ListModelMixin,
                      mixins.RetrieveModelMixin,
                      viewsets.GenericViewSet):
    queryset = Transfer.objects.all()
    serializer_class = TransferSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return self.queryset
        return self.queryset.filter(Q(from_wallet__user=user) | Q(to_wallet__user=user))


# ============================
# المركبات والسائقون
# ============================
class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer
    permission_classes = [IsDriverOrStaffOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return self.queryset
        if hasattr(user, 'driver'):
            return self.queryset.filter(drivers=user.driver)
        if hasattr(user, 'client'):
            return self.queryset.filter(trips__bookings__customer=user.client).distinct()
        return self.queryset.none()

    def perform_create(self, serializer):
        vehicle = serializer.save()
        driver = getattr(self.request.user, 'driver', None)
        if driver:
            driver.vehicles.add(vehicle)


class DriverViewSet(viewsets.ModelViewSet):
    serializer_class = DriverSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Driver.objects.all()
        # يعرض فقط بيانات السائق المرتبطة بالمستخدم الحالي
        if hasattr(user, 'driver'):
            return Driver.objects.filter(user=user)
        return Driver.objects.none()

    def perform_create(self, serializer):
        if hasattr(self.request.user, 'driver'):
            raise ValidationError({'detail': 'لديك ملف سائق بالفعل.'})
        # يجبر ربط السائق بالمستخدم الحالي
        serializer.save(user=self.request.user)


# ============================
# الرحلات والحجوزات
# ============================
class TripViewSet(viewsets.ModelViewSet):
    serializer_class = TripSerializer
    permission_classes = [IsDriverOrStaffOrReadOnly]
    queryset = Trip.objects.all()

    def get_queryset(self):
        user = self.request.user
        queryset = Trip.objects.all()
        if user.is_staff:
            return queryset
        # إذا كان المستخدم سائقاً، اعرض له فقط الرحلات التي هو السائق لها
        if hasattr(user, 'driver'):
            return queryset.filter(driver=user.driver)
        # إذا كان المستخدم عميلاً، اعرض له الرحلات التي لديه فيها Booking أو ItemDelivery فقط
        if hasattr(user, 'client'):
            return queryset.filter(
                Q(bookings__customer=user.client) | Q(deliveries__sender=user)
            ).distinct()
        return queryset.none()

    def perform_create(self, serializer):
        user = self.request.user
        if hasattr(user, 'driver') and not user.is_staff:
            serializer.save(driver=user.driver)
        elif serializer.validated_data.get('driver') is None:
            raise ValidationError({'driver': 'هذا الحقل مطلوب.'})
        else:
            serializer.save()

    def perform_update(self, serializer):
        if self.request.user.is_staff:
            serializer.save()
        else:
            # السائق لا يستطيع نقل رحلته لسائق آخر
            serializer.save(driver=serializer.instance.driver)


class BookingViewSet(viewsets.ModelViewSet):
    """
    واجهة للتعامل مع الحجوزات مع فلترة حسب المستخدم والحالة
    """
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        فلترة الحجوزات حسب:
        - إذا كان المستخدم عميلاً: يعرض حجوزاته فقط
        - إذا كان المستخدم سائقاً: يعرض حجوزات رحلاته فقط
        - إذا كان مديراً: يعرض جميع الحجوزات
        - أي مستخدم آخر: لا شيء (كان يرى كل الحجوزات!)
        مع إمكانية تصفية حسب الحالة أو الرحلة
        """
        user = self.request.user
        queryset = super().get_queryset()

        # فلترة حسب رقم الرحلة (trip)
        trip_id = self.request.query_params.get('trip')
        if trip_id:
            queryset = queryset.filter(trip_id=trip_id)

        # فلترة حسب الحالة إن وجدت
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)

        if user.is_staff:
            return queryset
        if hasattr(user, 'client'):
            return queryset.filter(customer=user.client)
        if hasattr(user, 'driver'):
            return queryset.filter(trip__driver=user.driver)
        return queryset.none()

    def perform_create(self, serializer):
        client = getattr(self.request.user, 'client', None)
        if client is None:
            raise PermissionDenied("الحجز متاح للعملاء فقط.")
        trip = serializer.validated_data['trip']
        seats = serializer.validated_data['seats']
        serializer.save(
            customer=client,
            total_price=trip.price_per_seat * len(seats),
            status=Booking.Status.PENDING,
        )

    def perform_update(self, serializer):
        user = self.request.user
        new_status = serializer.validated_data.get('status')
        booking = serializer.instance

        if not user.is_staff:
            is_driver_of_trip = hasattr(user, 'driver') and booking.trip.driver_id == user.driver.pk
            if is_driver_of_trip:
                pass  # السائق يدير حالة حجوزات رحلاته
            else:
                # العميل: يستطيع فقط إلغاء حجزه
                if new_status not in (None, booking.status, Booking.Status.CANCELLED):
                    raise PermissionDenied("يمكنك إلغاء الحجز فقط.")
                if set(serializer.validated_data) - {'status'}:
                    raise PermissionDenied("لا يمكن تعديل بيانات الحجز، يمكنك إلغاؤه فقط.")
        serializer.save()


class RatingViewSet(viewsets.ModelViewSet):
    queryset = Rating.objects.all()
    serializer_class = RatingSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        client = self.request.user.client  # تحقق منه المُسلسِل (يرفع خطأ 400 إن لم يوجد)
        serializer.save(rated_by=client, driver=serializer.validated_data['trip'].driver)

    def _check_owner(self, rating):
        user = self.request.user
        if not user.is_staff and rating.rated_by.user_id != user.id:
            raise PermissionDenied("لا يمكنك تعديل تقييم شخص آخر.")

    def perform_update(self, serializer):
        self._check_owner(serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        self._check_owner(instance)
        instance.delete()


class SupportTicketViewSet(viewsets.ModelViewSet):
    queryset = SupportTicket.objects.all()
    serializer_class = SupportTicketSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return SupportTicket.objects.all()
        return SupportTicket.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class NotificationViewSet(mixins.ListModelMixin,
                          mixins.RetrieveModelMixin,
                          mixins.UpdateModelMixin,
                          mixins.DestroyModelMixin,
                          viewsets.GenericViewSet):
    """إشعارات المستخدم: عرض، وسم كمقروء، حذف. الإنشاء من الخادم فقط."""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


# ============================
# الاشتراكات والمكافآت
# ============================
class SubscriptionPlanViewSet(viewsets.ModelViewSet):
    queryset = SubscriptionPlan.objects.all()
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [IsStaffOrReadOnly]


class SubscriptionViewSet(viewsets.ModelViewSet):
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    permission_classes = [IsStaffOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return self.queryset
        if hasattr(user, 'driver'):
            return self.queryset.filter(driver=user.driver)
        return self.queryset.none()


class BonusViewSet(viewsets.ModelViewSet):
    """المكافآت تضيف رصيداً للمحفظة تلقائياً، لذلك إنشاؤها للمشرفين فقط."""
    queryset = Bonus.objects.all()
    serializer_class = BonusSerializer
    permission_classes = [IsStaffOrReadOnly]

    def get_queryset(self):
        if self.request.user.is_staff:
            return self.queryset
        return self.queryset.filter(user=self.request.user)


class TripStopViewSet(viewsets.ModelViewSet):
    queryset = TripStop.objects.all()
    serializer_class = TripStopSerializer
    permission_classes = [IsDriverOrStaffOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return self.queryset
        if hasattr(user, 'driver'):
            return self.queryset.filter(trip__driver=user.driver)
        if hasattr(user, 'client'):
            return self.queryset.filter(
                Q(trip__bookings__customer=user.client) | Q(trip__deliveries__sender=user)
            ).distinct()
        return self.queryset.none()

    def _check_trip_owner(self, trip):
        user = self.request.user
        if not user.is_staff and trip.driver_id != getattr(getattr(user, 'driver', None), 'pk', None):
            raise PermissionDenied("لا يمكنك تعديل محطات رحلة سائق آخر.")

    def perform_create(self, serializer):
        self._check_trip_owner(serializer.validated_data['trip'])
        serializer.save()

    def perform_update(self, serializer):
        self._check_trip_owner(serializer.instance.trip)
        if 'trip' in serializer.validated_data:
            self._check_trip_owner(serializer.validated_data['trip'])
        serializer.save()


# ============================
# الطلبات المسبقة والشحنات
# ============================
class CasheBookingViewSet(viewsets.ModelViewSet):
    queryset = CasheBooking.objects.all()
    serializer_class = CasheBookingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return self.queryset
        if hasattr(user, 'client'):
            return self.queryset.filter(user=user.client)
        return self.queryset.none()

    def perform_create(self, serializer):
        client = getattr(self.request.user, 'client', None)
        if client is None:
            raise PermissionDenied("غير مصرح لك بإضافة حجز مسبق.")
        serializer.save(user=client)


class CasheItemDeliveryViewSet(viewsets.ModelViewSet):
    """
        واجهة للتعامل مع طلبات التوصيل المسبقة مع فلترة حسب المستخدم والحالة
        """
    queryset = CasheItemDelivery.objects.all()
    serializer_class = CasheItemDeliverySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        # فلترة حسب الحالة إذا وجدت
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)
        # المدير يرى الجميع
        if user.is_staff:
            return qs
        # إذا كان المستخدم عميلاً
        if hasattr(user, 'client'):
            return qs.filter(user=user.client)
        return qs.none()

    def perform_create(self, serializer):
        user = self.request.user
        if not hasattr(user, 'client'):
            raise PermissionDenied("غير مصرح لك بإضافة طلب توصيل مسبق.")
        serializer.save(user=user.client)


class ItemDeliveryViewSet(viewsets.ModelViewSet):
    """
    واجهة للتعامل مع الشحنات مع فلترة حسب رقم الرحلة أو حسب المستخدم (سائق / مرسل) والحالة
    """
    queryset = ItemDelivery.objects.all()
    serializer_class = ItemDeliverySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        # فلترة اختيارية حسب رقم الرحلة والحالة — تُطبَّق دائماً *قبل* فلترة الصلاحيات
        # (سابقاً: تمرير ?trip= كان يتجاوز فلترة المستخدم ويكشف شحنات الآخرين)
        trip_id = self.request.query_params.get('trip')
        if trip_id:
            qs = qs.filter(trip_id=trip_id)
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)

        # المدير يرى الجميع
        if user.is_staff:
            return qs
        # إذا كان المستخدم سائقاً: يعرض الشحنات المرتبطة بالرحلات التي يقودها
        if hasattr(user, 'driver'):
            return qs.filter(trip__driver=user.driver)
        # إذا كان المستخدم مرسلاً: يعرض الشحنات التي أرسلها
        if hasattr(user, 'client'):
            return qs.filter(sender=user)
        return qs.none()

    def perform_create(self, serializer):
        if not hasattr(self.request.user, 'client'):
            raise PermissionDenied("الإرسال متاح للعملاء فقط.")
        serializer.save(sender=self.request.user, status=ItemDelivery.Status.PENDING)

    def perform_update(self, serializer):
        user = self.request.user
        if not user.is_staff and not hasattr(user, 'driver'):
            # المرسل يستطيع فقط إلغاء شحنته وهي ما تزال قيد الانتظار
            new_status = serializer.validated_data.get('status')
            if (set(serializer.validated_data) - {'status'}
                    or new_status not in (None, ItemDelivery.Status.CANCELLED)
                    or serializer.instance.status != ItemDelivery.Status.PENDING):
                raise PermissionDenied("يمكنك إلغاء الشحنة فقط وهي قيد الانتظار.")
        serializer.save()


# ============================
# FCM
# ============================
class SaveFCMTokenView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        token = request.data.get('fcm_token')
        device_info = request.data.get('device_info', {})

        if not token or not isinstance(token, str):
            return Response(
                {'error': _('FCM token is required.')},
                status=status.HTTP_400_BAD_REQUEST
            )
        if len(token) > 255:
            return Response(
                {'error': _('FCM token is too long.')},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not isinstance(device_info, dict):
            device_info = {}

        # استخدم update_or_create لتحديث السجل إذا وُجد أو إنشائه إذا لم يوجد
        obj, created = FCMToken.objects.update_or_create(
            token=token,
            defaults={
                'user': request.user,
                'device_info': device_info,
            }
        )

        if created:
            message = _('FCM token saved successfully.')
            response_status = status.HTTP_201_CREATED
        else:
            message = _('FCM token updated successfully.')
            response_status = status.HTTP_200_OK

        return Response(
            {'message': message, 'created': created},
            status=response_status
        )


# ============================
# المحادثات
# ============================
class ChatListAPIView(generics.ListAPIView):
    serializer_class = ChatSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Chat.objects.filter(participants=self.request.user)
            .prefetch_related('participants')
            .select_related('last_message__sender')
            .order_by('-updated_at')
        )


class ChatCreateOrGetAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user_id = request.data.get("user_id")
        if not user_id:
            return Response({'detail': 'معرّف المستخدم مطلوب'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            other_user = User.objects.get(id=user_id)
        except (User.DoesNotExist, ValueError, TypeError):
            return Response({'detail': 'المستخدم غير موجود'}, status=status.HTTP_404_NOT_FOUND)

        if other_user.pk == request.user.pk:
            return Response({'detail': 'لا يمكنك بدء محادثة مع نفسك'}, status=status.HTTP_400_BAD_REQUEST)

        chat = (
            Chat.objects.filter(participants=request.user)
            .filter(participants=other_user)
            .first()
        )
        if not chat:
            chat = Chat.objects.create()
            chat.participants.set([request.user, other_user])

        serializer = ChatSerializer(chat, context={'request': request})
        return Response(serializer.data)


class MessageListAPIView(generics.ListAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        chat_id = self.kwargs['chat_id']
        chat = Chat.objects.filter(id=chat_id, participants=self.request.user).first()
        if not chat:
            return Message.objects.none()

        # وضع الرسائل كـ مقروءة
        chat.messages.filter(is_read=False).exclude(sender=self.request.user).update(is_read=True)
        return chat.messages.select_related('sender').order_by('created_at')


class MessageCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, chat_id):
        chat = Chat.objects.filter(id=chat_id, participants=request.user).first()
        if not chat:
            return Response({'detail': 'غير مصرح'}, status=status.HTTP_403_FORBIDDEN)

        # يمرّ عبر المُسلسِل ليُطبَّق فحص الامتداد والحجم (Message.objects.create كان يتجاوزهما)
        serializer = MessageSerializer(
            data={
                'content': request.data.get('content'),
                'attachment': request.FILES.get('attachment'),
            },
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        message = serializer.save(chat=chat, sender=request.user)

        return Response(
            MessageSerializer(message, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )
