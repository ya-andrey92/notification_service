from django.utils import timezone
from config import celery_app
from .models import Mailing
from .tasks import send_mailing
from uuid import UUID
import logging

logger = logging.getLogger(__name__)


class TaskMailing:
    """Управление задачей рассылки"""

    def __init__(self, mailing: Mailing):
        self.__mailing = mailing

    def create_task(self) -> UUID:
        """Создать задачу"""
        task = send_mailing.apply_async(
            kwargs={'mailing_id': self.__mailing.id},
            eta=self.__mailing.start_date,
            expires=self.__mailing.finish_date,
            soft_time_limit=self._get_time_life()
        )

        logger.info(f'[mailing_id={self.__mailing.id}]: created task, task_id={task.id}')
        return task.id

    def update_task(self):
        """Обновить задачу"""
        self.revoke_task()
        return self.create_task()

    def revoke_task(self):
        """Отменить/остановить задачу"""
        celery_app.control.revoke(self.__mailing.task_uuid, terminate=True)
        logger.info(f'[mailing_id={self.__mailing.id}]: revoke task, task_id={self.__mailing.task_uuid}')

    def _get_time_life(self) -> int:
        """Получить время жизни задачи в секундах"""
        start_date = self.__mailing.start_date
        if start_date < timezone.now():
            start_date = timezone.now()
        return int((self.__mailing.finish_date - start_date).total_seconds())
