from django.shortcuts import render
from django.core.paginator import Paginator
from course.models import *
from announcement.models import Announcement
from django.db.models import Q
from event.forms import EventForm
from event.models import Event, EventDisplaySettings



def home_view(request):
    
    featured_courses = Course.objects.filter(status=Course.Status.ACTIVE).prefetch_related('domains').order_by('-published_date')[:6]
    public_announcements = Announcement.objects.public_active()[:5]
    display_settings = EventDisplaySettings.get_solo()

    context = {
        'featured_courses': featured_courses,
        'public_announcements': public_announcements,
        "events": Event.objects.filter(is_active=True),
        "event_display_mode": display_settings.display_mode,
    }
    return render(request, 'public/home.html', context)



def courses_view(request):
    course_list = Course.objects.filter(status=Course.Status.ACTIVE).prefetch_related('domains').order_by('-published_date')

    # Filter by domain slug, e.g. /courses/?domain=cyber-security
    selected_domain_slug = request.GET.get('domain')
    if selected_domain_slug:
        course_list = course_list.filter(domains__slug=selected_domain_slug)

    # Free-text search across course name/description AND domain name —
    # this is the "don't need to remember exact course name" behavior
    query = request.GET.get('q', '').strip()
    if query:
        course_list = course_list.filter(
            Q(course_name__icontains=query) |
            Q(course_description__icontains=query) |
            Q(domains__name__icontains=query)
        ).distinct()

    paginator = Paginator(course_list, 12)
    courses = paginator.get_page(request.GET.get('page'))

    all_domains = Domain.objects.filter(is_active=True).order_by('name')

    return render(request, 'public/courses.html', {
        'courses': courses,
        'all_domains': all_domains,
        'selected_domain_slug': selected_domain_slug,
        'query': query,
    })



def announcements_view(request):
    announcement_list = Announcement.objects.public_active()
    paginator = Paginator(announcement_list, 10)
    announcements = paginator.get_page(request.GET.get('page'))

    return render(request, 'public/announcements.html', {'announcements': announcements,})