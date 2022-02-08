# Generated by Django 2.2 on 2022-02-08 20:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_dictionaryitems'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderitemsmercadolibre',
            name='xmlsending',
            field=models.TextField(help_text='XML enviado a Pacesetter.', null=True),
        ),
        migrations.AlterField(
            model_name='orderitemsmercadolibre',
            name='xmlresponse',
            field=models.TextField(help_text='XML recibido de Pacesetter', null=True),
        ),
    ]