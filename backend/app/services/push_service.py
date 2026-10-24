"""Web Push (browser notifications) for study reminders.

Implements the Web Push send itself with two small libraries by the web-push
authors: http-ece (RFC 8291 aes128gcm payload encryption) and py-vapid
(RFC 8292 signing), and posts with `requests`. This avoids pywebpush, which
pulls in aiohttp and its async stack for what is a single HTTP POST.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import time
from urllib.parse import urlparse

import http_ece
import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from py_vapid import Vapid02
from sqlalchemy.orm import Session

from app.config import settings
from app.models.engagement import PushSubscription

_log = logging.getLogger("delta.push")


def _b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def push_configured() -> bool:
    return bool(settings.VAPID_PUBLIC_KEY and settings.VAPID_PRIVATE_KEY and settings.VAPID_SUBJECT)


def _vapid() -> Vapid02:
    return Vapid02.from_raw(settings.VAPID_PRIVATE_KEY.encode())


def encrypt_payload(payload: bytes, p256dh: str, auth: str) -> bytes:
    server_key = ec.generate_private_key(ec.SECP256R1())
    return http_ece.encrypt(
        payload,
        salt=os.urandom(16),
        private_key=server_key,
        dh=_b64url_decode(p256dh),
        auth_secret=_b64url_decode(auth),
        version="aes128gcm",
    )


def send_to_subscription(db: Session, sub: PushSubscription, title: str, body: str, url: str) -> bool:
    """Send one notification. Expired subscriptions (404/410) are deleted."""
    payload = json.dumps({"title": title, "body": body, "url": url}).encode("utf-8")
    parsed = urlparse(sub.endpoint)
    claims = {
        "sub": settings.VAPID_SUBJECT,
        "aud": f"{parsed.scheme}://{parsed.netloc}",
        "exp": int(time.time()) + 12 * 3600,
    }
    headers = _vapid().sign(claims)
    headers.update({"TTL": str(12 * 3600), "Content-Encoding": "aes128gcm", "Urgency": "normal"})
    try:
        res = requests.post(sub.endpoint, data=encrypt_payload(payload, sub.p256dh, sub.auth),
                            headers=headers, timeout=10)
    except requests.RequestException as exc:
        _log.warning("push send failed: %s", type(exc).__name__)
        return False
    if res.status_code in (404, 410):
        db.delete(sub)
        db.commit()
        return False
    if res.status_code >= 300:
        _log.warning("push service returned %s", res.status_code)
        return False
    return True


def send_to_user(db: Session, user_id: str, title: str, body: str, url: str) -> int:
    if not push_configured():
        return 0
    sent = 0
    for sub in db.query(PushSubscription).filter(PushSubscription.user_id == user_id).all():
        sent += 1 if send_to_subscription(db, sub, title, body, url) else 0
    return sent


def generate_vapid_keys() -> dict:
    """Helper for ops (docs/OPERATIONS.md): new raw base64url key pair."""
    key = ec.generate_private_key(ec.SECP256R1())
    private_raw = key.private_numbers().private_value.to_bytes(32, "big")
    public_raw = key.public_key().public_bytes(serialization.Encoding.X962,
                                               serialization.PublicFormat.UncompressedPoint)
    enc = lambda b: base64.urlsafe_b64encode(b).decode().rstrip("=")  # noqa: E731
    return {"VAPID_PRIVATE_KEY": enc(private_raw), "VAPID_PUBLIC_KEY": enc(public_raw)}


if __name__ == "__main__":
    for k, v in generate_vapid_keys().items():
        print(f"{k}={v}")
