from django.urls import path
from . import views

app_name = 'stream'

urlpatterns = [
    path('<slug:slug>/lesson/<uuid:lesson_id>/', views.lesson_player_view, name='player'),
    path('progress/<uuid:lesson_id>/mark/', views.mark_lesson_progress, name='mark_progress'),

    path('admin/lesson/<uuid:lesson_id>/request-upload/', views.request_video_upload_url, name='request_upload'),
    path('admin/lesson/<uuid:lesson_id>/confirm-upload/', views.confirm_video_upload, name='confirm_upload'),

    path('webhook/mediaconvert/', views.mediaconvert_webhook, name='mediaconvert_webhook'),
]