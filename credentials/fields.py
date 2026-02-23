from django.conf import settings
from django.db import models
from cryptography.fernet import Fernet


def get_fernet():
    key = settings.FIELD_ENCRYPTION_KEY.encode()
    return Fernet(key)


class EncryptedTextField(models.TextField):
    def get_prep_value(self, value):
        if value is None:
            return value
        f = get_fernet()
        encrypted = f.encrypt(value.encode())
        return encrypted.decode()

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        f = get_fernet()
        decrypted = f.decrypt(value.encode())
        return decrypted.decode()

    def to_python(self, value):
        return value