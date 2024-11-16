import os
from django.db.models import Q, ForeignKey, DateTimeField
from datetime import datetime
from django.db.models.functions import Lower
import logging
import boto3
from io import BytesIO
from openpyxl import load_workbook
import csv
from openpyxl import Workbook
from rest_framework import filters
import django_filters
from django.db.models import Q
from rest_framework.filters import SearchFilter
from django.db import models
import operator
from functools import reduce


class CustomSearchFilter(SearchFilter):
    def filter_queryset(self, request, queryset, view):
        search_fields = self.get_search_fields(view, request)
        search_terms = self.get_search_terms(request)
        status_field = view.status_field

        if not search_fields or not search_terms:
            return queryset
        if 'active' in search_terms:
            param = { f"{status_field}": True}
            queryset = queryset.filter(**param)
            return queryset
        elif 'inactive' in search_terms:
            param = {f"{status_field}": False}
            queryset = queryset.filter(**param)
            return queryset
        orm_lookups = [
            self.construct_search(str(search_field), queryset)
            for search_field in search_fields
        ]

        base = queryset
        # generator which for each term builds the corresponding search
        conditions = (
            reduce(
                operator.or_,
                (models.Q(**{orm_lookup: term}) for orm_lookup in orm_lookups)
            ) for term in search_terms
        )
        queryset = queryset.filter(reduce(operator.and_, conditions))
        if self.must_call_distinct(queryset, search_fields):
            # inspired by django.contrib.admin
            # this is more accurate than .distinct form M2M relationship
            # also is cross-database
            queryset = queryset.filter(pk=models.OuterRef('pk'))
            queryset = base.filter(models.Exists(queryset))
        return queryset

class FilterBackendMixin:
    def filter_set_fields(self, column, qp=0):
        attr = {
            "contains": "django_filters.CharFilter(field_name='{field}', lookup_expr='icontains')",
            "equal": "django_filters.CharFilter(field_name='{field}', lookup_expr='iexact')",
            "notequal": "django_filters.CharFilter(field_name='{field}', method='exclude_exact_match')",
            "startswith": "django_filters.CharFilter(field_name='{field}', lookup_expr='istartswith')",
            "endswith": "django_filters.CharFilter(field_name='{field}', lookup_expr='iendswith')",
            "empty": "django_filters.CharFilter(field_name='{field}', method='exclude_exact_null')",
            "notempty": "django_filters.CharFilter(field_name='{field}', method='exclude_exact_not_null')"
        }
        date_attr = {
            "equal": "django_filters.DateFilter(field_name='{field}', lookup_expr='date')",
            "notequal": "django_filters.DateFilter(field_name='{field}', method='exclude_exact_match')",
            "before": "django_filters.DateFilter(field_name='{field}', lookup_expr='lte')",
            "after": "django_filters.DateFilter(field_name='{field}', lookup_expr='gte')",
            "empty": "django_filters.DateFilter(field_name='{field}', method='exclude_exact_null')",
            "notempty": "django_filters.DateFilter(field_name='{field}', method='exclude_exact_not_null')",
            "start": "django_filters.DateFilter(field_name='{field}', lookup_expr='gte')",
            "end": "django_filters.DateFilter(field_name='{field}', lookup_expr='lte')",
        }
        bool_attr = {
            "empty": "django_filters.BooleanFilter(field_name='{field}', method='boolean_match')",
            "notempty": "django_filters.BooleanFilter(field_name='{field}', method='exclude_boolean_match')"
        }
        if qp == 1:
            attr = date_attr
        elif qp == 2:
            attr = bool_attr
        for key in attr.keys():
            if key == column.split("_")[-1]: return attr[key]
        return None

    def exclude_exact_match(self, queryset, name, value):
        field_param = {f"{name}__iexact": value}
        return queryset.exclude(**field_param)

    def exclude_exact_null(self, queryset, name, value):
        if value in ("true", ""):
            value = False
        field_param = {f"{name}__isnull": value}
        return queryset.exclude(**field_param)

    def exclude_exact_not_null(self, queryset, name, value):
        if value in ("true", ""):
            value = True
        field_param = {f"{name}__isnull": value}
        return queryset.exclude(**field_param)

    def boolean_match(self, queryset, name, value):
        if value:
            field_param = {f"{name}": True}
            return queryset.filter(**field_param)
        field_param = {f"{name}": False}
        return queryset.filter(**field_param)

    def exclude_boolean_match(self, queryset, name, value):
        if value:
            field_param = {f"{name}": True}
            return queryset.exclude(**field_param)
        field_param = {f"{name}": False}
        return queryset.exlude(**field_param)

    def dynamic_model_filter_set(self, meta_model=None, fields=None, request=None, filter_fp=None):
        meta_fields = []
        data = {}
        for qp in filter_fp:
            if filter_fp[qp].get("date"):
                qp_filter = self.filter_set_fields(qp, 1)
            elif filter_fp[qp].get("bool"):
                qp_filter = self.filter_set_fields(qp, 2)
            else:
                qp_filter = self.filter_set_fields(qp)
            data[qp] = eval(qp_filter.format(field=filter_fp[qp]['fname']))
            meta_fields.append(qp)
        data["exclude_exact_match"] = self.exclude_exact_match
        data["exclude_exact_null"] = self.exclude_exact_null
        data["exclude_exact_not_null"] = self.exclude_exact_not_null
        data["boolean_match"] = self.boolean_match
        data["exclude_boolean_match"] = self.exclude_boolean_match
        meta_attrs = type("Meta", (), {"model": meta_model, "fields": meta_fields})
        data["Meta"] = meta_attrs
        _FilterSet = type("FilterSet", (django_filters.FilterSet,), data)
        return _FilterSet

    def dynamic_ordering(self, queryset=None, sort_by=None, order_by=None, annotate_fields=None):
        if sort_by in annotate_fields:
            alias = f"lower_{sort_by}"
            filter = {}
            filter[alias] = Lower(sort_by)
            if order_by == "asc":
                queryset = queryset.annotate(**filter).order_by(alias)
            else:
                queryset = queryset.annotate(**filter).order_by(f"-{alias}")
        else:
            if order_by == "asc":
                queryset = queryset.order_by(f"{sort_by}")
            else:
                queryset = queryset.order_by(f"-{sort_by}")
        return queryset

    def date_params_convertion(self, params, meta_model, filter_fp):
        for qp in params:
            if "__" in qp:
                _qp = qp.split("_")
                attr = getattr(meta_model, _qp[0], None)
                name = qp.replace(f"_{_qp[-1]}", "")
            else:
                _qp = qp.split("_")
                name = qp.replace(f"_{_qp[-1]}", "")
                attr = getattr(meta_model, name, None)
            if not attr:
                continue
            filter_fp[qp] = dict(fname=name)
            if isinstance(attr, models.query_utils.DeferredAttribute):
                if isinstance(attr.field, models.DateTimeField):
                    params[qp] = datetime.strptime(params.get(qp), '%Y-%m-%d')
                    filter_fp[qp]["date"] = True
                if isinstance(attr.field, models.BooleanField):
                    filter_fp[qp]["bool"] = True
            elif isinstance(attr, models.DateTimeField):
                params[qp] = datetime.strptime(params.get(qp), '%Y-%m-%d')
                filter_fp[qp]["date"] = True
            elif isinstance(attr, models.BooleanField):
                filter_fp[qp]["bool"] = True
            else:
                filter_fp[qp]["date"] = False
        return params, filter_fp