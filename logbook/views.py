"""
SIWES Logbook Manager — Views
=================================
Sections:
  1. Helpers
  2. Landing
  3. Authentication  (signup, verify, resend, login, logout)
  4. Password Reset  (forgot, reset)
  5. Dashboard
  6. Activities      (list, detail, add, edit, delete)
  7. Reports         (weekly, monthly, pdf)
  8. Profile
"""

import os
import secrets
import string
import csv
from collections import defaultdict
from datetime import timedelta
from functools import wraps

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import (
    authenticate, login, logout,
    update_session_auth_hash,
)
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.http import HttpResponse
from django.db.models import Q
from django.views.decorators.cache import never_cache

from .models import (
    DailyActivity,
    UserProfile,
    SchoolSupervisor,
    IndustrySupervisor,
    EmailVerification,
)


# ══════════════════════════════════════════════════════════════════════════════
# 1. HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _generate_otp():
    return ''.join(secrets.choice(string.digits) for _ in range(6))


def _send_verification_email(user, code):
    subject = "Verify your SIWES Logbook account"
    plain = (
        f"Hello {user.first_name or 'there'},\n\n"
        f"Welcome to SIWES Logbook Manager.\n\n"
        f"Your verification code is: {code}\n"
        f"Enter this code in the app to verify your email address.\n"
        f"This code expires in 30 minutes.\n\n"
        f"If you did not create an account, you can safely ignore this email.\n\n"
        f"— SIWES Logbook Manager"
    )
    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background:#f5f3ff; color:#111827; padding:24px;">
        <div style="max-width:600px; margin:0 auto; background:#ffffff; border-radius:16px; padding:32px; border:1px solid #e5e7eb;">
          <h2 style="margin:0 0 12px; color:#4c1d95;">Welcome to SIWES Logbook Manager</h2>
          <p>Hello {user.first_name or 'there'},</p>
          <p>Thank you for creating your account. Use the code below to verify your email address.</p>
          <div style="margin:24px 0; padding:20px; border-radius:12px; background:#f3e8ff; text-align:center; font-size:32px; letter-spacing:8px; font-weight:bold; color:#4c1d95;">{code}</div>
          <p>This code expires in 30 minutes.</p>
          <p>If you did not create this account, you can safely ignore this email.</p>
          <p style="margin-top:20px; color:#6b7280;">— SIWES Logbook Manager</p>
        </div>
      </body>
    </html>
    """
    from django.core.mail import EmailMultiAlternatives
    email = EmailMultiAlternatives(
        subject,
        plain,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
    )
    email.attach_alternative(html, "text/html")
    email.send(fail_silently=False)


def _send_reset_email(user, code):
    subject = "Reset your SIWES Logbook password"
    plain = (
        f"Hello {user.first_name or 'there'},\n\n"
        f"Your password reset code is: {code}\n"
        f"Enter this code in the app to reset your password.\n"
        f"This code expires in 30 minutes.\n\n"
        f"If you did not request a reset, you can ignore this email.\n\n"
        f"— SIWES Logbook Manager"
    )
    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background:#f5f3ff; color:#111827; padding:24px;">
        <div style="max-width:600px; margin:0 auto; background:#ffffff; border-radius:16px; padding:32px; border:1px solid #e5e7eb;">
          <h2 style="margin:0 0 12px; color:#4c1d95;">Password reset request</h2>
          <p>Hello {user.first_name or 'there'},</p>
          <p>Use the code below to reset your SIWES Logbook password.</p>
          <div style="margin:24px 0; padding:20px; border-radius:12px; background:#f3e8ff; text-align:center; font-size:32px; letter-spacing:8px; font-weight:bold; color:#4c1d95;">{code}</div>
          <p>This code expires in 30 minutes.</p>
          <p>If you did not request a password reset, you can ignore this email.</p>
          <p style="margin-top:20px; color:#6b7280;">— SIWES Logbook Manager</p>
        </div>
      </body>
    </html>
    """
    from django.core.mail import EmailMultiAlternatives
    email = EmailMultiAlternatives(
        subject,
        plain,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
    )
    email.attach_alternative(html, "text/html")
    email.send(fail_silently=False)


def _ensure_profiles(user):
    """Create related profile records if they don't already exist."""
    UserProfile.objects.get_or_create(user=user)
    SchoolSupervisor.objects.get_or_create(user=user)
    IndustrySupervisor.objects.get_or_create(user=user)


