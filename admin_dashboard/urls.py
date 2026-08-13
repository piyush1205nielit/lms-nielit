from django.urls import path
from . import views

app_name = 'admin_dashboard'

urlpatterns = [

    path('', views.dashboard_home, name='home'),

    path('users/', views.registered_users_view, name='registered_users'),
    path('users/data/', views.registered_users_data_view, name='registered_users_data'),
    path('users/<uuid:user_id>/detail-modal/', views.student_detail_modal_view, name='student_detail_modal'),
    path('users/<uuid:user_id>/edit-modal/', views.student_edit_modal_view, name='student_edit_modal'),
    path('users/<uuid:user_id>/delete/', views.student_delete_view, name='student_delete'),

    path('centres/', views.centre_list_view, name='centre_list'),
    path('centres/add/', views.centre_modal_view, name='centre_add'),
    path('centres/<uuid:centre_id>/edit/', views.centre_modal_view, name='centre_edit'),
    path('centres/<uuid:centre_id>/delete/', views.centre_delete_view, name='centre_delete'),

    path('registrations/', views.registration_requests_view, name='registration_requests'),
    path('registrations/bulk-approve/', views.bulk_approve_registrations_view, name='bulk_approve_registrations'),
    path('registrations/bulk-deny/', views.bulk_deny_registrations_view, name='bulk_deny_registrations'),

    path('user-access/', views.user_access_management_view, name='user_access_management'),
    path('user-access/bulk-grant/', views.bulk_grant_access_view, name='bulk_grant_access'),
    path('user-access/bulk-revoke/', views.bulk_revoke_access_view, name='bulk_revoke_access'),
    path('user-access/bulk-disable/', views.bulk_disable_access_view, name='bulk_disable_access'),
    path('user-access/bulk-delete/', views.bulk_delete_accounts_view, name='bulk_delete_accounts'),

    path('users/bulk-upload/', views.bulk_user_upload_view, name='bulk_user_upload'),
    path('users/bulk-upload/template/', views.download_upload_template_view, name='download_upload_template'),

    path('faculty-home/', views.faculty_dashboard_home, name='faculty_home'),
    path('admins/<uuid:admin_id>/toggle-course-permission/', views.toggle_admin_course_permission_view, name='toggle_admin_course_permission'),

    path('maintenance/', views.maintenance_mode_view, name='maintenance_mode'),

]