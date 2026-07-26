from django.urls import path
from . import views

app_name = 'course'

urlpatterns = [
    # Admin: course management
    path('manage/', views.manage_list_view, name='manage_list'),
    path('manage/create/', views.course_create_view, name='create'),
    path('manage/<uuid:course_id>/edit/', views.course_edit_view, name='edit'),
    path('manage/<uuid:course_id>/modules/', views.course_modules_view, name='modules'),
    path('manage/<uuid:course_id>/modules/add/', views.module_create_view, name='module_add'),

    path('manage/module/<uuid:module_id>/edit/', views.module_edit_view, name='module_edit'),
    path('manage/module/<uuid:module_id>/delete/', views.module_delete_view, name='module_delete'),
    path('manage/module/<uuid:module_id>/lessons/add/', views.lesson_create_view, name='lesson_add'),

    path('manage/lesson/<uuid:lesson_id>/edit/', views.lesson_edit_view, name='lesson_edit'),
    path('manage/lesson/<uuid:lesson_id>/delete/', views.lesson_delete_view, name='lesson_delete'),

    path('manage/<uuid:course_id>/publish/', views.course_publish_view, name='publish'),

    path('manage/domains/', views.domain_list_view, name='domain_list'),
    path('manage/domains/create/', views.domain_create_view, name='domain_create'),
    path('manage/domains/<uuid:domain_id>/edit/', views.domain_edit_view, name='domain_edit'),
    path('manage/domains/<uuid:domain_id>/delete/', views.domain_delete_view, name='domain_delete'),


    # Learner: enrollment
    path('my-courses/', views.my_courses_view, name='my_courses'),
    path('<slug:slug>/enroll/', views.course_enroll_view, name='enroll'),

    # Public: course detail — MUST stay last, it's a catch-all slug pattern
    path('<slug:slug>/', views.course_detail_view, name='detail'),
]