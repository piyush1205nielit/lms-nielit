from accounts.models import User
from course.models import Enrollment
from assignment.models import AssignmentSubmission


def admin_notifications_context(request):
    if request.user.is_authenticated and getattr(request.user, 'is_admin_role', False):
        return {
            'pending_registration_count': User.objects.filter(
                role=User.Role.USER, account_status=User.AccountStatus.PENDING
            ).count(),
            'pending_enrollment_count': Enrollment.objects.filter(
                access_status=Enrollment.AccessStatus.PENDING
            ).count(),
            'pending_grading_count': AssignmentSubmission.objects.filter(
                status=AssignmentSubmission.Status.SUBMITTED
            ).count(),
        }
    return {}