import os
import secrets
from datetime import timedelta

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_verification_expiry():
    return timezone.now() + timedelta(minutes=30)


def generate_otp():
    """Generate a cryptographically secure 6-digit OTP."""
    return ''.join([str(secrets.randbelow(10)) for _ in range(6)])


# ─── User Profile ─────────────────────────────────────────────────────────────

class UserProfile(models.Model):
    ROLE_STUDENT = 'student'
    ROLE_SUPERVISOR = 'supervisor'
    ROLE_ADMIN = 'admin'
    ROLE_CHOICES = [
        (ROLE_STUDENT, 'Student'),
        (ROLE_SUPERVISOR, 'Supervisor'),
        (ROLE_ADMIN, 'Admin'),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='profile'
    )
    assigned_supervisor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='assigned_students',
        null=True,
        blank=True,
        limit_choices_to={'profile__role': ROLE_SUPERVISOR},
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_STUDENT,
        db_index=True,
    )
    profile_picture = models.ImageField(
        upload_to='profiles/', blank=True, null=True
    )
    institution = models.CharField(max_length=200, blank=True, verbose_name="Institution/University")
    course = models.CharField(max_length=200, blank=True, verbose_name="Course")
    department = models.CharField(max_length=200, blank=True, verbose_name="Department")
    matric_number = models.CharField(max_length=50, blank=True, verbose_name="Matric Number")
    siwes_org = models.CharField(
        max_length=200, blank=True, verbose_name="SIWES Organization/Company"
    )
    siwes_start = models.DateField(null=True, blank=True, verbose_name="SIWES Start Date")
    siwes_end = models.DateField(null=True, blank=True, verbose_name="SIWES End Date")
    bio = models.TextField(blank=True)
    email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Profile"

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.email} — Profile"

    # ── Progress calculations ──────────────────────────────────────────────────

    @property
    def progress_percent(self):
        if not self.siwes_start or not self.siwes_end:
            return 0
        today = timezone.now().date()
        total = (self.siwes_end - self.siwes_start).days
        if total <= 0:
            return 0
        elapsed = (today - self.siwes_start).days
        elapsed = max(0, min(elapsed, total))
        return round((elapsed / total) * 100)

    @property
    def days_completed(self):
        if not self.siwes_start:
            return 0
        today = timezone.now().date()
        return max(0, (today - self.siwes_start).days)

    @property
    def days_remaining(self):
        if not self.siwes_end:
            return 0
        today = timezone.now().date()
        return max(0, (self.siwes_end - today).days)

    @property
    def total_days(self):
        if not self.siwes_start or not self.siwes_end:
            return 0
        return max(0, (self.siwes_end - self.siwes_start).days)

    @property
    def weeks_completed(self):
        return self.days_completed // 7


# ─── School Supervisor ────────────────────────────────────────────────────────

class SchoolSupervisor(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='school_supervisor'
    )
    full_name = models.CharField(max_length=200, blank=True, verbose_name="Full Name")
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True, verbose_name="Phone Number")
    department = models.CharField(max_length=200, blank=True)
    faculty = models.CharField(max_length=200, blank=True)
    institution = models.CharField(max_length=200, blank=True)
    staff_id = models.CharField(max_length=100, blank=True, verbose_name="Staff/ID Number")
    position = models.CharField(max_length=200, blank=True)
    signature = models.ImageField(
        upload_to='signatures/', blank=True, null=True,
        verbose_name="Signature (image)"
    )
    profile_picture = models.ImageField(
        upload_to='supervisor_pics/', blank=True, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "School Supervisor"

    def __str__(self):
        return f"School Supervisor — {self.user.get_full_name() or self.user.email}"


# ─── Industry Supervisor ──────────────────────────────────────────────────────

class IndustrySupervisor(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='industry_supervisor'
    )
    full_name = models.CharField(max_length=200, blank=True, verbose_name="Full Name")
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True, verbose_name="Phone Number")
    company = models.CharField(
        max_length=200, blank=True, verbose_name="Company/Organization"
    )
    department = models.CharField(
        max_length=200, blank=True, verbose_name="Department/Unit"
    )
    job_title = models.CharField(
        max_length=200, blank=True, verbose_name="Job Title/Position"
    )
    employee_id = models.CharField(
        max_length=100, blank=True, verbose_name="Employee ID (optional)"
    )
    office_address = models.TextField(blank=True, verbose_name="Office Address (optional)")
    signature = models.ImageField(
        upload_to='signatures/', blank=True, null=True,
        verbose_name="Signature (image)"
    )
    profile_picture = models.ImageField(
        upload_to='supervisor_pics/', blank=True, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Industry Supervisor"

    def __str__(self):
        return f"Industry Supervisor — {self.user.get_full_name() or self.user.email}"


# ─── Email Verification / Password Reset OTP ──────────────────────────────────

class EmailVerification(models.Model):
    TYPE_VERIFY = 'verify'
    TYPE_RESET = 'reset'
    TYPE_CHOICES = [
        (TYPE_VERIFY, 'Email Verification'),
        (TYPE_RESET, 'Password Reset'),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='verifications'
    )
    code = models.CharField(max_length=6, default=generate_otp)
    type = models.CharField(
        max_length=10, choices=TYPE_CHOICES, default=TYPE_VERIFY
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=get_verification_expiry)
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Email Verification"

    def is_expired(self):
        return timezone.now() > self.expires_at

    def is_valid(self):
        return not self.is_used and not self.is_expired()

    def __str__(self):
        return f"{self.get_type_display()} code for {self.user.email}"


# ─── Daily Activity ───────────────────────────────────────────────────────────

ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.doc', '.docx']


class DailyActivity(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='activities'
    )
    date = models.DateField(db_index=True)
    day = models.CharField(max_length=20, blank=True)
    title = models.CharField(
        max_length=300, blank=True, verbose_name="Activity Title/Summary"
    )
    activity = models.TextField(verbose_name="Activity Description")
    skills_learned = models.TextField(
        blank=True, verbose_name="Skills / Technologies Used"
    )
    challenges = models.TextField(blank=True, verbose_name="Challenges Encountered")
    what_learned = models.TextField(blank=True, verbose_name="What I Learned")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
        verbose_name="Status",
    )
    supervisor_comment = models.TextField(blank=True, verbose_name="Supervisor Comment")
    attachment = models.FileField(
        upload_to='attachments/', blank=True, null=True,
        verbose_name="Attachment (image/PDF/doc)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['user', '-date']),
        ]
        verbose_name = "Daily Activity"
        verbose_name_plural = "Daily Activities"

    def __str__(self):
        label = self.title or self.activity[:50]
        return f"{self.date} — {label}"

    @property
    def week_number(self):
        return self.date.isocalendar()[1]

    @property
    def iso_year(self):
        return self.date.isocalendar()[0]

    def attachment_is_image(self):
        if not self.attachment:
            return False
        ext = os.path.splitext(self.attachment.name)[1].lower()
        return ext in ['.jpg', '.jpeg', '.png', '.gif']