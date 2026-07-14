from django.urls import path
from . import views

app_name = 'stream'

urlpatterns = [
    path('<slug:slug>/lesson/<uuid:lesson_id>/', views.lesson_player_view, name='player'),
    path('progress/<uuid:lesson_id>/mark/', views.mark_lesson_progress, name='mark_progress'),
]