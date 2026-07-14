from django.shortcuts import render


from django.shortcuts import render
from django.core.paginator import Paginator
from course.models import Course


def home_view(request):
    featured_courses = Course.objects.filter(
        status=Course.Status.ACTIVE,
        is_featured=True
    )[:8]
    return render(request, 'public/home.html', {
        'featured_courses': featured_courses,
    })


def courses_view(request):
    course_list = Course.objects.filter(status=Course.Status.ACTIVE).order_by('-published_date')

    paginator = Paginator(course_list, 12)
    page_number = request.GET.get('page')
    courses = paginator.get_page(page_number)

    return render(request, 'public/courses.html', {
        'courses': courses,
    })


# def announcements_view(request):
#     return render(request, 'public/announcements.html')


# def centres_view(request):
#     return render(request, 'public/centres.html')