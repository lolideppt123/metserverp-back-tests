from django.urls import path
from .views import *
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    path('materials/', csrf_exempt(RawMaterialsPageView.as_view()), name='materials'),
    path('inventory/materials/', csrf_exempt(RawMaterialsInventoryPageView.as_view()), name='materials_inventory'),
    path('inventory/materials/transaction/<material_name>', csrf_exempt(RawMaterialsInventoryHistoryPageView.as_view()), name='materials_inventory_transaction'),
    
    path('products/', csrf_exempt(ProductsPageView.as_view()), name='products'),
    path('products/update/<id>', csrf_exempt(EditProductsPageView.as_view()), name='edit_products'),
    path('inventory/', csrf_exempt(ProductInventoryPageView.as_view()), name='products_inventory'),

    path('inventory/transaction/<id>/edit',  csrf_exempt(EditProductInventoryPageView.as_view()), name='products_inventory_edit'),
    path('inventory/products/transaction/<product_name>', csrf_exempt(InventoryHistoryPageView.as_view()), name='products_inventory_transaction'),
    path('inventory/inventory-summary', csrf_exempt(InventorySummaryPageView.as_view()), name='inventory_summary'),

    path('customer/', csrf_exempt(CustomerPageView.as_view()), name='customer'),
    path('supplier/', csrf_exempt(SupplierPageView.as_view()), name='supplier'),
    path('sales/', csrf_exempt(SalesPageView.as_view()), name='sales'),
    path('sales/transaction/<id>/edit', csrf_exempt(EditSalesPageView.as_view()), name='sales_edit'),
    path('sales/sales-summary/data-chart', csrf_exempt(SalesSummaryChartDataView.as_view()), name='sales_summary_chart'),
    path('sales/sales-summary/data-table', csrf_exempt(SalesSummaryDataTableView.as_view()), name='sales_summary_table'),


    path('products/unit', UnitPageView.as_view(), name='units'),
    path('products/unitcategory', UnitCategoryPageView.as_view(), name='unit_category'),
    path('products/getunitprice', csrf_exempt(getUnitPriceProduct), name='get_unit_price'),
]
