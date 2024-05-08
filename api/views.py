from django.views import View
from django.http import JsonResponse
from .models import *
from .serializer import *
from .validations import *
from .helper import *
from .procedure import *
from django.db.models import Sum, Q, Count
from django.db.models.functions import Length
from django.db.models.deletion import ProtectedError
from decimal import Decimal, InvalidOperation
import uuid
import json
import datetime
from django.shortcuts import get_object_or_404
from dateutil.relativedelta import relativedelta
from rest_framework.views import APIView
from rest_framework import permissions
from rest_framework.decorators import permission_classes, api_view
import calendar

# Create your views here.
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

class RawMaterialsPageView(APIView):
    permission_classes = (permissions.DjangoModelPermissions,)
    queryset = RawMaterials.objects.all() # This is needed even we don't use it to perform permission_classes
    
    def get(self, request, id=None, *args, **kwargs):
        materials = RawMaterials.objects.all()
        # Check if there is a material
        if not materials.exists():
            return JsonResponse([],safe=False)
        if id is not None:
            material_item = get_object_or_404(RawMaterials, pk=id)
            material_serialized = MaterialsSerializer(material_item)
            return JsonResponse(material_serialized.data, safe=False)

        material_serialized = MaterialsSerializer(materials, many=True)
        return JsonResponse(material_serialized.data, safe=False)

    def post(self, request):
        material_name, material_min_stock, material_unit, material_note = json.loads(request.body.decode('utf-8')).values()
        print(json.loads(request.body.decode('utf-8')))
        # Validation
        validation = registerNameValidation(material_name, 0, "no data", "material")
        if validation:
            return JsonResponse(validation, status=500)
        # Check if name already exists
        chk_material_name = RawMaterials.objects.filter(material_name__iexact=material_name)
        if chk_material_name:
            return JsonResponse({'label':'material_name', 'message':'Material Already Exists'}, status=500)

        # Create Material
        createMaterialInstance = RawMaterials.objects.create(
            material_name = material_name,
            material_min_stock = material_min_stock,
            material_unit = Unit.objects.get(unit_name=material_unit),
            material_note = material_note,
        )

        return JsonResponse({"message": f"Successfully added Product:{material_name} Unit:{material_unit} Minimum Stock:{material_min_stock}"})
        # return JsonResponse({"data":"data"}, safe=False)
    
    def put(self, request, id):
        material = get_object_or_404(RawMaterials, pk=id)
        data = json.loads(request.body.decode('utf-8'))
        
        material_name = data['material_name']
        material_min_stock = data['material_min_stock']
        material_unit = data['material_unit']
        material_note = data['material_note']

        if (material.material_name).lower() == material_name.lower():
            if Decimal(material_min_stock) < 0:
                return {'label':'material_min_stock', 'message':'Invalid Entry'}
        else:
            validation = registerNameValidation(material_name, material_min_stock, "no data", "material")
            if validation:
                return JsonResponse(validation, status=500)
            chk_material_name = RawMaterials.objects.filter(material_name__iexact=material_name)
            if chk_material_name:
                return JsonResponse({'label':'material_name', 'message':'Material Already Exists'}, status=500)
        
        material.material_name = material_name
        material.material_min_stock = material_min_stock
        material.material_unit = Unit.objects.get(unit_name=material_unit)
        material.material_note = material_note
        material.save()

        return JsonResponse({"message": "Successfully saved changes"})
    
    def delete(self, request, id):
        material = get_object_or_404(RawMaterials, pk=id)
        try:
            material.delete()
        except ProtectedError:
            return JsonResponse({"message": f"Delete action failed. {material.material_name} already has linked records."}, status=404)
        return JsonResponse({"message": f"{material.material_name} has successfully deleted."})
      
