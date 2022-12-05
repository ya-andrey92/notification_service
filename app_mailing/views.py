from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status, serializers
import logging
from .models import Mailing
from .serializers import MailingSerializer, StatisticsSerializer, StatisticsDetailSerializer
from .services import TaskMailing, Statistic
from app_user.paginations import CustomPagination

logger = logging.getLogger(__name__)


class MailingViewSet(ModelViewSet):
    """Управление рассылками"""
    queryset = Mailing.objects.all()
    serializer_class = MailingSerializer
    permission_classes = (IsAdminUser,)
    pagination_class = CustomPagination

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.status in (0, 1):
            task = TaskMailing(instance)
            task.revoke_task()

        msg_cnt = instance.message.filter(status=1).count()

        if instance.status == 1 and msg_cnt != 0:
            instance.status = 3
            instance.save()
            logger.info(f'[mailing_id={instance.id}]: stop mailing')
            return Response("Mailing stopped", status=status.HTTP_200_OK)

        elif msg_cnt == 0:
            logger.info(f'[mailing_id={instance.id}]: delete mailing')
            return super().destroy(request, *args, **kwargs)

        else:
            raise serializers.ValidationError(
                "Mailing can't be deleted because he sent messages"
            )


class StatisticsViewSet(ReadOnlyModelViewSet):
    """Статистика по рассылкам"""
    serializer_class = StatisticsSerializer
    permission_classes = (IsAdminUser,)
    pagination_class = CustomPagination

    def get_queryset(self):
        if self.kwargs.get('pk'):
            return Statistic.get_queryset()
        return Statistic.get_queryset_list()

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return StatisticsDetailSerializer
        return super().get_serializer_class()
