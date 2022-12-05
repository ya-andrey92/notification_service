from django.utils import timezone
from django.core.mail import EmailMessage
from django.conf import settings
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
import logging
from .services import (
    MailingDB,
    TaskMailingDB,
    TaskMailing,
    MsgAPI,
    Statistic,
    generation_csv
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=None, name='send_mailing')
def send_mailing(self, mailing_id: int) -> None:
    """Выполнение задачи по рассылке"""
    task_id = self.request.id
    logger.info(f'[mailing_id={mailing_id}]: run task, task_id={task_id}')

    mailing_db = MailingDB(mailing_id=mailing_id)

    if mailing_db.mailing:
        mailing_db.set_status('STARTED')
        task_mailing_db = TaskMailingDB(mailing_db.mailing)
        try:
            if self.request.retries == 0:
                task_mailing_db.create_messages()

            while True:
                messages = task_mailing_db.get_queryset_messages()
                if not messages.exists():
                    break
                msg_api = MsgAPI(mailing_db.mailing)

                for message in messages:
                    send_date = timezone.now()
                    status, data = msg_api.post(message)

                    if status:
                        task_mailing_db.set_sent_status_message(message, send_date)
                    else:
                        if data == msg_api.except_names[2]:
                            task_mailing = TaskMailing(mailing_db.mailing)
                            soft_time_limit = task_mailing.get_time_life()
                            countdown = 300

                            if soft_time_limit <= countdown:
                                raise SoftTimeLimitExceeded

                            logger.info(f'[mailing_id={mailing_id}]: retry task, task_id={task_id}')
                            raise self.retry(countdown=countdown, expires=mailing_db.mailing.finish_date,
                                             soft_time_limit=soft_time_limit)

            mailing_db.set_status('SUCCESS')
            logger.info(f'[mailing_id={mailing_id}]: success task, task_id={task_id}')
        except SoftTimeLimitExceeded:
            task_mailing_db.set_not_sent_status_message()
            mailing_db.set_status('REVOKED BY TIME')
            logger.info(f'[mailing_id={mailing_id}]: stop task by time limit, task_id={task_id}')
    else:
        TaskMailing.revoke_task_by_task_uuid(task_id, mailing_id)
        mailing_db.set_status('REVOKED')
        logger.info(f'[mailing_id={mailing_id}]: stop task, task_id={task_id}')


@shared_task(name='send_statistics')
def send_statistics() -> None:
    """Отправка ежедневной статистики админу"""
    current_date = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = current_date - timezone.timedelta(days=1)
    yesterday_str = yesterday.strftime('%d-%m-%Y')
    data = Statistic.get_queryset_to_date(yesterday)

    if data:
        file = generation_csv(data, yesterday_str)
        email = EmailMessage(
            subject=f'Статистика за {yesterday_str}',
            body='Статистика по рассылкам',
            from_email=settings.EMAIL_HOST_USER,
            to=[settings.EMAIL_HOST_ADMIN]
        )
        email.attach_file(file)
        email.send()
        logger.info(f'Статистика за {yesterday_str} отправлена')
    else:
        logger.info(f'Статистика за {yesterday_str} не обнаружена')
