#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QR code content test script
"""

import qrcode
from PIL import Image
import json
import base64
import hashlib
import hmac
import os

def b64url(data: bytes) -> str:
    """Base64 URL safe encoding"""
    return base64.urlsafe_b64encode(data).decode().rstrip("=")

def sign_payload(payload: dict, secret: str) -> str:
    """Generate signature"""
    p = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
    sig = hmac.new(secret.encode(), p, hashlib.sha256).digest()
    return f"CM1.{b64url(p)}.{b64url(sig)}"

def test_qr_generation():
    """Test QR code generation"""
    print("=== QR Code Content Test ===\n")
    
    # Simulate token data
    payload = {
        "amount": 500,  # 5 yuan, unit: cents
        "one": 1,       # One-time use
        "exp": 1734567890,  # Expiration timestamp
        "nonce": hashlib.sha256(os.urandom(16)).hexdigest(),
        "desc": "Class performance reward"
    }
    
    secret = "change-me-secret"
    
    # Generate token
    token = sign_payload(payload, secret)
    print(f"Generated token: {token}")
    
    # Parse token
    try:
        parts = token.split(".")
        if len(parts) == 3 and parts[0] == "CM1":
            payload_b64 = parts[1]
            signature = parts[2]
            
            # Decode payload
            payload_bytes = base64.urlsafe_b64decode(payload_b64 + "==")
            decoded_payload = json.loads(payload_bytes.decode())
            
            print(f"\nPayload data:")
            print(f"  Amount: {decoded_payload['amount']} cents (¥{decoded_payload['amount']/100:.2f})")
            print(f"  One-time use: {'Yes' if decoded_payload['one'] else 'No'}")
            print(f"  Expiration time: {decoded_payload['exp']}")
            print(f"  Nonce: {decoded_payload['nonce'][:16]}...")
            print(f"  Description: {decoded_payload.get('desc', 'None')}")
            
            # Generate QR code content
            qr_content = f"https://classmint.local/claim?token={token}"
            print(f"\nQR code content:")
            print(f"  {qr_content}")
            
            # Generate QR code image
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(qr_content)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            img.save("test_qr.png")
            print(f"\nQR code saved as: test_qr.png")
            
        else:
            print("Token format error")
            
    except Exception as e:
        print(f"Failed to parse token: {e}")

if __name__ == "__main__":
    test_qr_generation()
