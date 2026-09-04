from django.urls import path
from . import views

urlpatterns = [

    # ── Public ────────────────────────────────────────────────────────────────
    path("",                    views.landing,            name="landing"),

    # ── Authentication ────────────────────────────────────────────────────────
    path("signup/",             views.signup,             name="signup"),
    path("verify-email/",       views.verify_email,       name="verify_email"),
    path("resend-verification/",views.resend_verification,name="resend_verification"),
    path("login/",              views.user_login,         name="login"),
    path("logout/",             views.user_logout,        name="logout"),

    # ── Password Reset ────────────────────────────────────────────────────────
    path("forgot-password/",    views.forgot_password,    name="forgot_password"),
    path("reset-password/",     views.reset_password,     name="reset_password"),

    # ── Dashboard ─────────────────────────────────────────────────────────────
    path("dashboard/",          views.dashboard,          name="dashboard"),
    path("dashboard/student/",  views.student_dashboard,  name="student_dashboard"),
    path("dashboard/supervisor/", views.supervisor_dashboard, name="supervisor_dashboard"),
    path("dashboard/admin/",    views.admin_dashboard,    name="admin_dashboard"),
    path("supervisor/review/<int:pk>/", views.supervisor_review_activity, name="supervisor_review_activity"),
    path("supervisor/students/<int:pk>/", views.supervisor_student_detail, name="supervisor_student_detail"),

    # ── Activities ────────────────────────────────────────────────────────────
    path("activities/",             views.activity_list,   name="activity_list"),
    path("activities/add/",         views.add_activity,    name="add_activity"),
    path("activities/<int:pk>/",    views.activity_detail, name="activity_detail"),
    path("activities/<int:pk>/edit/",   views.edit_activity,   name="edit_activity"),
    path("activities/<int:pk>/delete/", views.delete_activity, name="delete_activity"),

    # ── Reports ───────────────────────────────────────────────────────────────
    path("reports/weekly/",  views.weekly_reports,  name="weekly_reports"),
    path("reports/monthly/", views.monthly_reports, name="monthly_reports"),
    path("reports/weekly/export/", views.export_week, name="export_week"),
    path("reports/pdf/",     views.generate_pdf,    name="generate_pdf"),

    # ── Profile ───────────────────────────────────────────────────────────────
    path("profile/", views.profile_view, name="profile"),
]