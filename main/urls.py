from django.urls import path, include, re_path
from django.views.static import serve
from django.conf import settings
from django.conf.urls.static import static
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

# Media is served by S3 in production (USE_S3=True) and never touches local
# disk, so MEDIA_ROOT only exists when USE_S3=False. Only wire up the local
# media-serving route in that case, and only outside DEBUG-served static().
if not settings.USE_S3:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)