from django.urls import path
from .views import *
from .validations import *
from django.views.decorators.csrf import csrf_exempt
from api.views.sales_view_draft import *

urlpatterns = [
    path('dashboard/', DashboardPageView.as_view(), name='dashboard'),

    path('materials/', RawMaterialsPageView.as_view(), name='materials'),
    path('materials/<int:id>', RawMaterialsPageView.as_view(), name='materials'),

    path('products/', ProductsPageView.as_view(), name='products'),
    path('products/<int:id>', ProductsPageView.as_view(), name='products_item'),

    path('inventory/materials/', RawMaterialsInventoryPageView.as_view(), name='materials_inventory'),
    path('inventory/materials/<int:id>', RawMaterialsInventoryPageView.as_view(), name='materials_inventory_edit'),
    path('inventory/materials/transaction/<int:material_pk>', RawMaterialsInventoryHistoryPageView.as_view(), name='materials_inventory_transaction'),
    
    path('inventory/products/', ProductInventoryPageView.as_view(), name='products_inventory'),
    path('inventory/products/<int:id>', ProductInventoryPageView.as_view(), name='products_inventory_edit'),
    path('inventory/products/transaction/<int:product_pk>', InventoryHistoryPageView.as_view(), name='products_inventory_transaction'),
    path('inventory/inventory-summary', InventorySummaryPageView.as_view(), name='inventory_summary'),

    path('customers/', CustomerPageView.as_view(), name='customer'),
    path('suppliers/', SupplierPageView.as_view(), name='supplier'),
    path('customers/<int:id>', CustomerPageView.as_view(), name='customer'),
    path('suppliers/<int:id>', SupplierPageView.as_view(), name='supplier'),
    
    path('sales/', SalesPageView.as_view(), name='sales'),
    # path('sales/<str:option>', SalesPageView.as_view(), name='sales'),
    # path('draft-sales/', SalesPageViewDraft.as_view(), name='sales'),
    path('sales/transaction/<int:id>/edit', SalesPageView.as_view(), name='sales_edit'),
    path('sales/sales-summary/data-chart', SalesSummaryChartDataView.as_view(), name='sales_summary_chart'),
    path('sales/sales-summary/data-table', SalesSummaryDataTableView.as_view(), name='sales_summary_table'),
    path('sales-data-filter/', getSalesFilteredData, name='sales_filter'),
    # path('sales-data-filter-draft/', DraftgetSalesFilteredData, name='sales_filter'),
    

    path('sales-invoice/', SalesInvoicePageView.as_view(), name='sales'),
    path('sales-invoice/<int:id>', SalesInvoicePageView.as_view(), name='sales_invoice'),

    path('dictionaries/', getDictionaryData),
    path('products/unit', UnitPageView.as_view(), name='units'),
    path('products/unitcategory', UnitCategoryPageView.as_view(), name='unit_category'),
    path('products/getunitprice', getUnitPriceProduct, name='get_unit_price'),
    path('products/production-run/validate', validateAddProductInventory, name='validate_production'),


    path("checkinvoice", getSalesInvoice, name="")
]
