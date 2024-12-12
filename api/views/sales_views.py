from django.http import JsonResponse
from api.models import *
from api.serializer import *
from api.validations import *
from api.helper import *
from api.procedure import *
from django.db.models import Sum, Q
from django.db.models.deletion import ProtectedError
import uuid
import json
import datetime
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework import permissions
from rest_framework.decorators import permission_classes, api_view
import calendar

import time


class SalesPageView(APIView):
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

        products = ProductSerializer(Product.objects.all(), many=True)
        supplier = SupplierSerializer(Supplier.objects.all(), many=True)
        customer = CustomerSerializer(Customer.objects.all(), many=True)

        # If id is supplied return early
        if id is not None:
            sales_item = get_object_or_404(Sales, pk=id)
            sales_serialized = SalesSerializer(sales_item)

            get_customer = get_object_or_404(Customer, company_name=sales_serialized.data['customer'])
            serialized_data = sales_serialized.data
            serialized_data['customer'] = {"id":get_customer.pk, "company_name": get_customer.company_name}

            api = {
                "product": products.data, 
                "supplier": supplier.data, 
                "customer": customer.data, 
                "sale": serialized_data,
            }

            return JsonResponse(api, safe=False)

        # build date filter
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
                    # print("this is str", item)
                    product_filter.append(item)
                elif isinstance(item, int):
                    # print("this is int", item)
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


        # Get the first DAY and MONTH of the year for GTE and get ONLY the LAST DAY of the SUPPLIED MONTH. 
        # 
        # LAST DAY of the SUPPLIED MONTH vs LAST DAY of the YEAR will result in a different cummulative totals
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

    def post(self, request):
        data = json.loads(request.body.decode('utf-8'))
        sales_invoice = data['sales_invoice']
        sales_date = datetime.datetime.strptime(data['sales_date'], "%Y-%m-%d").date()
        customer = data['customer']['company_name']

        products = data['products']
        
        if sales_invoice == '':
            sales_invoice = f'noinv-{sales_date}-' + str(uuid.uuid4())
        elif sales_invoice.lower() == 'sample':
            print("Sales Invoice Lower: ", sales_invoice.lower())
            print("Sales Invoice: ",sales_invoice)
            sales_invoice = f'sample-{sales_date}-' + str(uuid.uuid4())

        invoice_obj = SalesInvoice.objects.create(sales_invoice=sales_invoice, invoice_date=sales_date, invoice_note=data['sales_note'])
        customer_obj, create = Customer.objects.get_or_create(company_name=customer)

        # reassign values back as validated data
        data['sales_invoice'] = invoice_obj
        data['customer']['company_name'] = customer_obj
        

        # Loop throught number of products
        # Create sales in every loop
        for index, item in enumerate(products):
            addSalesValidation(item['product'], customer)
            data['product_name'] = item['product']
            data['quantity'] = item['sales_quantity']
            data['ucost'] = item['unit_cost']
            data['tcost'] = item['total_cost']
            data['uprice'] = item['unit_price']
            # Check if product name has stock                                           (Checked in getUnitPriceProduct)
            # Check if product has enought stock                                        (Checked in getUnitPriceProduct)
            # Prevents the User to input sales before starting Inventory                (Checked in getUnitPriceProduct)

            # Query inventory less than or equal sales date
            product_inventory = Product_Inventory.objects.filter(
                product_name = Product.objects.get(product_name=item['product']), 
                ordered_date__lte=sales_date,
                product_stock_left__gt=0
            )

            # Procedure Deducts Inventory Stock, creates Sales Instance, creates InventoryHistory Instance
            addSalesProcedure(product_inventory, item['sales_quantity'], data)
            
        return JsonResponse({"message": "Sales successfully Added.", 'variant': 'success'})

    def put(self, request, id):
        data = json.loads(request.body.decode('utf-8'))
        sales_date = datetime.datetime.strptime(data['sales_date'], "%Y-%m-%d").date()
        sales_invoice = data['sales_invoice']
        customer = data['customer']['company_name']

        product_name = data['product_name']
        quantity_diff = data['quantity_diff']

        # Allows the user to insert Sales into an invoice
        if sales_invoice == '':
            sales_invoice = f'noinv-{sales_date}-' + str(uuid.uuid4())
        invoice_obj, created = SalesInvoice.objects.get_or_create(sales_invoice=sales_invoice, invoice_date=sales_date)
        cust_obj = get_object_or_404(Customer, company_name=customer)

        # reassign values back as validated data
        data['sales_invoice'] = invoice_obj
        data['customer']['company_name'] = cust_obj


        # User did not change sales quantity. goes here
        if quantity_diff == 0:
            # Save changes
            updated_sales = update_sales_obj(id, data)
            updated_sales.save()
            pass
        else:
            product_inventory = Product_Inventory.objects.filter(product_name = Product.objects.get(product_name=product_name), ordered_date__lte=sales_date)
            print(data)
            updateSalesProcedure(product_inventory, data)

        # return JsonResponse({"message": "Feature has not yet been added. Please Contact me MASTER JOSEPH"})
        return JsonResponse({'message': f"Successfully updated Sales", 'variant': 'success'})
    
    def patch(self, request, id):
        print("patch triggered")
        data = json.loads(request.body.decode('utf-8'))
        sales_date = datetime.datetime.strptime(data['sales_date'], "%Y-%m-%d").date()
        sales_invoice = data['sales_invoice']
        customer = data['customer']['company_name']

        product_name = data['product_name']
        quantity_diff = data['quantity_diff']

        # Allows the user to insert Sales into an invoice
        if sales_invoice == '':
            sales_invoice = f'noinv-{sales_date}-' + str(uuid.uuid4())
        invoice_obj, created = SalesInvoice.objects.get_or_create(sales_invoice=sales_invoice, invoice_date=sales_date)
        cust_obj = get_object_or_404(Customer, company_name=customer)

        # reassign values back as validated data
        data['sales_invoice'] = invoice_obj
        data['customer']['company_name'] = cust_obj


        # User did not change sales quantity. goes here
        if quantity_diff == 0:
            # Save changes
            updated_sales = update_sales_obj(id, data)
            updated_sales.save()
            pass
        else:
            product_inventory = Product_Inventory.objects.filter(product_name = Product.objects.get(product_name=product_name), ordered_date__lte=sales_date)
            print(data)
            updateSalesProcedure(product_inventory, data)

        # return JsonResponse({"message": "Feature has not yet been added. Please Contact me MASTER JOSEPH"})
        return JsonResponse({'message': f"Successfully updated Sales", 'variant': 'success'})

    
    def delete(self, request, id):
        sales = get_object_or_404(Sales, pk=id)
        item_inventory_transaction = get_object_or_404(InventoryTransaction, sales_pk=id)
        add_quantity = abs(item_inventory_transaction.p_quantity)
        product_inventory = get_object_or_404(Product_Inventory, pk=item_inventory_transaction.inventory_pk.pk)

        try:
            product_inventory.product_stock_left += add_quantity
            product_inventory.save()
            item_inventory_transaction.delete()
            sales.delete()

            product_pk = product_inventory.product_name.pk
        except ProtectedError:
            return JsonResponse({"message": f"Delete action failed. {sales.product_name} already has linked records."}, status=404)
        return JsonResponse({
            "product_pk": product_pk, # returns back product_pk to be used in salesApiSLice tag invalidation
            "message": f"Invoice#: {sales.sales_invoice} {sales.product_name} has successfully deleted.",
        })
    

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def getSalesFilteredData(request):

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
            invoice_query = ~Q(sales_invoice__sales_invoice="")
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


