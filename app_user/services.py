from django.forms import model_to_dict
import logging
from .models import OperatorCode, Client

logger = logging.getLogger(__name__)


class OperatorCodeDB:
    """Работа с таблицей operatorcode"""

    def __init__(self, phone: str, client: Client = None):
        self.__code_new = phone[1:4]
        self.__client = client

    def get_or_create_operator_code(self) -> OperatorCode:
        """Получить или создать объект"""
        code, created = OperatorCode.objects.get_or_create(code=self.__code_new)
        if created:
            logger.info(f'[code_id={code.id}]: create operator code, params: {model_to_dict(code)}')
        return code

    def get_operator_code(self) -> OperatorCode:
        """Получить объект"""
        if self.__client.phone[1:4] == self.__code_new:
            return self.__client.code
        return self.get_or_create_operator_code()