class RawMaterialsInventoryPageView(APIView):
    permission_classes = (permissions.DjangoModelPermissions,)
    queryset = RawMaterials.objects.all() # This is needed even we don't use it to perform permission_classes

    def get(self, request, id=None):
        materials = RawMaterials.objects.all()
        # Check if there is a material
        if not materials.exists():
            return JsonResponse([], safe=False)
        if id is not None:
            material_inventory_item = get_object_or_404(RawMaterials_Inventory, pk=id)
            material_inventory_serializer = RawMaterialsInventorySerializer(material_inventory_item)

            get_supplier = get_object_or_404(Supplier, company_name=material_inventory_serializer.data['supplier'])
            serialized_data = material_inventory_serializer.data
            serialized_data['supplier'] = {"id":get_supplier.pk, "company_name": get_supplier.company_name}
            return JsonResponse(serialized_data, safe=False)
        
        material_inventory_data = []
        for material in materials:
            material_inventory = RawMaterials_Inventory.objects.filter(material_name=material.pk)
            material_unit = Unit.objects.get(unit_name=material.material_unit).unit_name
            if material_inventory.exists():
                material_stock_left = material_inventory.aggregate(total_inventory=Sum('material_stock_left'))
                width, color = productInventoryStatus(material.material_min_stock, *material_stock_left.values())

                last_ordered_date = material_inventory[len(material_inventory)-1].ordered_date
                order_update = material_inventory[len(material_inventory)-1].order_update # Get the last update date

                data_set = {'material_name': material.material_name}
                data_set.update(material_stock_left)
                data_set.update({"material_unit" : material_unit})
                data_set.update({'last_ordered_date': last_ordered_date})
                data_set.update({'order_update': order_update})
                # data_set.update({'material_type': material.material_type})
                data_set.update(width)
                data_set.update(color)

                # Get Price of the first material inventory in
                for item in material_inventory:
                    if item.material_stock_left > 0:
                        data_set.update({'unit_price': item.material_cost})
                        data_set.update({'stock_left': item.material_stock_left})
                        break
                    # Set price and stock to zero when empty
                    if item.material_stock_left == 0:
                        data_set.update({'unit_price': 0})
                        data_set.update({'stock_left': 0})
                material_inventory_data.append(data_set)

        # print(material_inventory_data)
        # return JsonResponse({"data": "data"}, safe=False)
        return JsonResponse(material_inventory_data, safe=False)

    def post(self, request):
        data = json.loads(request.body.decode('utf-8'))
        inventory_material_name = data['inventory_material_name']
        supplier = data['supplier']['company_name']
        material_quantity = data['material_quantity']
        price_per_unit = data['price_per_unit']
        total_cost = data['total_cost']
        ordered_date = data['ordered_date']
        inventory_material_note = data['inventory_material_note']

        obj, create = Supplier.objects.get_or_create(company_name=supplier)

        if material_quantity == "": 
            material_quantity = 0 
        else: 
            material_quantity = Decimal(material_quantity)

        if inventory_material_name == "": return JsonResponse({'label':'inventory_material_name', 'message':'Product name is required'}, status=500)
        if material_quantity == 0: return JsonResponse({'label':'material_quantity', 'message':'Quantity is required'}, status=500)

        createMaterialInventoryInstance = RawMaterials_Inventory.objects.create(
            material_name = RawMaterials.objects.get(material_name=inventory_material_name),
            supplier = obj,
            quantity = material_quantity,
            material_stock_left = material_quantity,
            material_cost = price_per_unit,
            material_total_cost = total_cost,
            ordered_date = ordered_date,
            inventory_note = inventory_material_note,
        )

        createRawMaterialsInventoryTransactionInstance = RawMaterials_InventoryTransaction.objects.create(
            transaction_date = ordered_date,
            materials_inventory_pk = createMaterialInventoryInstance
        )

        return JsonResponse({"message": f"Successfully added Product Name:{inventory_material_name} Quantity:{material_quantity} Order Date:{ordered_date}"})
    
    def put(self, request, id):
        data = json.loads(request.body.decode('utf-8'))
        material_inventory_item = get_object_or_404(RawMaterials_Inventory, pk=id)
        material_name = get_object_or_404(RawMaterials, material_name=material_inventory_item.material_name)

        # print(">>>", material_inventory_item)
        # print(material_inventory_item.material_cost, " -->> ", data['price_per_unit'])
        # print(material_inventory_item.material_total_cost, " -->> ", data['total_cost'])
        # print("-------------------")

        message = costChangeMessage(material_inventory_item, "material_cost", data['price_per_unit'])

        
        # Need to update Change in Material Inventory first.
        # Computations below are based on Material Inventory already changed.
        material_inventory_item.material_cost = Decimal(data['price_per_unit'])
        material_inventory_item.material_total_cost = Decimal(data['total_cost'])
        material_inventory_item.save()

        # START MATERIAL COST CHANGE UPDATE INVENTORY COST
        # Get the material_inv that changed price using material_inv.pk
        # Get only material_inv.pk that has product_inv.pk (Meaning get mat_inv transactions that already created a product inventory)
        material_inventory_trans = RawMaterials_InventoryTransaction.objects.filter(~Q(product_inventory_pk=None), materials_inventory_pk=material_inventory_item)
        for item in material_inventory_trans:

            # each ITEM allows me to get the product_inventory PK
            get_product_inventory = get_object_or_404(Product_Inventory, pk=item.product_inventory_pk.pk)
            # print(get_product_inventory)

            # After getting each Product_Inventory PK. Query RawMaterials_InventoryTransaction again as prod_inv_pk.
            # calculate new Product_Inventory TOTAL COST using RawMaterials_InventoryTransaction QUANTITY and U/PRICE
            materials_trans = RawMaterials_InventoryTransaction.objects.filter(product_inventory_pk=get_product_inventory.pk)
            # After getting each Product_Inventory PK. Query InventoryTransaction again as prod_inv_pk.
            # calculate new Sales TOTAL COST using InventoryTransaction QUANTITY and U/PRICE
            inventory_trans = InventoryTransaction.objects.filter(~Q(sales_pk=None), inventory_pk=get_product_inventory.pk)
            # print(inventory_trans)

            new_inv_cost = 0
            for mat in materials_trans:
                # Get the updated Material_Inventory.material_cost that was updated above "material_inventory_item.save()"
                # This code below is only used to compute for NEW TCOST
                new_inv_cost += mat.materials_inventory_pk.material_cost * abs(mat.m_quantity)
            #     print("_-------_")
            # print(">>>>>>>>>>>>>")
            # print("New total Cost for ", get_product_inventory, " : ", new_inv_cost, " UCOST ", Decimal(new_inv_cost)/get_product_inventory.quantity)
            # print("UCost ", get_product_inventory.product_cost, " New Ucost",  Decimal(new_inv_cost)/get_product_inventory.quantity)
            # print("TCost ", get_product_inventory.product_total_cost, " New Tcost",  new_inv_cost)

            get_product_inventory.product_cost = round(Decimal(new_inv_cost) / get_product_inventory.quantity, 2)
            get_product_inventory.product_total_cost = round(new_inv_cost, 2)
            get_product_inventory.save()
        # END MATERIAL COST CHANGE UPDATE INVENTORY COST
            
            # START INVENTORY COST CHANGE, UPDATE SALES COST
            # Needs to wait until prod_inv ucost change before doing changes to sales ucost
            for sale in inventory_trans:
                sale.sales_pk.sales_unit_cost = sale.inventory_pk.product_cost
                sale.sales_pk.sales_total_cost = sale.inventory_pk.product_cost * abs(sale.p_quantity)
                sale.sales_pk.save()
            # END INVENTORY COST CHANGE, UPDATE SALES COST

            
        


        # return JsonResponse({"message": "Feature has not yet been added. Please Contact me MASTER JOSEPH"}, status=404)
        return JsonResponse({'message': f"Successfully updated {message} {material_name}", 'variant': 'success'}, safe=False)
    
    def delete(self, request, id):
        material_inventory_item = get_object_or_404(RawMaterials_Inventory, pk=id)
        item_inventory_transaction = RawMaterials_InventoryTransaction.objects.filter(materials_inventory_pk=material_inventory_item)

        for trans in item_inventory_transaction:
            if trans.product_inventory_pk is not None:
                return JsonResponse({"message": f"Delete action failed. {material_inventory_item.material_name} already has Inventory record."}, status=404)
        
            
        # No need to loop if there's no prod_inventory record. Meaning there's only one entry of this mat_inv
        try:
            item_inventory_transaction.delete()
            material_inventory_item.delete()
        except ProtectedError:
            return JsonResponse({"message": f"Delete action failed. {material_inventory_item.material_name} already has linked records."}, status=404)
        print(material_inventory_item.material_name)
        return JsonResponse({"message": f"{material_inventory_item.material_name} has successfully deleted."})

