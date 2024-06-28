from .models import *
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from decimal import Decimal, InvalidOperation
from dateutil.relativedelta import relativedelta
import datetime
import math
import calendar


# get price per unit of product. 
# Used by SalesForm, ProductInventoryForm:(ManufactureProduct)
def unitPriceQuantityCalculator(query, fill_quantity=0, properties=[], decimal = [2,2]):
    print(query)
    # fill_quantity -> quantity need to be filled (sales_quantity or production quantity)
    # item_quantity -> quantity of ITEM (Finished Product Quantity or Material Inventory Quantity)
    primary, secondary = decimal # primary(decimal for quantity, secondary decimal for price)
    date, name, cost, stock_left, item_quantity = properties

    data_list = []
    sample_data_set = {}
    total_unit_cost = 0

    quantity_pending = fill_quantity
    if query is not None:
        for item in query:
            # print("line 76 ",getattr(item, name) ,": ",getattr(item, stock_left), "-", getattr(item, cost), "-", getattr(item, date))

            quantity_pending -= getattr(item, stock_left)
            if not getattr(item, stock_left) == 0:
                if quantity_pending <= 0:
                    # Goes here when loop is going to end. "Stock Left is greater than quantity after deductions"
                    # Then Set new value for stock left

                    try:
                        total_unit_cost += (quantity_pending + getattr(item, stock_left)) * getattr(item, cost)
                        total_unit_cost /= fill_quantity
                        # Removes trailing zero by casting to string then strip zero
                        total_unit_cost = str(total_unit_cost).rstrip('0')
                        total_unit_cost = Decimal(total_unit_cost)
                    except InvalidOperation:
                        total_unit_cost = 0
                    data_unit_cost = ({'unit_cost': round(total_unit_cost, secondary)})

                    sample_data_set = {'date': getattr(item, date).strftime('%m-%d-%y')}
                    sample_data_set.update({'product': getattr(getattr(item, name), name)})
                    sample_data_set.update({'unit_cost': round(getattr(item, cost), secondary)})
                    sample_data_set.update({'total_cost': round(getattr(item, cost) * (getattr(item, stock_left) - abs(quantity_pending)), secondary)})
                    sample_data_set.update({'quantity_bought': round(getattr(item, item_quantity), secondary)})
                    sample_data_set.update({'quantity_remaining': round(getattr(item, stock_left), secondary)})
                    sample_data_set.update({'quantity_deduct': round(getattr(item, stock_left) - abs(quantity_pending), primary)}) # 4 for manuf
                    sample_data_set.update({'quantity_left': round(abs(quantity_pending), primary)})# 4 for manuf

                    data_list.append(sample_data_set)
                    data_list.append(data_unit_cost)
                    # return data_list
                    break
                if quantity_pending > 0:
                    # Goes here if quantity is greater than reamaining stock left after deductions
                    total_unit_cost += getattr(item, cost) * getattr(item, stock_left)
                    sample_data_set = {'date': getattr(item, date).strftime('%m-%d-%y')}
                    sample_data_set.update({'product': getattr(getattr(item, name), name)})
                    sample_data_set.update({'unit_cost': round(getattr(item, cost), secondary)})
                    sample_data_set.update({'total_cost': round(getattr(item, cost) * getattr(item, stock_left), secondary)})
                    sample_data_set.update({'quantity_bought': round(getattr(item, item_quantity), )})
                    sample_data_set.update({'quantity_remaining': round(getattr(item, stock_left), secondary)})
                    sample_data_set.update({'quantity_deduct': round(getattr(item, stock_left), primary)}) # 4 for manuf
                    sample_data_set.update({'quantity_left': 0})

                    data_list.append(sample_data_set)
                    
    return data_list

# Used by Sales, SalesSummary
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
    myStart = datetime.datetime.strptime(start, "%Y-%m-%d")
    date_range = []

    # Create my first iteration manually to set start date to the next month with start day of 1
    # Get last day of the month
    getEndDay = calendar.monthrange(myStart.year, myStart.month)
    # Create a new end date
    getEndOfStart = str(myStart.year) + "-" + str(myStart.month) + "-" + str(getEndDay[1])
    myEnd = datetime.datetime.strptime(getEndOfStart, "%Y-%m-%d")
    date_range.append([myStart, myEnd])
    # Increment start date by one month
    myStart += relativedelta(months=1)
    getNewMonth = myStart.month
    getNewYear = myStart.year

    # Create my new start date. Next month of start date and starts with day 01
    newStartDate = datetime.datetime.strptime(f"{getNewYear}-{getNewMonth}-01", "%Y-%m-%d")

    # -1 on iteration because I manually add one before the loop
    for i in range(iteration - 1):
        # Get last day of the month
        getEndDay = calendar.monthrange(newStartDate.year, newStartDate.month)
        # Create a new end date
        getEndOfStart = str(newStartDate.year) + "-" + str(newStartDate.month) + "-" + str(getEndDay[1])
        newEnd = datetime.datetime.strptime(getEndOfStart, "%Y-%m-%d")
        # print(newStart, "---", newEnd)
        date_range.append([newStartDate, newEnd])
        newStartDate += relativedelta(months=1)
    # Replace end date with supplied end date
    date_range[iteration-1][1] = datetime.datetime.strptime(end, "%Y-%m-%d")
    return date_range

