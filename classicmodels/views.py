from django.shortcuts import render
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from rest_framework import generics
from .models import *
from django_filters import rest_framework as filters
from .serializers import get_read_only_serializer
from .filters import *
from rest_framework.response import Response
# Create your views here.

class CustomerAPIView(generics.ListAPIView, FilterBackendMixin):
    queryset = Customers.objects.all()
    serializer_class = get_read_only_serializer(meta_model=Customers, fields=[])
    # filterset_class = CustomerFilter
    # filterset_class = dynamic_model_filter_set
    filter_backends = [DjangoFilterBackend, CustomSearchFilter]
    search_fields = ['customernumber', "customername", "contactlastname", "contactfirstname"]
    status_field = ""

    def list(self, request, *args, **kwargs):
        params = request.query_params.copy()
        filter_fp = {}
        queryset = self.get_queryset()
        self.date_params_convertion(params, Customers, filter_fp, annotate_fields=[])
        filterset_class = self.dynamic_model_filter_set(meta_model=Customers, fields=[], request=self.request, filter_fp=filter_fp)
        filterset = filterset_class(data=params, queryset=queryset, request=request)
        if filterset.is_valid():
            queryset = filterset.qs
        else:
            return Response(filterset.errors, status=400)
        queryset = self.filter_queryset(queryset)
        sort_by = request.query_params.get('sort_by', None)
        order = request.query_params.get('order', 'asc').lower()
        if sort_by:
            queryset = self.dynamic_ordering(queryset=queryset, sort_by=sort_by, order_by=order,
                                             annotate_fields=[])
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