class RawMaterialsInventoryHistoryPageView(APIView):
    permission_classes = (permissions.DjangoModelPermissions,)
    queryset = RawMaterials_InventoryTransaction.objects.all() # This is needed even we don't use it to perform permission_classes

    def get(self, request, material_name):
        material_inventory_transaction = RawMaterials_InventoryTransaction.objects.all().order_by('transaction_date', "created_at")
        # m_inventory_transaction = RawMaterials_InventoryTransaction.objects.filter(materials_inventory_pk__material_name=RawMaterials.objects.get(material_name="Material 1").pk)
        try:
            material = RawMaterials.objects.get(material_name=material_name)
        except RawMaterials.DoesNotExist:
            return JsonResponse({"data": "No results found"}, safe=False)

        data_list = []
        running_total = 0
        for item in material_inventory_transaction:
            if item.materials_inventory_pk.material_name == material:
                if not item.product_inventory_pk==None:
                    try:
                        get_material_quantity_deducted = abs(item.m_quantity)
                    except RawMaterials_Product.DoesNotExist:
                        return JsonResponse({"data": "No results found"}, safe=False)
                    running_total -= get_material_quantity_deducted
                    data_set = {'transaction_date': item.transaction_date}
                    data_set.update({"material": item.materials_inventory_pk.material_name.material_name})
                    data_set.update({"supplier": item.product_inventory_pk.supplier.company_name})
                    data_set.update({"product": item.product_inventory_pk.product_name.product_name})
                    data_set.update({"quantity": abs(item.m_quantity)})
                    data_set.update({"stock": ""})
                    data_set.update({"uprice": item.materials_inventory_pk.material_cost})
                    data_set.update({"total": get_material_quantity_deducted})
                    data_set.update({"running_total": running_total})
                    data_set.update({"inv_id": item.product_inventory_pk.pk})
                    data_set.update({"id": item.pk})
                    data_set.update({"type": "prod"})
                    data_list.append(data_set)
                else:
                    running_total += item.materials_inventory_pk.quantity
                    data_set = {'transaction_date': item.transaction_date}
                    data_set.update({"material": item.materials_inventory_pk.material_name.material_name})
                    data_set.update({"supplier": item.materials_inventory_pk.supplier.company_name})
                    data_set.update({"product": ""})
                    data_set.update({"quantity": item.materials_inventory_pk.quantity})
                    data_set.update({"stock": item.materials_inventory_pk.material_stock_left})
                    data_set.update({"uprice": item.materials_inventory_pk.material_cost})
                    data_set.update({"total": item.materials_inventory_pk.quantity})
                    data_set.update({"running_total": running_total})
                    data_set.update({"inv_id": item.materials_inventory_pk.pk})
                    data_set.update({"id": item.pk})
                    data_set.update({"type": "mat"})
                    data_list.append(data_set)
                    
        return JsonResponse(data_list, safe=False)
    def post(self, request):
        pass

class ProductsPageView(APIView):
    permission_classes = (permissions.DjangoModelPermissions,)
    queryset = Product.objects.all() # This is needed even we don't use it to perform permission_classes

    def get(self, request, id=None, *args, **kwargs):
        product = Product.objects.all()

        # Check if there is a product
        if not product.exists():
            return JsonResponse([],safe=False)
        if id is not None:
            product_item = get_object_or_404(Product, pk=id)
            if product_item.product_type == 'IMPORTED' or product_item.product_type == 'LOCAL_PURCHASE':
                product_serializer = ProductSerializer(product_item)
                return JsonResponse(product_serializer.data, safe=False)

            prod_mat = RawMaterials_Product.objects.filter(product=product_item)
            sample = RawMaterials_ProductSerializer(prod_mat, many=True)
            product_serializer = ProductSerializer(product_item)
            return JsonResponse(sample.data, safe=False)


        product_serializer = ProductSerializer(product, many=True)
        return JsonResponse(product_serializer.data, safe=False)
    
    def post(self, request):
        data = json.loads(request.body.decode('utf-8'))
        product_name = data['product_name']
        product_min_stock = data['product_min_stock']
        product_unit = data['product_unit']
        product_note = data['product_note']
        inventory_type = data['inventory_type']

        # Validation
        validation = registerNameValidation(product_name, product_min_stock, inventory_type, "product")
        if validation:
            return JsonResponse(validation, status=500)
        # Check if Product exists
        chk_product_name = Product.objects.filter(product_name__iexact=product_name)
        if chk_product_name:
            return JsonResponse({'label':'product_name', 'message':'Product Already Exists'}, status=500)

        # Create New Product
        create_product = Product.objects.create(
            product_name = product_name,
            product_min_stock = product_min_stock,
            product_unit = Unit.objects.get(unit_name=product_unit),
            product_note = product_note,
        )

        # Creates RawMaterials_Product model for every materials listed
        # with the same product that was just created above
        if inventory_type == 'MANUFACTURED':
            create_product.product_type = inventory_type
            create_product.save()
            material_list = data['materials']
            for item in material_list:
                # print(item['material'], "---", item['quantity'])
                RawMaterials_Product.objects.create(product=create_product, materials=RawMaterials.objects.get(material_name=item['material']), quantity=item['quantity'])
            
            return JsonResponse({"message": f"Successfully added Product:{product_name} Unit:{product_unit} Minimum Stock:{product_min_stock}"})
            # return JsonResponse({"data":"data"}, safe=False)
            
        # Finishes creating product here. When inventory_type == IMPORTED
        # inventory_type below is == IMPORTED
        create_product.product_type = inventory_type
        create_product.save()

        return JsonResponse({"message": f"Successfully added Product:{product_name} Unit:{product_unit} Minimum Stock:{product_min_stock}"})

    def put(self, request, id):
        product = get_object_or_404(Product, pk=id)
        data = json.loads(request.body.decode('utf-8'))

        product_name = data['product_name']
        product_min_stock = data['product_min_stock']
        product_unit = data['product_unit']
        product_note = data['product_note']
        inventory_type = data['inventory_type']
        
        if (product.product_name).lower() == product_name.lower():
            if Decimal(product_min_stock) < 0:
                return {'label':'product_min_stock', 'message':'Invalid Entry'}
        else:
            validation = registerNameValidation(product_name, product_min_stock, "no data", "product")
            if validation:
                return JsonResponse(validation, status=500)
            chk_product_name = Product.objects.filter(product_name__iexact=product_name)
            if chk_product_name:
                return JsonResponse({'label':'product_name', 'message':'Product Already Exists'}, status=500)

        product.product_name = product_name
        product.product_min_stock = product_min_stock
        product.product_unit = Unit.objects.get(unit_name=product_unit)
        product.product_note = product_note
        product.save()

        return JsonResponse({"message": "Successfully saved changes"})

        # Postponed
        """""
        # ON HOLD. REMOVE A MATERIAL NEEDS TO DELETE RECORDS FROM RAWMAT_PROD && RAWMAT_INV_TRANS. THEN
        # RETURN QTY SINCE RECORD HAS BEEN DELETED.
        # if inventory_type == 'MANUFACTURED':
        #     material_list = data['materials']
        #     quantity = data['quantity']
        #     my_dict = dict(zip(material_list, quantity))

        #     getMaterialProduct = RawMaterials_Product.objects.filter(product=product)
        #     getMaterialItems = []
        #     for item in my_dict:
        #         # print(item, "is the material ", my_dict[item], "is the quantity")
        #         getMaterialItems.append((item, my_dict[item]))

        #     # Check which ever is higher use for range to get exept
        #     # Get diff to see if we're going to add or deduct items
        #     if len(getMaterialProduct) < len(getMaterialItems):
        #         rangeDiff = len(getMaterialItems) - len(getMaterialProduct)
        #         getRange = len(getMaterialItems)
        #     else:
        #         rangeDiff = len(getMaterialItems) - len(getMaterialProduct)
        #         getRange = len(getMaterialProduct)

        #     index = 0
        #     for item in getMaterialProduct:
        #         print(getRange)
        #         try:
        #             item.product = product
        #             mat, qty = getMaterialItems[index]
        #         except IndexError as err:
        #             print("line300, ",err)
        #             if rangeDiff < 0 :
        #                 print("deleted ",item.pk, ": ", item.product, " && ", item.materials)
        #                 # getMaterialProduct[index]
        #             else:
        #                 print("ADDED " )
        #         index += 1
            
            # print(rangeDiff)

                    # print("need to delete this ", getMaterialProduct[index].pk)
                    # createNewInstance = RawMaterials_Product(
                    #     product=product,

                    # )
                # if len(getMaterialProduct) > len(getMaterialItems):
                #     try:
                #         print(getMaterialProduct[index].pk)
                #         mat, qty = getMaterialItems[index]
                #         getMaterialProduct[index].product = product
                #         getMaterialProduct[index].materials = RawMaterials.objects.get(material_name=mat)
                #         getMaterialProduct[index].quantity = qty
                #     except IndexError as err:
                #         print("line300, ",err)
                #         print("need to delete this ", getMaterialProduct[index].pk)
                # if len(getMaterialProduct) < len(getMaterialItems):
                #     try:
                #         print(getMaterialProduct[index].pk)
                #         mat, qty = getMaterialItems[index]
                #         getMaterialProduct[index].product = product
                #         getMaterialProduct[index].materials = RawMaterials.objects.get(material_name=mat)
                #         getMaterialProduct[index].quantity = qty
                #     except IndexError as err:
                #         print("line311, ",err)
                #         print("need to create this ", getMaterialProduct[index].pk)
                
                # if len(getMaterialProduct) > len(getMaterialItems):
                #     print("Delete a material ingredient")
                #     pass
                # if len(getMaterialProduct) < len(getMaterialItems):
                #     print("Create a material ingredient")
                #     pass
                # print("Update material ingredient")
                # mat, qty = getMaterialItems[index]
                # getMaterialProduct[index].product = product
                # getMaterialProduct[index].materials = RawMaterials.objects.get(material_name=mat)
                # getMaterialProduct[index].quantity = qty

            # for item in getMaterialProduct:
            #     print(item.product, "--", item.materials, "--", item.quantity)
        """
                
    def delete(self, request, id):
        product = get_object_or_404(Product, pk=id)
        product_inventory = Product_Inventory.objects.filter(product_name=product)
        material_product = RawMaterials_Product.objects.filter(product=product)
        
        if not product_inventory:
            if product.product_type == "MANUFACTURED":
                for item in material_product:
                    # print("GOING to delete this ", item)
                    item.delete()
            # print("delete product here")
            product.delete()
            return JsonResponse({"message": f"{product.product_name} has successfully deleted."})

        return JsonResponse({"message": f"Delete action failed. {product.product_name} already has linked records."}, status=404)

