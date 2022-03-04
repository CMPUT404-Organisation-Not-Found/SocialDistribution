# Generated by Django 3.1.6 on 2022-03-03 23:45

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0010_auto_20220302_2305'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='author',
            name='profileImage',
        ),
        migrations.AddField(
            model_name='post',
            name='categories',
            field=models.TextField(default=111),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='post',
            name='contentType',
            field=models.CharField(default=111, max_length=200),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='post',
            name='count',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='post',
            name='post_image',
            field=models.ImageField(blank=True, null=True, upload_to='images/'),
        ),
        migrations.AlterField(
            model_name='post',
            name='id',
            field=models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False, unique=True),
        ),
        migrations.DeleteModel(
            name='Followers',
        ),
    ]