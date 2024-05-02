from .models import *
from .helper import *
from django.http import JsonResponse
from decimal import Decimal, InvalidOperation
from django.db.models import Sum, Q, Count
import json
import math
import datetime
from django.shortcuts import get_object_or_404
from dateutil.relativedelta import relativedelta
from rest_framework.views import APIView
from rest_framework import permissions
from rest_framework.decorators import permission_classes, api_view


def registerNameValidation(name, min_stock, product_type, register):

    name = name.strip()
    min_stock = Decimal(min_stock)
    
    if len(name) == 0:
        return {'label':f'{register}_name', 'message':'Invalid Entry'}
    if min_stock < 0:
        return {'label':f'{register}_min_stock', 'message':'Invalid Entry'}
    if len(product_type) == 0:
        return {'label':'product_type', 'message':'Product Type is required'}
    return False

def addSalesValidation(product_name, customer):
    if not product_name:
        return JsonResponse({'label':'product_name', 'message':'Product name is required'})
    if not customer:
        return JsonResponse({'label':'customer', 'message':'Customer is required'})

def quantityValidatorHelper(quantity):
    if quantity == "" or quantity is None:
        return 0
    else: 
        return Decimal(quantity)
    
# Validate AddProductInventory (Manufactured)
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def validateAddProductInventory(request):
    data = json.loads(request.body.decode('utf-8'))
    inventory_product_name = data['product_name']
    ordered_date = data['ordered_date']
    inventory_quantity = data['inventory_quantity']

    # Validates quantity, product, and date
    inventory_quantity = quantityValidatorHelper(inventory_quantity)
    if inventory_product_name == "" or ordered_date == "":
        return JsonResponse([], safe=False)
    # format date when it exists
    ordered_date = datetime.datetime.strptime(ordered_date, "%Y-%m-%d").date()

    # Validation 
    # Check product_type, Prevent user from creating product before initial material inventory
    # Check each material total stock if there is enough to create a product
    # Query only material inventory before or equal product creation date
    get_product = Product.objects.get(product_name=inventory_product_name)
    if get_product.product_type == "MANUFACTURED":
        main_data_list = [] # will be returned when the loop finishes
        
        # Get the product instance or product ID
        # Then get ingredients which is connected to RawMaterials_Product ".all()"
        # Which will output all materials listed with product instance of get_product
        for material in get_product.ingredients.all():
            material_name = RawMaterials.objects.get(material_name=material)
            # Get quantity for each material needed for the product
            get_material_qty_formula = RawMaterials_Product.objects.get(materials=material_name, product=get_product).quantity

            # Query material inventory less than or equal ordered date
            get_material_inventory = RawMaterials_Inventory.objects.filter(material_name=material_name, ordered_date__lte=ordered_date)

            # Get first item on the list. Check if None. Check ordered date.
            # Block it if creating before initalizing
            if get_material_inventory.first() is None: 
                return JsonResponse({'label': 'inventory_product_name', 'message':f'Cannot create {inventory_product_name}. Please check material inventory for {material_name}.'}, status=500)
                
            # Sums the material total stock
            total_material_stock_left = get_material_inventory.aggregate(total_inventory=Sum('material_stock_left'))
            total_material_stock_left = total_material_stock_left['total_inventory']

            # material_qty_formula * quantity of inventory that needs to be created
            # Check if material has enough stock to create number of product
            total_quantity_needed = Decimal(inventory_quantity) * Decimal(get_material_qty_formula)

            if Decimal(total_material_stock_left) < total_quantity_needed:
                return JsonResponse({"label":"inventory_quantity","message": f"Not Enough {material_name} to create this product"}, status=500)
    # Validation Done

            properties = [
                'ordered_date',
                'material_name',
                'material_cost',
                'material_stock_left',
                'quantity',
            ]
            result = unitPriceQuantityCalculator(get_material_inventory, total_quantity_needed, properties, [4,2])

            main_data_list.append(result)

        return JsonResponse(main_data_list, safe=False)
    return JsonResponse([], safe=False)

# Validates AddSalesForm
# Check if the product has stock
# check if product has enough stock
# get price per unit of product
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def getUnitPriceProduct(request):
    data = json.loads(request.body.decode('utf-8'))
    product_name = data['product_name']
    sales_quantity = data['sales_quantity']
    sales_date = data['sales_date']
    index = data['itemNo']

    if sales_quantity == "": 
        sales_quantity = 0 
    else: 
        sales_quantity = Decimal(sales_quantity)

    if product_name == "" or sales_date == "":
        return JsonResponse([], safe=False)

    get_product_inventory = Product_Inventory.objects.filter(product_name=Product.objects.get(product_name=product_name), ordered_date__lte=sales_date)
    if not get_product_inventory.exists():
        # return JsonResponse({'label':'sales_quantity', 'message':f'{product_name} has NO stock at the moment'}, status=500)
        return JsonResponse({'label':f'products.{index}.sales_quantity', 'message':f'{product_name} has NO stock at the moment'}, status=500)
    
    # Sum of current stock have for the product selected
    total_product_inventory = get_product_inventory.aggregate(total_inventory=Sum('product_stock_left'))

    # Check if there is enough stock in inventory
    if total_product_inventory['total_inventory'] < sales_quantity:
        # return JsonResponse({'label':'sales_quantity', 'message':f'{product_name} has {total_product_inventory["total_inventory"]} in stock'}, status=500)
        return JsonResponse({'label':f'products.{index}.sales_quantity', 'message':f'{product_name} has only {total_product_inventory["total_inventory"]} in stock'}, status=500)

    properties = [
        'ordered_date',
        'product_name',
        'product_cost',
        'product_stock_left',
        'quantity',
    ]
    result = unitPriceQuantityCalculator(get_product_inventory, sales_quantity, properties)

    return JsonResponse(result, safe=False)