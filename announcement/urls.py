from django.urls import path
from . import views

app_name = 'announcement'

urlpatterns = [
    path('manage/', views.announcement_list_view, name='manage_list'),
    path('manage/create/', views.announcement_create_view, name='create'),
    path('manage/<uuid:announcement_id>/edit/', views.announcement_edit_view, name='edit'),
    path('manage/<uuid:announcement_id>/delete/', views.announcement_delete_view, name='delete'),
    path('manage/<uuid:announcement_id>/toggle-active/', views.announcement_toggle_active_view, name='toggle_active'),

    path('my-announcements/', views.my_announcements_view, name='my_announcements'),
]