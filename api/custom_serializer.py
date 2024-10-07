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

class CustomProductInventorySerializer(serializers.ModelSerializer):
    supplier = CustomSupplierSerializer()
    product_name = CustomProductSerializer()

    class Meta:
        model = Product_Inventory
        fields = ['supplier', 'product_name']
