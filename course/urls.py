from django.urls import path
from . import views

app_name = 'course'

urlpatterns = [
    path('manage/', views.manage_list_view, name='manage_list'),
    path('manage/create/', views.course_create_view, name='create'),
    path('manage/<uuid:course_id>/edit/', views.course_edit_view, name='edit'),
    path('manage/<uuid:course_id>/toggle-active/', views.course_toggle_active_view, name='toggle_active'),
    path('manage/<uuid:course_id>/toggle-featured/', views.course_toggle_featured_view, name='toggle_featured'),
    path('manage/<uuid:course_id>/delete/', views.course_delete_view, name='delete'),

    path('manage/<uuid:course_id>/modules/', views.course_modules_view, name='modules'),
    path('manage/<uuid:course_id>/modules/add/', views.module_create_view, name='module_add'),
    path('manage/module/<uuid:module_id>/edit/', views.module_edit_view, name='module_edit'),
    path('manage/module/<uuid:module_id>/delete/', views.module_delete_view, name='module_delete'),
    path('manage/module/<uuid:module_id>/lessons/add/', views.lesson_create_view, name='lesson_add'),
    path('manage/lesson/<uuid:lesson_id>/edit/', views.lesson_edit_view, name='lesson_edit'),
    path('manage/lesson/<uuid:lesson_id>/delete/', views.lesson_delete_view, name='lesson_delete'),

    path('manage/domains/', views.domain_list_view, name='domain_list'),
    path('manage/domains/create/', views.domain_create_view, name='domain_create'),
    path('manage/domains/<uuid:domain_id>/edit/', views.domain_edit_view, name='domain_edit'),
    path('manage/domains/<uuid:domain_id>/delete/', views.domain_delete_view, name='domain_delete'),

    path('my-courses/', views.my_courses_view, name='my_courses'),
    path('<slug:slug>/enroll/', views.course_enroll_view, name='enroll'),
    path('<slug:slug>/', views.course_detail_view, name='detail'),   # catch-all — must stay last

    path('manage/<uuid:course_id>/overview/', views.course_overview_view, name='overview'),
    path('manage/<uuid:course_id>/students/', views.course_students_view, name='students'),

    path('manage/enrollments/', views.enrollment_management_view, name='enrollment_management'),
    path('manage/enrollments/bulk-grant/', views.bulk_grant_enrollment_view, name='bulk_grant_enrollment'),
    path('manage/enrollments/bulk-hold/', views.bulk_hold_enrollment_view, name='bulk_hold_enrollment'),
    path('manage/enrollments/bulk-revoke/', views.bulk_revoke_enrollment_view, name='bulk_revoke_enrollment'),
    path('manage/enrollments/bulk-deny/', views.bulk_deny_enrollment_view, name='bulk_deny_enrollment'),
]