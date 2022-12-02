from django.urls import reverse
from django.utils import timezone
from rest_framework import status
import uuid
from unittest import mock
from requests.exceptions import HTTPError, ConnectionError, Timeout
from app_user.tests import AuthAPITestCase
from .models import Mailing, Message
from .services import MsgAPI


class MockTask:
    """Mock для получения id задачи"""

    def __init__(self):
        self.id = uuid.uuid4()


class MockResponseMsgApi:
    """Mock для  MsgAPI"""

    def __init__(self, method: str, status_code: int = None, name_error: str = ''):
        self.method = method
        self.status_code = status_code
        self.name_error = name_error

    def json(self):
        if self.method == 'post' and self.status_code == 200:
            return {'code': 0, 'message': 'OK'}

    def raise_for_status(self):
        if self.status_code is not None and self.status_code == 400:
            raise HTTPError
        elif self.name_error == MsgAPI.except_names[0]:
            raise Timeout
        elif self.name_error == MsgAPI.except_names[1]:
            raise HTTPError
        elif self.name_error == MsgAPI.except_names[2]:
            raise ConnectionError


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

    @mock.patch('app_mailing.services.TaskMailing.revoke_task_by_task_uuid')
    @mock.patch('app_mailing.tasks.send_mailing.apply_async')
    def test_put_endpoints_if_change_date(self, call_task, revoke_task):
        task = MockTask()
        call_task.return_value = task
        revoke_task.return_value = None

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

    @mock.patch('app_mailing.services.TaskMailing.revoke_task_by_task_uuid')
    def test_delete_endpoints(self, revoke_task):
        mailings = Mailing.objects.all()
        revoke_task.return_value = None

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


class MsgAPITest(AuthAPITestCase):
    @classmethod
    def setUpTestData(cls):
        cls._create_users()
        cls._create_data_clients()

    def setUp(self) -> None:
        mailings = self._create_mailing()
        self._create_messages(mailings)
        self.client_admin = self._authorization_admin()

    @mock.patch('requests.post')
    def test_post_response_http_200(self, requests_post):
        requests_post.return_value = MockResponseMsgApi(method='post', status_code=200)
        message = Message.objects.first()

        msg_api = MsgAPI(message.mailing)
        result = msg_api.post(message)
        self.assertTrue(result[0])
        self.assertEqual(result[1].get('code'), 0)

    @mock.patch('requests.post')
    def test_post_response_http_400(self, requests_post):
        requests_post.return_value = MockResponseMsgApi(method='post', status_code=400)
        message = Message.objects.first()

        msg_api = MsgAPI(message.mailing)
        result = msg_api.post(message)
        self.assertFalse(result[0])
        self.assertEqual(result[1], MsgAPI.except_names[1])

    @mock.patch('requests.post')
    def test_post_response_error(self, requests_post):
        for except_name in MsgAPI.except_names:
            requests_post.return_value = MockResponseMsgApi(method='post', name_error=except_name)
            message = Message.objects.first()

            msg_api = MsgAPI(message.mailing)
            result = msg_api.post(message)
            self.assertFalse(result[0])
            self.assertEqual(result[1], except_name)
