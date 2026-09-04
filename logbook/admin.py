from django.contrib import admin
from .models import (
    DailyActivity,
    UserProfile,
    SchoolSupervisor,
    IndustrySupervisor,
    EmailVerification,
)


@admin.register(DailyActivity)
class DailyActivityAdmin(admin.ModelAdmin):
    list_display  = ('user', 'date', 'day', 'title', 'status', 'created_at')
    list_filter   = ('date', 'status', 'user')
    search_fields = ('title', 'activity', 'user__email', 'user__first_name')
    ordering      = ('-date',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ('user', 'role', 'assigned_supervisor', 'institution', 'matric_number', 'email_verified', 'created_at')
    list_filter   = ('role', 'email_verified')
    search_fields = ('user__email', 'user__first_name', 'institution', 'assigned_supervisor__email')


@admin.register(SchoolSupervisor)
class SchoolSupervisorAdmin(admin.ModelAdmin):
    list_display  = ('user', 'full_name', 'email', 'institution', 'department')
    search_fields = ('full_name', 'email', 'institution')


@admin.register(IndustrySupervisor)
class IndustrySupervisorAdmin(admin.ModelAdmin):
    list_display  = ('user', 'full_name', 'email', 'company', 'job_title')
    search_fields = ('full_name', 'email', 'company')


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display  = ('user', 'type', 'code', 'created_at', 'expires_at', 'is_used')
    list_filter   = ('type', 'is_used')
    search_fields = ('user__email',)
    ordering      = ('-created_at',)
