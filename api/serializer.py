from rest_framework import serializers
from .models import *

class MaterialsSerializer(serializers.ModelSerializer):
    material_unit_name = serializers.CharField(source='material_unit.unit_name')
    material_unit_abbv = serializers.CharField(source='material_unit.unit_abbv')

    class Meta:
        model = RawMaterials
        fields = (
            'material_name',
            'material_min_stock',
            'material_unit_name',
            'material_unit_abbv',
            'material_note',
            'date_created',
        )

class ProductSerializer(serializers.ModelSerializer):
    product_unit_name = serializers.CharField(source='product_unit.unit_name')
    product_unit_abbv = serializers.CharField(source='product_unit.unit_abbv')

    class Meta:
        model = Product
        fields = (
            'pk',
            'product_name',
            'product_min_stock',
            'product_unit_name',
            'product_unit_abbv',
            'product_note',
            'product_type',
        )

class ProductInventorySerializer(serializers.ModelSerializer):
    product_name_id = serializers.CharField(source='product_name.pk')
    product_name = serializers.CharField(source='product_name.product_name')
    product_unit_abbv = serializers.CharField(source='product_name.product_unit.unit_abbv')
    supplier = serializers.CharField(source='supplier.company_name')

    class Meta:
        model = Product_Inventory
        fields = (
            'pk',
            'product_name_id',
            'product_name',
            'product_unit_abbv',
            'quantity',
            'product_stock_left',
            'product_cost',
            'product_total_cost',
            'ordered_date',
            'order_update',
            'inventory_note',
            'supplier',
        )

class SalesSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product_name.product_name')
    customer = serializers.CharField(source='customer.company_name')
    # total_sales = serializers.IntegerField()
    # total_cost = serializers.IntegerField()
    # total_margin = serializers.IntegerField()

    class Meta:
        model = Sales
        fields = (
            'pk',
            'sales_dr',
            'sales_invoice',
            'sales_date',
            'sales_updated',
            'customer',
            'product_name',
            'sales_quantity',
            'sales_unit_cost',
            'sales_total_cost',
            'sales_unit_price',
            'sales_total_price',
            'sales_margin',
            'sales_margin_percent',
            'sales_status',
            'sales_note',
            'sales_paid_date',
            # 'total_sales',
            # 'total_cost',
            # 'total_margin',
        )

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'

class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = '__all__'

        
class UnitSerializer(serializers.ModelSerializer):
    unit_category = serializers.CharField(source='unit_category.unit_category')
    class Meta:
        model = Unit
        fields = '__all__'

class UnitCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = UnitCategory
        fields = '__all__'