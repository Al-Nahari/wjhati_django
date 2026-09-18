import os
from decimal import Decimal

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

import django

django.setup()

from django.test import TestCase
from django.contrib.auth import get_user_model

from apis.models import Client, Driver, Vehicle, Trip, Booking, Rating, SupportTicket, SubscriptionPlan, Subscription

User = get_user_model()


class ApiModelsTestCase(TestCase):
    def setUp(self):
        self.customer_user = User.objects.create_user(
            username="customer1",
            password="StrongPass123",
        )
        self.driver_user = User.objects.create_user(
            username="driver1",
            password="StrongPass123",
        )

        self.client = Client.objects.create(
            user=self.customer_user,
            phone_number="+966500000001",
            city="Riyadh",
        )

        self.vehicle = Vehicle.objects.create(
            model="Toyota Corolla",
            plate_number="ABC-1234",
            color="White",
            capacity=4,
            vehicle_type="sedan",
            manufacture_year=2023,
        )

        self.driver = Driver.objects.create(
            user=self.driver_user,
            phone_number="+966500000002",
            where_location="Riyadh Center",
            license_number="LIC-1001",
            rating=0.0,
            total_trips=0,
            is_available=True,
        )
        self.driver.vehicles.add(self.vehicle)

        self.trip = Trip.objects.create(
            from_location="Riyadh",
            to_location="Jeddah",
            departure_time="2026-09-18T10:00:00Z",
            distance_km=Decimal("300.50"),
            available_seats=4,
            price_per_seat=Decimal("50.00"),
            status=Trip.Status.PENDING,
            driver=self.driver,
            vehicle=self.vehicle,
        )

    def test_client_creation(self):
        self.assertEqual(self.client.user.username, "customer1")
        self.assertEqual(self.client.city, "Riyadh")
        self.assertTrue(self.client.status)

    def test_driver_and_vehicle_relationship(self):
        self.assertIn(self.vehicle, self.driver.vehicles.all())
        self.assertEqual(self.driver.vehicles.count(), 1)
        self.assertEqual(str(self.driver), f"{self.driver.user.username} - {self.driver.license_number}")

    def test_trip_update_availability_updates_status(self):
        Booking.objects.create(
            trip=self.trip,
            customer=self.client,
            seats=[1, 2],
            total_price=Decimal("100.00"),
            status=Booking.Status.CONFIRMED,
        )

        self.trip.update_availability()

        self.trip.refresh_from_db()
        self.assertEqual(self.trip.available_seats, 2)
        self.assertEqual(self.trip.status, Trip.Status.PENDING)

    def test_driver_rating_updates_from_ratings(self):
        trip_one = Trip.objects.create(
            from_location="Dammam",
            to_location="Khobar",
            departure_time="2026-09-20T08:00:00Z",
            distance_km=Decimal("50.00"),
            available_seats=2,
            price_per_seat=Decimal("30.00"),
            status=Trip.Status.COMPLETED,
            driver=self.driver,
            vehicle=self.vehicle,
        )
        trip_two = Trip.objects.create(
            from_location="Jubail",
            to_location="Riyadh",
            departure_time="2026-09-21T10:00:00Z",
            distance_km=Decimal("180.00"),
            available_seats=3,
            price_per_seat=Decimal("40.00"),
            status=Trip.Status.COMPLETED,
            driver=self.driver,
            vehicle=self.vehicle,
        )

        customer_two = User.objects.create_user(username="customer2", password="StrongPass123")
        customer_two_client = Client.objects.create(
            user=customer_two,
            phone_number="+966500000003",
            city="Jeddah",
        )

        Rating.objects.create(
            trip=trip_one,
            rated_by=self.client,
            driver=self.driver,
            rating=5,
            comment="Excellent",
        )
        Rating.objects.create(
            trip=trip_two,
            rated_by=customer_two_client,
            driver=self.driver,
            rating=3,
            comment="Good enough",
        )

        self.driver.update_rating()
        self.driver.refresh_from_db()

        self.assertEqual(self.driver.rating, 4.0)

    def test_support_ticket_and_subscription_creation(self):
        ticket = SupportTicket.objects.create(
            user=self.customer_user,
            subject="Problem in booking",
            message="I need help with my trip",
            status="open",
            priority="high",
        )

        plan = SubscriptionPlan.objects.create(
            name="Gold",
            description="Premium plan",
            price=Decimal("199.99"),
            duration_days=30,
            max_trips=20,
            is_active=True,
        )

        subscription = Subscription.objects.create(
            driver=self.driver,
            plan=plan,
            start_date="2026-09-01",
            end_date="2026-09-30",
            is_active=True,
            remaining_trips=15,
        )

        self.assertEqual(ticket.subject, "Problem in booking")
        self.assertEqual(subscription.plan.name, "Gold")
        self.assertEqual(plan.max_trips, 20)