class ProductInventoryPageView(APIView):
    permission_classes = (permissions.DjangoModelPermissions,)
    queryset = Product.objects.all() # This is needed even we don't use it to perform permission_classes

    def get(self, request, id=None):
        products = Product.objects.all()
        # Check if there is a product
        if not products.exists():
            return JsonResponse([], safe=False)
        if id is not None:
            product_inventory_item = get_object_or_404(Product_Inventory, pk=id)
            product_inventory_serializer = ProductInventorySerializer(product_inventory_item)
            return JsonResponse(product_inventory_serializer.data, safe=False)

        product_inventory_data = []
        for product in products:
            product_inventory = Product_Inventory.objects.filter(product_name=product.pk)
            product_unit = Unit.objects.get(unit_name=product.product_unit).unit_name
            if product_inventory.exists():
                product_stock_left = product_inventory.aggregate(total_inventory=Sum('product_stock_left'))
                # print(product.product_name, "--",  product_stock_left)
                width, color = productInventoryStatus(product.product_min_stock, *product_stock_left.values())

                last_ordered_date = product_inventory[len(product_inventory)-1].ordered_date
                order_update = product_inventory[len(product_inventory)-1].order_update # Get the last update date

                data_set = {'product_name': product.product_name}
                data_set.update({'product_pk': product.pk})
                data_set.update(product_stock_left)
                data_set.update({"product_unit" : product_unit})
                data_set.update({'last_ordered_date': last_ordered_date})
                data_set.update({'order_update': order_update})
                data_set.update({'product_type': product.product_type})
                data_set.update(width)
                data_set.update(color)

                # Get Price of the first inventory in
                for item in product_inventory:
                    if item.product_stock_left > 0:
                        data_set.update({'unit_price': item.product_cost})
                        data_set.update({'stock_left': item.product_stock_left})
                        break
                    # Set price and stock to zero when empty
                    if item.product_stock_left == 0:
                        data_set.update({'unit_price': 0})
                        data_set.update({'stock_left': 0})
                product_inventory_data.append(data_set)
                
        return JsonResponse(product_inventory_data, safe=False)

    def post(self, request):
        data = json.loads(request.body.decode('utf-8'))
        inventory_product_name = data['inventory_product_name']
        supplier = data['supplier']['company_name']
        inventory_quantity = data['inventory_quantity']
        ordered_date = datetime.datetime.strptime(data['ordered_date'], "%Y-%m-%d").date()

        obj, create = Supplier.objects.get_or_create(company_name=supplier)
        data['supplier']['company_name'] = obj
        
        # Other Validation with prod_name, inv_qty are in
        # "validateAddProductInventory()" located validations.py
        # validations made by "validateAddProductInventory()" are pre-POST request
        if inventory_product_name == "": return JsonResponse({'label':'inventory_product_name', 'message':'Product name is required'}, status=500)
        if inventory_quantity == 0: return JsonResponse({'label':'inventory_quantity', 'message':'Quantity is required'}, status=500)

        # Validation are in validations.py under "validateAddProductInventory()"
        # Check product_type, Prevent user from creating product before initial material inventory
        # Check each material total stock if there is enough to create a product
        # Query only material inventory before or equal product creation date
    
        get_product = Product.objects.get(product_name=inventory_product_name)
        if get_product.product_type == "MANUFACTURED":

            get_material_inventory_pk = [] # Use to store material inventory pk for transaction purpose
            for material in get_product.ingredients.all():

                material_name = RawMaterials.objects.get(material_name=material)
                # Query material inventory less than or equal ordered date
                get_material_inventory = RawMaterials_Inventory.objects.filter(material_name=material_name, ordered_date__lte=ordered_date)

                # Get quantity for each material needed for the product
                get_material_qty_formula = RawMaterials_Product.objects.get(materials=material_name, product=get_product).quantity
                # material_qty_formula * quantity of inventory that needs to be created
                # Check if material has enough stock to create number of product
                #                               3 * 2 = 6 ----- 3 * 1 = 3
                total_quantity_needed = Decimal(inventory_quantity) * Decimal(get_material_qty_formula)

                addProductionInventoryProcedure(get_material_inventory, total_quantity_needed, get_material_inventory_pk)
        
            
        productInventoryInstance = create_product_inventory_obj(data)

        createInventoryTransactionInstance = InventoryTransaction.objects.create(
            transaction_date = Product_Inventory.objects.get(pk=productInventoryInstance.pk).ordered_date,
            inventory_pk = Product_Inventory.objects.get(pk=productInventoryInstance.pk)
        )
                            
        # Get the number of material inventory items to fill product quantity ordered
        if get_product.product_type == "MANUFACTURED":
            for item in get_material_inventory_pk:
                RawMaterialsInventoryTransactionInstance = RawMaterials_InventoryTransaction.objects.create(
                    transaction_date = ordered_date,
                    product_inventory_pk = productInventoryInstance,
                    materials_inventory_pk = RawMaterials_Inventory.objects.get(pk=item[0]),
                    m_quantity = item[1]
                )

        return JsonResponse({"message": f"Successfully added Product Name:{inventory_product_name} Quantity:{inventory_quantity} Order Date:{ordered_date}"})

    def put(self, request, id):
        data = json.loads(request.body.decode('utf-8'))
        product_inventory_item = get_object_or_404(Product_Inventory, pk=id)
        product_name = get_object_or_404(Product, product_name=product_inventory_item.product_name)

        message = costChangeMessage(product_inventory_item, "product_cost", data['price_per_unit'])

        product_inventory_item.product_cost = Decimal(data['price_per_unit'])
        product_inventory_item.product_total_cost = Decimal(data['total_cost'])
        product_inventory_item.save()

        inventory_trans = InventoryTransaction.objects.filter(~Q(sales_pk=None), inventory_pk=product_inventory_item.pk)
        for sale in inventory_trans:
            sale.sales_pk.sales_unit_cost = sale.inventory_pk.product_cost
            sale.sales_pk.sales_total_cost = sale.inventory_pk.product_cost * abs(sale.p_quantity)
            sale.sales_pk.save()

        # return JsonResponse({'message': f"Successfully updated Inventory", 'variant': 'success'}, safe=False)
        return JsonResponse({'message': f"Successfully updated {message} {product_name}", 'variant': 'success'}, safe=False)
    
    def delete(self, request, id):
        print(id)
        product_inventory = get_object_or_404(Product_Inventory, pk=id)
        item_inventory_transaction = InventoryTransaction.objects.filter(inventory_pk=product_inventory)

        for trans in item_inventory_transaction:
            if trans.sales_pk is not None:
                return JsonResponse({"message": f"Delete action failed. {product_inventory.product_name} already has Sales record."}, status=404)

        if product_inventory.product_name.product_type == "MANUFACTURED":
            try:
                item_inventory_transaction.delete()
                material_inventory_trans = RawMaterials_InventoryTransaction.objects.filter(product_inventory_pk=product_inventory.pk)
                for item in material_inventory_trans:
                    print("pk ", item.pk, "   M Quantity ", item.m_quantity)
                    material_inv = get_object_or_404(RawMaterials_Inventory, pk=item.materials_inventory_pk.pk)
                    print("Material Stock Left", material_inv.pk, "--", material_inv.material_stock_left)
                    print("New Stock Left ", material_inv.pk, "--", material_inv.material_stock_left + abs(item.m_quantity))
                    material_inv.material_stock_left += abs(item.m_quantity)
                    material_inv.save()
                    item.delete()
                product_inventory.delete()

            except ProtectedError:
                return JsonResponse({"message": f"Delete action failed. {product_inventory.product_name} already has linked records."}, status=404)
            return JsonResponse({"message": f"{product_inventory.product_name} has successfully deleted. RAW MATERIALS will now be returned."})

        # No need to loop if there's no sales record. Meaning there's only one entry of this prod_inv
        try:
            item_inventory_transaction.delete()
            product_inventory.delete()
        except ProtectedError:
            return JsonResponse({"message": f"Delete action failed. {product_inventory.product_name} already has linked records."}, status=404)
        print(product_inventory.product_name)
        return JsonResponse({"message": f"{product_inventory.product_name} has successfully deleted."})


