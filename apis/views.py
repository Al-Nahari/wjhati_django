import Notification
from Notification.models import FCMToken
from Transaction.models import Transaction, Transfer, Wallet
from .models import Client , Chat, Message, Vehicle, Driver, Trip, Booking, Rating, SupportTicket, SubscriptionPlan, Subscription, Bonus, TripStop, ItemDelivery, CasheBooking, CasheItemDelivery
from .serializers import ChatSerializer, MessageSerializer, UserSerializer, ClientSerializer, WalletSerializer, TransactionSerializer, VehicleSerializer, DriverSerializer, TripSerializer, BookingSerializer, RatingSerializer, SupportTicketSerializer, NotificationSerializer, TransferSerializer, SubscriptionPlanSerializer, SubscriptionSerializer, BonusSerializer, TripStopSerializer, ItemDeliverySerializer, CasheBookingSerializer, CasheItemDeliverySerializer
from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.db.models import Q, Count, Prefetch
from django.contrib.auth import get_user_model
import logging
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import PermissionDenied

User = get_user_model()

logger = logging.getLogger(__name__)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

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
        if hasattr(user, 'client'):
            return Client.objects.filter(user=user)
        return Client.objects.none()

class WalletViewSet(viewsets.ModelViewSet):
    serializer_class = WalletSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Wallet.objects.filter(user=user)

    def retrieve(self, request, *args, **kwargs):
        wallet = self.get_queryset().first()
        if wallet:
            serializer = self.get_serializer(wallet)
            return Response(serializer.data)
        else:
            return Response({"detail": "المحفظة غير موجودة."}, status=status.HTTP_404_NOT_FOUND)
        
class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer

class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer

class DriverViewSet(viewsets.ModelViewSet):
    serializer_class = DriverSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # يعرض فقط بيانات السائق المرتبطة بالمستخدم الحالي
        if hasattr(user, 'driver'):
            return Driver.objects.filter(user=user)
        return Driver.objects.none()

    def perform_create(self, serializer):
        # يجبر ربط السائق بالمستخدم الحالي
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        # يمنع تغيير المستخدم عند التحديث
        serializer.save(user=self.request.user)

class TripViewSet(viewsets.ModelViewSet):
    serializer_class = TripSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Trip.objects.all()
        # إذا كان المستخدم سائقاً، اعرض له فقط الرحلات التي هو السائق لها
        if hasattr(user, 'driver'):
            queryset = queryset.filter(driver=user.driver)
        # إذا كان المستخدم عميلاً، اعرض له الرحلات التي لديه فيها Booking أو ItemDelivery فقط
        elif hasattr(user, 'client'):
            queryset = queryset.filter(
                Q(bookings__customer=user.client) | Q(deliveries__sender=user)
            ).distinct()
        return queryset

