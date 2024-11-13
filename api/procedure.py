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


def updateSalesProcedure(queryset, data):
    # data['sales_quantity'] -> Is the NEW_QUANTITY (Includes OLD_QUANTITY)
    # diff_quantity -> Is the difference between NEW_QUANTITY(revised quantity + OLD_QUANTITY) & OLD_QUANTITY
    # revised quantity -> Is what the user input in sale quantity field. 
    #                  -> Can either be increased, decreased, or same
    #                  -> same = 0; increased = 0+; decreased = 0-;
    diff_quantity = round(data['quantity_diff'], 2)
    # Initialize here to be used in adding new sales entries
    data['quantity'] = diff_quantity
    data['uprice'] = data['unit_price']

    prod_inv_pk = data['sales_transaction'][0]['id']
    sales_pk = data['pk']

    queryItem = get_object_or_404(Product_Inventory, pk=prod_inv_pk)
    # Get inventory trans using SalesPK
    inv_trans = get_object_or_404(InventoryTransaction, sales_pk=sales_pk)

    # If LESS than 0 sales_quantity was reduced compared to the actual
    diff_quantity = Decimal(diff_quantity)
    if diff_quantity < 0:
        # Need to return excess quantity | Update everything

        inv_trans.p_quantity += abs(diff_quantity)
        inv_trans.save()

        queryItem.product_stock_left += abs(diff_quantity)
        queryItem.save()

        updated_sales = update_sales_obj(sales_pk, data)
        updated_sales.save()

        return

    # If GREATER than 0 sales_quantity was increased compared to the actual
    else:
        # Deduct sales quantity increased from stock left. 
        # And Update stock left values
        quantity_pending = Decimal(diff_quantity)

        if not queryItem.product_stock_left == 0:
            quantity_pending -= queryItem.product_stock_left

            # Goes here if quantity_pending is LESS than reamaining stock left after deductions
            # Goes here. Does not have to create a new instances of sales, inv_trans, prod_inv
            if quantity_pending <= 0:
                # Update inventory transaction -> P.Quantity | I.U/Price should probably be the same
                inv_trans.p_quantity -= diff_quantity
                inv_trans.save()

                # Update sales -> update_sales_obj(sales_pk, requestObj)
                # data['sales_quantity'] would remain the same since the record will be updated with this value
                updated_sales = update_sales_obj(sales_pk, data)
                updated_sales.save()

                # Update product inventory stock left
                queryItem.product_stock_left = abs(quantity_pending)
                queryItem.save()

                # Exits function since procedure is done
                return
                

            # Goes here if quantity_pending is GREATER than remaining stock left after deductions
            # quantity_pending > 0:
            # This only happens when new sales quantity is more than stock left
            else: 
                # Quantity remained after decution of stock left from original source
                new_sales_quantity = diff_quantity - queryItem.product_stock_left
                

                # Update inventory transaction -> P.Quantity | I.U/Price should probably be the same
                inv_trans.p_quantity -= queryItem.product_stock_left

                # Update sales -> update_sales_obj(sales_pk, requestObj)
                data['sales_quantity'] = queryItem.product_stock_left + (data['sales_quantity'] - diff_quantity)
                data['total_cost'] = Decimal(data['sales_quantity']) * Decimal(data['unit_cost'])
                updated_sales = update_sales_obj(sales_pk, data)

                # Update product inventory stock left to 0
                queryItem.product_stock_left = 0

                inv_trans.save()
                queryItem.save()
                updated_sales.save()

                # After sales been updated. 
                # Reassign sales_quantity:quantity with the remainder of quantity that was not covered
                data['quantity'] = new_sales_quantity


        # Goes here. If original source has no stock left | Original source does not have enough stock left. 
        # Need to create a new sales now
        # O.G. source not enough stock -> Will only create the remainder of quantity not supplied by original source

        # function below creates sales & inv_trans instance, and update prod_inv
        addSalesProcedure(queryset, quantity_pending, data)

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


    