class InventoryHistoryPageView(APIView):
    permission_classes = (permissions.DjangoModelPermissions,)
    queryset = InventoryTransaction.objects.all() # This is needed even we don't use it to perform permission_classes

    def get(self, request, product_pk):
        print(product_pk)
        try:
            product = Product.objects.get(pk=product_pk)
        except Product.DoesNotExist:
            return JsonResponse({"data": "No results found"}, safe=False)
        inventory_transactions = InventoryTransaction.objects.filter(inventory_pk__product_name=product).order_by('transaction_date', "created_at")
                
        data_list = []
        running_qty = 0

        for item in inventory_transactions:
            if item.inventory_pk and item.p_quantity is None:
                running_qty += item.inventory_pk.quantity
                data_set = {'product_name': item.inventory_pk.product_name.product_name} # Model.foreignkey.foreignkey
                data_set.update({"cust_supp": item.inventory_pk.supplier.company_name}) # Model.foreignkey.foreignkey
                data_set.update({"transaction_date": item.transaction_date})
                data_set.update({"quantity": item.inventory_pk.quantity})
                data_set.update({"stock": item.inventory_pk.product_stock_left})
                data_set.update({"u_cost": item.inventory_pk.product_cost})
                data_set.update({"running_quantity": running_qty})
                data_set.update({"type": "inv"})
                data_set.update({"id": item.inventory_pk.pk}) # pk of product_inv
                data_set.update({"pk": item.pk}) # pk of prod_inv_trans
                data_list.append(data_set)
            else:
                running_qty -= item.sales_pk.sales_quantity
                data_set = {'product_name': item.sales_pk.product_name.product_name} # Model.foreignkey.foreignkey
                data_set.update({"cust_supp": item.sales_pk.customer.company_name}) # Model.foreignkey.foreignkey
                data_set.update({"transaction_date": item.transaction_date})
                data_set.update({"quantity": item.sales_pk.sales_quantity})
                data_set.update({"u_cost": item.sales_pk.sales_unit_cost})
                data_set.update({"u_price": round(Decimal(item.sales_pk.sales_unit_price) / Decimal(1.12), 2)}) # Gross selling price
                data_set.update({"running_quantity": running_qty})
                data_set.update({"type": "sales"})
                data_set.update({"id": item.sales_pk.pk}) # pk of sales
                data_set.update({"pk": item.pk})  # pk of prod_inv_trans
                data_list.append(data_set)
                    

        # asset_json = json.dumps({"data": [asset.to_dict() for asset in page_obj.object_list]})
        # return JsonResponse(page_obj.object_list, safe=False)
        return JsonResponse(data_list, safe=False)
    def post(self, request):
        pass

