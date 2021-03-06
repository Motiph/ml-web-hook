# Generated by Django 2.2 on 2021-12-29 00:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_auto_20211225_2104'),
    ]

    operations = [
        migrations.CreateModel(
            name='DictionaryItems',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('idMercadoLibre', models.CharField(max_length=200, verbose_name='ID de Mercado Libre')),
                ('long_brand', models.CharField(max_length=200, verbose_name='Marca (Nombre Largo)')),
                ('short_brand', models.CharField(max_length=200, verbose_name='Marca (Nombre corto)')),
                ('number_part', models.CharField(blank=True, max_length=200, null=True, verbose_name='Número de parte')),
                ('model', models.CharField(blank=True, max_length=200, null=True, verbose_name='Modelo')),
                ('stock', models.IntegerField(verbose_name='Stock disponible')),
                ('price', models.DecimalField(decimal_places=2, default=0.01, max_digits=9, verbose_name='Precio')),
            ],
        ),
    ]
