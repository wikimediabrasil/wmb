from django.urls import path
from events import views
from certificates.views import certificate_create_manually, certificate_update, certificate_delete

app_name = "events"

urlpatterns = [
    path('create', views.event_create, name='event_create'),
    path('', views.event_list, name='event_list'),
    path('<int:event_id>', views.event_detail, name='event_detail'),
    path('<int:event_id>/update', views.event_update, name='event_update'),
    path('<int:event_id>/delete', views.event_delete, name='event_delete'),
    path('<int:event_id>/certificate', views.event_certificate, name='event_certificate'),
    path('<int:event_id>/certificate/confirm', views.event_confirm_certification, name='event_confirm_certificate'),
    path('<int:event_id>/download/all', views.event_download_certificates, name='event_download_all'),
    path('<int:event_id>/download/<int:certificate_id>', views.event_download_certificates, name='event_download'),
    path('<int:event_id>/certificate/create', certificate_create_manually, name='event_certificate_manually'),
    path('<int:event_id>/certificate/<int:certificate_id>/delete', certificate_delete, name='certificate_delete'),
    path('<int:event_id>/certificate/<int:certificate_id>/update', certificate_update, name='certificate_update'),
]
