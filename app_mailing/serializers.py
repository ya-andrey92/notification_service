from django.utils import timezone
from django.forms import model_to_dict
from rest_framework import serializers
import logging
from .models import Mailing, Message
from .services import TaskMailing

logger = logging.getLogger(__name__)


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
        start_date = data.get('start_date')
        finish_date = data.get('finish_date')

        if start_date and finish_date and start_date >= finish_date:
            raise serializers.ValidationError(
                'finish_date must be greater than the start_date'
            )
        return data

    def create(self, validated_data):
        mailing_obj = super().create(validated_data)
        logger.info(f'[mailing_id={mailing_obj.id}]: created mailing, '
                    f'params: {model_to_dict(mailing_obj)}')

        task = TaskMailing(mailing=mailing_obj)
        mailing_obj.task_uuid = task.create_task()
        mailing_obj.save()

        logger.info(f'[mailing_id={mailing_obj.id}]: update task_uuid')
        return mailing_obj

    def update(self, instance, validated_data):
        self.update_validate(instance)
        start_date_old = instance.start_date
        finish_date_old = instance.finish_date

        mailing_obj = super().update(instance, validated_data)
        logger.info(f'[mailing_id={mailing_obj.id}]: update mailing, '
                    f'params: {model_to_dict(mailing_obj)}')

        if not (mailing_obj.start_date == start_date_old and
                mailing_obj.finish_date == finish_date_old):
            task = TaskMailing(mailing=mailing_obj)
            mailing_obj.task_uuid = task.update_task()
            mailing_obj.save()
            logger.info(f'[mailing_id={mailing_obj.id}]: update task_uuid')
        return mailing_obj

    @staticmethod
    def update_validate(instance) -> None:
        if instance.status == 1:
            raise serializers.ValidationError(
                'Cannot be changed because the task is already running. '
                'Delete mailing.'
            )
        elif instance.status > 1:
            raise serializers.ValidationError(
                f'Cannot be changed because the task has already been completed. '
                f'Create a new mailing.'
            )


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ('id', 'send_date', 'status', 'client_id')


class StatisticsSerializer(serializers.ModelSerializer):
    send_success = serializers.IntegerField()
    send_failed = serializers.IntegerField()

    class Meta:
        model = Mailing
        fields = ('id', 'start_date', 'finish_date', 'text', 'status',
                  'send_success', 'send_failed')


class StatisticsDetailSerializer(StatisticsSerializer):
    message = MessageSerializer(many=True, read_only=True)

    class Meta(StatisticsSerializer.Meta):
        fields = StatisticsSerializer.Meta.fields + ('tag', 'code', 'message',)
