from django.http import JsonResponse
from rest_framework.views import APIView
from api.models import *
from api.serializer import *
from api.validations import *
from api.helper import *
from api.procedure import *
from django.db.models.deletion import ProtectedError
from rest_framework import permissions
import json

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
            # product_serializer = ProductSerializer(product_item)
            return JsonResponse(sample.data, safe=False)

        product_serializer = ProductSerializer(product, many=True)
        serialized_data = product_serializer.data
        return JsonResponse(serialized_data, safe=False)
    
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












