from django.shortcuts import render
from django.conf import settings
from .models import MaintenanceMode

# Path prefixes that must ALWAYS work, even during maintenance — the entire
# admin/staff area, static/media assets, and the maintenance toggle view
# itself (so a superadmin isn't locked out of turning it back off).
EXEMPT_PATH_PREFIXES = [
    '/management/',
    '/dashboard/',
    '/courses/manage/',
    '/certificates/admin/',
    '/assignments/manage/',
    '/announcements/manage/',
    '/static/',
    '/media/',
    '/stream/webhook/',   # server-to-server MediaConvert webhook — must never be blocked
]


class MaintenanceModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        maintenance = MaintenanceMode.get_solo()

        if maintenance.is_enabled:
            path = request.path

            is_exempt_path = any(path.startswith(p) for p in EXEMPT_PATH_PREFIXES)
            is_staff_user = request.user.is_authenticated and getattr(request.user, 'is_staff_area_role', False)

            # Staff (superadmin/admin/faculty) can still use the admin panel;
            # everyone else — including logged-in students — sees the maintenance page,
            # for ANY path that isn't the admin area itself.
            if not is_exempt_path and not is_staff_user:
                return render(request, 'public/maintenance.html', {
                    'maintenance': maintenance,
                }, status=503)

        return self.get_response(request)