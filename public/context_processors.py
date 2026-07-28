from course.models import Domain


def domain_nav_context(request):
    return {'nav_domains': Domain.objects.filter(is_active=True).order_by('name')}