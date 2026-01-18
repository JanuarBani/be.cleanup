# generate_vapid_keys.py
from pywebpush import WebPushException, webpush
import json

# Generate VAPID keys
from pywebpush import WebPusher

# Cara 1: Generate menggunakan fungsi internal
import vapid

# Generate keys baru
vapid_keys = vapid.generate_vapid_keys()

print("=" * 50)
print("VAPID KEYS GENERATED")
print("=" * 50)
print("\n📋 WEBPUSH_SETTINGS untuk Django settings.py:")
print("=" * 50)

settings_dict = {
    "VAPID_PUBLIC_KEY": vapid_keys.public_key,
    "VAPID_PRIVATE_KEY": vapid_keys.private_key,
    "VAPID_ADMIN_EMAIL": "admin@cleanupkupang.id"  # Ganti dengan email Anda
}

print(json.dumps(settings_dict, indent=4))

print("\n📋 Atau format langsung untuk Django settings.py:")
print("=" * 50)

print(f"""
WEBPUSH_SETTINGS = {{
    "VAPID_PUBLIC_KEY": "{vapid_keys.public_key}",
    "VAPID_PRIVATE_KEY": "{vapid_keys.private_key}",
    "VAPID_ADMIN_EMAIL": "admin@cleanupkupang.id"
}}
""")

# Verifikasi keys
print("\n🔍 VERIFIKASI KEYS:")
print("=" * 50)
print(f"Public Key Length: {len(vapid_keys.public_key)} karakter")
print(f"Private Key Length: {len(vapid_keys.private_key)} karakter")
print("\n✅ Public key harus 87 karakter (base64 URL safe)")
print("✅ Private key harus 43 karakter")