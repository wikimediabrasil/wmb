from django.db import models
from users.models import User

class Event(models.Model):
    event_name = models.CharField(max_length=300)
    date_start = models.DateField()
    date_end = models.DateField(blank=True)
    link = models.CharField(max_length=1000, blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
    created_on = models.DateField(auto_now_add=True, blank=True, null=True)

    def __str__(self):
        return self.event_name


    def save(self, *args, **kwargs):
        if not self.date_end:
            self.date_end = self.date_start
        super().save(*args, **kwargs)