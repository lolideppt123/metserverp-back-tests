from django.views import View
from django.http import JsonResponse
from api.models import *
from api.serializer import *
from api.validations import *
from api.helper import *
from api.procedure import *
from django.db.models import Sum, Q, Count
from django.db.models.functions import Length
from django.db.models.deletion import ProtectedError
from decimal import Decimal, InvalidOperation
import uuid
import json
import datetime
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework import permissions
from rest_framework.decorators import permission_classes, api_view
from rest_framework.response import Response
from datetime import date


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
                data_set.update({'pk': material.pk})
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


        return JsonResponse(material_inventory_data, safe=False)
    
    def get_single_material_inventory(self, id):
        """Fetch a single material inventory and return serialized data."""
        material_inventory_item = get_object_or_404(RawMaterials_Inventory, pk=id)
        material_inventory_serializer = RawMaterialsInventorySerializer(material_inventory_item)

        # Manually injecting supplier data
        supplier = get_object_or_404(Supplier, pk=material_inventory_serializer.data['supplier']['id'])
        serialized_data = material_inventory_serializer.data
        serialized_data['supplier'] = {
            "id": supplier.pk,
            "company_name": supplier.company_name
        }

        return Response(serialized_data)

    def get_all_material_inventory(self):
        """Fetch and aggregate all material inventories, optimizing database queries."""
        materials = RawMaterials.objects.all()

        if not materials.exists():
            return Response([], safe=False)
        
        material_inventory_data = []
        for material in materials:
            # Using select_related and prefetch_related to minimize database hits
            material_inventory = RawMaterials_Inventory.objects.filter(
                material_name=material.pk
            ).select_related(
                'supplier', 
                'material_name'
            )
            material_unit = Unit.objects.get(unit_name=material.material_unit).unit_name

            # Check if material inventory exists and process
            if material_inventory.exists():
                # Aggregate stock left and price
                material_stock_left = material_inventory.aggregate(total_inventory=Sum('material_stock_left'))
                width, color = productInventoryStatus(material.material_min_stock, *material_stock_left.values())

                last_ordered_date = material_inventory.last().ordered_date
                order_update = material_inventory.last().order_update

                # Initialize dataset with material details
                data_set = {
                    'material_name': material.material_name,
                    'pk': material.pk,
                    'material_unit': material_unit,
                    'last_ordered_date': last_ordered_date,
                    'order_update': order_update
                }

                data_set.update(material_stock_left)
                data_set.update(width)
                data_set.update(color)

                # Get price and stock left of the first inventory item
                first_item = material_inventory.first()
                if first_item.material_stock_left > 0:
                    data_set.update({
                        'unit_price': first_item.material_cost,
                        'stock_left': first_item.material_stock_left
                    })
                else:
                    data_set.update({'unit_price': 0, 'stock_left': 0})

                material_inventory_data.append(data_set)
                
        return Response(material_inventory_data, safe=False)

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

    def patch(self, request, id):
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
        return JsonResponse({
            "material_pk": material_name.pk,
            "message": f"Successfully updated {message} {material_name}", 'variant': 'success'}, safe=False)
    
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
        return JsonResponse({
            "material_pk": material_inventory_item.material_name.pk, # returns back material_pk to be used in inventoryMaterialApiSlice tag invalidation
            "message": f"{material_inventory_item.material_name} has successfully deleted."
        })
    
