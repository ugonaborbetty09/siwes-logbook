from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User


class EmailBackend(ModelBackend):
    """
    Authenticate using email address instead of username.
    Works alongside Django's default ModelBackend.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        # Accept either 'username' or 'email' keyword
        email = kwargs.get('email', username)
        if not email or not password:
            return None

        email = email.strip().lower()

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            # Run the default password hasher to prevent timing attacks
            User().set_password(password)
            return None
        except User.MultipleObjectsReturned:
            # Should not happen due to unique email constraint, but guard it
            user = User.objects.filter(email__iexact=email).order_by('id').first()
            if not user:
                return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
