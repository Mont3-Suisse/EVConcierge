from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('property_manager', '0004_alter_order_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='DeviceToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(max_length=512, unique=True)),
                ('platform', models.CharField(
                    choices=[('android', 'Android'), ('ios', 'iOS'), ('web', 'Web')],
                    default='android', max_length=10)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('booking', models.ForeignKey(
                    on_delete=models.deletion.CASCADE,
                    related_name='device_tokens',
                    to='property_manager.booking')),
            ],
            options={
                'ordering': ['-updated_at'],
                'indexes': [models.Index(fields=['booking', 'is_active'], name='property_ma_booking_db2c74_idx')],
            },
        ),
    ]
