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
from dateutil.relativedelta import relativedelta
from rest_framework.views import APIView
from rest_framework import permissions
from rest_framework.decorators import permission_classes, api_view
import calendar


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
        invoice = (invoice_item.sales_invoice[:8] + '..') if len(invoice_item.sales_invoice) > 8 else invoice_item.sales_invoice
        return JsonResponse({"message": f"Invoice#: {invoice} successfully updated."}, safe=False)

    def delete(self, request, id):
        invoice_item = get_object_or_404(SalesInvoice, pk=id)

        invoice = (invoice_item.sales_invoice[:8] + '..') if len(invoice_item.sales_invoice) > 8 else invoice_item.sales_invoice

        try:
            invoice_item.delete()
        except ProtectedError:
            return JsonResponse({"message": f"Delete action failed. Invoice# {invoice_item.sales_invoice} already has linked records."}, status=404)
        return JsonResponse({"message": f"Invoice: {invoice} has successfully deleted."})

    
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