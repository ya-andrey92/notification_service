from django.urls import reverse
from django.utils import timezone
from rest_framework import status
import uuid
from unittest import mock
from app_user.tests import AuthAPITestCase
from .models import Mailing, Message
from app_user.models import Client


class MockTask:
    """Mock для получения id задачи"""

    def __init__(self):
        self.id = uuid.uuid4()


class MailingTest(AuthAPITestCase):
    __url_mailing = reverse('mailing-list')
    __name_url_mailing_detail = 'mailing-detail'

    @classmethod
    def setUpTestData(cls):
        cls._create_users()
        cls._create_data_clients()

    def setUp(self) -> None:
        mailings = self._create_mailing()
        self._create_messages(mailings)
        self.client_admin = self._authorization_admin()

    @staticmethod
    def _create_mailing():
        mailing_statuses = (i for i, _ in Mailing.STATUS_CHOICES)
        mailings = []

        for mailing_status in mailing_statuses:
            for i in range(2):
                start_date = timezone.now() + timezone.timedelta(hours=mailing_status)
                finish_date = start_date + timezone.timedelta(hours=1)
                task = MockTask()

                mailings.append(
                    Mailing(
                        start_date=start_date,
                        finish_date=finish_date,
                        text=f'Test{mailing_status}-{i}',
                        status=mailing_status,
                        task_uuid=task.id
                    )
                )
        Mailing.objects.bulk_create(mailings)
        return mailings

    @staticmethod
    def _create_messages(mailings):
        client = Client.objects.first()
        messages = []

        for mailing in mailings[::2]:
            messages.append(
                Message(
                    send_date=timezone.now(),
                    mailing=mailing,
                    client=client,
                    status=1
                )
            )
        Message.objects.bulk_create(messages)

    def test_post_endpoints_if_finish_date_less_current_date(self):
        finish_date = timezone.now()
        start_date = finish_date - timezone.timedelta(hours=5)
        data = {'start_date': start_date, 'finish_date': finish_date, 'text': 'test'}
        response = self.client_admin.post(self.__url_mailing, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_endpoints_if_finish_date_less_or_equal_start_date(self):
        start_date = timezone.now() + timezone.timedelta(hours=5)
        finish_date = start_date - timezone.timedelta(hours=3)

        data = {'start_date': start_date, 'finish_date': finish_date, 'text': 'test'}
        response = self.client_admin.post(self.__url_mailing, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        data = {'start_date': start_date, 'finish_date': start_date, 'text': 'test'}
        response = self.client_admin.post(self.__url_mailing, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch('app_mailing.tasks.send_mailing.apply_async')
    def test_post_endpoints(self, call_task):
        task = MockTask()
        call_task.return_value = task

        start_date = timezone.now() + timezone.timedelta(hours=5)
        finish_date = start_date + timezone.timedelta(hours=3)

        data = {'start_date': start_date, 'finish_date': finish_date, 'text': 'test'}
        response = self.client_admin.post(self.__url_mailing, data=data)

        mailing_id = response.json()['id']
        mailing = Mailing.objects.get(pk=mailing_id)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(task.id, mailing.task_uuid)

    @mock.patch('app_mailing.tasks.send_mailing.apply_async')
    def test_put_endpoints_if_change_date(self, call_task):
        task = MockTask()
        call_task.return_value = task

        mailing = Mailing.objects.filter(status=0).first()
        start_date = timezone.now() + timezone.timedelta(hours=5)
        finish_date = start_date + timezone.timedelta(hours=3)
        url = reverse(self.__name_url_mailing_detail, kwargs={'pk': mailing.id})

        data = {'start_date': start_date, 'finish_date': finish_date, 'text': 'test1'}
        response = self.client_admin.put(url, data=data)
        mailing_new = Mailing.objects.get(pk=mailing.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(mailing.task_uuid == mailing_new.task_uuid)
        self.assertEqual(task.id, mailing_new.task_uuid)

    @mock.patch('app_mailing.tasks.send_mailing.apply_async')
    def test_patch_endpoints_if_not_change_date(self, call_task):
        task = MockTask()
        call_task.return_value = task
        mailing = Mailing.objects.filter(status=0).first()

        url = reverse(self.__name_url_mailing_detail, kwargs={'pk': mailing.id})
        data = {'text': 'test2'}

        response = self.client_admin.patch(url, data=data)
        mailing_new = Mailing.objects.get(pk=mailing.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(task.id == mailing_new.task_uuid)
        self.assertEqual(mailing.task_uuid, mailing_new.task_uuid)
        self.assertEqual(mailing_new.text, data.get('text'))

    def test_delete_endpoints(self):
        mailings = Mailing.objects.all()

        for mailing in mailings:
            url = reverse(self.__name_url_mailing_detail, kwargs={'pk': mailing.id})
            message_cnt = mailing.message.count()
            response = self.client_admin.delete(url)

            if message_cnt == 0:
                self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            elif mailing.status == 1:
                mailing_new = Mailing.objects.get(pk=mailing.id)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertFalse(mailing_new.status == mailing.status)
                self.assertEqual(mailing_new.status, 3)
            else:
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