class BookingViewSet(viewsets.ModelViewSet):
    """
    واجهة للتعامل مع الحجوزات مع فلترة حسب المستخدم والحالة
    """
    queryset = Booking.objects.all()  # 👈 هذا السطر ضروري
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        فلترة الحجوزات حسب:
        - إذا كان المستخدم عميلاً: يعرض حجوزاته فقط
        - إذا كان المستخدم سائقاً: يعرض حجوزات رحلاته فقط
        - إذا كان مديراً: يعرض جميع الحجوزات
        مع إمكانية تصفية حسب الحالة أو الرحلة
        """
        user = self.request.user
        queryset = super().get_queryset()

        # فلترة حسب رقم الرحلة (trip)
        trip_id = self.request.query_params.get('trip')
        if trip_id:
            queryset = queryset.filter(trip_id=trip_id)

        # فلترة حسب الحالة إن وجدت
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)

        if hasattr(user, 'client'):
            return queryset.filter(customer=user.client)

        elif hasattr(user, 'driver'):
            return queryset.filter(trip__driver=user.driver)

        return queryset


class RatingViewSet(viewsets.ModelViewSet):
    queryset = Rating.objects.all()
    serializer_class = RatingSerializer


class SupportTicketViewSet(viewsets.ModelViewSet):
    queryset = SupportTicket.objects.all()
    serializer_class = SupportTicketSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # يمكن تخصيص الاستعلام ليعرض التذاكر الخاصة بالمستخدم فقط إذا رغبت
        return SupportTicket.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Notification.objects.filter(user=user)

class TransferViewSet(viewsets.ModelViewSet):
    queryset = Transfer.objects.all()
    serializer_class = TransferSerializer

class SubscriptionPlanViewSet(viewsets.ModelViewSet):
    queryset = SubscriptionPlan.objects.all()
    serializer_class = SubscriptionPlanSerializer

class SubscriptionViewSet(viewsets.ModelViewSet):
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer

class BonusViewSet(viewsets.ModelViewSet):
    queryset = Bonus.objects.all()
    serializer_class = BonusSerializer

class TripStopViewSet(viewsets.ModelViewSet):
    queryset = TripStop.objects.all()
    serializer_class = TripStopSerializer


class CasheBookingViewSet(viewsets.ModelViewSet):
    queryset = CasheBooking.objects.all()
    serializer_class = CasheBookingSerializer

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
        status = self.request.query_params.get('status')
        if status:
            qs = qs.filter(status=status)
        # إذا كان المستخدم عميلاً
        if hasattr(user, 'client'):
            return qs.filter(user=user.client)
        # المدير يرى الجميع
        return qs

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

        # إذا تم إرسال رقم الرحلة، نرجع الشحنات المرتبطة بها فقط
        trip_id = self.request.query_params.get('trip')
        if trip_id:
            return qs.filter(trip_id=trip_id)

        # فلترة حسب الحالة إذا لم يُرسل رقم الرحلة
        status = self.request.query_params.get('status')
        if status:
            qs = qs.filter(status=status)

        # إذا كان المستخدم سائقاً: يعرض الشحنات المرتبطة بالرحلات التي يقودها
        if hasattr(user, 'driver'):
            qs = qs.filter(trip__driver=user.driver)

        # إذا كان المستخدم مرسلاً: يعرض الشحنات التي أرسلها
        elif hasattr(user, 'client'):
            qs = qs.filter(sender=user)

        # المدير يرى الجميع
        return qs

class SaveFCMTokenView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        token = request.data.get('fcm_token')
        device_info = request.data.get('device_info', {})

        if not token:
            return Response(
                {'error': _('FCM token is required.')},
                status=status.HTTP_400_BAD_REQUEST
            )

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


class ChatListAPIView(generics.ListAPIView):
    serializer_class = ChatSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Chat.objects.filter(participants=self.request.user).order_by('-updated_at')


class ChatCreateOrGetAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user_id = request.data.get("user_id")
        if not user_id:
            return Response({'detail': 'معرّف المستخدم مطلوب'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            other_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'detail': 'المستخدم غير موجود'}, status=status.HTTP_404_NOT_FOUND)

        chat = Chat.objects.filter(participants=request.user).filter(participants=other_user).first()
        if not chat:
            chat = Chat.objects.create()
            chat.participants.set([request.user, other_user])

        serializer = ChatSerializer(chat)
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
        return chat.messages.order_by('created_at')


class MessageCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, chat_id):
        chat = Chat.objects.filter(id=chat_id, participants=request.user).first()
        if not chat:
            return Response({'detail': 'غير مصرح'}, status=status.HTTP_403_FORBIDDEN)

        content = request.data.get('content', '').strip()
        attachment = request.FILES.get('attachment')

        if not content and not attachment:
            return Response({'detail': 'أدخل محتوى أو مرفق'}, status=status.HTTP_400_BAD_REQUEST)

        message = Message.objects.create(
            chat=chat,
            sender=request.user,
            content=content if content else None,
            attachment=attachment if attachment else None
        )

        serializer = MessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
