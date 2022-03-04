# Generated by Django 3.1.6 on 2022-03-04 00:30

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0006_merge_20220225_1539'),
    ]

    operations = [
        migrations.AddField(
            model_name='comment',
            name='author',
            field=models.ForeignKey(default='', on_delete=django.db.models.deletion.CASCADE, to='myapp.author'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='post',
            name='author',
            field=models.ForeignKey(default='', on_delete=django.db.models.deletion.CASCADE, to='myapp.author'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='post',
            name='categories',
            field=models.TextField(default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='post',
            name='contentType',
            field=models.CharField(default='', max_length=200),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='post',
            name='count',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='author',
            name='github',
            field=models.TextField(default='https://github.com/KianaLiu1', null=True),
        ),
        migrations.AlterField(
            model_name='author',
            name='profileImage',
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        migrations.AlterField(
            model_name='comment',
            name='post',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='myapp.post'),
        ),
        migrations.AlterField(
            model_name='inbox',
            name='author',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='myapp.author'),
        ),
    ]