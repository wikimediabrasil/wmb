from django.urls import path
from certificates import views

app_name = "certificates"

urlpatterns = [
    path('', views.certificate_list, name='certificate_list'),
    path('validate/', views.certificate_validate, name='certificate_validate'),
    path('download/<str:certificate_hash>', views.certificate_download_by_hash, name='download_by_hash'),
]
