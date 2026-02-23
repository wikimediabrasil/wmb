"""
URL configuration for wmb project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
    path('', include(('users.urls', 'users'), namespace='users')),
    path('oauth/', include('social_django.urls', namespace='social')),
    path('certificates/', include(('certificates.urls', 'certificates'), namespace='certificates')),
    path('events/', include(('events.urls', 'events'), namespace='events')),
    path('calendars/', include(('calendars.urls', 'calendars'), namespace='calendars')),
    path('credentials/', include(('credentials.urls', 'credentials'), namespace='credentials')),
]

urlpatterns += staticfiles_urlpatterns()
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)