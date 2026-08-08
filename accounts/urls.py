from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('management/login/', views.admin_login_view, name='admin_login'),
    path('management/logout/', views.admin_logout_view, name='admin_logout'),

    path('management/admins/', views.admin_list_view, name='admin_list'),
    path('management/admins/create/', views.admin_create_view, name='admin_create'),
    path('management/admins/<uuid:pk>/edit/', views.admin_edit_view, name='admin_edit'),
    path('management/admins/<uuid:pk>/change-password/', views.admin_change_password_view, name='admin_change_password'),
    path('management/admins/<uuid:pk>/toggle-active/', views.admin_toggle_active_view, name='admin_toggle_active'),
    path('management/admins/<uuid:pk>/delete/', views.admin_delete_view, name='admin_delete'),

    path('faculty/', views.faculty_list_view, name='faculty_list'),
    path('faculty/create/', views.faculty_create_view, name='faculty_create'),
    path('faculty/<uuid:faculty_id>/edit/', views.faculty_edit_view, name='faculty_edit'),
    path('faculty/<uuid:faculty_id>/toggle-active/', views.faculty_toggle_active_view, name='faculty_toggle_active'),
    path('faculty/<uuid:faculty_id>/delete/', views.faculty_delete_view, name='faculty_delete'),
]