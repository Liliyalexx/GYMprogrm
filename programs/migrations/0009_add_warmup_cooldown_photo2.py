from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('programs', '0008_add_shared_sections_en_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='exerciselibrary',
            name='photo_url_2',
            field=models.URLField(blank=True, help_text='Peak / mid-movement image', max_length=2000),
        ),
        migrations.AddField(
            model_name='programday',
            name='warmup_data',
            field=models.JSONField(blank=True, help_text='List of warm-up exercises [{name, duration, description}]', null=True),
        ),
        migrations.AddField(
            model_name='programday',
            name='cooldown_data',
            field=models.JSONField(blank=True, help_text='List of cool-down stretches [{name, duration, description}]', null=True),
        ),
    ]
