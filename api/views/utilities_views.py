from django.views import View
from api.models import *
from api.serializer import *
from django.http import JsonResponse

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