def get_user_role(user):
    profile = getattr(user, 'profile', None)
    if profile is None:
        return UserProfile.ROLE_STUDENT
    return profile.role or UserProfile.ROLE_STUDENT


def role_required(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            _ensure_profiles(request.user)
            if request.user.profile.role not in allowed_roles:
                messages.error(request, 'You do not have access to this page.')
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


ALLOWED_IMAGE_EXT = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
ALLOWED_ATTACH_EXT = ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.doc', '.docx']


# ══════════════════════════════════════════════════════════════════════════════
# 2. LANDING PAGE
# ══════════════════════════════════════════════════════════════════════════════

def landing(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'logbook/landing.html')


# ══════════════════════════════════════════════════════════════════════════════
# 3. AUTHENTICATION
# ══════════════════════════════════════════════════════════════════════════════

# ── Sign Up ───────────────────────────────────────────────────────────────────

def signup(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == "POST":
        first_name  = request.POST.get("first_name", "").strip()
        last_name   = request.POST.get("last_name", "").strip()
        email       = request.POST.get("email", "").strip().lower()
        password    = request.POST.get("password", "")
        password2   = request.POST.get("password2", "")
        role        = request.POST.get("role", UserProfile.ROLE_STUDENT).strip().lower()

        errors = []

        if not first_name:
            errors.append("First name is required.")
        if not last_name:
            errors.append("Last name is required.")
        if not email:
            errors.append("Email address is required.")
        elif "@" not in email or "." not in email.split("@")[-1]:
            errors.append("Please enter a valid email address.")
        if not password:
            errors.append("Password is required.")
        elif len(password) < 8:
            errors.append("Password must be at least 8 characters long.")
        elif password.isdigit():
            errors.append("Password cannot be entirely numeric.")
        if password and password2 and password != password2:
            errors.append("Passwords do not match.")
        if role not in {UserProfile.ROLE_STUDENT, UserProfile.ROLE_SUPERVISOR}:
            errors.append("You can only register as a student or supervisor.")

        if not errors and User.objects.filter(email__iexact=email).exists():
            errors.append("An account with this email already exists.")

        if errors:
            for err in errors:
                messages.error(request, err)
            return render(request, 'logbook/signup.html', {
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'role': role,
            })

        # Create inactive user (email as username for uniqueness)
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )
        user.is_active = False
        user.save()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = role
        profile.save()
        _ensure_profiles(user)

        # Generate and store OTP
        code = _generate_otp()
        EmailVerification.objects.create(
            user=user,
            code=code,
            type=EmailVerification.TYPE_VERIFY,
        )

        try:
            _send_verification_email(user, code)
        except Exception:
            user.delete()
            messages.error(
                request,
                "Could not send the verification email. Please try again later."
            )
            return render(request, 'logbook/signup.html', {
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
            })

        request.session['pending_verify_email'] = email
        messages.success(
            request,
            "Account created! We sent a 6-digit verification code to your email."
        )
        return redirect('verify_email')

    return render(request, 'logbook/signup.html')


# ── Verify Email ──────────────────────────────────────────────────────────────

def verify_email(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    pending_email = request.session.get('pending_verify_email', '')

    if request.method == "POST":
        code         = request.POST.get("code", "").strip()
        email_input  = request.POST.get("email", pending_email).strip().lower()

        # Find the user
        try:
            user = User.objects.get(email__iexact=email_input)
        except User.DoesNotExist:
            messages.error(request, "No account found for that email address.")
            return render(request, 'logbook/verify_email.html', {'email': email_input})

        if user.is_active:
            messages.info(request, "Your email is already verified. Please log in.")
            return redirect('login')

        verification = (
            EmailVerification.objects
            .filter(user=user, code=code, type=EmailVerification.TYPE_VERIFY, is_used=False)
            .order_by('-created_at')
            .first()
        )

        if not verification:
            messages.error(request, "Invalid verification code. Please check and try again.")
            return render(request, 'logbook/verify_email.html', {'email': email_input})

        if verification.is_expired():
            messages.error(
                request,
                "This verification code has expired. Click 'Resend Code' to get a new one."
            )
            return render(request, 'logbook/verify_email.html', {'email': email_input})

        # Mark code used and activate user
        verification.is_used = True
        verification.save()

        user.is_active = True
        user.save()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.email_verified = True
        profile.save()

        request.session.pop('pending_verify_email', None)
        messages.success(request, "🎉 Email verified successfully! You can now log in.")
        return redirect('login')

    return render(request, 'logbook/verify_email.html', {'email': pending_email})


# ── Resend Verification Code ──────────────────────────────────────────────────

def resend_verification(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()

        try:
            user = User.objects.get(email__iexact=email, is_active=False)
        except User.DoesNotExist:
            # Don't reveal whether account exists
            messages.info(
                request,
                "If that email is registered and unverified, a new code has been sent."
            )
            return redirect('verify_email')

        # Rate limit: 60-second cooldown
        last = (
            EmailVerification.objects
            .filter(user=user, type=EmailVerification.TYPE_VERIFY)
            .order_by('-created_at')
            .first()
        )
        if last:
            secs = (timezone.now() - last.created_at).total_seconds()
            if secs < 60:
                wait = int(60 - secs)
                messages.warning(
                    request,
                    f"Please wait {wait} second(s) before requesting another code."
                )
                return render(request, 'logbook/verify_email.html', {'email': email})

        code = _generate_otp()
        EmailVerification.objects.create(
            user=user, code=code, type=EmailVerification.TYPE_VERIFY
        )

        try:
            _send_verification_email(user, code)
            messages.success(request, "A new verification code has been sent to your email.")
        except Exception:
            messages.error(request, "Failed to send email. Please try again later.")

        request.session['pending_verify_email'] = email

    return redirect('verify_email')


# ── Login ─────────────────────────────────────────────────────────────────────

@never_cache
def user_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == "POST":
        email    = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")

        user = authenticate(request, username=email, password=password)

        if user is not None:
            if not user.is_active:
                request.session['pending_verify_email'] = email
                messages.warning(
                    request,
                    "Your email is not yet verified. "
                    "Please enter the code we sent you."
                )
                return redirect('verify_email')

            login(request, user)
            _ensure_profiles(user)
            next_url = request.GET.get('next') or 'dashboard'
            messages.success(
                request,
                f"Welcome back, {user.first_name or email}! 👋"
            )
            return redirect(next_url)

        # Check if the account exists but is inactive
        try:
            inactive_user = User.objects.get(email__iexact=email)
            if not inactive_user.is_active:
                request.session['pending_verify_email'] = email
                messages.warning(
                    request,
                    "Please verify your email before logging in."
                )
                return redirect('verify_email')
        except User.DoesNotExist:
            pass

        messages.error(request, "Invalid email or password.")

    return render(request, 'logbook/login.html')


# ── Logout ────────────────────────────────────────────────────────────────────

@never_cache
def user_logout(request):
    logout(request)
    messages.success(request, "You've been logged out. See you soon! 👋")
    return redirect('landing')


# ══════════════════════════════════════════════════════════════════════════════
# 4. PASSWORD RESET
# ══════════════════════════════════════════════════════════════════════════════

def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()

        try:
            user = User.objects.get(email__iexact=email, is_active=True)

            # Rate limit
            last = (
                EmailVerification.objects
                .filter(user=user, type=EmailVerification.TYPE_RESET)
                .order_by('-created_at')
                .first()
            )
            if last:
                secs = (timezone.now() - last.created_at).total_seconds()
                if secs < 60:
                    wait = int(60 - secs)
                    messages.warning(
                        request,
                        f"Please wait {wait} second(s) before requesting another reset."
                    )
                    return render(request, 'logbook/forgot_password.html')

            code = _generate_otp()
            EmailVerification.objects.create(
                user=user, code=code, type=EmailVerification.TYPE_RESET
            )
            _send_reset_email(user, code)

        except User.DoesNotExist:
            pass  # Anti-enumeration: always show the same message
        except Exception:
            pass

        # Always the same response
        messages.success(
            request,
            "If an account with that email exists, a reset code has been sent."
        )
        request.session['pending_reset_email'] = email
        return redirect('reset_password')

    return render(request, 'logbook/forgot_password.html')


def reset_password(request):
    pending_email = request.session.get('pending_reset_email', '')

    if request.method == "POST":
        email_input = request.POST.get("email", pending_email).strip().lower()
        code        = request.POST.get("code", "").strip()
        password    = request.POST.get("password", "")
        password2   = request.POST.get("password2", "")

        errors = []
        if len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        if password.isdigit():
            errors.append("Password cannot be entirely numeric.")
        if password != password2:
            errors.append("Passwords do not match.")

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'logbook/reset_password.html', {'email': email_input})

        try:
            user = User.objects.get(email__iexact=email_input, is_active=True)
        except User.DoesNotExist:
            messages.error(request, "Invalid request. Please start again.")
            return redirect('forgot_password')

        verification = (
            EmailVerification.objects
            .filter(user=user, code=code, type=EmailVerification.TYPE_RESET, is_used=False)
            .order_by('-created_at')
            .first()
        )

        if not verification:
            messages.error(request, "Invalid reset code. Please check and try again.")
            return render(request, 'logbook/reset_password.html', {'email': email_input})

        if verification.is_expired():
            messages.error(
                request,
                "This reset code has expired. Please request a new one."
            )
            return redirect('forgot_password')

        verification.is_used = True
        verification.save()

        user.set_password(password)
        user.save()

        request.session.pop('pending_reset_email', None)
        messages.success(
            request,
            "✅ Password reset successfully! Log in with your new password."
        )
        return redirect('login')

    return render(request, 'logbook/reset_password.html', {'email': pending_email})


# ══════════════════════════════════════════════════════════════════════════════
# 5. DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

@role_required(UserProfile.ROLE_STUDENT)
@never_cache
def student_dashboard(request):
    return _render_dashboard(request, 'student')


@role_required(UserProfile.ROLE_SUPERVISOR)
@never_cache
def supervisor_dashboard(request):
    students = User.objects.filter(
        profile__assigned_supervisor=request.user,
        profile__role=UserProfile.ROLE_STUDENT,
    ).select_related('profile')
    activities = DailyActivity.objects.filter(
        user__profile__assigned_supervisor=request.user
    ).select_related('user').order_by('-date', '-created_at')
    return render(request, 'logbook/supervisor_dashboard.html', {
        'students': students,
        'recent_activities': activities[:10],
        'assigned_students': students.count(),
        'pending_reviews': activities.filter(status=DailyActivity.STATUS_PENDING).count(),
        'approved_activities': activities.filter(status=DailyActivity.STATUS_APPROVED).count(),
        'rejected_activities': activities.filter(status=DailyActivity.STATUS_REJECTED).count(),
    })


@role_required(UserProfile.ROLE_ADMIN)
@never_cache
def admin_dashboard(request):
    return _render_dashboard(request, 'admin')


@role_required(UserProfile.ROLE_SUPERVISOR)
def supervisor_review_activity(request, pk):
    activity = get_object_or_404(
        DailyActivity,
        pk=pk,
        user__profile__assigned_supervisor=request.user,
    )
    if request.method == 'POST':
        status = request.POST.get('status', '').strip().lower()
        comment = request.POST.get('supervisor_comment', '').strip()
        if status not in {
            DailyActivity.STATUS_APPROVED,
            DailyActivity.STATUS_REJECTED,
        }:
            messages.error(request, 'Choose Approve or Reject before submitting.')
        else:
            activity.status = status
            activity.supervisor_comment = comment
            activity.save(update_fields=['status', 'supervisor_comment', 'updated_at'])
            messages.success(request, f'Activity {status}.')
            return redirect('supervisor_dashboard')
    return render(request, 'logbook/supervisor_review.html', {'activity': activity})


@role_required(UserProfile.ROLE_SUPERVISOR)
def supervisor_student_detail(request, pk):
    student = get_object_or_404(
        User,
        pk=pk,
        profile__role=UserProfile.ROLE_STUDENT,
        profile__assigned_supervisor=request.user,
    )
    activities = DailyActivity.objects.filter(user=student)
    return render(request, 'logbook/supervisor_student_detail.html', {
        'student': student,
        'profile': student.profile,
        'activities': activities,
    })


def _render_dashboard(request, role):
    user = request.user
    _ensure_profiles(user)

    profile = user.profile
    today = timezone.now().date()

    this_week_start = today - timedelta(days=today.weekday())
    this_month_start = today.replace(day=1)

    qs = DailyActivity.objects.filter(user=user)
    total = qs.count()
    this_week = qs.filter(date__gte=this_week_start).count()
    this_month = qs.filter(date__gte=this_month_start).count()
    recent = qs[:5]

    context = {
        'profile': profile,
        'school_sup': getattr(user, 'school_supervisor', None),
        'industry_sup': getattr(user, 'industry_supervisor', None),
        'total_activities': total,
        'this_week': this_week,
        'this_month': this_month,
        'weeks_completed': profile.weeks_completed,
        'days_completed': profile.days_completed,
        'days_remaining': profile.days_remaining,
        'total_days': profile.total_days,
        'progress': profile.progress_percent,
        'recent_activities': recent,
        'today': today,
        'dashboard_role': role,
    }
    return render(request, 'logbook/dashboard.html', context)


@login_required
@never_cache
def dashboard(request):
    profile = request.user.profile
    if profile.role == UserProfile.ROLE_SUPERVISOR:
        return redirect('supervisor_dashboard')
    if profile.role == UserProfile.ROLE_ADMIN:
        return redirect('admin_dashboard')
    return redirect('student_dashboard')



# ══════════════════════════════════════════════════════════════════════════════
# 6. ACTIVITIES
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def activity_list(request):
    activities = DailyActivity.objects.filter(user=request.user)

    q         = request.GET.get('q', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to   = request.GET.get('date_to', '').strip()
    month     = request.GET.get('month', '').strip()
    status    = request.GET.get('status', '').strip().lower()

    if q:
        activities = activities.filter(
            Q(title__icontains=q)       |
            Q(activity__icontains=q)    |
            Q(skills_learned__icontains=q) |
            Q(what_learned__icontains=q)
        )
    if date_from:
        activities = activities.filter(date__gte=date_from)
    if date_to:
        activities = activities.filter(date__lte=date_to)
    if month:
        try:
            yr, mo = month.split('-')
            activities = activities.filter(date__year=int(yr), date__month=int(mo))
        except (ValueError, AttributeError):
            pass
    if status in {DailyActivity.STATUS_PENDING, DailyActivity.STATUS_APPROVED, DailyActivity.STATUS_REJECTED}:
        activities = activities.filter(status=status)

    return render(request, 'logbook/activity_list.html', {
        'activities': activities,
        'q':          q,
        'date_from':  date_from,
        'date_to':    date_to,
        'month':      month,
        'status':     status,
        'total':      activities.count(),
    })


@login_required
def activity_detail(request, pk):
    activity = get_object_or_404(DailyActivity, pk=pk)
    if activity.user != request.user:
        messages.error(request, "You don't have permission to view that activity.")
        return redirect('activity_list')
    return render(request, 'logbook/activity_detail.html', {'activity': activity})


@login_required
def add_activity(request):
    if request.user.profile.role != UserProfile.ROLE_STUDENT:
        messages.error(request, 'Only students can add activities.')
        return redirect('dashboard')
    if request.method == "POST":
        date_str   = request.POST.get("date", "").strip()
        day        = request.POST.get("day", "").strip()
        title      = request.POST.get("title", "").strip()
        activity_t = request.POST.get("activity", "").strip()
        skills     = request.POST.get("skills_learned", "").strip()
        challenges = request.POST.get("challenges", "").strip()
        learned    = request.POST.get("what_learned", "").strip()
        sup_cmt    = request.POST.get("supervisor_comment", "").strip()
        attachment = request.FILES.get("attachment")

        errors = []
        if not date_str:
            errors.append("Date is required.")
        if not activity_t:
            errors.append("Activity description is required.")

        if attachment:
            ext = os.path.splitext(attachment.name)[1].lower()
            if ext not in ALLOWED_ATTACH_EXT:
                errors.append(
                    f"Invalid file type '{ext}'. Allowed: {', '.join(ALLOWED_ATTACH_EXT)}"
                )
            if attachment.size > 10 * 1024 * 1024:
                errors.append("File too large. Maximum is 10 MB.")

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'logbook/add_activity.html', {'post': request.POST})

        DailyActivity.objects.create(
            user=request.user,
            date=date_str,
            day=day,
            title=title,
            activity=activity_t,
            skills_learned=skills,
            challenges=challenges,
            what_learned=learned,
            status=DailyActivity.STATUS_PENDING,
            supervisor_comment=sup_cmt,
            attachment=attachment,
        )
        messages.success(request, "✅ Activity added successfully!")
        return redirect('activity_list')

    return render(request, 'logbook/add_activity.html')


@login_required
def edit_activity(request, pk):
    if request.user.profile.role != UserProfile.ROLE_STUDENT:
        messages.error(request, 'Only students can edit activities.')
        return redirect('dashboard')
    activity = get_object_or_404(DailyActivity, pk=pk)
    if activity.user != request.user:
        messages.error(request, "You don't have permission to edit that activity.")
        return redirect('activity_list')

    if activity.status != DailyActivity.STATUS_PENDING:
        messages.warning(request, "Only pending activities can be edited.")
        return redirect('activity_detail', pk=activity.pk)

    if request.method == "POST":
        activity.date             = request.POST.get("date", "")
        activity.day              = request.POST.get("day", "").strip()
        activity.title            = request.POST.get("title", "").strip()
        activity.activity         = request.POST.get("activity", "").strip()
        activity.skills_learned   = request.POST.get("skills_learned", "").strip()
        activity.challenges       = request.POST.get("challenges", "").strip()
        activity.what_learned     = request.POST.get("what_learned", "").strip()
        activity.supervisor_comment = request.POST.get("supervisor_comment", "").strip()

        if not activity.activity:
            messages.error(request, "Activity description is required.")
            return render(request, 'logbook/edit_activity.html', {'activity': activity})

        attachment = request.FILES.get("attachment")
        if attachment:
            ext = os.path.splitext(attachment.name)[1].lower()
            if ext not in ALLOWED_ATTACH_EXT:
                messages.error(request, f"Invalid file type '{ext}'.")
                return render(request, 'logbook/edit_activity.html', {'activity': activity})
            if attachment.size > 10 * 1024 * 1024:
                messages.error(request, "File too large. Maximum is 10 MB.")
                return render(request, 'logbook/edit_activity.html', {'activity': activity})
            activity.attachment = attachment

        activity.save()
        messages.success(request, "✅ Activity updated successfully!")
        return redirect('activity_detail', pk=activity.pk)

    return render(request, 'logbook/edit_activity.html', {'activity': activity})


@login_required
def delete_activity(request, pk):
    activity = get_object_or_404(DailyActivity, pk=pk)
    if activity.user != request.user:
        messages.error(request, "You don't have permission to delete that activity.")
        return redirect('activity_list')

    if request.method == "POST":
        activity.delete()
        messages.success(request, "Activity deleted.")
        return redirect('activity_list')

    return render(request, 'logbook/delete_activity.html', {'activity': activity})


# ══════════════════════════════════════════════════════════════════════════════
# 7. REPORTS
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def weekly_reports(request):
    _ensure_profiles(request.user)
    profile     = request.user.profile
    activities  = DailyActivity.objects.filter(user=request.user).order_by('date')
    siwes_start = profile.siwes_start

    # Group by ISO (year, week)
    raw = defaultdict(list)
    for act in activities:
        iso = act.date.isocalendar()
        raw[(iso[0], iso[1])].append(act)

    weeks = []
    for i, (key, acts) in enumerate(sorted(raw.items()), 1):
        first_day = acts[0].date
        last_day  = acts[-1].date
        if siwes_start and first_day:
            siwes_week = ((first_day - siwes_start).days // 7) + 1
        else:
            siwes_week = i

        skills_list     = [a.skills_learned for a in acts if a.skills_learned]
        challenges_list = [a.challenges     for a in acts if a.challenges]
        learned_list    = [a.what_learned   for a in acts if a.what_learned]

        weeks.append({
            'week_number':    siwes_week,
            'iso_year':       key[0],
            'iso_week':       key[1],
            'activities':     acts,
            'activity_count': len(acts),
            'first_day':      first_day,
            'last_day':       last_day,
            'skills':         skills_list,
            'challenges':     challenges_list,
            'what_learned':   learned_list,
        })

    return render(request, 'logbook/weekly_reports.html', {
        'weeks':   weeks,
        'profile': profile,
    })


@login_required
def monthly_reports(request):
    _ensure_profiles(request.user)
    profile    = request.user.profile
    activities = DailyActivity.objects.filter(user=request.user).order_by('date')

    raw = defaultdict(list)
    for act in activities:
        raw[(act.date.year, act.date.month)].append(act)

    MONTH_NAMES = [
        '', 'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ]

    months = []
    for (yr, mo), acts in sorted(raw.items()):
        # Weekly breakdown within the month
        wk_groups = defaultdict(list)
        for act in acts:
            wk_groups[act.date.isocalendar()[1]].append(act)

        months.append({
            'year':         yr,
            'month':        mo,
            'month_name':   MONTH_NAMES[mo],
            'activities':   acts,
            'count':        len(acts),
            'skills':       [a.skills_learned for a in acts if a.skills_learned],
            'challenges':   [a.challenges     for a in acts if a.challenges],
            'what_learned': [a.what_learned   for a in acts if a.what_learned],
            'weeks':        sorted(wk_groups.items()),
        })

    # Optional: filter to single month
    selected     = request.GET.get('month', '').strip()
    selected_data = None
    if selected:
        try:
            sy, sm = selected.split('-')
            for m in months:
                if m['year'] == int(sy) and m['month'] == int(sm):
                    selected_data = m
                    break
        except (ValueError, AttributeError):
            pass

    return render(request, 'logbook/monthly_reports.html', {
        'months':        months,
        'selected_data': selected_data,
        'selected':      selected,
        'profile':       profile,
    })


@login_required
def export_week(request):
    """Download the logged-in user's activities for one ISO week as CSV."""
    try:
        iso_year = int(request.GET.get('year', ''))
        iso_week = int(request.GET.get('week', ''))
        if not 1 <= iso_week <= 53:
            raise ValueError
    except (TypeError, ValueError):
        messages.error(request, "Choose a valid report week to export.")
        return redirect('weekly_reports')

    activities = DailyActivity.objects.filter(
        user=request.user,
        date__week=iso_week,
        date__iso_year=iso_year,
    ).order_by('date')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        f'attachment; filename="siwes-week-{iso_year}-{iso_week:02d}.csv"'
    )
    writer = csv.writer(response)
    writer.writerow([
        'Date', 'Day', 'Title', 'Activity', 'Skills Learned',
        'Challenges', 'What Learned', 'Status', 'Supervisor Comment',
    ])
    for activity in activities:
        writer.writerow([
            activity.date,
            activity.day,
            activity.title,
            activity.activity,
            activity.skills_learned,
            activity.challenges,
            activity.what_learned,
            activity.get_status_display(),
            activity.supervisor_comment,
        ])
    return response


@login_required
def generate_pdf(request):
    """Generate a professional PDF report for the logged-in user."""
    try:
        from xhtml2pdf import pisa
        from io import BytesIO
        from django.template.loader import render_to_string
    except ImportError:
        messages.error(
            request,
            "PDF generation requires xhtml2pdf. "
            "Run: pip install xhtml2pdf"
        )
        return redirect('dashboard')

    user = request.user
    _ensure_profiles(user)

    profile      = user.profile
    school_sup   = getattr(user, 'school_supervisor', None)
    industry_sup = getattr(user, 'industry_supervisor', None)
    activities   = DailyActivity.objects.filter(user=user).order_by('date')

    # Weekly grouping for PDF
    raw = defaultdict(list)
    for act in activities:
        iso = act.date.isocalendar()
        raw[(iso[0], iso[1])].append(act)

    week_list = []
    for i, (key, acts) in enumerate(sorted(raw.items()), 1):
        first_day = acts[0].date if acts else None
        if profile.siwes_start and first_day:
            siwes_week = ((first_day - profile.siwes_start).days // 7) + 1
        else:
            siwes_week = i
        week_list.append({
            'week_number': siwes_week,
            'activities':  acts,
            'first_day':   first_day,
            'last_day':    acts[-1].date if acts else None,
        })

    context = {
        'user':         user,
        'profile':      profile,
        'school_sup':   school_sup,
        'industry_sup': industry_sup,
        'activities':   activities,
        'weeks':        week_list,
        'generated':    timezone.now().date(),
        'generated_at': timezone.now(),
    }

    html     = render_to_string('logbook/pdf_report.html', context)
    buffer   = BytesIO()
    pdf_file = pisa.CreatePDF(html, dest=buffer)

    if pdf_file.err:
        messages.error(request, "PDF generation failed. Please try again.")
        return redirect('dashboard')

    buffer.seek(0)
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    fname    = f"siwes-report-{(user.get_full_name() or user.email).replace(' ', '-')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{fname}"'
    return response


# ══════════════════════════════════════════════════════════════════════════════
# 8. PROFILE
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def profile_view(request):
    user = request.user
    _ensure_profiles(user)

    prof         = user.profile
    school_sup   = user.school_supervisor
    industry_sup = user.industry_supervisor

    if request.method == "POST":
        section = request.POST.get("section", "personal")

        # ── Personal Info ──────────────────────────────────────────────────
        if section == "personal":
            user.first_name = request.POST.get("first_name", "").strip()
            user.last_name  = request.POST.get("last_name",  "").strip()
            user.save()

            prof.institution  = request.POST.get("institution", "").strip()
            prof.course       = request.POST.get("course", "").strip()
            prof.department   = request.POST.get("department", "").strip()
            prof.matric_number = request.POST.get("matric_number", "").strip()
            prof.siwes_org    = request.POST.get("siwes_org", "").strip()
            prof.bio          = request.POST.get("bio", "").strip()

            ss = request.POST.get("siwes_start", "").strip()
            se = request.POST.get("siwes_end", "").strip()
            prof.siwes_start = ss if ss else None
            prof.siwes_end   = se if se else None

            if 'profile_picture' in request.FILES:
                pic = request.FILES['profile_picture']
                ext = os.path.splitext(pic.name)[1].lower()
                if ext in ALLOWED_IMAGE_EXT:
                    prof.profile_picture = pic
                else:
                    messages.error(request, "Profile picture must be JPG, PNG, GIF, or WebP.")
                    return redirect('profile')

            prof.save()
            messages.success(request, "✅ Profile updated successfully!")

        # ── School Supervisor ──────────────────────────────────────────────
        elif section == "school_supervisor":
            school_sup.full_name   = request.POST.get("ss_full_name",   "").strip()
            school_sup.email       = request.POST.get("ss_email",        "").strip()
            school_sup.phone       = request.POST.get("ss_phone",        "").strip()
            school_sup.department  = request.POST.get("ss_department",   "").strip()
            school_sup.faculty     = request.POST.get("ss_faculty",      "").strip()
            school_sup.institution = request.POST.get("ss_institution",  "").strip()
            school_sup.staff_id    = request.POST.get("ss_staff_id",     "").strip()
            school_sup.position    = request.POST.get("ss_position",     "").strip()

            if 'ss_profile_picture' in request.FILES:
                pic = request.FILES['ss_profile_picture']
                if os.path.splitext(pic.name)[1].lower() in ALLOWED_IMAGE_EXT:
                    school_sup.profile_picture = pic
            if 'ss_signature' in request.FILES:
                sig = request.FILES['ss_signature']
                if os.path.splitext(sig.name)[1].lower() in ALLOWED_IMAGE_EXT:
                    school_sup.signature = sig

            school_sup.save()
            messages.success(request, "✅ School supervisor information updated!")

        # ── Industry Supervisor ────────────────────────────────────────────
        elif section == "industry_supervisor":
            industry_sup.full_name      = request.POST.get("is_full_name",     "").strip()
            industry_sup.email          = request.POST.get("is_email",          "").strip()
            industry_sup.phone          = request.POST.get("is_phone",          "").strip()
            industry_sup.company        = request.POST.get("is_company",        "").strip()
            industry_sup.department     = request.POST.get("is_department",     "").strip()
            industry_sup.job_title      = request.POST.get("is_job_title",      "").strip()
            industry_sup.employee_id    = request.POST.get("is_employee_id",    "").strip()
            industry_sup.office_address = request.POST.get("is_office_address", "").strip()

            if 'is_profile_picture' in request.FILES:
                pic = request.FILES['is_profile_picture']
                if os.path.splitext(pic.name)[1].lower() in ALLOWED_IMAGE_EXT:
                    industry_sup.profile_picture = pic
            if 'is_signature' in request.FILES:
                sig = request.FILES['is_signature']
                if os.path.splitext(sig.name)[1].lower() in ALLOWED_IMAGE_EXT:
                    industry_sup.signature = sig

            industry_sup.save()
            messages.success(request, "✅ Industry supervisor information updated!")

        # ── Change Password ────────────────────────────────────────────────
        elif section == "password":
            old  = request.POST.get("old_password",  "")
            new  = request.POST.get("new_password",  "")
            new2 = request.POST.get("new_password2", "")

            if not user.check_password(old):
                messages.error(request, "Current password is incorrect.")
                return redirect('profile')
            if len(new) < 8:
                messages.error(request, "New password must be at least 8 characters.")
                return redirect('profile')
            if new.isdigit():
                messages.error(request, "Password cannot be entirely numeric.")
                return redirect('profile')
            if new != new2:
                messages.error(request, "New passwords do not match.")
                return redirect('profile')

            user.set_password(new)
            user.save()
            update_session_auth_hash(request, user)
            messages.success(request, "✅ Password changed successfully!")

        return redirect('profile')

    return render(request, 'logbook/profile.html', {
        'prof':         prof,
        'school_sup':   school_sup,
        'industry_sup': industry_sup,
    })