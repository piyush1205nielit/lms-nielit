from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect

from accounts.models import User
from .forms import SignupForm, UserLoginForm, ProfileCompletionForm
from .models import LearnerProfile
from .utils import generate_enrollment_number


def signup_view(request):
    form = SignupForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = User.objects.create_user(
            email=form.cleaned_data['email'],
            contact=form.cleaned_data['contact'],
            password=form.cleaned_data['password1'],
            role=User.Role.USER,
        )
        LearnerProfile.objects.create(
            user=user,
            enrollment_number=generate_enrollment_number(),
        )
        login(request, user, backend='accounts.backends.EmailOrPhoneBackend')
        return redirect('user:complete_profile')

    return render(request, 'user/signup.html', {'form': form})


def user_login_view(request):
    if request.user.is_authenticated and request.user.role == 'user':
        return redirect('user_dashboard:home')

    form = UserLoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        identifier = form.cleaned_data['identifier']
        password = form.cleaned_data['password']
        user = authenticate(request, username=identifier, password=password)

        if user is not None and user.role == 'user':
            login(request, user)
            return redirect('user_dashboard:home')

        messages.error(request, "Invalid credentials.")

    return render(request, 'user/login.html', {'form': form})


def user_logout_view(request):
    logout(request)
    return redirect('user:login')


@login_required(login_url='user:login')
def complete_profile_view(request):
    profile = request.user.learner_profile

    if profile.profile_completed:
        return redirect('user_dashboard:home')

    form = ProfileCompletionForm(
        request.POST or None,
        request.FILES or None,
        instance=profile
    )

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Profile completed successfully. Welcome aboard!")
        return redirect('user_dashboard:home')

    return render(request, 'user/complete_profile.html', {'form': form})