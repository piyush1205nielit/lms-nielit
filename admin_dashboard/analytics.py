from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Q
from django.db.models.functions import TruncDate

from accounts.models import User
from course.models import Course, Domain, Enrollment
from assignment.models import Assignment, AssignmentSubmission
from certificate.models import StudentCertificate
from announcement.models import Announcement
from admin_dashboard.models import Centre


def _daily_trend(queryset, date_field, days=14):
    since = timezone.now() - timedelta(days=days - 1)
    raw = (
        queryset.filter(**{f"{date_field}__gte": since})
        .annotate(day=TruncDate(date_field))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    counts_by_day = {row["day"]: row["count"] for row in raw}
    result = []
    for i in range(days):
        day = (since + timedelta(days=i)).date()
        result.append({"date": day.strftime("%d %b"), "count": counts_by_day.get(day, 0)})
    return result


def _pct(numerator, denominator):
    if not denominator:
        return 0
    return round((numerator / denominator) * 100)


def _week_over_week(queryset, date_field):
    """Returns (this_week_count, pct_change_vs_last_week)."""
    now = timezone.now()
    this_week_start = now - timedelta(days=7)
    last_week_start = now - timedelta(days=14)

    this_week = queryset.filter(**{f"{date_field}__gte": this_week_start}).count()
    last_week = queryset.filter(**{f"{date_field}__gte": last_week_start, f"{date_field}__lt": this_week_start}).count()

    if last_week == 0:
        change = 100 if this_week > 0 else 0
    else:
        change = round(((this_week - last_week) / last_week) * 100)
    return this_week, change


def get_dashboard_analytics(user):
    role = user.role
    data = {"role": role}

    is_superadmin = role == User.Role.SUPERADMIN
    is_admin = role == User.Role.ADMIN
    can_see_content_stats = is_superadmin or is_admin
    can_see_staff_stats = is_superadmin

    # ═══ Students & accounts ═══
    all_students = User.objects.filter(role=User.Role.USER)
    data["total_students"] = all_students.count()
    data["active_students"] = all_students.filter(account_status=User.AccountStatus.ACTIVE).count()
    data["pending_registrations"] = all_students.filter(account_status=User.AccountStatus.PENDING).count()
    data["disabled_students"] = all_students.filter(account_status=User.AccountStatus.DISABLED).count()
    data["revoked_students"] = all_students.filter(account_status=User.AccountStatus.REVOKED).count()
    data["profile_complete_count"] = all_students.filter(learner_profile__profile_completed=True).count()

    data["active_account_rate"] = _pct(data["active_students"], data["total_students"])
    data["profile_completion_rate"] = _pct(data["profile_complete_count"], data["total_students"])

    reg_this_week, reg_change = _week_over_week(all_students, "date_joined")
    data["registrations_this_week"] = reg_this_week
    data["registrations_change_pct"] = reg_change

    data["account_status_breakdown"] = {
        "active": data["active_students"],
        "pending": data["pending_registrations"],
        "disabled": data["disabled_students"],
        "revoked": data["revoked_students"],
    }

    # ═══ Enrollments ═══
    all_enrollments = Enrollment.objects.all()
    data["total_enrollments"] = all_enrollments.count()
    data["pending_enrollments"] = all_enrollments.filter(access_status=Enrollment.AccessStatus.PENDING).count()
    data["granted_enrollments"] = all_enrollments.filter(access_status=Enrollment.AccessStatus.GRANTED).count()
    data["hold_enrollments"] = all_enrollments.filter(access_status=Enrollment.AccessStatus.HOLD).count()
    data["revoked_enrollments"] = all_enrollments.filter(access_status=Enrollment.AccessStatus.REVOKED).count()
    data["completed_enrollments"] = all_enrollments.filter(status=Enrollment.Status.COMPLETED).count()

    data["enrollment_grant_rate"] = _pct(data["granted_enrollments"], data["total_enrollments"])
    data["course_completion_rate"] = _pct(data["completed_enrollments"], data["granted_enrollments"])

    enr_this_week, enr_change = _week_over_week(all_enrollments, "enrolled_at")
    data["enrollments_this_week"] = enr_this_week
    data["enrollments_change_pct"] = enr_change

    # ═══ Assignments ═══
    data["total_assignments"] = Assignment.objects.filter(is_active=True).count()
    all_submissions = AssignmentSubmission.objects.all()
    data["pending_grading"] = all_submissions.filter(status=AssignmentSubmission.Status.SUBMITTED).count()
    data["total_submissions"] = all_submissions.count()
    data["graded_submissions"] = all_submissions.filter(status=AssignmentSubmission.Status.GRADED).count()
    data["late_submissions"] = all_submissions.filter(is_late=True).count()

    data["grading_completion_rate"] = _pct(data["graded_submissions"], data["total_submissions"])

    # ═══ Certificates ═══
    all_certs = StudentCertificate.objects.all()
    data["pending_certificates"] = all_certs.filter(status=StudentCertificate.Status.REQUESTED).count()
    data["approved_certificates"] = all_certs.filter(status=StudentCertificate.Status.APPROVED).count()
    data["revoked_certificates"] = all_certs.filter(status=StudentCertificate.Status.REVOKED).count()
    data["denied_certificates"] = all_certs.filter(status=StudentCertificate.Status.DENIED).count()
    data["total_certificates"] = all_certs.count()

    data["certificate_approval_rate"] = _pct(data["approved_certificates"], data["total_certificates"])

    data["certificate_breakdown"] = {
        "approved": data["approved_certificates"],
        "requested": data["pending_certificates"],
        "revoked": data["revoked_certificates"],
        "denied": data["denied_certificates"],
    }

    # ═══ Content authoring — admin/superadmin only ═══
    if can_see_content_stats:
        all_courses = Course.objects.all()
        data["total_courses"] = all_courses.count()
        data["active_courses"] = all_courses.filter(status=Course.Status.ACTIVE).count()
        data["inactive_courses"] = all_courses.filter(status=Course.Status.INACTIVE).count()
        data["featured_courses"] = all_courses.filter(is_featured=True).count()
        data["course_active_rate"] = _pct(data["active_courses"], data["total_courses"])

        all_domains = Domain.objects.all()
        data["total_domains"] = all_domains.count()
        data["active_domains"] = all_domains.filter(is_active=True).count()

        data["total_announcements"] = Announcement.objects.filter(is_system_generated=False).count()
        data["active_announcements"] = Announcement.objects.filter(is_system_generated=False, is_active=True).count()

        data["course_status_breakdown"] = {"active": data["active_courses"], "inactive": data["inactive_courses"]}

        top_courses = (
            Course.objects.annotate(enrollment_count=Count("enrollments"))
            .filter(enrollment_count__gt=0)
            .order_by("-enrollment_count")[:6]
        )
        data["top_courses"] = [{"name": c.course_name[:28], "count": c.enrollment_count} for c in top_courses]

        top_domains = (
            Domain.objects.annotate(course_count=Count("courses"))
            .filter(course_count__gt=0)
            .order_by("-course_count")[:6]
        )
        data["top_domains"] = [{"name": d.name, "count": d.course_count} for d in top_domains]

    # ═══ Staff & centres — superadmin only ═══
    if can_see_staff_stats:
        data["total_admins"] = User.objects.filter(role=User.Role.ADMIN).count()
        data["total_faculty"] = User.objects.filter(role=User.Role.FACULTY).count()
        data["total_centres"] = Centre.objects.filter(is_active=True).count()

        centre_dist = (
            User.objects.filter(role=User.Role.USER, nielit_centre__isnull=False)
            .values("nielit_centre__centre_name")
            .annotate(count=Count("id"))
            .order_by("-count")[:6]
        )
        data["centre_distribution"] = [{"name": c["nielit_centre__centre_name"], "count": c["count"]} for c in centre_dist]

    # ═══ Trend charts ═══
    data["registration_trend"] = _daily_trend(all_students, "date_joined")
    data["enrollment_trend"] = _daily_trend(all_enrollments, "enrolled_at")
    data["assignment_breakdown"] = {"graded": data["graded_submissions"], "pending": data["pending_grading"]}

    # ═══ Recent activity feed ═══
    activity = []
    for u in User.objects.filter(role=User.Role.USER).order_by("-date_joined")[:5]:
        activity.append({"icon": "bi-person-plus-fill", "color": "amber", "text": f"{u.email} registered", "timestamp": u.date_joined})
    for e in Enrollment.objects.select_related("user", "course").order_by("-enrolled_at")[:5]:
        activity.append({"icon": "bi-journal-check", "color": "blue", "text": f"{e.user.email} requested \u2018{e.course.course_name}\u2019", "timestamp": e.enrolled_at})
    for c in all_certs.select_related("user", "course").filter(status=StudentCertificate.Status.REQUESTED).order_by("-requested_at")[:5]:
        activity.append({"icon": "bi-award-fill", "color": "purple", "text": f"{c.user.email} requested a certificate for \u2018{c.course.course_name}\u2019", "timestamp": c.requested_at})
    for s in all_submissions.select_related("student", "assignment").filter(status=AssignmentSubmission.Status.SUBMITTED).order_by("-submitted_at")[:5]:
        activity.append({"icon": "bi-file-earmark-check-fill", "color": "green", "text": f"{s.student.email} submitted \u2018{s.assignment.title}\u2019", "timestamp": s.submitted_at})
    activity.sort(key=lambda x: x["timestamp"], reverse=True)
    data["recent_activity"] = activity[:10]

    return data