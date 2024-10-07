from django.http import Http404, JsonResponse
from api.models import *
from api.serializer import *
from api.validations import *
from api.helper import *
from api.procedure import *
from django.db.models import Sum, Q, F, DecimalField, FloatField
from django.db.models.deletion import ProtectedError
import uuid
import json
import datetime
from datetime import datetime
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework import permissions
from rest_framework.decorators import permission_classes, api_view
import calendar

from django.db.models.functions import TruncMonth
from django.db.models.expressions import ExpressionWrapper
from django.db.models import Func

# from rest_framework.pagination import PageNumberPagination
# from rest_framework.response import Response

class Round(Func):
    function = 'ROUND'
    arity = 2

class SalesPageViewDraft(APIView):
    permission_classes = (permissions.DjangoModelPermissions,)
    queryset = Sales.objects.all() # This is needed even we don't use it to perform permission_classes


    def get(self, request, id=None, option=None, **kwargs):
        try:
            [year, month] = option.split("-")
        except ValueError:
            return JsonResponse({'error', "Invalid Year"}, status=400)
        
        year_sales = Sales.objects.filter(sales_date__year=year)

        # Check if there is a sales
        if not year_sales.exists():
            # Needs to return empty array for frontend
            return JsonResponse([],safe=False)
        if id is not None:
            sales_item = get_object_or_404(Sales, pk=id)
            sales_serialized = SalesSerializer(sales_item)

            get_customer = get_object_or_404(Customer, company_name=sales_serialized.data['customer'])
            serialized_data = sales_serialized.data
            serialized_data['customer'] = {"id":get_customer.pk, "company_name": get_customer.company_name}

            return JsonResponse(serialized_data, safe=False)
        
        # Create a list of months for the given year
        months = [datetime(year, month, 1) for month in range(1, 13)]
        
        # Compute monthly totals
        monthly_totals = year_sales.annotate(
            month=TruncMonth('sales_date')
        ).values('month').annotate(
            total_cost = Sum(
                F('sales_total_cost')
            ),
            total_gross = Sum(ExpressionWrapper(
                Round(
                F('sales_unit_price') * F('sales_quantity') / (1 + F('tax_percent') / 100),
                    2), output_field=DecimalField(decimal_places=2)
            )),
            total_VAT = Sum(ExpressionWrapper(
                Round(
                    (F('sales_unit_price') * F('sales_quantity') / 
                    (1 + F('tax_percent') / 100)) * (F('tax_percent') / 100), 
                    2), output_field=DecimalField()
                
            )),
            total_margin=Sum(ExpressionWrapper(
                Round(
                    F('sales_unit_price') * F('sales_quantity') / 
                    (1 + F('tax_percent') / 100) - F('sales_total_cost'), 
                    2), output_field=DecimalField()
                
            ))
        ).order_by('month')

        cumulative_total_cost = 0
        cumulative_total_gross = 0
        cumulative_total_VAT = 0
        cumulative_total_margin = 0
        monthly_details = []

        for month in months:
            month_str = month.strftime('%B %Y')
            month_data = next((item for item in monthly_totals if item['month'].month == month.month), None)
            transactions = year_sales.filter(sales_date__month=month.month, sales_date__year=year).order_by('sales_invoice', 'sales_date', 'created_at', 'customer')
            serializer = SalesSerializer(transactions, many=True)
            transactions_details = serializer.data

            # If month_data is not None
            if month_data:
                total_cost = month_data['total_cost']
                total_gross = month_data['total_gross']
                total_VAT = month_data['total_VAT']
                total_margin = month_data['total_margin']
            else:
                total_cost = 0
                total_gross = 0
                total_VAT = 0
                total_margin = 0

            cumulative_total_cost += total_cost
            cumulative_total_gross += total_gross
            cumulative_total_VAT += total_VAT
            cumulative_total_margin += total_margin

            monthly_details.append({
                'month': month_str,
                'transactions': transactions_details,
                'total_cost': total_cost,
                'total_gross': total_gross,
                'total_VAT': total_VAT,
                'total_margin': total_margin,
                'cumulative_total_cost': cumulative_total_cost,
                'cumulative_total_gross': cumulative_total_gross,
                'cumulative_total_VAT': cumulative_total_VAT,
                'cumulative_margin': cumulative_total_margin,
            })

        return JsonResponse({'year': year, "monthly_details": monthly_details}, safe=False)


