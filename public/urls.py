from django.urls import path
from . import views

app_name = 'public'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('courses/', views.courses_view, name='courses'),
    # path('announcements/', views.announcements_view, name='announcements'),
    # path('centres/', views.centres_view, name='centres'),
]