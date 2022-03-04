# Generated by Django 3.1.6 on 2022-03-04 07:36

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='FollowerCount',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('follower', models.CharField(max_length=100)),
                ('user', models.CharField(max_length=100)),
            ],
        ),
        migrations.RemoveField(
            model_name='like',
            name='content',
        ),
        migrations.RemoveField(
            model_name='like',
            name='summary',
        ),
        migrations.RemoveField(
            model_name='post',
            name='comments',
        ),
        migrations.RemoveField(
            model_name='post',
            name='commentsSrc',
        ),
        migrations.RemoveField(
            model_name='post',
            name='unlisted',
        ),
        migrations.RemoveField(
            model_name='post',
            name='visiblity',
        ),
        migrations.AddField(
            model_name='comment',
            name='post',
            field=models.ForeignKey(default=True, on_delete=django.db.models.deletion.CASCADE, to='myapp.post'),
        ),
        migrations.AddField(
            model_name='post',
            name='likes',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='post',
            name='post_image',
            field=models.ImageField(blank=True, null=True, upload_to='images/'),
        ),
        migrations.AddField(
            model_name='post',
            name='visibility',
            field=models.CharField(choices=[('PUBLIC', 'Public'), ('FRIENDS', 'Friends'), ('PRIVATE', 'Specific friend')], default='PUBLIC', max_length=7),
        ),
        migrations.AlterField(
            model_name='author',
            name='displayName',
            field=models.CharField(max_length=200, null=True),
        ),
        migrations.AlterField(
            model_name='author',
            name='github',
            field=models.CharField(max_length=200, null=True),
        ),
        migrations.AlterField(
            model_name='author',
            name='profileImage',
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        migrations.AlterField(
            model_name='comment',
            name='id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True),
        ),
        migrations.AlterField(
            model_name='comment',
            name='published',
            field=models.DateTimeField(blank=True, default=django.utils.timezone.localtime, editable=False),
        ),
        migrations.AlterField(
            model_name='inbox',
            name='author',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='myapp.author'),
        ),
        migrations.AlterField(
            model_name='liked',
            name='items',
            field=models.ManyToManyField(to='myapp.Like'),
        ),
        migrations.AlterField(
            model_name='post',
            name='contentType',
            field=models.CharField(choices=[('md', 'text/markdown'), ('plain', 'text/plain'), ('app', 'application/base64'), ('png', 'image/png;base64'), ('jpeg', 'image/jpeg;base64')], default='md', max_length=30),
        ),
        migrations.AlterField(
            model_name='post',
            name='count',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='post',
            name='id',
            field=models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False, unique=True),
        ),
        migrations.AlterField(
            model_name='post',
            name='published',
            field=models.DateTimeField(blank=True, default=django.utils.timezone.localtime, editable=False),
        ),
        migrations.DeleteModel(
            name='Followers',
        ),
    ]