class RawMaterialsInventoryHistoryPageView(APIView):
    permission_classes = (permissions.DjangoModelPermissions,)
    queryset = RawMaterials_InventoryTransaction.objects.all() # This is needed even we don't use it to perform permission_classes

    def get(self, request, material_pk):
        print("FIFED")
        print("Material PK: ", material_pk)
        try:
            material = RawMaterials.objects.get(pk=material_pk)
        except RawMaterials.DoesNotExist:
            return JsonResponse({"data": "No results found"}, safe=False)
        
        # Gets current year
        getYear = date.today().year
        # change this later to get all inventory transaction where product inventory has stock
        # because transaction will be continous and need to get transactions even it's in the past year
        # only if they have stock
        material_inventory_transaction = RawMaterials_InventoryTransaction.objects.filter(
            # transaction_date__year=getYear,
            materials_inventory_pk__material_name=material
        ).select_related(
            'materials_inventory_pk',
            'materials_inventory_pk__supplier',
            'materials_inventory_pk__material_name',
            'product_inventory_pk',
            'product_inventory_pk__supplier',
            'product_inventory_pk__product_name'
        ).order_by(
            'transaction_date', 
            'created_at'
        )

        data_list = []
        running_total = 0
        print(material_inventory_transaction)
        for item in material_inventory_transaction:
            print("here af")
            # Check if Product_Inventory PK exists in current record
            if item.product_inventory_pk and item.m_quantity:
                # Goes here when it has product_inventory_pk meaning user created a FINISHED PRODUCT
                # using "RawMaterials_Inventory" therefore automatically creates "RawMaterials_InventoryTransaction"
                running_total -= self.handle_material_quantity_deducted(item)
                data_list.append(self.prepare_product_transaction(item, running_total))
            elif item.materials_inventory_pk and item.product_inventory_pk is None:
                # It should always goes here first.
                # The query logic is ordered_by transaction_date. 
                # So the user would have to create a Raw Material Inventory First. 
                # then after it would automatically creates a "RawMaterials_InventoryTransaction" FIRST RECORD 
                # hence "it should always goes here first".
                # Because the logic is you can't create a Finished Product without Raw Materials.
                running_total += item.materials_inventory_pk.quantity  # Add quantity to stock
                data_list.append(self.prepare_inventory_transaction(item, running_total))




        # for item in material_inventory_transaction:
        #     if item.materials_inventory_pk.material_name == material:
        #         if not item.product_inventory_pk==None:
        #             try:
        #                 get_material_quantity_deducted = abs(item.m_quantity)
        #             except RawMaterials_Product.DoesNotExist:
        #                 return JsonResponse({"data": "No results found"}, safe=False)
        #             running_total -= get_material_quantity_deducted
        #             data_set = {'transaction_date': item.transaction_date}
        #             data_set.update({"material": item.materials_inventory_pk.material_name.material_name})
        #             data_set.update({"supplier": item.product_inventory_pk.supplier.company_name})
        #             data_set.update({"product": item.product_inventory_pk.product_name.product_name})
        #             data_set.update({"quantity": abs(item.m_quantity)})
        #             data_set.update({"stock": ""})
        #             data_set.update({"uprice": item.materials_inventory_pk.material_cost})
        #             data_set.update({"total": get_material_quantity_deducted})
        #             data_set.update({"running_total": running_total})
        #             data_set.update({"inv_id": item.product_inventory_pk.pk})
        #             data_set.update({"id": item.pk})
        #             data_set.update({"type": "prod"})
        #             data_list.append(data_set)
        #         else:
        #             running_total += item.materials_inventory_pk.quantity
        #             data_set = {'transaction_date': item.transaction_date}
        #             data_set.update({"material": item.materials_inventory_pk.material_name.material_name})
        #             data_set.update({"supplier": item.materials_inventory_pk.supplier.company_name})
        #             data_set.update({"product": ""})
        #             data_set.update({"quantity": item.materials_inventory_pk.quantity})
        #             data_set.update({"stock": item.materials_inventory_pk.material_stock_left})
        #             data_set.update({"uprice": item.materials_inventory_pk.material_cost})
        #             data_set.update({"total": item.materials_inventory_pk.quantity})
        #             data_set.update({"running_total": running_total})
        #             data_set.update({"inv_id": item.materials_inventory_pk.pk})
        #             data_set.update({"id": item.pk})
        #             data_set.update({"type": "mat"})
        #             data_list.append(data_set)
                    
        return Response(data_list)
    
    def handle_material_quantity_deducted(self, item):
        """Handles the material quantity deduction logic when raw material is consumed in production."""
        try:
            return abs(item.m_quantity)  # Return the absolute value of material quantity deducted
        except RawMaterials_Product.DoesNotExist:
            return 0
            
    def prepare_inventory_transaction(self, item, running_qty):
        """Prepares a dictionary for raw material (inventory) transaction details."""
        return {
            'transaction_type': "restock",
            'material': RawMaterialsInventorySerializer(item.materials_inventory_pk).data,
            "supplier": item.materials_inventory_pk.supplier.company_name,
            'product': '',
            'quantity': item.materials_inventory_pk.quantity,
            'stock': item.materials_inventory_pk.material_stock_left,
            'unit_cost': item.materials_inventory_pk.material_cost,
            'total_cost': item.materials_inventory_pk.material_total_cost,
            'running_total': running_qty,
            'id': item.materials_inventory_pk.pk,  # pk of RawMaterials_Inventory
            'transaction_id': item.pk  # pk of RawMaterials_InventoryTransaction
        }
    
    def prepare_product_transaction(self, item, running_qty):
        """Prepares a dictionary for product (finished goods) transaction details."""
        return {
            'transaction_type': "production",
            'material': RawMaterialsInventorySerializer(item.materials_inventory_pk).data,
            'product': ProductInventorySerializer(item.product_inventory_pk).data,
            'supplier': item.product_inventory_pk.supplier.company_name,
            'quantity': abs(item.m_quantity),
            'stock': "",  # No stock left since it's a finished product
            'unit_cost': item.materials_inventory_pk.material_cost,
            'total': abs(item.m_quantity) * item.materials_inventory_pk.material_cost,
            'running_total': running_qty,
            'id': item.product_inventory_pk.pk,  # pk of Product_Inventory
            'transaction_id': item.pk  # pk of RawMaterials_InventoryTransaction
        }

    

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
    
    def patch(self, request, id):
        print("PAtch triggered")
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
        return JsonResponse({
            "product_pk": product_name.pk,
            'message': f"Successfully updated {message} {product_name}", 'variant': 'success'}, safe=False)
    
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
        return JsonResponse({
            "product_pk": product_inventory.product_name.pk, # returns back product_pk to be used in inventoryApiSlice tag invalidation
            "message": f"{product_inventory.product_name} has successfully deleted."
        })

