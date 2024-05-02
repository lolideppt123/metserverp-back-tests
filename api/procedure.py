from decimal import Decimal
from .models import *
from .helper import *
import datetime


def addSalesProcedure(queryset, quantity, requestObj):
    # Deduct sales quantity from stock left. And Update stock left values
    quantity_pending = Decimal(quantity)
    for product in queryset:
        quantity_pending -= product.product_stock_left
        if not product.product_stock_left == 0:
            if quantity_pending <= 0:
                # Goes here when loop is going to end.
                # Goes here if Stock Left is greater than quantity after deductions
                # --Updating UCost & TCost--
                requestObj['ucost'] = product.product_cost
                requestObj['tcost'] = Decimal(requestObj['quantity']) * Decimal(requestObj['ucost'])

                # Create Sales Instance
                sales_instance = create_sales_obj(requestObj)

                # Create InventoryTransaction Instance
                createInventoryTransactionInstance = InventoryTransaction.objects.create(
                    transaction_date = Sales.objects.get(pk=sales_instance.pk).sales_date,
                    sales_pk = sales_instance,
                    inventory_pk = Product_Inventory.objects.get(pk=product.pk),
                    p_quantity = -abs(requestObj['quantity'])
                )

                # Set new value for stock left
                product.product_stock_left = abs(quantity_pending)
                product.save()
                break

            if quantity_pending > 0:
                # Goes here if quantity is greater than reamaining stock left after deductions
                # Deduct product_stock_left
                new_qty_data = requestObj['quantity'] - product.product_stock_left
                # Update requestOjb values. Set Obj Quantity and get new TCOst
                requestObj['ucost'] = product.product_cost
                requestObj['quantity'] = product.product_stock_left
                requestObj['tcost'] = Decimal(requestObj['quantity']) * Decimal(requestObj['ucost'])

                # Create Sales Instance
                sales_instance = create_sales_obj(requestObj)

                # Create InventoryTransaction Instance
                createInventoryTransactionInstance = InventoryTransaction.objects.create(
                    transaction_date = Sales.objects.get(pk=sales_instance.pk).sales_date,
                    sales_pk = sales_instance,
                    inventory_pk = Product_Inventory.objects.get(pk=product.pk),
                    p_quantity = -abs(product.product_stock_left)
                )

                # Update Obj Quantity with initial qty - product_stock_left
                requestObj['quantity'] = new_qty_data

                # Then Set product_stock_left to 0
                product.product_stock_left = 0
                product.save()
    return


def addProductionInventoryProcedure(query, quantity, query_pk = []):
    quantity_pending = Decimal(quantity)
    for item in query:
        # print("line 303 ",item.material_name ,": ",item.material_stock_left)
        quantity_pending -= item.material_stock_left
        if not item.material_stock_left == 0:
            # Add pk to list when they have stock left
            # query_pk.append(item.pk)
            if quantity_pending <= 0:
                # Get the deducted quantity mat_inventory
                last_quantity = -abs(quantity_pending + item.material_stock_left)
                query_pk.append([item.pk, last_quantity])
                # Goes here when loop is going to end.
                # Goes here if Stock Left is greater than quantity after deductions
                # Then Set new value for stock left
                item.material_stock_left = abs(quantity_pending)
                item.save()
                break
            if quantity_pending > 0:
                # Get the deducted quantity mat_inventory
                query_pk.append([item.pk, -abs(item.material_stock_left)])
                # Goes here if quantity is greater than reamaining stock left after deductions
                # Then Set value for stock left to 0
                item.material_stock_left = 0
                item.save()



# def DRAFTaddProductionInventoryProcedure(query, quantity requestObj, quantityFill):

#     for index, item in enumerate(products):
#         data['product_name'] = item['product']
#         data['quantity'] = item['sales_quantity']
#         data['ucost'] = item['unit_cost']
#         data['tcost'] = item['total_cost']
#         data['uprice'] = item['unit_price']
#         product_inventory = Product_Inventory.objects.filter(product_name = Product.objects.get(product_name=item['product']), ordered_date__lte=sales_date)

#         quantity_pending = item['sales_quantity']
#         for product in product_inventory:
#             quantity_pending -= product.product_stock_left
#             if not product.product_stock_left == 0:

#     # if quantity_pending <= 0:
#     #     print("Going to End ", product.pk)
#     #     print("--Updating UCost & TCost--")
#     #     print("New UCost ", product.product_cost)
#     #     print("New TCost ", product.product_total_cost)
#     #     data['ucost'] = product.product_cost
#     #     data['tcost'] = Decimal(data['quantity']) * Decimal(data['ucost'])
#         print("Data going to be sent", data.values())
#         print("Instance Created")
#         print("------")
#         pass
#     if quantity_pending > 0:
#         print("Not Going to End ", product.pk)
#         print("Quantity to be Deducted ", product.product_stock_left)
#         new_qty_data = data['quantity'] - product.product_stock_left
#         print("Value that will replace qty ", product.product_stock_left)
#         print("Setting new UCost Point ", product.product_cost)
#         data['ucost'] = product.product_cost
#         data['quantity'] = product.product_stock_left
#         data['tcost'] = Decimal(data['quantity']) * Decimal(data['ucost'])
#         print("Data going to be sent", data.values())
#         print("Instance Created")
#         print("--Updating Data--")
#         data['quantity'] = new_qty_data
#         data['tcost'] = Decimal(new_qty_data) * Decimal(data['ucost']) # redundant
#         print(">>>> New Data going to be sent", data.values())
#         print("------")
#         pass
    