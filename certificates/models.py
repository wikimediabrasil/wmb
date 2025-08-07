from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from events.models import Event
from users.models import User, Participant
import hashlib

PRONOUN_CHOICES = [('a', 'a'), ('o', 'o')]


class Certificate(models.Model):
    name = models.CharField(max_length=500)
    username = models.ForeignKey(Participant, on_delete=models.SET_NULL, null=True, blank=True)
    pronoun = models.CharField(max_length=200, choices=PRONOUN_CHOICES, default='o')
    event = models.ForeignKey(Event, on_delete=models.SET_NULL, related_name='event_certificates', null=True)
    hours = models.CharField(max_length=10, validators=[RegexValidator(regex=r"^\d+[h,H]\d+$")])
    with_hours = models.BooleanField(default=True)
    role = models.CharField(max_length=200, default='ouvinte')
    background = models.ImageField(upload_to=settings.UPLOAD_FOLDER)
    certificate_hash = models.CharField(max_length=500, blank=True, null=True)
    emitted_at = models.DateTimeField(auto_now_add=True)
    emitted_by = models.ForeignKey(User,
                                   on_delete=models.SET_NULL,
                                   related_name="certificates_emitted",
                                   blank=True,
                                   null=True)

    permissions = [
        ("download_all", "Can download all certificates"),
    ]


    def save(self, *args, **kwargs):
        if self.name and self.event and self.hours and self.role:
            certificate_hash = hashlib.sha1(bytes("Certificate " + self.name + str(self.event) + str(self.hours) + str(self.role), 'utf-8')).hexdigest()
        else:
            certificate_hash = ""

        if not self.certificate_hash:
            self.certificate_hash = certificate_hash

        super().save(*args, **kwargs)

    def __str__(self):
        if self.username:
            return f"{self.event} - {self.username}"
        else:
            return f"{self.event} - {self.name}"