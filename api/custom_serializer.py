from rest_framework import serializers
from .models import *


class CustomSupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ['id', 'company_name']

class CustomProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['product_name']

class InventoryTransactionSerializer(serializers.ModelSerializer):
    # sales_pk = serializers.PrimaryKeyRelatedField(queryset=Sales.objects.all())
    # inventory_pk = serializers.PrimaryKeyRelatedField(queryset=Product_Inventory.objects.all())

    class Meta:
        model: InventoryTransaction
        fields = ['pk']


# For Sales Serializer
class CustomSalesSerializerProperty(serializers.ModelSerializer):
    supplier = CustomSupplierSerializer()
    product_name = CustomProductSerializer()
    pk = InventoryTransactionSerializer()

    class Meta:
        model = Product_Inventory
        fields = ['supplier', 'product_name', 'pk']
