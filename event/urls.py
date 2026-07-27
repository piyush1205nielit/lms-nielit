from django.urls import path

from . import views

app_name = "event"

urlpatterns = [
    path("", views.public_event_list, name="public_event_list"),

    path("admin/", views.event_list, name="event_list"),
    path("admin/create/", views.event_create, name="event_create"),
    path("admin/<uuid:pk>/edit/", views.event_update, name="event_update"),
    path("admin/<uuid:pk>/delete/", views.event_delete, name="event_delete"),
    path("admin/<uuid:pk>/preview/", views.event_preview, name="event_preview"),
    path("admin/<uuid:pk>/toggle-active/", views.event_toggle_active, name="event_toggle_active"),
    path("admin/display-mode/<str:mode>/", views.event_set_display_mode, name="event_set_display_mode"),
]