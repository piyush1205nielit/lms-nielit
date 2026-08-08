from django.urls import path
from . import views

app_name = 'assignment'

urlpatterns = [
    path('manage/', views.assignment_list_view, name='manage_list'),
    path('manage/create/', views.assignment_create_view, name='create'),
    path('manage/<uuid:assignment_id>/edit/', views.assignment_edit_view, name='edit'),
    path('manage/<uuid:assignment_id>/delete/', views.assignment_delete_view, name='delete'),
    path('manage/<uuid:assignment_id>/submissions/', views.assignment_submissions_view, name='submissions_list'),
    path('manage/submission/<uuid:submission_id>/grade/', views.grade_submission_view, name='grade_submission'),

    path('my-assignments/', views.my_assignments_view, name='my_assignments'),
    path('<uuid:assignment_id>/submit/', views.assignment_submit_view, name='submit'),

    path('submissions/<uuid:submission_id>/json/', views.submission_detail_json, name='submission_detail_json'),
    path('<uuid:assignment_id>/bulk-grade/', views.bulk_grade_submissions_view, name='bulk_grade_submissions'),
]