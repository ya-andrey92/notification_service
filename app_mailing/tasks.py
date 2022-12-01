from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded


@shared_task(bind=True, max_retries=None, name='send_mailing')
def send_mailing(self, mailing_id: int) -> None:
    while True:
        try:
            print(f'!!!Request {mailing_id}')
        except SoftTimeLimitExceeded:
            break
