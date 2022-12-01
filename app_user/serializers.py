from django.db import transaction
from django.forms import model_to_dict
from rest_framework import serializers
import logging
from .models import Client, OperatorCode, Tag
from .services import OperatorCodeDB

logger = logging.getLogger(__name__)


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = '__all__'
        read_only_fields = ('code', )

    def create(self, validated_data):
        with transaction.atomic():
            code = OperatorCodeDB(phone=validated_data['phone'])
            validated_data['code'] = code.get_or_create_operator_code()
            client_obj = super().create(validated_data)
        logger.info(f'[client_id={client_obj.id}]: created client, params: {model_to_dict(client_obj)}')
        return client_obj

    def update(self, instance, validated_data):
        with transaction.atomic():
            code = OperatorCodeDB(phone=validated_data['phone'], client=instance)
            validated_data['code'] = code.get_operator_code()
            client_obj = super().update(instance, validated_data)
        logger.info(f'[client_id={client_obj.id}]: updated client, params: {model_to_dict(client_obj)}')
        return client_obj


class OperatorCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OperatorCode
        fields = '__all__'


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'
