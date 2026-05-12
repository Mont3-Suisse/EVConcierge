"""Tests for the deferred deep-link bridge."""

from __future__ import annotations

import json

from django.test import Client, TestCase, override_settings
from django.urls import reverse


IOS_UA = (
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) '
    'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
)
ANDROID_UA = (
    'Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
)
DESKTOP_UA = (
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
)


@override_settings(
    DEEPLINK_DOMAIN='evconcierge.example.com',
    DEEPLINK_IOS_APP_ID='1234567890',
    DEEPLINK_IOS_TEAM_ID='ABCDE12345',
    DEEPLINK_IOS_BUNDLE_ID='com.evconcierge.evConcierge',
    DEEPLINK_ANDROID_PACKAGE='com.evconcierge.ev_concierge',
    DEEPLINK_ANDROID_CERT_SHA256=['AA:BB:CC:DD'],
)
class LandingViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_rejects_invalid_code(self):
        # Path-converter `<str:code>` blocks slashes, but the regex must
        # still reject anything containing punctuation that could break out
        # of the template attributes.
        resp = self.client.get('/l/bad code!/', HTTP_USER_AGENT=ANDROID_UA)
        self.assertEqual(resp.status_code, 400)

    def test_android_branch_includes_intent_and_referrer(self):
        resp = self.client.get('/l/DEMO2025/', HTTP_USER_AGENT=ANDROID_UA)
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode()
        self.assertIn('intent://login?code=DEMO2025', body)
        self.assertIn('package=com.evconcierge.ev_concierge', body)
        self.assertIn('play.google.com/store/apps/details', body)
        # The Play Store URL carries the booking code through the install
        # referrer; it appears once at the top level (URL-encoded) and again
        # nested inside the intent's browser_fallback_url (double-encoded).
        self.assertIn('referrer=code%3DDEMO2025', body)
        self.assertIn('referrer%3Dcode%253DDEMO2025', body)
        self.assertIn('Get it on Google Play', body)

    def test_ios_branch_includes_smart_banner_and_scheme(self):
        resp = self.client.get('/l/DEMO2025/', HTTP_USER_AGENT=IOS_UA)
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode()
        self.assertIn('apple-itunes-app', body)
        self.assertIn('app-id=1234567890', body)
        self.assertIn('app-argument=https://evconcierge.example.com/l/DEMO2025/', body)
        self.assertIn('evconcierge://login?code=DEMO2025', body)
        self.assertIn('apps.apple.com/app/id1234567890', body)

    def test_desktop_shows_qr(self):
        resp = self.client.get('/l/DEMO2025/', HTTP_USER_AGENT=DESKTOP_UA)
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode()
        self.assertIn('qrserver.com', body)
        self.assertNotIn('intent://', body)


@override_settings(
    DEEPLINK_IOS_TEAM_ID='ABCDE12345',
    DEEPLINK_IOS_BUNDLE_ID='com.evconcierge.evConcierge',
    DEEPLINK_ANDROID_PACKAGE='com.evconcierge.ev_concierge',
    DEEPLINK_ANDROID_CERT_SHA256=['AA:BB:CC:DD', 'EE:FF:00:11'],
)
class WellKnownTests(TestCase):
    def test_apple_app_site_association(self):
        resp = self.client.get('/.well-known/apple-app-site-association')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/json')
        payload = json.loads(resp.content)
        self.assertEqual(
            payload['applinks']['details'][0]['appID'],
            'ABCDE12345.com.evconcierge.evConcierge',
        )
        self.assertEqual(payload['applinks']['details'][0]['paths'], ['/l/*'])

    def test_assetlinks(self):
        resp = self.client.get('/.well-known/assetlinks.json')
        self.assertEqual(resp.status_code, 200)
        payload = json.loads(resp.content)
        self.assertEqual(payload[0]['target']['package_name'],
                         'com.evconcierge.ev_concierge')
        self.assertEqual(payload[0]['target']['sha256_cert_fingerprints'],
                         ['AA:BB:CC:DD', 'EE:FF:00:11'])

    def test_landing_url_reverse(self):
        # Sanity: the namespaced URL resolves.
        url = reverse('deeplink:landing', kwargs={'code': 'DEMO2025'})
        self.assertEqual(url, '/l/DEMO2025/')
