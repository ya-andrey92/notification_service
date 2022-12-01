from django.utils import timezone
from rest_framework import serializers
from .models import Mailing


class MailingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mailing
        fields = ('id', 'start_date', 'finish_date', 'text', 'tag', 'code', 'status')
        read_only_fields = ('status',)

    def validate_finish_date(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError('Date must be greater than current')
        return value

    def validate(self, data):
        if data['start_date'] >= data['finish_date']:
            raise serializers.ValidationError(
                'finish_date must be greater than the start_date'
            )
        return data