class SalesSummaryChartDataView(APIView):
    permission_classes = (permissions.DjangoModelPermissions,)
    queryset = Sales.objects.all() # This is needed even we don't use it to perform permission_classes

    def get(self, request):
        pass
    def post(self, request):
        data = json.loads(request.body.decode('utf-8'))
        start_date = data['start']
        end_date = data['end']
        query = data['query']
        # print(start_date, "--", end_date)
        
        date_range = getDateRange(start_date, end_date)

        if query == "ALL":
            data_list = []
            for index in date_range:
                sales = Sales.objects.filter(sales_date__gte=index[0], sales_date__lte=index[1])

                if sales.exists():
                    total_sales_cost = sales.aggregate(total_cost=Sum('sales_total_cost'))
                    total_sales_price = sumOfSales(sales, 'sales_gross_price')
                    total_sales_margin = sumOfSales(sales, 'sales_margin')

                    # From string to Float
                    sales_cost = float(*total_sales_cost.values())
                    sales_price = float(*total_sales_price.values())
                    sales_margin = float(*total_sales_margin.values())

                    data_set = ({"start_date": index[0].strftime("%b %d %Y")})
                    data_set.update({"end_date": index[1].strftime("%b %d %Y")})
                    data_set.update({"date_label": index[0].strftime("%b %Y")})
                    data_set.update({"sales_cost":sales_cost})
                    data_set.update({"sales_price":sales_price})
                    data_set.update({"sales_margin":sales_margin})
                    data_list.append(data_set)
                else:
                    # When no record shows set items to 0
                    data_set = ({"start_date": index[0].strftime("%b %d %Y")})
                    data_set.update({"end_date": index[1].strftime("%b %d %Y")})
                    data_set.update({"date_label": index[0].strftime("%b %Y")})
                    data_set.update({"sales_cost":0})
                    data_set.update({"sales_price":0})
                    data_set.update({"sales_margin":0})
                    data_list.append(data_set)

            return JsonResponse(data_list, safe=False)
        
        if query == "PRODUCTS":
            data_sorted = []
            data_list = []
            for index in date_range:
                query_list = []
                for product in Product.objects.all():
                    sales = Sales.objects.filter(sales_date__gte=index[0], sales_date__lte=index[1], product_name=product.pk)

                    if sales.exists():
                        total_sales_cost = sales.aggregate(total_cost=Sum('sales_total_cost'))
                        total_sales_price = sumOfSales(sales, 'sales_gross_price')
                        total_sales_margin = sumOfSales(sales, 'sales_margin')

                        # From string to Float
                        sales_cost = float(*total_sales_cost.values())
                        sales_price = float(*total_sales_price.values())
                        sales_margin = float(*total_sales_margin.values())

                        data_set = ({'product': product.product_name})
                        data_set.update({"sales_margin":sales_margin})
                        query_list.append(data_set)
                    else:
                        data_set = ({'product': product.product_name})
                        data_set.update({"sales_margin":0})
                        query_list.append(data_set)
                # Sort query_list from highest to lowest using sales_margin. then return only from 0 upto 3 index 
                data_sorted = sorted(query_list, key=lambda item : item['sales_margin'], reverse=True)[0:3]

                new_data_set = ({"date_label": index[0].strftime("%b %Y")})
                new_data_set.update({"start_date": index[0].strftime("%b %d %Y")})
                new_data_set.update({"end_date": index[1].strftime("%b %d %Y")})

                for index, item in enumerate(data_sorted):
                    new_data_set.update({f"rank_{index}": item['product']})
                    new_data_set.update({f"rank_{index}_margin": item['sales_margin']})

                data_list.append(new_data_set)

            return JsonResponse(data_list, safe=False)

        if query == "CUSTOMERS":
            data_sorted = []
            data_list = []
            for index in date_range:
                query_list = []
                for customer in Customer.objects.all():
                    sales = Sales.objects.filter(sales_date__gte=index[0], sales_date__lte=index[1], customer=customer.pk)

                    if sales.exists():
                        total_sales_cost = sales.aggregate(total_cost=Sum('sales_total_cost'))
                        total_sales_price = sumOfSales(sales, 'sales_gross_price')
                        total_sales_margin = sumOfSales(sales, 'sales_margin')

                        # From string to Float
                        sales_cost = float(*total_sales_cost.values())
                        sales_price = float(*total_sales_price.values())
                        sales_margin = float(*total_sales_margin.values())

                        data_set = ({'customer': customer.company_name})
                        data_set.update({"sales_margin":sales_margin})
                        query_list.append(data_set)
                    else:
                        data_set = ({'customer': customer.company_name})
                        data_set.update({"sales_margin":0})
                        query_list.append(data_set)
                # Sort query_list from highest to lowest using sales_margin. then return only from 0 upto 3 index 
                data_sorted = sorted(query_list, key=lambda item : item['sales_margin'], reverse=True)[0:3]

                new_data_set = ({"date_label": index[0].strftime("%b %Y")})
                new_data_set.update({"start_date": index[0].strftime("%b %d %Y")})
                new_data_set.update({"end_date": index[1].strftime("%b %d %Y")})

                for index, item in enumerate(data_sorted):
                    new_data_set.update({f"rank_{index}": item['customer']})
                    new_data_set.update({f"rank_{index}_margin": item['sales_margin']})

                data_list.append(new_data_set)

            return JsonResponse(data_list, safe=False)
        return JsonResponse({"data": "data"}, safe=False)
    

