from django.urls import path
from . import views

app_name = 'user_dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='home'),
    path('notifications/dropdown/', views.notifications_dropdown_view, name='notifications_dropdown'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit_view, name='profile_edit'),
    path('my-courses/', views.my_courses_view, name='my_courses'),
]