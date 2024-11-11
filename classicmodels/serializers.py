from rest_framework import serializers


def get_read_only_serializer(meta_model=None, fields=[]):
    meta_fields = [*fields] if fields else "__all__"
    class _Serializer(serializers.ModelSerializer):

        class Meta:
            model = meta_model
            fields = meta_fields

    return _Serializer