class SalesSummaryDataTableView(APIView):
    permission_classes = (permissions.DjangoModelPermissions,)
    queryset = Sales.objects.all() # This is needed even we don't use it to perform permission_classes

    def post(self, request):
        data = json.loads(request.body.decode('utf-8'))
        start_date = data['start']
        end_date = data['end']
        query = data['query']

        if not query == "CUSTOMERS":
            data_list = []
            for product in Product.objects.all():
                sales = Sales.objects.filter(sales_date__gte=start_date, sales_date__lte=end_date, product_name=product)

                total_sales_cost = sales.aggregate(total_cost=Sum('sales_total_cost'))
                total_sales_gross = sumOfSales(sales, 'sales_gross_price')
                total_sales_margin = sumOfSales(sales, 'sales_margin')

                if total_sales_cost['total_cost'] is None:
                    total_sales_cost['total_cost'] = 0

                sales_cost = float(*total_sales_cost.values())
                sales_gross = float(*total_sales_gross.values())
                sales_margin = float(*total_sales_margin.values())
                try:
                    profit_margin = ((sales_gross - sales_cost) / sales_gross) * 100
                except ZeroDivisionError:
                    profit_margin = 0

                data_set = ({'product': product.product_name})
                data_set.update({"sales_cost":sales_cost})
                data_set.update({"sales_gross":sales_gross})
                data_set.update({"sales_margin":sales_margin})
                data_set.update({"profit_margin":profit_margin})
                data_set.update({"pk":product.pk})
                data_list.append(data_set)
                
            data_sorted = sorted(data_list, key=lambda item : item['sales_margin'], reverse=True)

        if query == 'CUSTOMERS':
            data_list = []
            for customer in Customer.objects.all():
                sales = Sales.objects.filter(sales_date__gte=start_date, sales_date__lte=end_date, customer=customer)

                total_sales_cost = sales.aggregate(total_cost=Sum('sales_total_cost'))
                total_sales_gross = sumOfSales(sales, 'sales_gross_price')
                total_sales_margin = sumOfSales(sales, 'sales_margin')
                
                if total_sales_cost['total_cost'] is None:
                    total_sales_cost['total_cost'] = 0

                sales_cost = float(*total_sales_cost.values())
                sales_gross = float(*total_sales_gross.values())
                sales_margin = float(*total_sales_margin.values())
                try:
                    profit_margin = ((sales_gross - sales_cost) / sales_gross) * 100
                except ZeroDivisionError:
                    profit_margin = 0

                data_set = ({'customer': customer.company_name})
                data_set.update({"sales_cost":sales_cost})
                data_set.update({"sales_gross":sales_gross})
                data_set.update({"sales_margin":sales_margin})
                data_set.update({"profit_margin":profit_margin})
                data_set.update({"pk":customer.pk})
                data_list.append(data_set)

            data_sorted = sorted(data_list, key=lambda item : item['sales_margin'], reverse=True)

        sales_query = Sales.objects.filter(sales_date__gte=start_date, sales_date__lte=end_date)
        sales_totals = getSalesTotals(sales_query, "CUMM_TOTAL_SALES")
        print(sales_totals)
        data_sorted.append(sales_totals)

        return JsonResponse(data_sorted, safe=False)


