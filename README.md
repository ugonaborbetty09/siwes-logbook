# SIWES Logbook Manager

A Django-based SIWES logbook and reporting platform for students, supervisors, and academic coordinators.

## Features

- Student signup and login with email-based authentication
- Email verification for new accounts
- Password reset through secure code-based flow
- Daily activity tracking and uploads
- Weekly and monthly reporting
- PDF report generation
- Supervisor profile handling
- Responsive dashboard and dark mode

## Local development

1. Create and activate a virtual environment.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Copy the sample environment file:

   ```bash
   copy .env.example .env
   ```

4. Update the values in `.env` for your local configuration.
5. Run database migrations:

   ```bash
   python manage.py migrate
   ```

6. Create a superuser:

   ```bash
   python manage.py createsuperuser
   ```

7. Start the app:

   ```bash
   python manage.py runserver
   ```

## Testing

```bash
python manage.py test
```

## Production deployment

This project is prepared for deployment on Render using PostgreSQL and SMTP email delivery.

### Required environment variables

- `SECRET_KEY`
- `DEBUG`
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`
- `DATABASE_URL`
- `EMAIL_BACKEND`
- `EMAIL_HOST`
- `EMAIL_PORT`
- `EMAIL_USE_TLS`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`
- `DEFAULT_FROM_EMAIL`

### Render setup

1. Push the repository to GitHub.
2. Import the project into Render.
3. Connect a PostgreSQL database.
4. Add the environment variables from `.env.example`.
5. Deploy the web service.
6. Configure your custom domain and HTTPS in Render.

## Security notes

- Never commit `.env` or secrets to GitHub.
- `DEBUG` should be `False` in production.
- Use HTTPS and secure cookies behind a reverse proxy or managed hosting platform.

## License

This project is intended for educational and institutional use.
