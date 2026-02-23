from django.urls import path
from . import views

app_name = 'credentials'

urlpatterns = [
    path("list/", views.credential_list, name="credential_list"),
    path("create/", views.credential_create, name="credential_create"),
    path("<str:verification_code>/", views.credential_detail, name="credential_detail"),
    path("<str:verification_code>/edit/", views.credential_update, name="credential_update"),
    path("<str:verification_code>/delete/", views.credential_delete, name="credential_delete"),
    path("", views.credential_validate, name="credential_validate"),
]