# Used by Sales, Sales Summary
def getSalesTotals(query, option):
    total_sales_cost = query.aggregate(total=Sum('sales_total_cost'))
    total_sales_price = sumOfSales(query, 'sales_gross_price') # helper.py
    total_sales_margin = sumOfSales(query, 'sales_margin') # helper.py
    total_sales_vat = sumOfSales(query, 'sales_VAT') # helper.py

    if option == "TOTAL_SALES":
        sales_totals = {
            "sales_cost": total_sales_cost['total'],
            "sales_price": total_sales_price['total'],
            "sales_total_margin": total_sales_margin['total'],
            "sales_vat": total_sales_vat['total'],
        }
        return sales_totals

    if option == "CUMM_TOTAL_SALES":
        cumm_sales_totals = {
            "cumm_sales_cost": total_sales_cost['total'],
            "cumm_sales_price": total_sales_price['total'],
            "cumm_sales_margin": total_sales_margin['total'],
            "cumm_sales_vat": total_sales_vat['total'],
        }
        return cumm_sales_totals

# Used by Sales, Sales Summary
def sumOfSales(query, attr):
    # Sum of query using attribute
    total_sales = {"total": 0}
    for item in query:
        total_sales['total'] += Decimal(getattr(item, attr))
    return total_sales

# Used by Dashboard, ProductsInventory, MaterialsInventory
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

def costChangeMessage(obj, attr, cost):
    message = ""
    if getattr(obj, attr) < Decimal(cost):
        message = "Increase of Unit Cost"
    if getattr(obj, attr) > Decimal(cost):
        message = "Decrease of Unit Cost"
    if getattr(obj, attr) == Decimal(cost):
        message = "No change in Unit Cost"
    return message








# Create Product Inventory
def create_product_inventory_obj(requestObj):
    product_name = requestObj['inventory_product_name']
    supplier = requestObj['supplier']['company_name']
    quantity = requestObj['inventory_quantity']
    ucost = requestObj['price_per_unit']
    tcost = requestObj['total_cost']
    note = requestObj['inventory_product_note']
    date = datetime.datetime.strptime(requestObj['ordered_date'], "%Y-%m-%d").date()

    inventory_instance = Product_Inventory.objects.create(
        product_name = Product.objects.get(product_name=product_name),
        supplier = supplier,
        quantity = quantity,
        product_stock_left = quantity,
        product_cost = ucost,
        product_total_cost = tcost,
        ordered_date = date,
        inventory_note = note,
    )
    return inventory_instance

# Create Sales
def create_sales_obj(requestObj):
    sales_dr = requestObj['sales_dr']
    invoice = requestObj['sales_invoice']
    customer = requestObj['customer']['company_name']
    tax_percent = requestObj['tax_percent']
    # sales_status = requestObj['sales_status']
    sales_note = requestObj['sales_note']
    # paid_date = requestObj['sales_paid_date']

    date = datetime.datetime.strptime(requestObj['sales_date'], "%Y-%m-%d").date()

    product = requestObj['product_name']
    quantity = requestObj['quantity']
    ucost = requestObj['ucost']
    tcost = requestObj['tcost']
    uprice = requestObj['uprice']

    createSalesInstance = Sales.objects.create(
        sales_dr = sales_dr,
        sales_invoice = invoice,
        sales_date = date,
        customer = customer,
        product_name = Product.objects.get(product_name=product),
        sales_quantity = quantity,

        sales_unit_cost = ucost,
        sales_total_cost = tcost,
        sales_unit_price = uprice,

        tax_percent = tax_percent,
        # sales_status = sales_status,
        sales_note = sales_note,
        # sales_paid_date = paid_date,
    )
    return createSalesInstance

# Updates Sales
def update_sales_obj(id, requestObj):
    sales = get_object_or_404(Sales, pk=id)
    sales_dr = requestObj['sales_dr']
    invoice = requestObj['sales_invoice']

    customer = requestObj['customer']['company_name']
    s_quantity = requestObj['sales_quantity']
    unit_cost = requestObj['unit_cost']
    total_cost = requestObj['total_cost']
    unit_price = requestObj['unit_price']

    tax_percent = requestObj['tax_percent']
    sales_note = requestObj['sales_note']

    # Set sales first then updates it below when needed
    sales.sales_dr = sales_dr
    sales.sales_invoice = invoice

    sales.customer = customer
    sales.sales_quantity = s_quantity
    sales.sales_unit_cost = unit_cost
    sales.sales_total_cost = total_cost
    sales.sales_unit_price = unit_price

    sales.tax_percent = tax_percent
    sales.sales_note = sales_note


    return sales