# Generated by Django 3.2.10 on 2022-03-31 07:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ServerSetting',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(default='Social Distribution Settings', max_length=200)),
                ('allow_independent_user_login', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'server setting',
                'verbose_name_plural': 'server settings',
            },
        ),
    ]
