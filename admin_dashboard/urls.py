from django.urls import path
from . import views

app_name = 'admin_dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='home'),
    path('users/', views.registered_users_view, name='registered_users'),
    path('users/<uuid:user_id>/profile-edit/', views.user_profile_edit_view, name='user_profile_edit'),
    path('users/<uuid:user_id>/credentials/', views.user_credentials_edit_view, name='user_credentials_edit'),
]