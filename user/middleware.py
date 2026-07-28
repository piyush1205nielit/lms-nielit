from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages

# Paths a logged-in-but-incomplete-profile learner may still reach.
# Keep this list tight — anything not listed here redirects to profile completion.
EXEMPT_PATH_PREFIXES = [
    '/static/',
    '/media/',
    '/admin/',            # Django admin
    '/management/',       # staff/admin-facing app routes
    '/accounts/',          # admin login etc.
    '/user/logout/',
    '/user/complete-profile/',
    '/stream/webhook/',    # server-to-server MediaConvert webhook — must never be gated
]


class ProfileCompletionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user

        if user.is_authenticated and getattr(user, 'role', None) == 'user':
            profile = getattr(user, 'learner_profile', None)

            if profile is not None and not profile.profile_completed:
                path = request.path
                if not any(path.startswith(p) for p in EXEMPT_PATH_PREFIXES):
                    if path != reverse('user:complete_profile'):
                        messages.info(request, "Please complete your profile to access this page.")
                        return redirect('user:complete_profile')

        return self.get_response(request)