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
    list_display = ["pk",'materials', "product", "quantity"]

class RawMaterialsInventoryAdmin(admin.ModelAdmin):
    list_display = [
        "ordered_date",
        "created_at",
        "pk",
        "material_name", 
        "supplier",
        "quantity", 
        "material_stock_left", 
        "material_cost", 
        "material_total_cost", 
        "order_update", 
        "inventory_note"
    ]
    ordering = ["-ordered_date", "-created_at", "-pk"]

class RawMaterialsInventoryTransactionAdmin(admin.ModelAdmin):
    list_display = ["pk", "product_inventory_pk", "p_quantity", "materials_inventory_pk", "m_quantity", "get_uprice", "transaction_date", "created_at"]
    ordering = ['-transaction_date']
    def get_uprice(self, obj):
        return round(obj.materials_inventory_pk.material_cost, 2)
    # get_uprice.admin_order_field  = 'author'  #Allows column order sorting
    get_uprice.short_description = 'M. U/Price'  #Renames column head

class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = ["pk","sales_pk", "s_quantity", "inventory_pk", "p_quantity", "get_uprice", "transaction_date", "created_at"]
    ordering = ['-transaction_date']
    def get_uprice(self, obj):
        # print(dir(obj.inventory_pk))
        return round(obj.inventory_pk.product_cost, 2)
    # get_uprice.admin_order_field  = 'author'  #Allows column order sorting
    get_uprice.short_description = 'I. U/Price'  #Renames column head

class ProductAdmin(admin.ModelAdmin):
    list_display = ["product_name", "product_min_stock", "product_unit", "product_note", "product_type", "date_created"]

class ProductInventoryAdmin(admin.ModelAdmin):
    list_display = ["ordered_date", "created_at", "pk", "product_name", "supplier", "quantity", "product_stock_left", "product_cost", "product_total_cost", "order_update", "inventory_note"]
    ordering = ['-ordered_date', "-created_at", "-pk"]


class UnitAdmin(admin.ModelAdmin):
    list_display = ["unit_name", "unit_abbv", "unit_category"]

class CustomerAdmin(admin.ModelAdmin):
    list_display = ["company_name", "contact_person", "contact_number", "company_address"]

class SupplierAdmin(admin.ModelAdmin):
    list_display = ["company_name", "pk", "contact_person", "contact_number", "company_address"]

class SalesAdmin(admin.ModelAdmin):
    list_display = [
        "pk",
        # "get_supplier",
        "sales_dr",
        "sales_invoice",
        "sales_date",
        "created_at",
        "sales_updated",
        "customer",
        "product_name",
        "sales_quantity",
        "sales_unit_cost",
        "sales_total_cost",
        "sales_unit_price",
        'sales_gross_price',
        'tax_percent',
        'sales_VAT',
        "sales_total_price",
        "sales_margin",
        "sales_margin_percent",
        # 'sales_status',
        # 'sales_paid_date',
        'sales_note',
        ]
    ordering = ['-sales_date', '-created_at', '-pk']

    # def get_supplier(self, obj):
    #     print(obj.inventorytransaction_set.get(sales_pk=obj.pk).inventory_pk.supplier)
    #     return obj.inventorytransaction_set.get(sales_pk=obj.pk).inventory_pk.supplier

class SalesInvoiceAdmin(admin.ModelAdmin):
    list_display = [
        "sales_invoice",
        "pk",
        "invoice_status",
        "invoice_date",
        "invoice_paid_date",
        "invoice_note",
        "created_at",
        "updated_at"
    ]

admin.site.register(Sales, SalesAdmin)
admin.site.register(SalesInvoice, SalesInvoiceAdmin)
admin.site.register(RawMaterials_Inventory, RawMaterialsInventoryAdmin)
admin.site.register(Product_Inventory, ProductInventoryAdmin)
admin.site.register(RawMaterials_InventoryTransaction, RawMaterialsInventoryTransactionAdmin)
admin.site.register(InventoryTransaction, InventoryTransactionAdmin)

admin.site.register(RawMaterials_Product, RawMaterialsProductAdmin)
# admin.site.register(RawMaterials, RawMaterialsAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Customer, CustomerAdmin)
admin.site.register(Supplier, SupplierAdmin)
# admin.site.register(Unit, UnitAdmin)
# admin.site.register(UnitCategory)