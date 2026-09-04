from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("logbook", "0003_dailyactivity_status_userprofile_role"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="assigned_supervisor",
            field=models.ForeignKey(
                blank=True,
                limit_choices_to={"profile__role": "supervisor"},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="assigned_students",
                to="auth.user",
            ),
        ),
    ]
