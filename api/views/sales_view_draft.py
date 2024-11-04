from django.http import Http404, JsonResponse
from api.models import *
from api.serializer import *
from api.validations import *
from api.helper import *
from api.procedure import *
from django.db.models import Sum, Q, F, DecimalField, FloatField
from django.db.models.deletion import ProtectedError
import uuid
import json
import datetime
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework import permissions
from rest_framework.decorators import permission_classes, api_view
import calendar

from django.db.models.functions import TruncMonth
from django.db.models.expressions import ExpressionWrapper
from django.db.models import Func

# from rest_framework.pagination import PageNumberPagination
# from rest_framework.response import Response

import time

class Round(Func):
    function = 'ROUND'
    arity = 2

class SalesPageViewDraft(APIView):
    permission_classes = (permissions.DjangoModelPermissions,)
    queryset = Sales.objects.all() # This is needed even we don't use it to perform permission_classes


    def get(self, request, id=None, **kwargs):
        start_time = time.time()

        # Get filters from query parameters
        invoice_filter = request.GET.getlist('salesInvoice')
        customer_filter = request.GET.getlist('customer')
        product_supplier_filter = request.GET.getlist('productName')  # Handle list of product names
        date_filter = request.GET.get('dateFilter')

        product_supplier_filter = [
            int(product) if product.isdigit() else product
            for product in product_supplier_filter
        ]

        # Returns all sales if no year and id supplied
        if id is None and date_filter is None:
            sales = Sales.objects.all()
            sales_serializer = SalesSerializer(sales, many=True)
            return JsonResponse(sales_serializer.data, safe=False)

        # If id is supplied return early
        if id is not None:
            sales_item = get_object_or_404(Sales, pk=id)
            sales_serialized = SalesSerializer(sales_item)

            get_customer = get_object_or_404(Customer, company_name=sales_serialized.data['customer'])
            serialized_data = sales_serialized.data
            serialized_data['customer'] = {"id":get_customer.pk, "company_name": get_customer.company_name}

            return JsonResponse(serialized_data, safe=False)

        try:
            year_str, month_str = date_filter.split("-")
            year = int(year_str)
            month = int(month_str)
            # month = 10
        except:
            year = datetime.date.today().year
            month = datetime.date.today().month


        # Setting filter Query for supplier and product default is []
        if product_supplier_filter is not None and len(product_supplier_filter) > 0:
            supplier_filter = []
            product_filter = []

            # Seperates product and suppliers filter
            for item in product_supplier_filter:
                if isinstance(item, str):
                    print("this is str", item)
                    product_filter.append(item)
                elif isinstance(item, int):
                    print("this is int", item)
                    supplier_filter.append(item)

            # Build the product query based on the presence of filters
            # Start with an empty query
            product_query = Q()  

            # Check conditions and build the query
            if product_filter and supplier_filter:
                # Both filters are present, use OR logic
                product_query = Q(sales_transaction__product_name__product_name__in=product_filter) | Q(sales_transaction__supplier__in=supplier_filter)
            elif product_filter:
                # Only product filter is present
                product_query = Q(sales_transaction__product_name__product_name__in=product_filter)
            elif supplier_filter:
                # Only supplier filter is present
                product_query = Q(sales_transaction__supplier__in=supplier_filter)
            else:
                # No filtering, returns all
                product_query = Q() 

        else:
            # Goes here if product_supplier_filter is none or empty. 
            # which is also the default query for both supplier and product
            # it also means len(supplier_filter) == 0 and len(product_filter) == 0
            product_query = Q()  # No filtering, returns all


        # Setting filter for customer
        if customer_filter:
            customer_query = Q(customer__company_name__in=customer_filter)
        else:
            customer_query = Q()  # Returns all customers


        # Setting filter for invoice
        if len(invoice_filter) == 0 or len(invoice_filter) == 3:
            invoice_query = Q()
        else:
            # Initialize an empty query
            invoice_query = Q()

            # Check for each filter and construct the query
            if 'Without Invoice' in invoice_filter:
                invoice_query |= Q(sales_invoice__sales_invoice__startswith='noinv')

            if 'Sample' in invoice_filter:
                invoice_query |= Q(sales_invoice__sales_invoice__startswith='sample')

            if 'With Invoice' in invoice_filter:
                invoice_query |= ~Q(sales_invoice__sales_invoice__regex=r'[a-zA-Z]')

        
        combined_filter_query = product_query & customer_query & invoice_query

        # This query will return all sales from YEAR-MONTH-01 to YEAR-MONTH-31/30/29/28
        month_year_sales = Sales.objects.filter(sales_date__year=year, sales_date__month=month)
        filtered_monthly_year_sales = month_year_sales.filter(
            combined_filter_query # If there is filter it will filter, if not it will return normal values
        ).order_by(
            'sales_invoice',
            'sales_date', 
            'created_at', 
            'customer', 
            'product_name'
        )


        # Declare here incase we need to return early
        data_title = str(year) + "-" + str(month)
        products = ProductSerializer(Product.objects.all(), many=True)
        supplier = SupplierSerializer(Supplier.objects.all(), many=True)
        customer = CustomerSerializer(Customer.objects.all(), many=True)


        # Check if there is a sales
        if not filtered_monthly_year_sales.exists():
            sales_data = {
                "sales_list": [],
                "sales_totals": {},
                "sales_cummulative": {}
            }
            api = {
                "products": products.data, 
                "supplier": supplier.data, 
                "customer": customer.data, 
                "sales": sales_data,
                "data_title": data_title
            }
            return JsonResponse(api, safe=False)
        

        sales_serializer = SalesSerializer(filtered_monthly_year_sales, many=True)
        filtered_serialized_data = sales_serializer.data
        # Done with the list of sales that's been filtered.

        getEndDay = calendar.monthrange(year, month)
        start_date = datetime.datetime.strptime(str(year) + '-01-01', "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(str(year) + "-" + str(month) + "-" + str(getEndDay[1]), "%Y-%m-%d").date()

        # Get the first DAY and MONTH of the year for GTE and get the last DAY of the supplied Month
        month_year_sales_commulative = Sales.objects.filter(sales_date__gte=start_date, sales_date__lte=end_date)
        filtered_monthly_year_sales_commulative = month_year_sales_commulative.filter(
            combined_filter_query
        )
        

        # Compute sales totals & cummulative
        sales_totals = getSalesTotals(filtered_monthly_year_sales, "TOTAL_SALES") # helper.py
        sales_cummulative = getSalesTotals(filtered_monthly_year_sales_commulative, "CUMM_TOTAL_SALES") # helper.py

        sales_data = {
            "sales_list": filtered_serialized_data,
            "sales_totals": sales_totals,
            "sales_cummulative": sales_cummulative
        }

        api = {
            "products": products.data, 
            "supplier": supplier.data, 
            "customer": customer.data, 
            "sales": sales_data,
            "data_title": data_title
        }

        end_time = time.time()
        execution_time = end_time - start_time
        print(f"Execution time: {execution_time:.2f} seconds")

        return JsonResponse(api, safe=False)
        # return JsonResponse(data_list, safe=False)



@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def DraftgetSalesFilteredData(request):

    data = json.loads(request.body.decode('utf-8'))
    print(data)

    if data['SalesFilter'] is None:
        return JsonResponse([], safe=False)
    
    if data['SalesFilter'] is not None:
        query_year = data['SalesFilter']
        getStartDate = str(query_year) + '-01-01'
        getEndDate = str(query_year) + '-12-31'

        date_range = getDateRange(getStartDate, getEndDate)

        # Setting filter for supplier and product
        if data['productName'] is not None:
            supplier_filter = []
            product_filter = []
            for item in data['productName']:
                if(type(item) == str):
                    product_filter.append(item)
                else:
                # if(type(item) == int):
                    supplier_filter.append(item)

            if len(supplier_filter) == 0 and len(product_filter) > 0:
                product_query = ~Q(sales_transaction__supplier__company_name="") & Q(sales_transaction__product_name__product_name__in=product_filter)
                
            elif len(supplier_filter) > 0 and len(product_filter) == 0:
                product_query = Q(sales_transaction__supplier__in=supplier_filter) & ~Q(sales_transaction__product_name__product_name="")
            else:
                # Means both supplier & productname contains filter
                product_query = Q(sales_transaction__supplier__in=supplier_filter) | Q(sales_transaction__product_name__product_name__in=product_filter)

        else:
            # Goes here if data['productName'] is none. which is also the default query for both supplier and product
            # it also means len(supplier_filter) == 0 and len(product_filter) == 0
            product_query = ~Q(sales_transaction__supplier__company_name="") & ~Q(sales_transaction__product_name__product_name="")

        # Setting filter for supplier and product
        if data['customer'] is not None:
            customer_filter = data['customer']
            customer_query = Q(customer__company_name__in=customer_filter)
        else:
            customer_query = ~Q(customer__company_name="")

        # Setting filter for invoice
        if data['salesInvoice'] is None or len(data['salesInvoice']) > 1:
            # If with or without invoice was picked goes here
            invoice_query = Q()
        elif data['salesInvoice'][0] == 'Without Invoice':
            invoice_query = Q(sales_invoice__sales_invoice__regex=r'[a-zA-Z]')
        else:
            # Goes here if With Invoice
            invoice_query = ~Q(sales_invoice__sales_invoice__regex=r'[a-zA-Z]')

        data_list = []
        for index in date_range:

            sales = Sales.objects.filter(sales_date__gte=index[0], sales_date__lte=index[1]).order_by('sales_invoice', 'sales_date', 'created_at', 'customer', 'product_name')
            sales_commulative = Sales.objects.filter(sales_date__gte=date_range[0][0], sales_date__lte=index[1])

            sales_filtered = sales.filter(product_query & customer_query & invoice_query).order_by('sales_invoice', 'sales_date', 'created_at', 'customer', 'product_name')
            sales_commulative_filtered = sales_commulative.filter(product_query & customer_query & invoice_query)

            sales_serializer = SalesSerializer(sales_filtered, many=True)
            new_serializer = list(sales_serializer.data)

            sales_list = getSalesTotals(sales_filtered, "TOTAL_SALES") # helper.py
            cumm_sales_list = getSalesTotals(sales_commulative_filtered, "CUMM_TOTAL_SALES") # helper.py

            data_title = str(index[0].year) + "-" + str(index[0].month)
            new_serializer.append(sales_list)
            new_serializer.append(cumm_sales_list)
            new_serializer.append({"data_title":data_title})
            data_list.append(new_serializer)

        return JsonResponse(data_list, safe=False)

    return JsonResponse([], safe=False) 