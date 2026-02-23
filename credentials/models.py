import secrets
from urllib.parse import quote
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from .fields import EncryptedTextField


class Credential(models.Model):
    username = models.CharField(_("Wikimedia username"), max_length=240, help_text=_("Username of the user whose credentials are being created."))
    full_name = EncryptedTextField(_("Full name"), max_length=240, help_text=_("Full name of user."))
    cpf = EncryptedTextField(_("CPF"), blank=True, null=True, help_text=_("CPF of user."))
    cin = EncryptedTextField(_("CIN"), max_length=24, blank=True, null=True, help_text=_("CIN of user."))
    photograph = EncryptedTextField(_("Photograph URL"), max_length=420, default="", help_text=_("Photograph URL."))
    url = models.URLField(_("Meta-Wiki Profile URL"), blank=True, default="", help_text=_("Meta-Wiki Profile URL."))

    event = models.CharField(_("Event name"), max_length=240, help_text=_("Event which credentials are being created."))
    verification_code = models.CharField(_("Verification code"), max_length=24, unique=True, editable=False)

    issued_at = models.DateTimeField(_("Issued at"),auto_now_add=True)
    issued_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="credential_issued_by", verbose_name=_("Issued by"))
    valid_from = models.DateField(_("Valid from"))
    valid_until = models.DateField(_("Valid until"))

    def save(self, *args, **kwargs):
        if not self.verification_code:
            self.verification_code = secrets.token_urlsafe(16)
        super().save(*args, **kwargs)

    def get_wikimedia_profile_url(self):
        return f"https://meta.wikimedia.org/wiki/User:{quote(self.username)}"

    def masked_cpf(self):
        if not self.cpf:
            return ""

        cpf = str(self.cpf)

        if len(cpf) == 11:
            return f"***.{self.cpf[3:6]}.{self.cpf[6:9]}-**"
        else:
            return "*" * len(cpf)

    def masked_cin(self):
        if not self.cin:
            return ""

        cin = str(self.cin)
        visible = 3

        if len(cin) <= visible:
            return "*" * len(cin)

        return cin[:visible] + "*" * (len(cin) - visible)

    def masked_name(self):
        if not self.full_name:
            return ""

        parts = self.full_name.split()

        if len(parts) == 1:
            return parts[0]

        first = parts[0]
        initials = [p[0] + "." for p in parts[1:]]

        return f"{first} {' '.join(initials)}"

    def __str__(self):
        return f"{self.event} - {self.username}"