class InventoryHistoryPageView(APIView):
    permission_classes = (permissions.DjangoModelPermissions,)
    queryset = InventoryTransaction.objects.all() # This is needed even we don't use it to perform permission_classes

    def get(self, request, product_pk):
        print(product_pk)
        try:
            product = Product.objects.get(pk=product_pk)
        except Product.DoesNotExist:
            return JsonResponse({"data": "No results found"}, safe=False)
        
        # Gets current year
        getYear = date.today().year
        inventory_transactions = InventoryTransaction.objects.filter(
            # transaction_date__year=getYear,
            inventory_pk__product_name=product
        ).select_related(
            'inventory_pk', 
            'inventory_pk__supplier', 
            'inventory_pk__product_name',
            'sales_pk',
            'sales_pk__customer',
            'sales_pk__sales_invoice'
        ).order_by(
            'transaction_date', 
            'created_at'
        )
                
        data_list = []
        running_qty = 0
        
        for item in inventory_transactions:
            if item.inventory_pk and item.p_quantity is None:
                data_list.append(self.prepare_inventory_transaction(item, running_qty))
                running_qty += item.inventory_pk.quantity

            elif item.sales_pk:
                running_qty -= item.sales_pk.sales_quantity
                data_list.append(self.prepare_sales_transaction(item, running_qty))


        return JsonResponse(data_list, safe=False)
    
    def prepare_inventory_transaction(self, item, running_qty):
        return {
            'transaction_type': "restock",
            'product': ProductInventorySerializer(item.inventory_pk).data,
            'transaction_date': item.transaction_date,
            'quantity': item.inventory_pk.quantity,
            'unit_cost': item.inventory_pk.product_cost,
            'running_quantity': running_qty + item.inventory_pk.quantity,
            'inventory_stock_left': item.inventory_pk.product_stock_left,
            'total_cost': item.inventory_pk.product_total_cost,
            'id': item.inventory_pk.pk,  # pk of Product_Inventory
            'transaction_id': item.pk  # pk of InventoryTransaction
        }

    
    def prepare_sales_transaction(self, item, running_qty):
        return {
            'transaction_type': "sales",
            'product': SalesSerializer(item.sales_pk).data,
            'transaction_date': item.transaction_date,
            'quantity_sold': item.sales_pk.sales_quantity,
            'unit_cost': item.sales_pk.sales_unit_cost,
            'unit_price': round(Decimal(item.sales_pk.sales_unit_price) / Decimal(1.12), 2),  # Adjusted price (net)
            'running_quantity': running_qty,
            'sales_gross_price': item.sales_pk.sales_gross_price,
            'sales_VAT': item.sales_pk.sales_VAT,
            'total_sales_price': item.sales_pk.sales_total_price,
            'margin': item.sales_pk.sales_margin,
            'sales_margin_percent': item.sales_pk.sales_margin_percent,
            'transaction_id': item.pk,  # pk of InventoryTransaction
            'inventory_id': item.inventory_pk.pk  # pk of Product_Inventory
        }

