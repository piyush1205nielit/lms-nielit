import random
from datetime import datetime

from .models import LearnerProfile


def generate_enrollment_number():
    """
    Generates a unique enrollment number in the format YYYYMM-XXXXXX
    e.g. 202607-483920

    Called once, at the moment a LearnerProfile is first created —
    either right after email/password signup, or right after a user's
    first Google login (both paths create a LearnerProfile immediately).
    """
    prefix = datetime.now().strftime('%Y%m')

    max_attempts = 10
    for _ in range(max_attempts):
        suffix = str(random.randint(0, 999999)).zfill(6)
        candidate = f"{prefix}-{suffix}"

        if not LearnerProfile.objects.filter(enrollment_number=candidate).exists():
            return candidate

    # Extremely unlikely at your scale (1 in a million per attempt, 10 attempts),
    # but fail loudly rather than silently returning a colliding number.
    raise RuntimeError(
        "Could not generate a unique enrollment number after "
        f"{max_attempts} attempts. Check LearnerProfile volume for this month."
    )

def generate_otp():
    return str(random.randint(0, 999999)).zfill(6)