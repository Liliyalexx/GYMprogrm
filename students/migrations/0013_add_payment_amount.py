from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0012_add_payment_reminder_sent_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='payment_amount',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Amount charged per billing period (e.g. 150.00)', max_digits=8, null=True),
        ),
    ]
