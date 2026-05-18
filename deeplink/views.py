"""Deferred deep-link bridge.

Single landing endpoint that hands a booking access code off to the native
app. If the app is installed it opens directly; otherwise the user is sent
to the appropriate store, with the code threaded through Play Install
Referrer (Android) or Universal Link / smart-app-banner (iOS) so the app can
auto-login on first launch.
"""

from __future__ import annotations

import json
import re
from urllib.parse import quote, urlencode

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

# Booking codes in this project are short alphanumerics (e.g. DEMO2025) — keep
# the validator deliberately wide so we don't need to touch this when the
# format evolves, but tight enough to refuse anything that looks like an
# injection attempt before it reaches the template.
_CODE_RE = re.compile(r'^[A-Za-z0-9_-]{4,64}$')


def _detect_platform(user_agent: str) -> str:
    ua = (user_agent or '').lower()
    if 'android' in ua:
        return 'android'
    if 'iphone' in ua or 'ipad' in ua or 'ipod' in ua:
        return 'ios'
    # iPadOS 13+ identifies as Macintosh; treat real Mac as desktop unless the
    # touch hint is present.
    if 'macintosh' in ua and 'mobile' in ua:
        return 'ios'
    return 'desktop'


def _deeplink_config() -> dict:
    return {
        'domain': getattr(settings, 'DEEPLINK_DOMAIN', ''),
        'scheme': getattr(settings, 'DEEPLINK_SCHEME', 'evconcierge'),
        'scheme_host': getattr(settings, 'DEEPLINK_SCHEME_HOST', 'login'),
        'ios_app_id': getattr(settings, 'DEEPLINK_IOS_APP_ID', ''),
        'ios_team_id': getattr(settings, 'DEEPLINK_IOS_TEAM_ID', ''),
        'ios_bundle_id': getattr(settings, 'DEEPLINK_IOS_BUNDLE_ID', 'com.evconcierge.evConcierge'),
        'android_package': getattr(settings, 'DEEPLINK_ANDROID_PACKAGE', 'com.evconcierge.ev_concierge'),
        'android_cert_sha256': getattr(settings, 'DEEPLINK_ANDROID_CERT_SHA256', []),
    }


@require_GET
def landing(request: HttpRequest, code: str) -> HttpResponse:
    """Render the bridge page for a booking code.

    The same URL is registered as the iOS Universal Link and Android App Link
    target, so the OS will intercept it and open the installed app before the
    template is rendered. Reaching the HTML means the app is *not* installed,
    in which case we redirect to the appropriate store (Android carrying the
    code via Play Install Referrer, iOS via the smart-app-banner argument).
    """
    if not _CODE_RE.match(code):
        return HttpResponse('Invalid code.', status=400)

    cfg = _deeplink_config()
    platform = _detect_platform(request.META.get('HTTP_USER_AGENT', ''))

    scheme_url = f"{cfg['scheme']}://{cfg['scheme_host']}?code={quote(code)}"

    play_referrer = urlencode({'code': code})
    play_store_url = (
        f"https://play.google.com/store/apps/details?"
        f"id={cfg['android_package']}&referrer={quote(play_referrer)}"
    )
    # intent:// fallback — if the app isn't there, Chrome on Android follows
    # browser_fallback_url which is our Play Store URL with the referrer.
    intent_url = (
        f"intent://{cfg['scheme_host']}?code={quote(code)}"
        f"#Intent;scheme={cfg['scheme']};package={cfg['android_package']};"
        f"S.browser_fallback_url={quote(play_store_url)};end"
    )

    app_store_url = (
        f"https://apps.apple.com/app/id{cfg['ios_app_id']}"
        if cfg['ios_app_id'] else 'https://apps.apple.com/'
    )

    universal_link = (
        f"https://{cfg['domain']}/l/{code}/" if cfg['domain'] else request.build_absolute_uri()
    )

    context = {
        'code': code,
        'platform': platform,
        'scheme_url': scheme_url,
        'intent_url': intent_url,
        'play_store_url': play_store_url,
        'app_store_url': app_store_url,
        'ios_app_id': cfg['ios_app_id'],
        'universal_link': universal_link,
    }
    return render(request, 'deeplink/landing.html', context)


@require_GET
def apple_app_site_association(request: HttpRequest) -> HttpResponse:
    """Serve the AASA file for iOS Universal Links.

    Must be served at /.well-known/apple-app-site-association over HTTPS,
    with content-type application/json and no redirects.
    """
    cfg = _deeplink_config()
    team_id = cfg['ios_team_id']
    bundle = cfg['ios_bundle_id']
    payload = {
        "applinks": {
            "apps": [],
            "details": [
                {
                    "appID": f"{team_id}.{bundle}" if team_id else bundle,
                    "paths": ["/l/*"],
                }
            ],
        }
    }
    return HttpResponse(
        json.dumps(payload),
        content_type='application/json',
    )


@require_GET
def android_assetlinks(request: HttpRequest) -> HttpResponse:
    """Serve assetlinks.json for Android App Links verification."""
    cfg = _deeplink_config()
    fingerprints = cfg['android_cert_sha256']
    if isinstance(fingerprints, str):
        fingerprints = [fingerprints] if fingerprints else []
    payload = [
        {
            "relation": ["delegate_permission/common.handle_all_urls"],
            "target": {
                "namespace": "android_app",
                "package_name": cfg['android_package'],
                "sha256_cert_fingerprints": fingerprints,
            },
        }
    ]
    return JsonResponse(payload, safe=False)
