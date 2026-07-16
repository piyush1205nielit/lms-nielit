from django.urls import path
from . import views

app_name = 'user'


urlpatterns = [
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.user_login_view, name='login'),
    path('logout/', views.user_logout_view, name='logout'),
    path('complete-profile/', views.complete_profile_view, name='complete_profile'),

    path('profile/edit/', views.profile_edit_view, name='profile_edit'),
    path('profile/change-password/', views.change_password_view, name='change_password'),

    path('forgot-password/', views.forgot_password_verify_view, name='forgot_password'),
    path('forgot-password/otp/', views.forgot_password_otp_view, name='forgot_password_otp'),
    path('forgot-password/resend-otp/', views.forgot_password_resend_otp_view, name='forgot_password_resend_otp'),
    path('forgot-password/reset/', views.reset_password_view, name='reset_password'),
]
