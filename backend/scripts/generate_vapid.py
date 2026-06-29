"""
Generate VAPID keys for Web Push notifications.
Run once and save the output to your .env file and Railway environment variables.

Usage:
    pip install pywebpush
    python scripts/generate_vapid.py
"""
from pywebpush import Vapid

v = Vapid()
v.generate_keys()

private_key = v.private_pem().decode("utf-8").strip()
public_key = v.public_key.public_bytes(
    encoding=__import__("cryptography.hazmat.primitives.serialization", fromlist=["Encoding"]).Encoding.X962,
    format=__import__("cryptography.hazmat.primitives.serialization", fromlist=["PublicFormat"]).PublicFormat.UncompressedPoint
)

import base64
public_key_b64 = base64.urlsafe_b64encode(public_key).rstrip(b"=").decode("utf-8")

print("\n── VAPID Keys Generated ──────────────────────────────────")
print(f"\nVAPID_PRIVATE_KEY={private_key}")
print(f"\nVAPID_PUBLIC_KEY={public_key_b64}")
print("\nAdd both values to your .env file and Railway environment variables.")
print("The PUBLIC key also goes into the frontend (src/lib/push.js).\n")
