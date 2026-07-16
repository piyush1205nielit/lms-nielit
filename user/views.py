from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

from accounts.models import User
from .models import LearnerProfile, PasswordResetOTP
from .utils import generate_enrollment_number

from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import update_session_auth_hash

from .forms import *
from .models import PasswordResetOTP
from .utils import generate_otp


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




# ── Self-service profile & password ─────────────────────────

@login_required(login_url='user:login')
def profile_edit_view(request):
    profile = request.user.learner_profile
    form = ProfileEditForm(request.POST or None, request.FILES or None, instance=profile)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Profile updated successfully.")
        return redirect('user_dashboard:home')

    return render(request, 'user/profile_edit.html', {'form': form, 'active_page': 'profile'})


@login_required(login_url='user:login')
def change_password_view(request):
    form = UserPasswordChangeForm(user=request.user, data=request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)   # keeps the user logged in after password change
        messages.success(request, "Password changed successfully.")
        return redirect('user_dashboard:home')

    return render(request, 'user/change_password.html', {'form': form, 'active_page': 'profile'})


# ── Forgot password — Step 1: identity verification ─────────

def forgot_password_verify_view(request):
    form = ForgotPasswordVerifyForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email'].lower().strip()
        contact = form.cleaned_data['contact'].strip()
        dob = form.cleaned_data['date_of_birth']

        try:
            user = User.objects.get(email=email, contact=contact, role=User.Role.USER)
            profile = user.learner_profile
            if profile.date_of_birth != dob:
                raise User.DoesNotExist
        except (User.DoesNotExist, LearnerProfile.DoesNotExist):
            messages.error(request, "We couldn't verify your details. Please check and try again.")
            return render(request, 'user/forgot_password_verify.html', {'form': form})

        otp_code = generate_otp()
        PasswordResetOTP.objects.create(user=user, otp_code=otp_code)

        send_mail(
            subject="Your NIELIT LMS Password Reset Code",
            message=(
                f"Your OTP for password reset is: {otp_code}\n\n"
                f"This code is valid for 10 minutes. If you did not request this, please ignore this email."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        request.session['password_reset_user_id'] = str(user.id)
        messages.success(request, f"An OTP has been sent to {user.email}.")
        return redirect('user:forgot_password_otp')

    return render(request, 'user/forgot_password_verify.html', {'form': form})


# ── Forgot password — Step 2: OTP verification ───────────────

def forgot_password_otp_view(request):
    user_id = request.session.get('password_reset_user_id')
    if not user_id:
        messages.error(request, "Please verify your details first.")
        return redirect('user:forgot_password')

    form = OTPVerifyForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        entered_otp = form.cleaned_data['otp_code']
        otp_record = PasswordResetOTP.objects.filter(
            user_id=user_id, is_used=False
        ).order_by('-created_at').first()

        if not otp_record or otp_record.is_expired():
            messages.error(request, "This OTP has expired. Please request a new one.")
            return redirect('user:forgot_password')

        if otp_record.otp_code != entered_otp:
            messages.error(request, "Incorrect OTP. Please try again.")
            return render(request, 'user/forgot_password_otp.html', {'form': form})

        otp_record.is_used = True
        otp_record.save(update_fields=['is_used'])

        request.session['password_reset_verified'] = True
        return redirect('user:reset_password')

    return render(request, 'user/forgot_password_otp.html', {'form': form})


def forgot_password_resend_otp_view(request):
    user_id = request.session.get('password_reset_user_id')
    if not user_id:
        return redirect('user:forgot_password')

    user = get_object_or_404(User, id=user_id)
    otp_code = generate_otp()
    PasswordResetOTP.objects.create(user=user, otp_code=otp_code)

    send_mail(
        subject="Your NIELIT LMS Password Reset Code",
        message=f"Your new OTP for password reset is: {otp_code}\n\nThis code is valid for 10 minutes.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
    messages.success(request, "A new OTP has been sent to your email.")
    return redirect('user:forgot_password_otp')


# ── Forgot password — Step 3: set new password ────────────────

def reset_password_view(request):
    user_id = request.session.get('password_reset_user_id')
    verified = request.session.get('password_reset_verified')

    if not user_id or not verified:
        messages.error(request, "Please complete OTP verification first.")
        return redirect('user:forgot_password')

    form = SetNewPasswordForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = get_object_or_404(User, id=user_id)
        user.set_password(form.cleaned_data['new_password1'])
        user.save(update_fields=['password'])

        del request.session['password_reset_user_id']
        del request.session['password_reset_verified']

        messages.success(request, "Password reset successful. Please log in with your new password.")
        return redirect('user:login')

    return render(request, 'user/reset_password.html', {'form': form})