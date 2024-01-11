from django.shortcuts import render
from django.views import View
from django.http import JsonResponse
from rest_framework.response import Response
from .models import *
from.serializer import *
from django.contrib import messages
from django.db.models import Sum
from decimal import Decimal, InvalidOperation
from itertools import chain
import json
import math
from django.core.paginator import Paginator
from dateutil.relativedelta import relativedelta

# Create your views here.
class RawMaterialsPageView(View):
    def get(self, request):
        materials = RawMaterials.objects.all()

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
            return {'label':'material_name', 'message':'Material Already Exists'}

        # Create Material
        material_name = material_name.upper()
        createMaterialInstance = RawMaterials.objects.create(
            material_name =material_name,
            material_min_stock = material_min_stock,
            material_unit = Unit.objects.get(unit_name=material_unit),
            material_note = material_note,
        )

        return JsonResponse({"message": f"Successfully added Product:{material_name} Unit:{material_unit} Minimum Stock:{material_min_stock}"})
        # return JsonResponse({"data":"data"}, safe=False)
    
class RawMaterialsInventoryPageView(View):
    def get(self, request):

        material_inventory_data = []
        for material in RawMaterials.objects.all():
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
        supplier = data['supplier']
        material_quantity = data['material_quantity']
        price_per_unit = data['price_per_unit']
        total_cost = data['total_cost']
        ordered_date = data['ordered_date']
        inventory_material_note = data['inventory_material_note']

        if material_quantity == "": 
            material_quantity = 0 
        else: 
            material_quantity = Decimal(material_quantity)

        if inventory_material_name == "": return JsonResponse({'label':'inventory_material_name', 'message':'Product name is required'}, status=500)
        if material_quantity == 0: return JsonResponse({'label':'material_quantity', 'message':'Quantity is required'}, status=500)

        createMaterialInventoryInstance = RawMaterials_Inventory.objects.create(
            material_name = RawMaterials.objects.get(material_name=inventory_material_name),
            supplier = Supplier.objects.get(company_name=supplier),
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
        return JsonResponse({"data":"data"}, safe=False) 

class RawMaterialsInventoryHistoryPageView(View):
    def get(self, request, material_name):
        material = RawMaterials.objects.get(material_name=material_name)
        material_inventory_transaction = RawMaterials_InventoryTransaction.objects.all()

        data_list = []
        running_total = 0
        for item in material_inventory_transaction:
            if item.materials_inventory_pk.material_name == material:
                if not item.product_inventory_pk==None:
                    get_portion = RawMaterials_Product.objects.get(product=item.product_inventory_pk.product_name.pk, materials=material).quantity
                    get_total_portion = Decimal(get_portion) * Decimal(item.product_inventory_pk.quantity)
                    running_total -= get_total_portion
                    data_set = {'transaction_date': item.transaction_date}
                    data_set.update({"supplier": item.product_inventory_pk.supplier.company_name})
                    data_set.update({"product": item.product_inventory_pk.product_name.product_name})
                    data_set.update({"quantity": item.product_inventory_pk.quantity})
                    data_set.update({"portion": get_portion})
                    data_set.update({"total": get_total_portion})
                    data_set.update({"running_total": running_total})
                    data_set.update({"id": item.product_inventory_pk.pk})
                    data_list.append(data_set)
                else:
                    running_total += item.materials_inventory_pk.quantity
                    data_set = {'transaction_date': item.transaction_date}
                    data_set.update({"supplier": item.materials_inventory_pk.supplier.company_name})
                    data_set.update({"product": ""})
                    data_set.update({"quantity": item.materials_inventory_pk.quantity})
                    data_set.update({"portion": ""})
                    data_set.update({"total": item.materials_inventory_pk.quantity})
                    data_set.update({"running_total": running_total})
                    data_set.update({"id": item.materials_inventory_pk.pk})
                    data_list.append(data_set)
                    
        return JsonResponse(data_list, safe=False)
    def post(self, request):
        pass

class ProductsPageView(View):
    def get(self, request):
        product = Product.objects.all()
        
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
        product_name = product_name.upper()
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
            quantity = data['quantity']
            my_dict = dict(zip(material_list, quantity))
            for item in my_dict:
                # print(item, "is the material ", my_dict[item], "is the quantity")
                RawMaterials_Product.objects.create(product=create_product, materials=RawMaterials.objects.get(material_name=item), quantity=my_dict[item])
            
            return JsonResponse({"message": f"Successfully added Product:{product_name} Unit:{product_unit} Minimum Stock:{product_min_stock}"})
            # return JsonResponse({"data":"data"}, safe=False)
            
        # Finishes creating product here. When inventory_type == IMPORTED
        # inventory_type below is == IMPORTED
        create_product.product_type = inventory_type
        create_product.save()

        # print(create_product.pk)
        return JsonResponse({"message": f"Successfully added Product:{product_name} Unit:{product_unit} Minimum Stock:{product_min_stock}"})
        # return JsonResponse({"data":"data"}, safe=False)
    
class EditProductsPageView(View):
    def get(self, request, id):
        product = Product.objects.get(pk=id)
        product_serializer = ProductSerializer(product)
        return JsonResponse(product_serializer.data, safe=False)

    def put(self, request, id):
        product = Product.objects.get(pk=id)
        data = json.loads(request.body.decode('utf-8'))
        product_name, product_min_stock, product_unit, product_note = data.values()
        
        # Validation
        validation = registerNameValidation(product_name, product_min_stock, "no data", "product")
        if validation:
            return JsonResponse(validation, status=500)
        
        # Watch Changes
        # changes = {}
        # unit = Unit.objects.get(unit_name=product.product_unit).unit_name
        # if not product.product_name == product_name:
        #     changes.update({"product_name":product.product_name})
        # if not product.product_min_stock == product_min_stock:
        #     changes.update({"product_min_stock":product.product_min_stock})
        # if not unit == product_unit:
        #     changes.update({"product_unit": unit})
        # if not product.product_note == product_note:
        #     changes.update({"product_note":product.product_note})

        product.product_name = product_name
        product.product_min_stock = product_min_stock
        product.product_unit = Unit.objects.get(unit_name=product_unit)
        product.product_note = product_note
        product.save()

        return JsonResponse({"message": "Successfully saved changes"})

class ProductInventoryPageView(View):
    def get(self, request):

        product_inventory_data = []
        for product in Product.objects.all():
            product_inventory = Product_Inventory.objects.filter(product_name=product.pk)
            product_unit = Unit.objects.get(unit_name=product.product_unit).unit_name
            if product_inventory.exists():
                product_stock_left = product_inventory.aggregate(total_inventory=Sum('product_stock_left'))
                print(product.product_name, "--",  product_stock_left)
                width, color = productInventoryStatus(product.product_min_stock, *product_stock_left.values())

                last_ordered_date = product_inventory[len(product_inventory)-1].ordered_date
                order_update = product_inventory[len(product_inventory)-1].order_update # Get the last update date

                data_set = {'product_name': product.product_name}
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
        supplier = data['supplier']
        inventory_quantity = data['inventory_quantity']
        price_per_unit = data['price_per_unit']
        total_cost = data['total_cost']
        inventory_product_note = data['inventory_product_note']
        ordered_date = datetime.datetime.strptime(data['ordered_date'], "%Y-%m-%d").date()
        

        if inventory_quantity == "": 
            inventory_quantity = 0 
        else: 
            inventory_quantity = Decimal(inventory_quantity)

        if inventory_product_name == "": return JsonResponse({'label':'inventory_product_name', 'message':'Product name is required'}, status=500)
        if inventory_quantity == 0: return JsonResponse({'label':'inventory_quantity', 'message':'Quantity is required'}, status=500)

        # Validation 
        # Check product_type, Prevent user from creating product before initial material inventory
        # Check each material total stock if there is enough to create a product
        # Query only material inventory before or equal product creation date
        get_product = Product.objects.get(product_name=inventory_product_name)
        if get_product.product_type == "MANUFACTURED":
            # Get the product instance or product ID
            # Then get ingredients which is connected to RawMaterials_Product ".all()"
            # Which will output all materials listed with product instance of get_product
            # print(get_product.ingredients.all())
            get_material_inventory_pk = [] # Use to store material inventory pk for transaction purpose
            for material in get_product.ingredients.all():
                material_name = RawMaterials.objects.get(material_name=material)
                # Get quantity for each material needed for the product
                get_material_qty_formula = RawMaterials_Product.objects.get(materials=material_name, product=get_product).quantity

                # Query material inventory less than or equal ordered date
                get_material_inventory = RawMaterials_Inventory.objects.filter(material_name=material_name, ordered_date__lte=ordered_date)
                for item in get_material_inventory[0:1]:
                    if item.ordered_date > ordered_date:
                        return JsonResponse({'label': 'ordered_date', 'message':f'Cannot add Inventory before initial material inventory {item.ordered_date.strftime("%b-%d-%Y")}'}, status=500)

                total_material_stock_left = get_material_inventory.aggregate(total_inventory=Sum('material_stock_left'))
                total_material_stock_left = total_material_stock_left['total_inventory']
                # Above block Sums the material total stock
                # material_qty_formula * quantity of inventory that needs to be created
                # Check if material has enough stock to create number of product
                total_quantity_needed = Decimal(inventory_quantity) * Decimal(get_material_qty_formula)
                # print("line 293 ",material ,": ",Decimal(total_material_stock_left), "--", get_material_qty_formula, "--", total_quantity_needed)
                # print("line 294 ",Decimal(total_material_stock_left) < total_quantity_needed)
                if Decimal(total_material_stock_left) < total_quantity_needed:
                    return JsonResponse({"label":"inventory_quantity","message": f"Not Enought {material_name} to create this product"}, status=500)
        # Validation Done

                # Deduct materials needed in material inventory
                # store material pk in variable above
                quantity_pending = total_quantity_needed
                for item in get_material_inventory:
                    # print("line 303 ",item.material_name ,": ",item.material_stock_left)
                    quantity_pending -= item.material_stock_left
                    if not item.material_stock_left == 0:
                        # Add pk to list when they have stock left
                        get_material_inventory_pk.append(item.pk)
                        if quantity_pending <= 0:
                            # Goes here when loop is going to end.
                            # Goes here if Stock Left is greater than quantity after deductions
                            # Then Set new value for stock left
                            item.material_stock_left = abs(quantity_pending)
                            item.save()
                            break
                        if quantity_pending > 0:
                            # Goes here if quantity is greater than reamaining stock left after deductions
                            # Then Set value for stock left to 0
                            item.material_stock_left = 0
                            item.save()

        createInventoryInstance = Product_Inventory.objects.create(
            product_name = Product.objects.get(product_name=inventory_product_name),
            supplier = Supplier.objects.get(company_name=supplier),
            quantity = inventory_quantity,
            product_stock_left = inventory_quantity,
            product_cost = price_per_unit,
            product_total_cost = total_cost,
            ordered_date = ordered_date,
            inventory_note = inventory_product_note,
        )
        
        createInventoryTransactionInstance = InventoryTransaction.objects.create(
            transaction_date = Product_Inventory.objects.get(pk=createInventoryInstance.pk).ordered_date,
            inventory_pk = Product_Inventory.objects.get(pk=createInventoryInstance.pk)
        )
                            
        # Get the number of material inventory items to fill product quantity ordered
        if get_product.product_type == "MANUFACTURED":
            get_range = len(get_material_inventory_pk)
            for material in range(get_range):
                # print("line341 ", get_material_inventory_pk)
                get_pk = get_material_inventory_pk.pop(0)
                RawMaterialsInventoryTransactionInstance = RawMaterials_InventoryTransaction.objects.create(
                    transaction_date = ordered_date,
                    product_inventory_pk = createInventoryInstance,
                    materials_inventory_pk = RawMaterials_Inventory.objects.get(pk=get_pk)
                )

        # return JsonResponse({"data":"data"}, safe=False)
        return JsonResponse({"message": f"Successfully added Product Name:{inventory_product_name} Quantity:{inventory_quantity} Order Date:{ordered_date}"})

class EditProductInventoryPageView(View):
    def get(self, request, id):
        product_inventory = Product_Inventory.objects.get(pk=id)
        product_inventory_serializer = ProductInventorySerializer(product_inventory)
        return JsonResponse(product_inventory_serializer.data, safe=False)
    def put(self, request, id):
        product_inventory = Product_Inventory.objects.get(pk=id)
        data = json.loads(request.body.decode('utf-8'))
        print(data.keys())
        print("imhere")

        return JsonResponse({'data': 'data'}, safe=False)

class InventoryHistoryPageView(View):
    def get(self, request, product_name):
        product = Product.objects.get(product_name=product_name).product_name
        inventory_transactions = InventoryTransaction.objects.all()
                
        data_list = []
        running_qty = 0
        for item in inventory_transactions:
            if item.inventory_pk:
                if item.inventory_pk.product_name.product_name == product:
                    running_qty += item.inventory_pk.quantity
                    data_set = {'product_name': item.inventory_pk.product_name.product_name} # Model.foreignkey.foreignkey
                    data_set.update({"cust_supp": item.inventory_pk.supplier.company_name}) # Model.foreignkey.foreignkey
                    data_set.update({"transaction_date": item.transaction_date})
                    data_set.update({"quantity": item.inventory_pk.quantity})
                    data_set.update({"running_quantity": running_qty})
                    data_set.update({"type": "inv"})
                    data_set.update({"id": item.inventory_pk.pk})
                    data_list.append(data_set)               
            else:
                if item.sales_pk.product_name.product_name == product:
                    running_qty -= item.sales_pk.sales_quantity
                    data_set = {'product_name': item.sales_pk.product_name.product_name} # Model.foreignkey.foreignkey
                    data_set.update({"cust_supp": item.sales_pk.customer.company_name}) # Model.foreignkey.foreignkey
                    data_set.update({"transaction_date": item.transaction_date})
                    data_set.update({"quantity": item.sales_pk.sales_quantity})
                    data_set.update({"running_quantity": running_qty})
                    data_set.update({"type": "sales"})
                    data_set.update({"id": item.sales_pk.pk})
                    data_list.append(data_set)

        # paginator = Paginator(data_list, 2)
        # page_number = request.GET.get('page')
        # page_obj = paginator.get_page(page_number)
        # print(paginator.data)
                    

        # asset_json = json.dumps({"data": [asset.to_dict() for asset in page_obj.object_list]})
        # return JsonResponse(page_obj.object_list, safe=False)
        return JsonResponse(data_list, safe=False)
    def post(self, request):
        pass

class SalesPageView(View):
    def get(self, request):
        sales = Sales.objects.all().order_by("-sales_date")
        
        # total_sales_cost = sales.aggregate(total_cost=Sum('sales_total_cost'))
        # total_sales_price = sales.aggregate(total_price=Sum('sales_total_price'))
        # total_sales_margin = sales.aggregate(total_margin=Sum('sales_margin'))

        # sales_cost = float(*total_sales_cost.values())
        # sales_price = float(*total_sales_price.values())
        # sales_margin = float(*total_sales_margin.values())

        # data_set = ({"sales_cost":sales_cost})
        # data_set.update({"sales_price":sales_price})
        # data_set.update({"sales_margin":sales_margin})
        # data_list = [data_set]

        sales_serializer = SalesSerializer(sales, many=True)
        # return JsonResponse({"serialized":sales_serializer.data, "sales_totals": data_list}, safe=False)
        return JsonResponse(sales_serializer.data, safe=False)

    def post(self,request):
        data = json.loads(request.body.decode('utf-8'))
        sales_dr = data['sales_dr']
        sales_invoice = data['sales_invoice']
        sales_date = datetime.datetime.strptime(data['sales_date'], "%Y-%m-%d").date()
        customer = data['customer']
        product_name = data['product_name']
        sales_quantity = data['sales_quantity']
        unit_cost = data['unit_cost']
        total_cost = data['total_cost']
        unit_price = data['unit_price']
        total_price = data['total_price']
        sales_status = data['sales_status']
        sales_note = data['sales_note']
        try:
            sales_paid_date = datetime.datetime.strptime(data['sales_paid_date'], "%Y-%m-%d").date()
        except ValueError:
            sales_paid_date = None

        sales_margin = Decimal(total_price) - Decimal(total_cost)

        sales_margin_percent = addSalesValidation(product_name, customer, sales_margin, total_cost)

        # Check if product name has stock                                           (Checked in getUnitPriceProduct)
        # Check if product has enought stock                                        (Checked in getUnitPriceProduct)
        # Prevents the User to input sales before starting Inventory                (Checked in getUnitPriceProduct)

        # Query inventory less than or equal sales date
        product_inventory = Product_Inventory.objects.filter(product_name = Product.objects.get(product_name=product_name), ordered_date__lte=sales_date)

        # Deduct sales quantity from stock left. And Update stock left values
        addSalesProcedure(product_inventory, sales_quantity, sales_date)

        createSalesInstance = Sales.objects.create(
            sales_dr = sales_dr,
            sales_invoice = sales_invoice,
            sales_date = sales_date,
            customer = Customer.objects.get(company_name=customer),
            product_name = Product.objects.get(product_name=product_name),
            sales_quantity = sales_quantity,
            sales_unit_cost = unit_cost,
            sales_total_cost = total_cost,
            sales_unit_price = unit_price,
            sales_total_price = total_price,
            sales_margin = sales_margin,
            sales_margin_percent = sales_margin_percent,
            sales_status = sales_status,
            sales_note = sales_note,
            sales_paid_date = sales_paid_date,
        )

        createInventoryTransactionInstance = InventoryTransaction.objects.create(
            transaction_date = Sales.objects.get(pk=createSalesInstance.pk).sales_date,
            sales_pk = createSalesInstance,
        )

        return JsonResponse({"message": f"Successfully listed the Sale of {product_name} Quantity:{sales_quantity} Order Date:{sales_date.strftime('%b-%d-%Y')} Unit Price:{unit_price} Total Sale Price:{total_price}"})
    
class EditSalesPageView(View):
    def get(self, request, id):
        sales = Sales.objects.get(pk=id)
        sales_serializer = SalesSerializer(sales)
        return JsonResponse(sales_serializer.data, safe=False)
        
    def put(self, request, id):
        sales = Sales.objects.get(pk=id)
        data = json.loads(request.body.decode('utf-8'))

        sales_dr = data['sales_dr']
        sales_invoice = data['sales_invoice']
        sales_date = datetime.datetime.strptime(data['sales_date'], "%Y-%m-%d").date()
        customer = data['customer']
        product_name = data['product_name']
        sales_quantity = data['sales_quantity']
        unit_cost = data['unit_cost']
        total_cost = data['total_cost']
        unit_price = data['unit_price']
        total_price = data['total_price']
        sales_status = data['sales_status']
        sales_note = data['sales_note']

        try:
            sales_paid_date = datetime.datetime.strptime(data['sales_paid_date'], "%Y-%m-%d").date()
        except ValueError:
            sales_paid_date = None
        sales_margin = Decimal(total_price) - Decimal(total_cost)

        if not sales.product_name.product_name == product_name or not sales.sales_date == sales_date or not sales.sales_quantity == sales_quantity:
            print("im here")
            sales_margin = Decimal(total_price) - Decimal(total_cost)
            sales_margin_percent = addSalesValidation(product_name, customer, sales_margin, total_cost)

            # Get product name inventory less that sales date. Nearest item to the sales date first
            product_inventory = Product_Inventory.objects.filter(
                product_name=Product.objects.get(product_name=sales.product_name), 
                ordered_date__lte=sales.sales_date
            ).order_by('-ordered_date')

            # Return sales quantity to inventory
            quantity_to_return = sales.sales_quantity
            for item in product_inventory:
                # print("line 546 ",item.ordered_date, "--", item.quantity, "--", item.product_stock_left )
                #     print("nothing to do")
                quantity_to_return -= item.quantity - item.product_stock_left
                print(item.quantity - item.product_stock_left)
                if quantity_to_return <= 0:
                    print("line552 ", quantity_to_return)
                    print("line553 ", sales.sales_quantity)
                    item.product_stock_left += sales.sales_quantity
                    item.save()
                    print("line 553 ",item.ordered_date, "--", item.quantity, "--", item.product_stock_left )
                    break
                if quantity_to_return > 0:
                    item.product_stock_left = item.quantity
                    item.save()
                    print("line 558 ",item.ordered_date, "--", item.quantity, "--", item.product_stock_left )

            # Query product inventory again different value for product name and sales date
            product_inventory = Product_Inventory.objects.filter(
                product_name=Product.objects.get(product_name=product_name), 
                ordered_date__lte=sales_date
            )
            for item in product_inventory:
                print(item.product_stock_left)

            # Prevents the User to input sales before starting Inventory
            # Deduct sales quantity from stock left. And Update stock left values
            addSalesProcedure(product_inventory, sales_quantity, sales_date)

            sales.sales_date = sales_date
            sales.product_name = Product.objects.get(product_name=product_name)
            sales.sales_quantity = sales_quantity
            sales.sales_unit_cost = unit_cost
            sales.sales_total_cost = total_cost
            sales.sales_unit_price = unit_price
            sales.sales_total_price = total_price
            sales.sales_margin = sales_margin
            sales.sales_margin_percent = sales_margin_percent
            print(sales_date)

        sales.sales_dr = sales_dr
        sales.sales_invoice = sales_invoice
        sales.customer = Customer.objects.get(company_name=customer)
        sales.sales_status = sales_status
        sales.sales_note = sales_note
        sales.sales_paid_date = sales_paid_date
        sales.save()

        inventory_transaction = InventoryTransaction.objects.get(sales_pk=Sales.objects.get(pk=id))

        # return JsonResponse({"data":"data"}, safe=False)
        return JsonResponse({'message': f"Successfully updated Sales Status", 'variant': 'success'})

class CustomerPageView(View):
    def get(self, request):
        customer = Customer.objects.all()

        # Check if there is a customer
        if not customer.exists():
            return JsonResponse({'data': 'No Registered Customer'})
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

class SupplierPageView(View):
    def get(self, request):
        supplier = Supplier.objects.all()

        # Check if there is a supplier
        if not supplier.exists():
            return JsonResponse({'data': 'No Registered Supplier'})
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

class InventorySummaryPageView(View):
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

class SalesSummaryChartDataView(View):
    def get(self, request):
        pass
    def post(self, request):
        data = json.loads(request.body.decode('utf-8'))
        start_date = data['start']
        end_date = data['end']
        query = data['query']
        
        date_range = getDateRange(start_date, end_date)

        if query == "ALL":
            data_list = []
            for index in range(len(date_range) -1):
                sales = Sales.objects.filter(sales_date__gte=date_range[index], sales_date__lt=date_range[index + 1])
                if sales.exists():
                    # print(sales, "---", date_range[index].strftime("%b %d %Y"), "---", date_range[index + 1].strftime("%b %d %Y"))
                    total_sales_cost = sales.aggregate(total_cost=Sum('sales_total_cost'))
                    total_sales_price = sales.aggregate(total_price=Sum('sales_total_price'))
                    total_sales_margin = sales.aggregate(total_margin=Sum('sales_margin'))
                    # From string to Float
                    sales_cost = float(*total_sales_cost.values())
                    sales_price = float(*total_sales_price.values())
                    sales_margin = float(*total_sales_margin.values())

                    data_set = ({"start_date": date_range[index].strftime("%b %d %Y")})
                    data_set.update({"end_date": date_range[index + 1].strftime("%b %d %Y")})
                    data_set.update({"sales_cost":sales_cost})
                    data_set.update({"sales_price":sales_price})
                    data_set.update({"sales_margin":sales_margin})
                    data_list.append(data_set)
                else:
                    # When no record shows set items to 0
                    data_set = ({"start_date": date_range[index].strftime("%b %d %Y")})
                    data_set.update({"end_date": date_range[index + 1].strftime("%b %d %Y")})
                    data_set.update({"sales_cost":0})
                    data_set.update({"sales_price":0})
                    data_set.update({"sales_margin":0})
                    data_list.append(data_set)
            # print(data_list)
            return JsonResponse(data_list, safe=False)
        elif query == "CUSTOMERS":
            data_list = []
            for customer in Customer.objects.all():
                sales = Sales.objects.filter(sales_date__gte=start_date, sales_date__lt=end_date, customer=customer.pk)
                if sales.exists():
                    total_sales_cost = sales.aggregate(total_cost=Sum('sales_total_cost'))
                    total_sales_price = sales.aggregate(total_price=Sum('sales_total_price'))
                    total_sales_margin = sales.aggregate(total_margin=Sum('sales_margin'))
                    try:
                        sales_cost = float(*total_sales_cost.values())
                        sales_price = float(*total_sales_price.values())
                        sales_margin = float(*total_sales_margin.values())
                    except TypeError:
                        sales_cost = 0
                        sales_price = 0
                        sales_margin = 0

                    data_set = ({'customer': customer.company_name})
                    data_set.update({"sales_cost":sales_cost})
                    data_set.update({"sales_price":sales_price})
                    data_set.update({"sales_margin":sales_margin})
                    data_list.append(data_set)
            return JsonResponse(data_list, safe=False)
        else:
            data_list = []
            for product in Product.objects.all():
                sales = Sales.objects.filter(sales_date__gte=start_date, sales_date__lt=end_date, product_name=product.pk)
                if sales.exists():
                    total_sales_cost = sales.aggregate(total_cost=Sum('sales_total_cost'))
                    total_sales_price = sales.aggregate(total_price=Sum('sales_total_price'))
                    total_sales_margin = sales.aggregate(total_margin=Sum('sales_margin'))
                    try:
                        sales_cost = float(*total_sales_cost.values())
                        sales_price = float(*total_sales_price.values())
                        sales_margin = float(*total_sales_margin.values())
                    except TypeError:
                        sales_cost = 0
                        sales_price = 0
                        sales_margin = 0

                    data_set = ({'product': product.product_name})
                    data_set.update({"sales_cost":sales_cost})
                    data_set.update({"sales_price":sales_price})
                    data_set.update({"sales_margin":sales_margin})
                    data_list.append(data_set)
            return JsonResponse(data_list, safe=False)
        # return JsonResponse({"data": "data"}, safe=False)

class SalesSummaryDataTableView(View):
    def post(self, request):
        data = json.loads(request.body.decode('utf-8'))
        start_date = data['start']
        end_date = data['end']
        query = data['query']

        sales = Sales.objects.filter(sales_date__gte=start_date, sales_date__lt=end_date)
        sales_serializer = SalesSerializer(sales, many=True)

        if query == "ALL":
            total_sales_cost = sales.aggregate(total_cost=Sum('sales_total_cost'))
            total_sales_price = sales.aggregate(total_price=Sum('sales_total_price'))
            total_sales_margin = sales.aggregate(total_margin=Sum('sales_margin'))

            sales_cost = float(*total_sales_cost.values())
            sales_price = float(*total_sales_price.values())
            sales_margin = float(*total_sales_margin.values())

            data_set = ({"sales_cost":sales_cost})
            data_set.update({"sales_price":sales_price})
            data_set.update({"sales_margin":sales_margin})
            data_list = [data_set]
            
            return JsonResponse({"serialized": sales_serializer.data, "sales_totals": data_list}, safe=False)
        return JsonResponse({"data": "data"})

def getUnitPriceProduct(request):
    data = json.loads(request.body.decode('utf-8'))
    product_name = data['product_name']
    sales_quantity = data['sales_quantity']
    sales_date = data['sales_date']

    if sales_quantity == "": 
        sales_quantity = 0 
    else: 
        sales_quantity = Decimal(sales_quantity)

    if product_name == "" or sales_quantity == 0:
        return JsonResponse({"message": "Nothing to return yet"})

    get_product_inventory = Product_Inventory.objects.filter(product_name=Product.objects.get(product_name=product_name), ordered_date__lte=sales_date)
    if not get_product_inventory.exists():
        return JsonResponse({'label':'sales_quantity', 'message':f'{product_name} has NO stock at the moment'}, status=500)
    
    # Sum of current stock have for the product selected
    total_product_inventory = get_product_inventory.aggregate(total_inventory=Sum('product_stock_left'))

    # Check if there is enough stock in inventory
    if total_product_inventory['total_inventory'] < sales_quantity:
        return JsonResponse({'label':'sales_quantity', 'message':f'{product_name} has {total_product_inventory["total_inventory"]} in stock'}, status=500)

    data_list = []
    total_unit_cost = 0
    get_quantity = sales_quantity
    for item in get_product_inventory:

        get_quantity -= item.product_stock_left
        if get_quantity <= 0:
            # Goes here when loop is going to end.
            total_unit_cost += (get_quantity + item.product_stock_left) * item.product_cost
            total_unit_cost /= sales_quantity
            # Removes trailing zero by casting to string then strip zero
            total_unit_cost = str(total_unit_cost).rstrip('0')
            total_unit_cost = Decimal(total_unit_cost)
            data_set = ({'unit_cost': total_unit_cost})
            data_list.append(data_set)
            break
        if get_quantity > 0:
            # Goes here when sold qty is greater than remaining qty for a specific unit cost
            total_unit_cost += item.product_cost * item.product_stock_left

    return JsonResponse(data_list, safe=False)
    
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

def addSalesValidation(product_name, customer, sales_margin, total_cost):
    if not product_name:
        return JsonResponse({'label':'product_name', 'message':'Product name is required'})
    if not customer:
        return JsonResponse({'label':'customer', 'message':'Customer is required'})

    try:
        sales_margin_percent = (sales_margin / Decimal(total_cost)) * 100
    except InvalidOperation:
        return JsonResponse({'label':'sales_quantity', 'message':'Cannot have 0 as Quantity '})
        
    return sales_margin_percent

def addSalesProcedure(queryset, quantity, date):
    # Deduct sales quantity from stock left. And Update stock left values
    quantity_pending = Decimal(quantity)
    for item in queryset:
        quantity_pending -= item.product_stock_left
        if quantity_pending <= 0:
            # Goes here when loop is going to end.
            # Goes here if Stock Left is greater than quantity after deductions
            # Then Set new value for stock left
            item.product_stock_left = abs(quantity_pending)
            new_stock_left = Decimal(item.product_stock_left)
            item.save()
            break
        if quantity_pending > 0:
            # Goes here if quantity is greater than reamaining stock left after deductions
            # Then Set value for stock left to 0
            item.product_stock_left = 0
            item.save()

def productInventoryStatus(min_stock, current_stock):
    info = Decimal(min_stock) * Decimal(2.25)
    warning = Decimal(min_stock) * Decimal(1.5)
    danger = Decimal(min_stock)

    if current_stock <= danger:
        return {"width": "30%"}, {"color": "danger"}
    if current_stock <= warning:
        return {"width": "55%"}, {"color": "warning"}
    if current_stock <= info:
        return {"width": "70%"}, {"color": "info"}
    return {"width": "100%"}, {"color": "success"}

def getDateRange(start, end):
    time = str(datetime.datetime.strptime(start, "%Y-%m-%d") - datetime.datetime.strptime(end, "%Y-%m-%d"))

    if time == '0:00:00':
        time = '1'
    try:
        days = time.split('days')
        to_float_days = float(days[0])
    except ValueError as ve:
        days = time.split('day')
        to_float_days = float(days[0])

    # Converts to months
    iteration = math.ceil(abs(to_float_days) * 0.0328767)
    # print("line 932 ",iteration)
    date_range = [datetime.datetime.strptime(start, "%Y-%m-%d")]
    for i in range(iteration - 1):
        date_range.append(date_range[i] + relativedelta(months=1))
    date_range.append(datetime.datetime.strptime(end, "%Y-%m-%d"))
    return date_range
    