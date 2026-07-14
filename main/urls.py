from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

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

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)