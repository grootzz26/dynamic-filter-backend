from array import array
from dataclasses import fields

from rest_framework import filters
import django_filters

from classicmodels.models import Customers

BOOLEAN_CHOICES = (('Active', 'Active'), ('InActive', 'InActive'),)

queries = ["contains", "equal", "notequal", "startswith", "endswith", "empty", "notempty"]

def filter_set_fields(column):
    attr = {
        "contains": "django_filters.CharFilter(field_name='{field}', lookup_expr='icontains')",
        "equal": "django_filters.CharFilter(field_name='{field}', lookup_expr='iexact')",
        "notequal": "django_filters.CharFilter(field_name='{field}', method='exclude_exact_match')",
        "startswith": "django_filters.CharFilter(field_name='{field}', lookup_expr='istartswith')",
        "endswith": "django_filters.CharFilter(field_name='{field}', lookup_expr='iendswith')",
        "empty": "django_filters.CharFilter(field_name='{field}', lookup_expr='isnull')",
        "notempty": "django_filters.CharFilter(field_name='{field}', lookup_expr='isnull')"
    }
    for key in attr.keys():
        if key == column.split("_")[-1]: return attr[key]
    return None

def exclude_exact_match(self, queryset, name, value):
    field_param = {f"{name}__iexact": value}
    return queryset.exclude(**field_param)

class EvalFilterFields:
    charField = django_filters.CharFilter(lookup_expr='icontains')
    boolField = django_filters.TypedChoiceFilter(choices=BOOLEAN_CHOICES)

    @classmethod
    def get_eval_filters(cls,fields):
        data_types = {}
        for _d in fields:
            data_types[_d] = cls.charField
        return data_types

# def dynamic_model_filter_set(meta_model=None, fields=[]):
#     meta_fields = [*fields]
#     data = EvalFilterFields().get_eval_filters(meta_fields)
#     class _FilterSet(django_filters.FilterSet):
#         pass
#     for field_name, filter_instance in data.items():
#         setattr(_FilterSet, field_name, filter_instance)
#     _FilterSet.Meta = type("Meta", (), {"model": meta_model, "fields": meta_fields})
#     return _FilterSet

def dynamic_model_filter_set(meta_model=None, fields=None, request=None):
    meta_fields = [*fields] if fields else []
    data = {}
    # data = EvalFilterFields().get_eval_filters(fields)
    for qp in request.query_params:
        qp_filter = filter_set_fields(qp)
        if qp_filter:
            name = qp.split("_")[0]
            data = { qp: eval(qp_filter.format(field=name))}
            meta_fields.append(qp)
    data["exclude_exact_match"] = exclude_exact_match
    meta_attrs = type("Meta", (), {"model": meta_model, "fields": meta_fields})
    data["Meta"] = meta_attrs
    _FilterSet = type("FilterSet", (django_filters.FilterSet,), data)
    return _FilterSet


class DynamicFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        custom_param = request.query_params.get('custom_param', None)
        if custom_param:
            # Perform your custom filtering logic here
            queryset = queryset.filter(custom_attribute=custom_param)
        return queryset


class CustomerFilter(django_filters.FilterSet):
    customername_contains = django_filters.CharFilter(field_name="customername", lookup_expr="icontains")

    class Meta:
        model = Customers
        fields = ("customername_contains",)

    # def exclude_exact_match(self, queryset, name, value):
    #     field_param = {f"{name}__iexact": value}
    #     return queryset.exclude(**field_param)
