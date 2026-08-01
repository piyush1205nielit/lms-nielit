from course.models import Enrollment
from assignment.models import Assignment, AssignmentSubmission


def is_eligible_for_certificate(user, course):
    """
    A student may request a certificate only if:
    1. Their enrollment is GRANTED and the course itself is marked COMPLETED
       (i.e. every lesson has been watched — this already happens automatically
       via mark_lesson_progress once all lessons are done).
    2. Every active Assignment for this course has a submission from this user
       (submitted or graded — an ungraded-but-submitted assignment still counts,
       since the requirement is "submitted", not "graded").
    """
    enrollment = Enrollment.objects.filter(
        user=user, course=course,
        access_status=Enrollment.AccessStatus.GRANTED,
        status=Enrollment.Status.COMPLETED,
    ).first()

    if not enrollment:
        return False, "Course must be fully completed before requesting a certificate."

    course_assignments = Assignment.objects.filter(course=course, is_active=True)
    if course_assignments.exists():
        submitted_assignment_ids = set(
            AssignmentSubmission.objects.filter(
                student=user, assignment__in=course_assignments
            ).values_list('assignment_id', flat=True)
        )
        missing = course_assignments.exclude(id__in=submitted_assignment_ids)
        if missing.exists():
            return False, f"Submit all assignments for this course first ({missing.count()} pending)."

    return True, None