from django.urls import path
from . import views

app_name = "formbuilder"

urlpatterns = [
    path("manage/", views.form_list, name="form_list"),
    path("manage/create/", views.form_create, name="form_create"),
    path("manage/<uuid:pk>/edit/", views.form_edit, name="form_edit"),
    path("manage/<uuid:pk>/delete/", views.form_delete, name="form_delete"),
    path("manage/<uuid:pk>/publish/", views.form_toggle_publish, name="form_toggle_publish"),
    path("manage/<uuid:pk>/data/", views.form_data, name="form_data"),
    path("manage/<uuid:pk>/export/<str:fmt>/", views.form_export, name="form_export"),
    path("manage/<uuid:pk>/data/<uuid:resp_pk>/delete/", views.response_delete,name="response_delete",),
    path("f/<slug:slug>/", views.form_fill, name="form_fill"),
    path("f/<slug:slug>/success/", views.form_success, name="form_success"),
    path("manage/<uuid:pk>/pin/", views.form_toggle_pin, name="form_toggle_pin"),
]