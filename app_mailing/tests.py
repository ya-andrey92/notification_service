from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from app_user.tests import AuthAPITestCase


class MailingTest(AuthAPITestCase):
    __url_mailing = reverse('mailing-list')

    @classmethod
    def setUpTestData(cls):
        cls._create_users()
        cls._create_data_clients()

    def test_post_endpoints_if_finish_date_less_current_date(self):
        client = self._authorization(self._username_admin)
        finish_date = timezone.now()
        start_date = finish_date - timezone.timedelta(hours=5)
        data = {'start_date': start_date, 'finish_date': finish_date, 'text': 'test'}
        response = client.post(self.__url_mailing, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_endpoints_if_finish_date_less_or_equal_start_date(self):
        client = self._authorization(self._username_admin)
        start_date = timezone.now() + timezone.timedelta(hours=5)
        finish_date = start_date - timezone.timedelta(hours=3)

        data = {'start_date': start_date, 'finish_date': finish_date, 'text': 'test'}
        response = client.post(self.__url_mailing, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        data = {'start_date': start_date, 'finish_date': start_date, 'text': 'test'}
        response = client.post(self.__url_mailing, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
