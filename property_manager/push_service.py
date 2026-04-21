"""
Firebase Cloud Messaging (FCM) integration.

Responsible for initialising the Firebase Admin SDK once per process and
delivering PushNotification instances to every active DeviceToken registered
for the target booking(s). Tokens that FCM reports as invalid are marked
inactive so the next send skips them.

Configuration:
    FIREBASE_CREDENTIALS_PATH — absolute path to the service-account JSON.
    FIREBASE_CREDENTIALS_JSON — inline JSON string (overrides the path).

If neither setting is provided, send_push_notification is a no-op — the
backend still records that the notification was "sent" so the guest app's
polling fallback continues to work.
"""

from __future__ import annotations

import json
import logging
import threading
from typing import Iterable

from django.conf import settings
from django.db.models import Q

log = logging.getLogger(__name__)

_init_lock = threading.Lock()
_initialised = False
_enabled = False


def _initialise() -> bool:
    """Initialise the Firebase Admin SDK on first use. Returns True if FCM is
    usable in this process."""
    global _initialised, _enabled
    if _initialised:
        return _enabled
    with _init_lock:
        if _initialised:
            return _enabled
        _initialised = True
        try:
            import firebase_admin
            from firebase_admin import credentials
        except ImportError:
            log.warning("firebase-admin not installed; FCM disabled.")
            return False

        if firebase_admin._apps:
            _enabled = True
            return True

        cred = None
        inline = getattr(settings, "FIREBASE_CREDENTIALS_JSON", "") or ""
        path = getattr(settings, "FIREBASE_CREDENTIALS_PATH", "") or ""
        try:
            if inline.strip():
                cred = credentials.Certificate(json.loads(inline))
            elif path.strip():
                cred = credentials.Certificate(path)
        except Exception as e:
            log.error("Failed to load Firebase credentials: %s", e)
            return False

        if cred is None:
            log.info(
                "No Firebase credentials configured; FCM disabled. "
                "Set FIREBASE_CREDENTIALS_PATH or FIREBASE_CREDENTIALS_JSON.",
            )
            return False

        try:
            firebase_admin.initialize_app(cred)
            _enabled = True
            return True
        except Exception as e:
            log.error("Failed to initialise Firebase Admin SDK: %s", e)
            return False


def _target_tokens(notification) -> list:
    """Resolve the DeviceToken queryset for a PushNotification instance."""
    from .models import Booking, DeviceToken

    if notification.target_type == "specific_booking" and notification.target_booking_id:
        qs = DeviceToken.objects.filter(
            booking_id=notification.target_booking_id,
            is_active=True,
        )
    else:
        # All *current* guests of the property.
        from django.utils import timezone
        today = timezone.now().date()
        bookings = Booking.objects.filter(
            property_id=notification.property_id,
            is_active=True,
            check_in_date__lte=today,
            check_out_date__gte=today,
        ).values_list("id", flat=True)
        qs = DeviceToken.objects.filter(
            booking_id__in=list(bookings),
            is_active=True,
        )
    return list(qs)


def send_push_notification(notification) -> dict:
    """Deliver a PushNotification through FCM.

    Returns a dict with `sent`, `failed`, and `disabled_tokens` counters.
    Safe to call even when FCM is not configured — it becomes a no-op.
    """
    result = {"sent": 0, "failed": 0, "disabled_tokens": 0, "skipped": False}

    if not _initialise():
        result["skipped"] = True
        return result

    tokens = _target_tokens(notification)
    if not tokens:
        return result

    try:
        from firebase_admin import messaging
    except ImportError:
        result["skipped"] = True
        return result

    data_payload = {
        "notification_id": str(notification.id),
        "booking_id": str(notification.target_booking_id or ""),
        "property_id": str(notification.property_id),
        "linked_item_id": str(notification.linked_item_id or ""),
    }

    invalid_tokens: list[str] = []
    for dt in tokens:
        msg = messaging.Message(
            notification=messaging.Notification(
                title=notification.title,
                body=notification.body,
            ),
            data=data_payload,
            token=dt.token,
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    channel_id="ev_concierge_push",
                    sound="default",
                ),
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(sound="default", badge=1),
                ),
            ),
        )
        try:
            messaging.send(msg)
            result["sent"] += 1
        except messaging.UnregisteredError:
            invalid_tokens.append(dt.token)
            result["failed"] += 1
        except Exception as e:
            log.warning("FCM send failed for token %s: %s", dt.token[:12], e)
            result["failed"] += 1

    if invalid_tokens:
        from .models import DeviceToken
        DeviceToken.objects.filter(token__in=invalid_tokens).update(is_active=False)
        result["disabled_tokens"] = len(invalid_tokens)

    return result


def prune_tokens_for_booking(booking_id: int, keep: Iterable[str] = ()) -> None:
    """Deactivate all tokens for a booking except the ones in `keep`."""
    from .models import DeviceToken
    DeviceToken.objects.filter(
        booking_id=booking_id,
    ).filter(~Q(token__in=list(keep))).update(is_active=False)
