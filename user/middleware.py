from django.shortcuts import redirect
from django.urls import reverse


class ProfileCompletionMiddleware:
    """
    Forces learners to complete their profile (LearnerProfile.profile_completed)
    before they can access anything else on the site, except a small allowlist
    of paths (the completion form itself, logout, static/media, admin routes).
    """

    # path prefixes that are always allowed, even with an incomplete profile
    EXEMPT_PATH_PREFIXES = (
        '/static/',
        '/media/',
        '/admin/',           # Django's built-in admin
        '/management/',      # your custom admin console
        '/accounts/',        # allauth's Google OAuth flow + your admin login/mgmt urls
        '/stream/',          # MediaConvert webhook — AWS calling in, not a browser session
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._should_check(request):
            profile = getattr(request.user, 'learner_profile', None)
            if profile and not profile.profile_completed:
                complete_profile_url = reverse('user:complete_profile')
                if request.path != complete_profile_url:
                    return redirect(complete_profile_url)

        return self.get_response(request)

    def _should_check(self, request):
        if not request.user.is_authenticated:
            return False
        if request.user.role != 'user':
            return False   # admins/superadmins never go through this gate
        if request.path.startswith(self.EXEMPT_PATH_PREFIXES):
            return False
        return True