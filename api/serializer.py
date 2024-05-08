from rest_framework import serializers
from .models import *

class MaterialsSerializer(serializers.ModelSerializer):
    material_unit_name = serializers.CharField(source='material_unit.unit_name')
    material_unit_abbv = serializers.CharField(source='material_unit.unit_abbv')

    class Meta:
        model = RawMaterials
        fields = (
            'id',
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
    ingredients = serializers.StringRelatedField(many=True) # https://www.django-rest-framework.org/api-guide/relations/#inspecting-relationships

    class Meta:
        model = Product
        fields = (
            'id',
            'product_name',
            'product_min_stock',
            'product_unit_name',
            'product_unit_abbv',
            'product_note',
            'product_type',
            'ingredients',
        )

class RawMaterials_ProductSerializer(serializers.ModelSerializer):
    product = serializers.CharField(source='product.product_name')
    product_unit = serializers.CharField(source='product.product_unit.unit_name')
    product_min_stock = serializers.CharField(source='product.product_min_stock')
    product_note = serializers.CharField(source='product.product_note')
    product_type = serializers.CharField(source='product.product_type')

    material = serializers.CharField(source='materials.material_name')

    class Meta:
        model = RawMaterials_Product
        fields = (
            'product', 
            'product_unit', 
            'product_min_stock', 
            'product_note', 
            'material', 
            'quantity',
            'product_type'
        )

class RawMaterialsInventorySerializer(serializers.ModelSerializer):
    material_name_id = serializers.CharField(source='material_name.pk')
    material_name = serializers.CharField(source='material_name.material_name')
    material_unit_name = serializers.CharField(source='material_name.material_unit.unit_name')
    material_unit_abbv = serializers.CharField(source='material_name.material_unit.unit_abbv')
    supplier = serializers.CharField(source='supplier.company_name')

    class Meta:
        model = RawMaterials_Inventory
        fields = (
            'pk',
            'material_name_id',
            'material_name',
            'material_unit_name',
            'material_unit_abbv',
            'supplier',
            'quantity',
            'material_stock_left',
            'material_cost',
            'material_total_cost',
            'material_cost',
            'ordered_date',
            'order_update',
            'inventory_note',
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
    sales_invoice = serializers.CharField(source='sales_invoice.sales_invoice', allow_null=True)
    sales_status = serializers.CharField(source='sales_invoice.invoice_status', allow_null=True)
    sales_paid_date = serializers.CharField(source='sales_invoice.invoice_paid_date', allow_null=True)
    sales_date = serializers.DateField(format="%Y-%m-%d")

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
            'tax_percent',
            'sales_gross_price',
            'sales_VAT',
            'sales_total_price',
            'sales_margin',
            'sales_margin_percent',
            'sales_status',
            'sales_note',
            'sales_paid_date',
            'sales_transaction'
        )
        depth = 2 # https://testdriven.io/blog/drf-serializers/

class SalesInvoiceSerializer(serializers.ModelSerializer):
    invoice_paid_date = serializers.DateTimeField(format="%Y-%m-%d")
    class Meta:
        model = SalesInvoice
        fields = (
            'pk',
            'sales_invoice',
            'invoice_paid_date',
            'invoice_status',
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