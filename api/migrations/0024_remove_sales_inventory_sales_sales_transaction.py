# Generated by Django 4.0 on 2024-03-08 23:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0023_sales_inventory'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='sales',
            name='inventory',
        ),
        migrations.AddField(
            model_name='sales',
            name='sales_transaction',
            field=models.ManyToManyField(through='api.InventoryTransaction', to='api.Product_Inventory'),
        ),
    ]
