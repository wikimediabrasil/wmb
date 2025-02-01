from django.contrib import admin
from calendars.models import MonthCalendar, Calendar, Activity

admin.site.register(MonthCalendar)
admin.site.register(Calendar)
admin.site.register(Activity)
