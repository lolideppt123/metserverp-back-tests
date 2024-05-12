from django.views import View
from django.http import JsonResponse
from api.models import *
from api.serializer import *
from api.validations import *
from api.helper import *
from api.procedure import *
from django.db.models import Sum, Q, Count
from django.db.models.functions import Length
from decimal import Decimal
import datetime
from rest_framework.views import APIView
from rest_framework import permissions

class DashboardPageView(APIView):
    permission_classes = (permissions.DjangoModelPermissions,)
    queryset = Sales.objects.all() # This is needed even we don't use it to perform permission_classes

    def get(self, request):
        getYear = datetime.date.today().year
        getStartDate = str(getYear) + '-01-01'
        date_today = datetime.date.today().strftime("%Y-%m-%d")
        sales = Sales.objects.filter(sales_date__gte=getStartDate, sales_date__lte=date_today)
        # salesWInvoice = Sales.objects.filter(~Q(sales_invoice=None), sales_date__gte=getStartDate, sales_date__lte=date_today)
        # salesWoInvoice = Sales.objects.filter(sales_invoice=None, sales_date__gte=getStartDate, sales_date__lte=date_today)

        salesWInvoice = Sales.objects.annotate(text_len=Length('sales_invoice__sales_invoice')).filter(text_len__lte=4, sales_date__gte=getStartDate, sales_date__lte=date_today)
        salesWoInvoice = Sales.objects.annotate(text_len=Length('sales_invoice__sales_invoice')).filter(text_len__gt=4, sales_date__gte=getStartDate, sales_date__lte=date_today)

        
        paidSales = Sales.objects.filter(sales_invoice__invoice_status="PAID", sales_date__gte=getStartDate, sales_date__lte=date_today)
        unpaidSales = Sales.objects.filter(sales_invoice__invoice_status="UNPAID", sales_date__gte=getStartDate, sales_date__lte=date_today)
        products = Product.objects.all()
        materials = RawMaterials.objects.all()

        # Count salepaid with invoice
        # salesWInvoice.filter(sales_status="PAID").aggregate(count_invoice_paid=Count('sales_invoice'))
        # paid_salesWInvoice = salesWInvoice.filter(sales_status="PAID").aggregate(invoice_paid=Count('sales_invoice'))['invoice_paid']
        # unpaid_salesWInvoice = salesWInvoice.filter(sales_status="UNPAID").aggregate(invoice_unpaid=Count('sales_invoice'))['invoice_unpaid']
        # total_salesWInvoice = salesWInvoice.aggregate(invoice_unpaid=Count('sales_invoice'))['invoice_unpaid']

        def getSmallBox(query, title):
            total_sales_output = {'total_sales': 0}
            for item in query:
                total_sales_output['total_sales'] += Decimal(item.sales_total_price)
            total_sales_output.update({'title': title})
            return total_sales_output
        
        total_sales_WInvoice = getSmallBox(salesWInvoice, 'Sales with Invoice')
        total_sales_WoInvoice = getSmallBox(salesWoInvoice, 'Sales without Invoice')
        total_paid_sales = getSmallBox(paidSales, 'Sales Collected')
        total_unpaid_sales = getSmallBox(unpaidSales, 'Sales Uncollected')     

        def getInvoicePercentages(qobj, title):
            paid_sales_query = qobj.filter(sales_invoice__invoice_status="PAID").aggregate(sales_paid=Count('sales_invoice'))['sales_paid']
            unpaid_sales_query = qobj.filter(sales_invoice__invoice_status="UNPAID").aggregate(sales_unpaid=Count('sales_invoice'))['sales_unpaid']
            total_sales_query = qobj.aggregate(sales_count=Count('sales_invoice'))['sales_count']
            try:
                paid_percent = round(paid_sales_query / total_sales_query * 100)
                unpaid_percent = round(unpaid_sales_query / total_sales_query * 100)
            except ZeroDivisionError:
                paid_percent = 0
                unpaid_percent = 0
            return {'paid_percent': paid_percent, 'unpaid_percent': unpaid_percent, 'title': title}
        
        salesWInvoice_percentages = getInvoicePercentages(salesWInvoice, 'With Invoice')
        salesWoInvoice_percentages = getInvoicePercentages(salesWoInvoice, 'Without Invoice')
        sales_percentages = getInvoicePercentages(sales, 'Sales')

        product_data = []
        for product in products:
            product_inventory = Product_Inventory.objects.filter(product_name=product.pk)
            if product_inventory.exists():
                product_stock_left = product_inventory.aggregate(total_inventory=Sum('product_stock_left'))
                width, color = productInventoryStatus(product.product_min_stock, *product_stock_left.values())
                if color['color'] == 'warning' or color['color'] == 'danger':
                    data_set = {"name": product.product_name}
                    data_set.update({'stock_left':product_stock_left['total_inventory']})
                    data_set.update({'unit':product.product_unit.unit_abbv})
                    data_set.update({'color': color['color']})
                    product_data.append(data_set)
        # print(product_data)

        material_data = []
        for material in materials:
            material_inventory = RawMaterials_Inventory.objects.filter(material_name=material.pk)
            if material_inventory.exists():
                material_stock_left = material_inventory.aggregate(total_inventory=Sum('material_stock_left'))
                width, color = productInventoryStatus(material.material_min_stock, *material_stock_left.values())
                if color['color'] == 'warning' or color['color'] == 'danger':
                    data_set = {"name": material.material_name}
                    data_set.update({'stock_left': round(material_stock_left['total_inventory'], 2)})
                    data_set.update({'unit':material.material_unit.unit_abbv})
                    data_set.update({'color': color['color']})
                    material_data.append(data_set)
        # print(material_data)

        data_list = [
            {
                'small_box': [
                    total_sales_WInvoice,
                    total_sales_WoInvoice,
                    total_paid_sales,
                    total_unpaid_sales
                ]
            },
            {
                'mid_box': [
                    salesWInvoice_percentages,
                    salesWoInvoice_percentages,
                    sales_percentages
                ]
            },
            {
                'large_box': [
                {
                    'title': 'Low Inventory Products',
                    'data': product_data
                },
                {
                    'title': 'Low Inventory Materials',
                    'data': material_data
                }
                ]
            }
        ]

        return JsonResponse(data_list, safe=False)