from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

from .models import User


class EmailOrPhoneBackend(ModelBackend):
    """
    Authenticates against either email or contact number, for both
    admin and learner logins. Django's `authenticate()` always passes
    the entered identifier in as `username` regardless of your form's
    field name, so we accept it as `username` here and check it against
    both columns.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        try:
            user = User.objects.get(Q(email__iexact=username) | Q(contact=username))
        except User.DoesNotExist:
            return None
        except User.MultipleObjectsReturned:
            # Shouldn't happen given unique=True on both fields, but fail safe
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None