from django.urls import path
from . import views

app_name = 'admin_dashboard'

urlpatterns = [

    path('', views.dashboard_home, name='home'),
    
    # path('users/', views.registered_users_view, name='registered_users'),
    # path('users/<uuid:user_id>/detail-modal/', views.student_detail_modal_view, name='student_detail_modal'),
    # path('users/<uuid:user_id>/edit-modal/', views.student_edit_modal_view, name='student_edit_modal'),
    # path('users/<uuid:user_id>/delete/', views.student_delete_view, name='student_delete'),

    path('users/', views.registered_users_view, name='registered_users'),
    path('users/data/', views.registered_users_data_view, name='registered_users_data'),
    path('users/<uuid:user_id>/detail-modal/', views.student_detail_modal_view, name='student_detail_modal'),
    path('users/<uuid:user_id>/edit-modal/', views.student_edit_modal_view, name='student_edit_modal'),
    path('users/<uuid:user_id>/delete/', views.student_delete_view, name='student_delete'),

]