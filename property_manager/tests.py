"""Tests for the guest-facing API."""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Booking, Property


class ValidateAccessCodeTests(TestCase):
    """Regression tests for /api/v1/auth/access-code/."""

    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user(
            username='owner', password='x',
        )
        self.property = Property.objects.create(
            name='Test Villa',
            address='Via Roma 1',
            owner=self.owner,
        )
        self.booking = Booking.objects.create(
            property=self.property,
            guest_name='Test Guest',
            check_in_date=date.today(),
            check_out_date=date.today() + timedelta(days=2),
        )

    def test_valid_uuid_code_returns_200(self):
        resp = self.client.post(
            '/api/v1/auth/access-code/',
            data={'access_code': str(self.booking.access_code)},
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['booking']['guest_name'], 'Test Guest')

    def test_unknown_uuid_returns_404(self):
        resp = self.client.post(
            '/api/v1/auth/access-code/',
            data={'access_code': '00000000-0000-0000-0000-000000000000'},
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 404)

    def test_non_uuid_string_returns_404_not_500(self):
        # Was returning 500 because the UUIDField raised ValidationError on
        # coercion and the view only caught DoesNotExist.
        resp = self.client.post(
            '/api/v1/auth/access-code/',
            data={'access_code': 'DEMO2025'},
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 404)

    def test_missing_code_returns_400(self):
        resp = self.client.post(
            '/api/v1/auth/access-code/',
            data={},
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)
