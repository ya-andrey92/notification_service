from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAdminUser
from rest_framework.decorators import action
from rest_framework.response import Response
import logging
from .models import Client, OperatorCode
from .serializers import ClientSerializer, OperatorCodeSerializer
from .paginations import CustomPagination

logger = logging.getLogger(__name__)


class ClientViewSet(ModelViewSet):
    """Информация о клиенте"""
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = (IsAdminUser,)
    pagination_class = CustomPagination

    @action(methods=['get'], detail=False)
    def code(self, request) -> Response:
        """Информация о кодах оператора"""
        code = OperatorCode.objects.all()
        return Response(OperatorCodeSerializer(code, many=True).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        response = super().destroy(request, *args, **kwargs)
        logger.info(f'[client_id={instance.id}]: deleted client')
        return response