class SalesPageView(APIView):
    permission_classes = (permissions.DjangoModelPermissions,)
    queryset = Sales.objects.all() # This is needed even we don't use it to perform permission_classes
    
    def get(self, request, id=None, option=None, **kwargs):
        sales = Sales.objects.all().order_by("-sales_date", "sales_updated")
        # Check if there is a sales
        if not sales.exists():
            return JsonResponse([],safe=False)
        if id is not None:
            sales_item = get_object_or_404(Sales, pk=id)
            sales_serialized = SalesSerializer(sales_item)

            get_customer = get_object_or_404(Customer, company_name=sales_serialized.data['customer'])
            serialized_data = sales_serialized.data
            serialized_data['customer'] = {"id":get_customer.pk, "company_name": get_customer.company_name}

            return JsonResponse(serialized_data, safe=False)

        getYear = datetime.date.today().year
        getEndDay = calendar.monthrange(getYear, 12)
        # reassign getYear if filter exists
        if option is not None:
            getYear = int(option)

        getStartDate = str(getYear) + '-01-01'
        getEndDate = str(getYear) + '-12-' + str(getEndDay[1])

        date_range = getDateRange(getStartDate, getEndDate)
        data_list = []
        for index in date_range:
            sales = Sales.objects.filter(sales_date__gte=index[0], sales_date__lte=index[1]).order_by('sales_invoice', 'sales_date', 'created_at', 'customer', 'product_name')
            sales_commulative = Sales.objects.filter(sales_date__gte=date_range[0][0], sales_date__lte=index[1])

            sales_serializer = SalesSerializer(sales, many=True)
            new_serializer = list(sales_serializer.data)

            sales_list = getSalesTotals(sales, "TOTAL_SALES") # helper.py
            cumm_sales_list = getSalesTotals(sales_commulative, "CUMM_TOTAL_SALES") # helper.py

            data_title = str(index[0].year) + "-" + str(index[0].month)
            new_serializer.append(sales_list)
            new_serializer.append(cumm_sales_list)
            new_serializer.append({"data_title":data_title})
            data_list.append(new_serializer)

        return JsonResponse(data_list, safe=False)

    def post(self, request):
        data = json.loads(request.body.decode('utf-8'))
        sales_invoice = data['sales_invoice']
        sales_date = datetime.datetime.strptime(data['sales_date'], "%Y-%m-%d").date()
        customer = data['customer']['company_name']

        products = data['products']
        
        if sales_invoice == '':
            sales_invoice = f'noinv-{sales_date}-' + uuid.uuid4()
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
            product_inventory = Product_Inventory.objects.filter(product_name = Product.objects.get(product_name=item['product']), ordered_date__lte=sales_date)
            for i in data:
                print(i, " : ", data[i])
            # Procedure Deducts Inventory Stock, creates Sales Instance, creates InventoryHistory Instance
            addSalesProcedure(product_inventory, item['sales_quantity'], data)
            
        return JsonResponse({"message": "Sales successfully Added."})
        # return JsonResponse({"message": f"Sales successfully saved.\nInvoice: {invoice_obj} Customer: {obj.company_name} Order Date:{sales_date.strftime('%b-%d-%Y')}"})

    def put(self, request, id):
        data = json.loads(request.body.decode('utf-8'))
        sales_date = datetime.datetime.strptime(data['sales_date'], "%Y-%m-%d").date()
        sales_invoice = data['sales_invoice']
        customer = data['customer']['company_name']

        # Allows the user to insert Sales into an invoice
        if sales_invoice == '':
            sales_invoice = uuid.uuid4()
        invoice_obj, created = SalesInvoice.objects.get_or_create(sales_invoice=sales_invoice, invoice_date=sales_date)
        cust_obj = get_object_or_404(Customer, company_name=customer)

        # reassign values back as validated data
        data['sales_invoice'] = invoice_obj
        data['customer']['company_name'] = cust_obj
        # Save changes
        updated_sales = update_sales_obj(id, data)
        updated_sales.save()
        
        """""
        # if not sales.product_name.product_name == product_name or not sales.sales_date == sales_date or not sales.sales_quantity == sales_quantity:
        #     print("im here")
        #     # sales_margin = Decimal(total_price) - Decimal(total_cost)
        #     sales_margin_percent = addSalesValidation(product_name, customer)

        #     # Get product name inventory less that sales date. Nearest item to the sales date first
        #     product_inventory = Product_Inventory.objects.filter(
        #         product_name=Product.objects.get(product_name=sales.product_name), 
        #         ordered_date__lte=sales.sales_date
        #     ).order_by('-ordered_date')

        #     # Return sales quantity to inventory
        #     quantity_to_return = sales.sales_quantity
        #     for item in product_inventory:
        #         # print("line 546 ",item.ordered_date, "--", item.quantity, "--", item.product_stock_left )
        #         #     print("nothing to do")
        #         quantity_to_return -= item.quantity - item.product_stock_left
        #         print(item.quantity - item.product_stock_left)
        #         if quantity_to_return <= 0:
        #             print("line552 ", quantity_to_return)
        #             print("line553 ", sales.sales_quantity)
        #             item.product_stock_left += sales.sales_quantity
        #             item.save()
        #             print("line 553 ",item.ordered_date, "--", item.quantity, "--", item.product_stock_left )
        #             break
        #         if quantity_to_return > 0:
        #             item.product_stock_left = item.quantity
        #             item.save()
        #             print("line 558 ",item.ordered_date, "--", item.quantity, "--", item.product_stock_left )

        #     # Query product inventory again different value for product name and sales date
        #     # Prevents the User to input sales before starting Inventory
        #     product_inventory = Product_Inventory.objects.filter(
        #         product_name=Product.objects.get(product_name=product_name), 
        #         ordered_date__lte=sales_date
        #     )
        #     for item in product_inventory:
        #         print(item.product_stock_left)

        #     sales.sales_date = sales_date
        #     sales.product_name = Product.objects.get(product_name=product_name)
        #     sales.sales_quantity = sales_quantity
        #     sales.sales_unit_cost = unit_cost
        #     sales.sales_total_cost = total_cost
        #     sales.sales_unit_price = unit_price
        #     sales.tax_percent = tax_percent
            
        #     print(sales_date)

        #     # Deduct sales quantity from stock left. And Update stock left values
        #     addSalesProcedure(product_inventory, sales_quantity)

        # sales.save()
        # inventory_transaction = InventoryTransaction.objects.get(sales_pk=Sales.objects.get(pk=id))
        """""

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
        except ProtectedError:
            return JsonResponse({"message": f"Delete action failed. {sales.product_name} already has linked records."}, status=404)
        return JsonResponse({"message": f"Invoice#: {sales.sales_invoice} {sales.product_name} has successfully deleted."})

