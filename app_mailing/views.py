from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAdminUser
from .models import Mailing
from .serializers import MailingSerializer
from app_user.paginations import CustomPagination


class MailingViewSet(ModelViewSet):
    queryset = Mailing.objects.all()
    serializer_class = MailingSerializer
    permission_classes = (IsAdminUser,)
    pagination_class = CustomPagination
