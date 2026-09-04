from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from datetime import date

from .models import DailyActivity, UserProfile

User = get_user_model()


class AuthenticationFlowTests(TestCase):
    def test_signup_creates_user_with_names_and_email(self):
        response = self.client.post(
            reverse('signup'),
            {
                'first_name': 'Betty',
                'last_name': 'Okafor',
                'email': 'betty@example.com',
                'password': 'StrongPass123',
                'password2': 'StrongPass123',
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(email='betty@example.com').exists())
        user = User.objects.get(email='betty@example.com')
        self.assertEqual(user.first_name, 'Betty')
        self.assertEqual(user.last_name, 'Okafor')

    def test_login_requires_verified_email(self):
        user = User.objects.create_user(
            username='demo@example.com',
            email='demo@example.com',
            password='StrongPass123',
            first_name='Demo',
            last_name='User',
            is_active=False,
        )
        response = self.client.post(
            reverse('login'),
            {'email': 'demo@example.com', 'password': 'StrongPass123'},
            follow=True,
        )
        self.assertRedirects(response, reverse('verify_email'))
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_login_with_valid_verified_user(self):
        user = User.objects.create_user(
            username='verified@example.com',
            email='verified@example.com',
            password='StrongPass123',
            first_name='Verified',
            last_name='User',
            is_active=True,
        )
        response = self.client.post(
            reverse('login'),
            {'email': 'verified@example.com', 'password': 'StrongPass123'},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.wsgi_request.user.email, 'verified@example.com')


class RoleAccessTests(TestCase):
    def test_student_cannot_access_supervisor_dashboard(self):
        student = User.objects.create_user(
            username='student@example.com',
            email='student@example.com',
            password='StrongPass123',
            first_name='Student',
            last_name='User',
            is_active=True,
        )
        profile, _ = UserProfile.objects.get_or_create(user=student)
        profile.role = UserProfile.ROLE_STUDENT
        profile.save()

        self.client.force_login(student)
        response = self.client.get(reverse('supervisor_dashboard'))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('dashboard'))

    def test_supervisor_cannot_access_student_dashboard(self):
        supervisor = User.objects.create_user(
            username='supervisor@example.com',
            email='supervisor@example.com',
            password='StrongPass123',
            first_name='Supervisor',
            last_name='User',
            is_active=True,
        )
        profile, _ = UserProfile.objects.get_or_create(user=supervisor)
        profile.role = UserProfile.ROLE_SUPERVISOR
        profile.save()

        self.client.force_login(supervisor)
        response = self.client.get(reverse('student_dashboard'))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('dashboard'))


class ReportExportTests(TestCase):
    def test_week_export_returns_csv_for_logged_in_user(self):
        user = User.objects.create_user(
            username='export@example.com',
            email='export@example.com',
            password='StrongPass123',
            is_active=True,
        )
        UserProfile.objects.create(user=user)
        DailyActivity.objects.create(
            user=user,
            date=date(2026, 9, 2),
            day='Wednesday',
            title='Testing export',
            activity='Created a weekly export.',
        )

        self.client.force_login(user)
        response = self.client.get(
            reverse('export_week'),
            {'year': 2026, 'week': date(2026, 9, 2).isocalendar().week},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('Testing export', response.content.decode())