class SalesInvoicePageView(APIView):
    permission_classes = (permissions.DjangoModelPermissions,)
    queryset = SalesInvoice.objects.all() # This is needed even we don't use it to perform permission_classes

    def get(self, request, id=None):
        invoice_list = SalesInvoice.objects.all()
        if id:
            print("id is ", id)
        data_list = []
        for invoice in invoice_list:
            invoice_total = 0
            data_set = {"invoice_num": invoice.sales_invoice}
            data_set.update({"id": invoice.pk})
            data_set.update({"customer": ""})
            data_set.update({"invoice_date": (invoice.invoice_date).strftime('%Y-%m-%d')})
            data_set.update({"invoice_gross": 0})
            data_set.update({"tax_rate": 12})
            data_set.update({"invoice_vat": 0})
            data_set.update({"invoice_total": 0})
            # data_set.update({"invoice_profit": 0})
            # data_set.update({"invoice_margin": 0})
            data_set.update({"invoice_status": invoice.invoice_status})
            data_set.update({"invoice_paid_date": invoice.invoice_paid_date})
            data_set.update({"invoice_note": invoice.invoice_note})
            data_set.update({"sales_data": []})
            sales = Sales.objects.filter(sales_invoice=invoice)
            for sale in sales:
                data_set['customer'] = sale.customer.company_name

                sale_set = {"pk": sale.pk}
                sale_set.update({"product": sale.product_name.product_name})
                sale_set.update({"quantity": sale.sales_quantity})
                sale_set.update({"ucost": sale.sales_unit_cost})
                sale_set.update({"tcost": sale.sales_total_cost})

                sale_set.update({"gross_uprice": round(sale.sales_unit_price / Decimal(1.12), 2) })
                sale_set.update({"gross_tprice": sale.sales_gross_price })
                sale_set.update({"uprice": round(sale.sales_unit_price, 2) })
                sale_set.update({"tprice": sale.sales_total_price })

                sale_set.update({"vat": sale.sales_VAT })
                sale_set.update({"profit": sale.sales_margin })
                sale_set.update({"profit_margin": sale.sales_margin_percent })

                data_set['invoice_gross'] += round(sale.sales_gross_price, 2)
                data_set['tax_rate'] = round(sale.tax_percent, 0)
                data_set['invoice_vat'] += round(sale.sales_VAT, 2)
                data_set['invoice_total'] += round(sale.sales_total_price, 2)
                # data_set['invoice_profit'] += round(sale.sales_margin, 2)
                # data_set['invoice_margin'] += round(sale.sales_margin / 100, 2)
                data_set['sales_data'].append(sale_set)

            data_list.append(data_set)
            # print(sales)
        # print(invoice_list)
        return JsonResponse(data_list, safe=False)
        pass
    def post(self, request):
        pass

    def patch(self, request, id):
        data = json.loads(request.body.decode('utf-8'))
        invoice_item = get_object_or_404(SalesInvoice, pk=id)

        invoice_item.invoice_status = data['invoice_status']
        if data['pay_date'] == "":
            data['pay_date'] = None
        
        invoice_item.invoice_paid_date = data['pay_date']
        invoice_item.save()
        return JsonResponse({"message": f"Invoice#: {invoice_item.sales_invoice} successfully updated."}, safe=False)

    def delete(self, request, id):
        invoice_item = get_object_or_404(SalesInvoice, pk=id)
        try:
            invoice_item.delete()
        except ProtectedError:
            return JsonResponse({"message": f"Delete action failed. Invoice# {invoice_item.sales_invoice} already has linked records."}, status=404)
        return JsonResponse({"message": f"Invoice#: {invoice_item.sales_invoice} has successfully deleted."})

    
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def getSalesInvoice(request):
    data = json.loads(request.body.decode('utf-8'))
    list_invoices = SalesInvoice.objects.all()
    print(data)
    data_str = str(data)
    for invoice in list_invoices:
        if data_str == invoice.sales_invoice:
            return JsonResponse({'label':'sales_invoice', 'message':f'Invoice #{data_str} already been registered'}, status=500)
    return JsonResponse([], safe=False)





class CustomerPageView(APIView):
    permission_classes = (permissions.DjangoModelPermissions,)
    queryset = Customer.objects.all() # This is needed even we don't use it to perform permission_classes
    
    def get(self, request, id=None, *args, **kwargs):
        customer = Customer.objects.all()
        
        # Check if there is a customer
        if not customer.exists():
            return JsonResponse([], safe=False)
        if id is not None:
            customer_item = get_object_or_404(Customer, pk=id)
            customer_serializer = SupplierSerializer(customer_item)
            return JsonResponse(customer_serializer.data, safe=False)

        customer_serializer = CustomerSerializer(customer, many=True)
        return JsonResponse(customer_serializer.data, safe=False)
    
    def post(self, request):
        data = json.loads(request.body.decode('utf-8'))
        company_name, contact_person, contact_number, company_address = data.values()
        company_name = company_name.strip()

        # Check if item exists
        chk_company_name = Customer.objects.filter(company_name__iexact=company_name)
        if chk_company_name:
            return JsonResponse({'label':'company_name', 'message':'Customer Already Exists'}, status=500)
        
        if len(company_name) == 0:
            return JsonResponse({'label':'company_name', 'message':'Invalid Entry'}, status=500)
        
        createCustomerInstance = Customer.objects.create(
            company_name=company_name,
            contact_person=contact_person,
            contact_number=contact_number,
            company_address=company_address,
        )

        return JsonResponse({'message': f"Successfully added {company_name}", 'variant': 'success'})
    
    def put(self, request, id):
        customer = get_object_or_404(Customer, pk=id)
        data = json.loads(request.body.decode('utf-8'))
        company_name = data['company_name']
        contact_person = data['contact_person']
        contact_number = data['contact_number']
        company_address = data['company_address']

        if customer.company_name == company_name:
            customer.contact_person = contact_person
            customer.contact_number = contact_number
            customer.company_address = company_address
            customer.save()
            return JsonResponse({"message": "Successfully saved changes"})
        else:
            validation = registerNameValidation(company_name, 1, "no data", "customer")
            if validation:
                return JsonResponse(validation, status=500)
            chk_company_name = Customer.objects.filter(company_name__iexact=company_name)
            if chk_company_name:
                return JsonResponse({'label':'company_name', 'message':'Customer Already Exists'}, status=500)
        customer.company_name = company_name
        customer.contact_person = contact_person
        customer.contact_number = contact_number
        customer.company_address = company_address
        customer.save()
        return JsonResponse({"message": "Successfully saved changes"})
    
    def delete(self, request, id):
        customer = get_object_or_404(Customer, pk=id)
        try:
            customer.delete()
        except ProtectedError:
            return JsonResponse({"message": f"Delete action failed. {customer.company_name} already has linked records."}, status=404)
        print(customer.company_name)
        return JsonResponse({"message": f"{customer.company_name} has successfully deleted."})

