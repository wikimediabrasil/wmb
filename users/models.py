from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    full_name = models.CharField(_("full name"), max_length=300, blank=True)

    username = models.CharField(_("username"),
                                max_length=150,
                                unique=True,
                                blank=True,
                                help_text=_("Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."),
                                error_messages={"unique": _("A user with that username already exists."), })

    def __str__(self):
        return self.username

class Participant(models.Model):
    participant_full_name = models.CharField(_("full name"), max_length=300)
    participant_username = models.CharField(_("username"), max_length=150, blank=True, null=True)
    number_of_certificates = models.IntegerField(_("number of certificates"), default=0)
    enrolled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(_("date created"), auto_now_add=True)
    modified_at = models.DateTimeField(_("date modified"), auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='created_users', null=True, blank=True)
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='modified_users', null=True, blank=True)

    def __str__(self):
        if self.participant_username:
            return self.participant_username
        else:
            return ""
