from django.urls import path
from . import views

app_name = 'certificate'

urlpatterns = [
    # Student
    path('request/<uuid:course_id>/', views.request_certificate_view, name='request_certificate'),
    path('view/<str:certificate_number>/', views.view_certificate, name='view_certificate'),
    path('verify/<str:cert_number>/', views.verify_certificate, name='verify_certificate'),
    path('qr/<str:cert_number>/', views.certificate_qr_code, name='certificate_qr_code'),
    path('image-proxy/', views.image_proxy, name='image_proxy'),

    # Admin — designs
    path('admin/designs/', views.design_list, name='design_list'),
    path('admin/designs/create/', views.design_create, name='design_create'),
    path('admin/designs/<uuid:pk>/edit/', views.design_edit, name='design_edit'),
    path('admin/designs/<uuid:pk>/preview/', views.design_preview, name='design_preview'),
    path('admin/designs/<uuid:pk>/delete/', views.design_delete, name='design_delete'),

    # Admin — certificate request management
    path('admin/requests/', views.certificate_management_view, name='certificate_management'),
    path('admin/requests/<uuid:certificate_id>/issue/', views.issue_certificate_view, name='issue_certificate'),
    path('admin/requests/bulk-approve/', views.bulk_approve_certificates_view, name='bulk_approve_certificates'),
    path('admin/requests/bulk-revoke/', views.bulk_revoke_certificates_view, name='bulk_revoke_certificates'),
    path('admin/requests/bulk-deny/', views.bulk_deny_certificates_view, name='bulk_deny_certificates'),
    path('admin/requests/bulk-delete/', views.bulk_delete_certificates_view, name='bulk_delete_certificates'),

    path('my-certificates/', views.my_certificates_view, name='my_certificates'),
]