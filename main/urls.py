from django.urls import path, include, re_path
from django.views.static import serve
from django.conf import settings
from django.contrib import admin

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('public.urls')),
    path('', include('user.urls')),
    path('dashboard/', include('user_dashboard.urls')),
    path('', include('accounts.urls')),
    path('management/', include('admin_dashboard.urls')),
    path('courses/', include('course.urls')),
    path('stream/', include('stream.urls')),
]

# Serve media manually — static() no-ops when DEBUG=False, so we bypass it here.
# This is fine for local testing; use nginx or S3 in real production (see below).
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)