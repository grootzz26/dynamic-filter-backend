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
import ast
import datetime as dt


class CustomSearchFilter(SearchFilter):
    def filter_queryset(self, request, queryset, view):
        search_fields = self.get_search_fields(view, request)
        search_terms = self.get_search_terms(request)
        status_field = getattr(view, "status_field", None)
        and_filter = getattr(view, "and_search_field", None)

        if not search_fields or not search_terms:
            return queryset
        if status_field:
            if any(x.lower() in ['active', 'yes'] for x in search_terms):
                param = { f"{status_field}": True}
                queryset = queryset.filter(**param)
                return queryset
            elif any(x.lower() in ['inactive', 'no'] for x in search_terms):
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
        if and_filter:
            queryset = queryset.filter(**and_filter)
        if self.must_call_distinct(queryset, search_fields):
            # inspired by django.contrib.admin
            # this is more accurate than .distinct form M2M relationship
            # also is cross-database
            queryset = queryset.filter(pk=models.OuterRef('pk'))
            queryset = base.filter(models.Exists(queryset))
        return queryset

class FilterBackendMixin:
    fields = ['_contains', '_equal', '_notequal', '_startswith', '_endswith', '_empty', '_notempty', '_before',
              '_after', '_start', '_end', '_is']
    def filter_set_fields(self, column, qp=0, lookup_field=None):
        attr = [
            {
                "attribute": "contains",
                "map_attr": django_filters.CharFilter(field_name=lookup_field, lookup_expr='icontains'),
            },
            {
                "attribute": "equal",
                "map_attr": django_filters.CharFilter(field_name=lookup_field, lookup_expr='iexact'),
            },
            {
                "attribute": "notequal",
                "map_attr": django_filters.CharFilter(field_name=lookup_field, method='exclude_exact_match'),
            },
            {
                "attribute": "startswith",
                "map_attr": django_filters.CharFilter(field_name=lookup_field, lookup_expr='istartswith'),
            },
            {
                "attribute": "endswith",
                "map_attr": django_filters.CharFilter(field_name=lookup_field, lookup_expr='iendswith'),
            },
            {
                "attribute": "empty",
                "map_attr": django_filters.BooleanFilter(field_name=lookup_field, method='exclude_exact_null'),
            },
            {
                "attribute": "notempty",
                "map_attr": django_filters.BooleanFilter(field_name=lookup_field, method='exclude_exact_not_null'),
            },
            {
                "attribute": "listin",
                "map_attr": django_filters.CharFilter(field_name=lookup_field, method='list_filter'),
            },
            {
                "attribute": "notlistin",
                "map_attr": django_filters.CharFilter(field_name=lookup_field, method='exclude_list_filter')
            }
        ]
        date_attr = [
            {
                "attribute": "equal",
                "map_attr": django_filters.DateFilter(field_name=lookup_field, lookup_expr='date'),
            },
            {
                "attribute": "notequal",
                "map_attr": django_filters.DateFilter(field_name=lookup_field, method='exclude_exact_match'),
            },
            {
                "attribute": "before",
                "map_attr": django_filters.DateFilter(field_name=lookup_field, lookup_expr='lte'),
            },
            {
                "attribute": "after",
                "map_attr": django_filters.DateFilter(field_name=lookup_field, lookup_expr='gte'),
            },
            {
                "attribute": "empty",
                "map_attr": django_filters.BooleanFilter(field_name=lookup_field, method='exclude_exact_null'),
            },
            {
                "attribute": "notempty",
                "map_attr": django_filters.BooleanFilter(field_name=lookup_field, method='exclude_exact_not_null'),
            },
            {
                "attribute": "start",
                "map_attr": django_filters.DateFilter(field_name=lookup_field, lookup_expr='gte'),
            },
            {
                "attribute": "end",
                "map_attr": django_filters.DateFilter(field_name=lookup_field, lookup_expr='lte')
            }
        ]
        bool_attr = [
            {
                "attribute": "empty",
                "map_attr": django_filters.BooleanFilter(field_name=lookup_field, method='exclude_boolean_match'),
            },
            {
                "attribute": "notempty",
                "map_attr": django_filters.BooleanFilter(field_name=lookup_field, method='boolean_match'),
            },
            {
                "attribute": "is",
                "map_attr": django_filters.BooleanFilter(field_name=lookup_field, method='boolean_match'),
            }
        ]
        date_only_attr = [
            {
                "attribute": "equal",
                "map_attr": django_filters.DateFilter(field_name=lookup_field),
            },
            {
                "attribute": "notequal",
                "map_attr": django_filters.DateFilter(field_name=lookup_field, method='exclude_exact_match'),
            },
            {
                "attribute": "before",
                "map_attr": django_filters.DateFilter(field_name=lookup_field, lookup_expr='lte'),
            },
            {
                "attribute": "after",
                "map_attr": django_filters.DateFilter(field_name=lookup_field, lookup_expr='gte'),
            },
            {
                "attribute": "empty",
                "map_attr": django_filters.BooleanFilter(field_name=lookup_field, method='exclude_exact_null'),
            },
            {
                "attribute": "notempty",
                "map_attr": django_filters.BooleanFilter(field_name=lookup_field, method='exclude_exact_not_null'),
            },
            {
                "attribute": "start",
                "map_attr": django_filters.DateFilter(field_name=lookup_field, lookup_expr='gte'),
            },
            {
                "attribute": "end",
                "map_attr": django_filters.DateFilter(field_name=lookup_field, lookup_expr='lte')
            }
        ]
        if qp == 1:
            attr = date_attr
        elif qp == 2:
            attr = bool_attr
        elif qp == 3:
            attr = date_only_attr
        for key in attr:
            if key["attribute"] == column.split("_")[-1]: return key["map_attr"]
        return None

    def exclude_exact_match(self, queryset, name, value):
        if isinstance(value, dt.date):
            field_param = {f"{name}__date": value}
        else:
            field_param = {f"{name}__iexact": value}
        return queryset.exclude(**field_param)

    def exclude_exact_null(self, queryset, name, value):
        try:
            field_param = Q(**{f"{name}__isnull": value}) | Q(**{name: ""})
            return queryset.filter(field_param)
        except Exception as e:
            logger.error(e)
            field_param = {f"{name}__isnull": value}
        return queryset.filter(**field_param)

    def exclude_exact_not_null(self, queryset, name, value):
        try:
            field_param = Q(**{f"{name}__isnull": value}) | Q(**{name: ""})
            return queryset.exclude(field_param)
        except Exception as e:
            logger.error(e)
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
        return queryset.exclude(**field_param)

    def list_filter(self, queryset, name, value):
        fs = {f"{name}__in": ast.literal_eval(value)}
        return queryset.filter(**fs).distinct()

    def exclude_list_filter(self, queryset, name, value):
        fs = {f"{name}__in": ast.literal_eval(value)}
        return queryset.exclude(**fs).distinct()

    def dynamic_model_filter_set(self, meta_model=None, fields=None, request=None, filter_fp=None):
        meta_fields = []
        data = {}
        for qp in filter_fp:
            if filter_fp[qp].get("date"):
                qp_filter = self.filter_set_fields(qp, 1, lookup_field=filter_fp[qp]['fname'])
            elif filter_fp[qp].get("bool"):
                qp_filter = self.filter_set_fields(qp, 2, lookup_field=filter_fp[qp]['fname'])
            elif filter_fp[qp].get("date_only"):
                qp_filter = self.filter_set_fields(qp, 3, lookup_field=filter_fp[qp]['fname'])
            else:
                qp_filter = self.filter_set_fields(qp, lookup_field=filter_fp[qp]['fname'])
            if qp_filter:
                data[qp] = qp_filter
                meta_fields.append(qp)
        data["exclude_exact_match"] = self.exclude_exact_match
        data["exclude_exact_null"] = self.exclude_exact_null
        data["exclude_exact_not_null"] = self.exclude_exact_not_null
        data["boolean_match"] = self.boolean_match
        data["exclude_boolean_match"] = self.exclude_boolean_match
        data["list_filter"] = self.list_filter
        data["exclude_list_filter"] = self.exclude_list_filter
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

    def date_params_convertion(self, params, meta_model, filter_fp, annotate_fields=[]):
        equal_fs = {}
        for qp in params:
            ref = qp
            if "__" in qp:
                _qp = qp.split("__")
                attr = getattr(meta_model, _qp[0], None)
                name = qp.rsplit('_', 1)[0]
            else:
                _qp = qp.split("_")
                name = qp.replace(f"_{_qp[-1]}", "")
                attr = getattr(meta_model, name, None)
            # check for equal filter param. we need to remove this condition code, after front end code changes done
            if not any(x in qp for x in self.fields):
                if "__" in qp:
                    _qp = qp.split("__")[0]
                    name = qp
                    qp = qp + "_equal"
                else:
                    _qp = qp
                    name = qp
                    qp = qp + "_equal"
                attr = getattr(meta_model, _qp, None)
                if attr or name in annotate_fields:
                    equal_fs[qp] = params[name]
            if not attr:
                if name in annotate_fields:
                    pass
                else:
                    continue
            filter_fp[qp] = dict(fname=name)
            self.model_field_check(filter_fp, attr, qp, params, name, ref)
        params.update(equal_fs)
        return params, filter_fp

    def model_field_check(self, filter_fp, attr, qp, params, name, ref):
        if isinstance(attr, models.query_utils.DeferredAttribute):
            if isinstance(attr.field, models.DateTimeField) and isinstance(attr.field, models.DateField):
                if not any(x in qp for x in ["empty", "notempty"]):
                    params[ref] = datetime.strptime(params.get(ref), '%Y-%m-%d')
                filter_fp[qp]["date"] = True
            elif isinstance(attr.field, models.DateField):
                try:
                    del filter_fp[qp]["date"]
                except KeyError:
                    pass
                filter_fp[qp]["date_only"] = True
            elif isinstance(attr.field, models.BooleanField):
                filter_fp[qp]["bool"] = True
        elif isinstance(attr, models.fields.related_descriptors.ReverseOneToOneDescriptor):
            attr_field = getattr(attr.related.related_model, name.split("__")[1])
            if attr_field:
                if isinstance(attr_field, models.query_utils.DeferredAttribute):
                    return self.model_field_check(filter_fp, attr_field, qp, params, name, ref)
                elif isinstance(attr_field, models.fields.related_descriptors.ReverseOneToOneDescriptor):
                    return self.model_field_check(filter_fp, attr_field, qp, params, name, ref)
                elif isinstance(attr_field, models.fields.related_descriptors.ForwardManyToOneDescriptor):
                    rename = name.split("__")
                    rename.pop(0)
                    rename = "__".join(rename)
                    return self.model_field_check(filter_fp, attr_field, qp, params, rename, ref)
                elif isinstance(attr_field, models.DateTimeField) and isinstance(attr_field, models.DateField):
                    if not any(x in qp for x in ["empty", "notempty"]):
                        params[ref] = datetime.strptime(params.get(ref), '%Y-%m-%d')
                    filter_fp[qp]["date"] = True
                elif isinstance(attr_field, models.DateField):
                    try:
                        del filter_fp[qp]["date"]
                    except KeyError:
                        pass
                    filter_fp[qp]["date_only"] = True
                elif isinstance(attr_field, models.BooleanField):
                    filter_fp[qp]["bool"] = True
        elif isinstance(attr, models.DateTimeField) and isinstance(attr, models.DateField):
            if not any(x in qp for x in ["empty", "notempty"]):
                params[ref] = datetime.strptime(params.get(ref), '%Y-%m-%d')
            filter_fp[qp]["date"] = True
        elif isinstance(attr, models.DateField):
            try:
                del filter_fp[qp]["date"]
            except KeyError:
                pass
            filter_fp[qp]["date_only"] = True
        elif isinstance(attr, models.BooleanField):
            filter_fp[qp]["bool"] = True
        else:
            filter_fp[qp]["date"] = False
        return filter_fp