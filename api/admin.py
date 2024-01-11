from django.contrib import admin
from .models import *

# Register your models here.
class RawMaterialsAdmin(admin.ModelAdmin):
    list_display = [
        'material_name',
        'material_min_stock',
        'material_unit',
        'material_note',
        'date_created',
    ]

class RawMaterialsProductAdmin(admin.ModelAdmin):
    list_display = ['materials', "product", "quantity"]

class RawMaterialsInventoryAdmin(admin.ModelAdmin):
    list_display = [
        "pk",
        "material_name", 
        "quantity", 
        "material_stock_left", 
        "material_cost", 
        "material_total_cost", 
        "ordered_date", 
        "order_update", 
        "inventory_note"
    ]
    ordering = ["-ordered_date"]

class RawMaterialsInventoryTransactionAdmin(admin.ModelAdmin):
    list_display = ["product_inventory_pk", "materials_inventory_pk", "transaction_date"]

class UnitAdmin(admin.ModelAdmin):
    list_display = ["unit_name", "unit_abbv", "unit_category"]

class ProductAdmin(admin.ModelAdmin):
    list_display = ["product_name", "product_min_stock", "product_unit", "product_note", "product_type", "date_created"]

class ProductInventoryAdmin(admin.ModelAdmin):
    list_display = ["ordered_date", "product_name", "quantity", "product_stock_left", "product_cost", "product_total_cost", "order_update", "inventory_note"]
    ordering = ["-ordered_date"]

class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = ["pk","sales_pk", "inventory_pk", "transaction_date"]
    ordering = ['-transaction_date']

class CustomerAdmin(admin.ModelAdmin):
    list_display = ["company_name", "contact_person", "contact_number", "company_address"]

class SalesAdmin(admin.ModelAdmin):
    list_display = [
        "sales_dr",
        "sales_invoice", 
        "sales_date",
        "sales_updated",
        "customer","product_name",
        "sales_quantity",
        "sales_unit_cost",
        "sales_total_cost",
        "sales_unit_price",
        "sales_total_price",
        "sales_margin",
        "sales_margin_percent",
        'sales_status',
        'sales_note',
        'sales_paid_date',
        ]
    ordering = ["-sales_date"]

admin.site.register(Sales, SalesAdmin)
admin.site.register(RawMaterials_Inventory, RawMaterialsInventoryAdmin)
admin.site.register(Product_Inventory, ProductInventoryAdmin)
admin.site.register(RawMaterials_InventoryTransaction, RawMaterialsInventoryTransactionAdmin)
admin.site.register(InventoryTransaction, InventoryTransactionAdmin)

admin.site.register(RawMaterials_Product, RawMaterialsProductAdmin)
# admin.site.register(RawMaterials, RawMaterialsAdmin)
# admin.site.register(Product, ProductAdmin)
# admin.site.register(Customer, CustomerAdmin)
# admin.site.register(Unit, UnitAdmin)
# admin.site.register(UnitCategory)
