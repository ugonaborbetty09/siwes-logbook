from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("logbook", "0002_emailverification_industrysupervisor_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="dailyactivity",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("approved", "Approved"),
                    ("rejected", "Rejected"),
                ],
                db_index=True,
                default="pending",
                max_length=20,
                verbose_name="Status",
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="role",
            field=models.CharField(
                choices=[
                    ("student", "Student"),
                    ("supervisor", "Supervisor"),
                    ("admin", "Admin"),
                ],
                db_index=True,
                default="student",
                max_length=20,
            ),
        ),
    ]
