from django.utils import timezone
from django.db.models.query import QuerySet
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from rest_framework import status
from config import celery_app

from itertools import islice
import logging
import requests
from requests.exceptions import Timeout, ConnectionError, HTTPError
from uuid import UUID
from typing import Tuple, Dict

from .models import Mailing, Message
from app_user.models import Client

logger = logging.getLogger(__name__)


class TaskMailing:
    """Управление задачей рассылки"""

    def __init__(self, mailing: Mailing):
        self.__mailing = mailing

    def create_task(self) -> UUID:
        """Создать задачу"""
        from .tasks import send_mailing

        task = send_mailing.apply_async(
            kwargs={'mailing_id': self.__mailing.id},
            eta=self.__mailing.start_date,
            expires=self.__mailing.finish_date,
            soft_time_limit=self.get_time_life()
        )

        logger.info(f'[mailing_id={self.__mailing.id}]: created task, task_id={task.id}')
        return task.id

    def update_task(self) -> UUID:
        """Обновить задачу"""
        self.revoke_task()
        return self.create_task()

    def revoke_task(self) -> None:
        """Отменить/остановить задачу"""
        self.revoke_task_by_task_uuid(self.__mailing.task_uuid, self.__mailing.id)

    @staticmethod
    def revoke_task_by_task_uuid(task_uuid: UUID, mailing_id: int) -> None:
        """Отменить/остановить задачу по параметрам"""
        celery_app.control.revoke(task_uuid, terminate=True)
        logger.info(f'[mailing_id={mailing_id}]: revoke task, task_id={task_uuid}')

    def get_time_life(self) -> int:
        """Получить время жизни задачи в секундах"""
        start_date = self.__mailing.start_date
        if start_date < timezone.now():
            start_date = timezone.now()
        return int((self.__mailing.finish_date - start_date).total_seconds())


class MailingDB:
    """Класс для работы c таблицей Mailing"""

    def __init__(self, mailing_id: int):
        self.__mailing_id = mailing_id
        self.__mailing = self._get_mailing()

    @property
    def mailing(self) -> Mailing | None:
        return self.__mailing

    def _get_mailing(self) -> Mailing | None:
        """Получить объект рассылки"""
        try:
            mailing = Mailing.objects.get(pk=self.__mailing_id)
        except ObjectDoesNotExist as ex:
            logger.exception(f'[mailing_id={self.__mailing_id}]: {ex}', exc_info=None)
            return None
        return mailing

    def set_status(self, status_name: str) -> None:
        """Изменить статус рассылки"""
        statuses = dict((key, value) for (value, key) in self.__mailing.STATUS_CHOICES)
        self.__mailing.status = statuses[status_name]
        if statuses[status_name] > 1:
            self.__mailing.finish_date = timezone.now()
        self.__mailing.save()
        logger.info(f'[mailing_id={self.__mailing_id}]: set status {status_name}')


class TaskMailingDB:
    """Класс для работы с БД для задачи рассылки"""

    def __init__(self, mailing: Mailing):
        self.__mailing = mailing

    def _get_queryset_clients(self) -> QuerySet:
        """Получить клиентов по критериям"""
        queryset = Client.objects.all()
        if self.__mailing.code:
            queryset = queryset.filter(code__in=self.__mailing.code.all())
        if self.__mailing.tag:
            queryset = queryset.filter(tag__in=self.__mailing.tag.all())
        return queryset

    def create_messages(self) -> None:
        """Создание пустых сообщений"""
        client = self._get_queryset_clients()
        if client.exists():
            batch_size = 500
            message_objs = (Message(mailing=self.__mailing, client=client)
                            for client in client.iterator())
            while True:
                batch = list(islice(message_objs, batch_size))
                if not batch:
                    break
                Message.objects.bulk_create(batch, batch_size)
            logger.info(f'[mailing_id={self.__mailing.id}]: create message for clients')

    def set_sent_status_message(self, message: Message, send_date: timezone) -> None:
        """Обновить статус на отправленный"""
        message.status = 1
        message.send_date = send_date
        message.save()
        logger.info(f'[mailing_id={self.__mailing.id}]-[message_id={message.id}]-'
                    f'[client_id={message.client_id}]: save status send')

    def set_not_sent_status_message(self) -> None:
        """Обновить статус на не отправленный"""
        Message.objects.filter(mailing=self.__mailing, status__isnull=True). \
            update(status=0, send_date=timezone.now())
        logger.info(f'[mailing_id={self.__mailing.id}]: save status not send')

    def get_queryset_messages(self) -> QuerySet:
        """Получить пустые сообщения для рассылки"""
        queryset = Message.objects.select_related('client'). \
            filter(mailing=self.__mailing, status__isnull=True). \
            defer('client__code', 'client__tag', 'client__time_zone')
        return queryset


class MsgAPI:
    """Класс для отправления сообщений на стороннее API"""
    url = settings.PROBE_SERVER_URL
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': settings.PROBE_SERVER_TOKEN
    }
    timeout = settings.PROBE_SERVER_TIMEOUT
    except_names = ('Timeout', 'HTTPError', 'ConnectionError')

    def __init__(self, mailing: Mailing):
        self.__mailing = mailing

    def post(self, message: Message) -> Tuple[bool, str | Dict]:
        phone = message.client.phone
        log_msg = f'[mailing_id={self.__mailing.id}]-[message_id={message.id}]-' \
                  f'[client_id={message.client_id}]'
        data = {'id': message.id, 'phone': phone, 'text': self.__mailing.text}

        try:
            response = requests.post(f'{self.url}{message.id}', headers=self.headers,
                                     json=data, timeout=self.timeout)
            response.raise_for_status()
        except Timeout as time_ex:
            except_msg = time_ex
            except_name = self.except_names[0]
        except HTTPError as http_ex:
            except_msg = http_ex
            except_name = self.except_names[1]
        except ConnectionError as conn_ex:
            except_msg = conn_ex
            except_name = self.except_names[2]
        else:
            if response.status_code == status.HTTP_200_OK:
                logger.info(f'{log_msg}: send on phone {phone}')
                return True, response.json()
            logger.info(f"{log_msg}: didn't send on phone {phone}")
            return False, "Not send"

        logger.exception(f'{log_msg}: {except_name} - {except_msg}', exc_info=None)
        return False, except_name
