import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from django.conf import settings


class Crypt(object):
    def __init__(self):
        self.password = settings.SECRET_KEY

    def encrypt(self, plaintext):
        f = Fernet(base64.urlsafe_b64encode(PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=b'abcd', iterations=1000, backend=default_backend()).derive(self.password.encode())))
        return f.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext):
        f = Fernet(base64.urlsafe_b64encode(PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=b'abcd', iterations=1000, backend=default_backend()).derive(self.password.encode())))
        return f.decrypt(ciphertext.encode()).decode()