class SupplierPageView(APIView):
    permission_classes = (permissions.DjangoModelPermissions,)
    queryset = Supplier.objects.all() # This is needed even we don't use it to perform permission_classes

    def get(self, request, id=None, *args, **kwargs):
        supplier = Supplier.objects.all()

        # Check if there is a supplier
        if not supplier.exists():
            return JsonResponse([], safe=False)
        if id is not None:
            supplier_item = get_object_or_404(Supplier, pk=id)
            supplier_serializer = SupplierSerializer(supplier_item)
            return JsonResponse(supplier_serializer.data, safe=False)

        supplier_serializer = SupplierSerializer(supplier, many=True)
        return JsonResponse(supplier_serializer.data, safe=False)
    
    def post(self, request):
        data = json.loads(request.body.decode('utf-8'))
        company_name, contact_person, contact_number, company_address = data.values()
        company_name = company_name.strip()

        # Check if item exists
        chk_company_name = Supplier.objects.filter(company_name__iexact=company_name)
        if chk_company_name:
            return JsonResponse({'label':'company_name', 'message':'Supplier Already Exists'}, status=500)
        
        if len(company_name) == 0:
            return JsonResponse({'label':'company_name', 'message':'Invalid Entry'}, status=500)
        
        createSupplierInstance = Supplier.objects.create(
            company_name=company_name,
            contact_person=contact_person,
            contact_number=contact_number,
            company_address=company_address,
        )

        return JsonResponse({'message': f"Successfully added {company_name}", 'variant': 'success'})
    
    def put(self, request, id):
        supplier = get_object_or_404(Supplier, pk=id)
        data = json.loads(request.body.decode('utf-8'))
        company_name = data['company_name']
        contact_person = data['contact_person']
        contact_number = data['contact_number']
        company_address = data['company_address']

        if supplier.company_name == company_name:
            supplier.contact_person = contact_person
            supplier.contact_number = contact_number
            supplier.company_address = company_address
            supplier.save()
            return JsonResponse({"message": "Successfully saved changes"})
        else:
            validation = registerNameValidation(company_name, 1, "no data", "supplier")
            if validation:
                return JsonResponse(validation, status=500)
            chk_company_name = Supplier.objects.filter(company_name__iexact=company_name)
            if chk_company_name:
                return JsonResponse({'label':'company_name', 'message':'Supplier Already Exists'}, status=500)
        supplier.company_name = company_name
        supplier.contact_person = contact_person
        supplier.contact_number = contact_number
        supplier.company_address = company_address
        supplier.save()
        return JsonResponse({"message": "Successfully saved changes"})
    
    def delete(self, request, id):
        supplier = get_object_or_404(Supplier, pk=id)
        try:
            supplier.delete()
        except ProtectedError:
            return JsonResponse({"message": f"Delete action failed. {supplier.company_name} already has linked records."}, status=404)
        print(supplier.company_name)
        return JsonResponse({"message": f"{supplier.company_name} has successfully deleted."})


class UnitPageView(View):
    def get(self, request):
        units = Unit.objects.all()
        
        unit_serializer = UnitSerializer(units, many=True)
        return JsonResponse(unit_serializer.data, safe=False)

class UnitCategoryPageView(View):
    def get(self, request):
        unit_category = UnitCategory.objects.all()
        
        unit_category_serializer = UnitCategorySerializer(unit_category, many=True)
        return JsonResponse(unit_category_serializer.data, safe=False)

class InventorySummaryPageView(APIView):
    permission_classes = (permissions.DjangoModelPermissions,)
    queryset = Product_Inventory.objects.all() # This is needed even we don't use it to perform permission_classes

    def get(self, request):
        pass
    def post(self, request):
        data = json.loads(request.body.decode('utf-8'))
        start_date = data['start']
        end_date = data['end']

        product_inventory = Product_Inventory.objects.filter(ordered_date__gte=start_date, ordered_date__lte=end_date)
        product_inventory_serializer = ProductInventorySerializer(product_inventory, many=True)
        # print(product_inventory_serializer.data)
        data_list = []
        for product in Product.objects.all():
            product_inventory = Product_Inventory.objects.filter(ordered_date__gte=start_date, ordered_date__lte=end_date, product_name=product.pk)
            if product_inventory.exists():
                total_inventory_cost = product_inventory.aggregate(total_cost=Sum('product_total_cost'))
                print(total_inventory_cost.values())
                total_cost = float(*total_inventory_cost.values())
                data_set = ({'product_name': product.product_name})
                data_set.update({'total_cost': total_cost})
                data_list.append(data_set)
        

        return JsonResponse(data_list , safe=False)

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

class SalesSummaryDataTableTotalsView(APIView):
    permission_classes = (permissions.DjangoModelPermissions,)
    queryset = Sales.objects.all() # This is needed even we don't use it to perform permission_classes

    def post(self,request):
        data = json.loads(request.body.decode('utf-8'))
        start_date = data['start']
        end_date = data['end']
        query = data['query']

        sales = Sales.objects.filter(sales_date__gte=start_date, sales_date__lt=end_date)
        # if not sales.exists():
        #     return JsonResponse({"data": "No Sales data to show"})
        
        if query == "ALL":
        #     total_sales_cost = sales.aggregate(total_cost=Sum('sales_total_cost'))
        #     total_sales_price = sales.aggregate(total_price=Sum('sales_total_price'))
        #     total_sales_margin = sales.aggregate(total_margin=Sum('sales_margin'))

        #     sales_cost = float(*total_sales_cost.values())
        #     sales_price = float(*total_sales_price.values())
        #     sales_margin = float(*total_sales_margin.values())

        #     data_set = ({"sales_cost":sales_cost})
        #     data_set.update({"sales_price":sales_price})
        #     data_set.update({"sales_margin":sales_margin})
        #     data_list = [data_set]

            return JsonResponse([], safe=False)
            # return JsonResponse(data_list, safe=False)
        return JsonResponse({"data": "No result found"})



