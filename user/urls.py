from django.urls import path
from . import views

app_name = 'user'

urlpatterns = [
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.user_login_view, name='login'),
    path('logout/', views.user_logout_view, name='logout'),
    path('complete-profile/', views.complete_profile_view, name='complete_profile'),
]