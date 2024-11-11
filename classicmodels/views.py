from django.shortcuts import render
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from rest_framework import generics
from .models import *
from django_filters import rest_framework as filters
from .serializers import get_read_only_serializer
from .filters import dynamic_model_filter_set, CustomerFilter
from rest_framework.response import Response
# Create your views here.

class CustomerAPIView(generics.ListAPIView):
    queryset = Customers.objects.all()
    serializer_class = get_read_only_serializer(meta_model=Customers, fields=[])
    # filterset_class = CustomerFilter
    # filterset_class = dynamic_model_filter_set
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['customernumber', "customername", "contactlastname", "contactfirstname"]

    def list(self, request, *args, **kwargs):
        params = request.query_params.copy()
        queryset = self.get_queryset()
        filterset_class = dynamic_model_filter_set(meta_model=Customers, fields=[], request=self.request)
        # for i in params:
        #     if params[i] == "true":
        #         params[i] = True
        # breakpoint()
        filterset = filterset_class(data=params, queryset=queryset, request=request)
        if filterset.is_valid():
            queryset = filterset.qs
        else:
            return Response(filterset.errors, status=400)
        queryset = self.filter_queryset(queryset)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class OfficeAPIView(generics.ListAPIView):
    pass

class OrderAPIView(generics.ListAPIView):
    pass

class PaymentsApIview(generics.ListAPIView):
    pass

class ProductLinesAPIView(generics.ListAPIView):
    pass

class ProductsAPIView(generics.ListAPIView):
    pass

class EmployeesAPIView(generics.ListAPIView):
    pass

class OrderDetailsAPIView(generics.ListAPIView):
    pass