class InventorySummaryPageView(APIView):
    permission_classes = (permissions.DjangoModelPermissions,)
    queryset = Product_Inventory.objects.all() # This is needed even we don't use it to perform permission_classes

    def get(self, request):
        pass
    def post(self, request):
        data = json.loads(request.body.decode('utf-8'))
        getYear = datetime.date.today().year
        yearBeg = str(getYear) + '-01-01'

        filter = data['filter']
        start_date = data['start']
        end_date = data['end']

        data_list = []
        if(filter == ''):

            products = Product.objects.all()
            materials = RawMaterials.objects.all()

            for product in products:

                product_inventory = Product_Inventory.objects.filter(product_name=product, ordered_date__gte=start_date, ordered_date__lte=end_date)
                sales = Sales.objects.filter(product_name=product, sales_date__gte=start_date, sales_date__lte=end_date)

                prod_inventory_total_quantity = product_inventory.aggregate(total_quantity_bought=Sum('quantity'))
                prod_inventory_total_stock_left = product_inventory.aggregate(total_stock_left=Sum('product_stock_left'))

                # Gets sales totalcost, inv_Quantity totalcost, inv_StockLeft total cost
                sales_COGS = sales.aggregate(total_COGS=Sum('sales_total_cost'))
                prod_inventory_total_quantity_cost = product_inventory.aggregate(total_quantity_cost=Sum('product_total_cost'))
                prod_inventory_total_stock_left_cost = product_inventory.filter(product_stock_left__gt=0).aggregate(total_stock_cost=Sum('product_total_cost'))

                data_set = {"pk": f"{product.pk}_{product.product_name}"}
                data_set.update({"name": product.product_name})
                if(product_inventory.exists()):
                    data_set.update(prod_inventory_total_quantity)
                    data_set.update(prod_inventory_total_stock_left)
                    data_set.update(sales_COGS)
                    data_set.update(prod_inventory_total_quantity_cost)
                    data_set.update(prod_inventory_total_stock_left_cost)

                    # There might be an inventory but no sales
                    if(sales_COGS['total_COGS'] is None or prod_inventory_total_stock_left_cost['total_stock_cost'] is None):
                        data_set.update({"turn_over_ratio": 0})
                    else:
                        data_set.update({'turn_over_ratio': sales_COGS['total_COGS'] / prod_inventory_total_stock_left_cost['total_stock_cost']})

                    data_list.append(data_set)

                else:
                    data_set.update({"total_quantity_bought": 0})
                    data_set.update({"total_stock_left": 0})
                    data_set.update({"total_COGS": 0})
                    data_set.update({"total_quantity_cost": 0})
                    data_set.update({"total_stock_cost": 0})
                    data_set.update({"turn_over_ratio": 0})

                    data_list.append(data_set)


                # print(product, "===", product_inventory)
                # print(product, "===", product_inventory.filter(product_stock_left__gt=0))
                # print(product, "===", prod_inventory_total_stock_left_cost)

                # print(product, "===", sales_COGS)
                # print(product, "===", prod_inventory_total_quantity_cost)
                # if(sales_COGS['total_COGS'] is None or prod_inventory_total_stock_left_cost['total_stock_cost'] is None):
                #     print(product, "===", {'turn_over_ratio': 0})
                # else:
                #     print(product, "===", {'turn_over_ratio': sales_COGS['total_COGS'] / prod_inventory_total_stock_left_cost['total_stock_cost']})
                # print("=======================================")

                # if(not product_inventory):
                #     pass
                # #     print(product)
                # # print(product_inventory)

            for material in materials:

                material_inventory = RawMaterials_Inventory.objects.filter(material_name=material, ordered_date__gte=start_date, ordered_date__lte=end_date)


                product_inventory = Product_Inventory.objects.filter(product_name=product, ordered_date__gte=start_date, ordered_date__lte=end_date)
                sales = Sales.objects.filter(product_name=product, sales_date__gte=start_date, sales_date__lte=end_date)



        print(data)
        
        

        return JsonResponse(data_list , safe=False)
        # return JsonResponse([], safe=False)




