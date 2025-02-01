from django.urls import path
from calendars import views

app_name = 'calendars'

urlpatterns = [
    path('month_calendars', views.month_calendar_list, name='month_calendar_list'),
    path('month_calendars/<int:pk>/', views.month_calendar_detail, name='month_calendar_detail'),
    path('month_calendars/create/', views.month_calendar_create, name='month_calendar_create'),
    path('month_calendars/<int:pk>/update/', views.month_calendar_update, name='month_calendar_update'),
    path('month_calendars/<int:pk>/delete/', views.month_calendar_delete, name='month_calendar_delete'),
    path('', views.calendar_list, name='calendar_list'),
    path('create/', views.calendar_create, name='calendar_create'),
    path('<int:pk>/', views.calendar_detail, name='calendar_detail'),
    path('<int:pk>/update/', views.calendar_update, name='calendar_update'),
    path('<int:pk>/delete/', views.calendar_delete, name='calendar_delete'),
    path('<int:pk>/download/', views.calendar_download, name='calendar_download'),
    path('<int:calendar_id>/activity/create/', views.activity_create, name='activity_create'),
    path('<int:calendar_id>/activity/create_in_bulk/', views.activity_create_in_bulk, name='activity_create_in_bulk'),
    path('<int:calendar_id>/activity/<int:pk>/update/', views.activity_update, name='activity_update'),
    path('<int:calendar_id>/activity/<int:pk>/delete/', views.activity_delete, name='activity_delete')
]
