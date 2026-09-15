"""Run locally to create a VAPID key pair. Never commit the printed private key."""
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

if __name__=='__main__':
    key=ec.generate_private_key(ec.SECP256R1())
    public=key.public_key().public_bytes(serialization.Encoding.X962,serialization.PublicFormat.UncompressedPoint)
    private=key.private_bytes(serialization.Encoding.DER,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())
    for name,value in [('VAPID_PUBLIC_KEY',public),('VAPID_PRIVATE_KEY',private)]:
        print(name+'='+base64.urlsafe_b64encode(value).decode().rstrip('='))
