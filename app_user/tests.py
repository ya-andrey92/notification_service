from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
import random
from .models import Client, OperatorCode, Tag


class AuthAPITestCase(APITestCase):
    _username_admin = 'admin'
    _username = 'test{}'
    _password = 'test1234qwe'

    def _authorization(self, username: str) -> APIClient:
        url = reverse('jwt-create')
        data = {'username': username, 'password': self._password}
        response = self.client.post(url, data=data)
        access_token = response.data.get('access')

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        return client

    @classmethod
    def _create_users(cls) -> None:
        user = User.objects.create_user(username=cls._username_admin, password=cls._password)
        user.is_staff = True
        user.save()

        for i in range(3):
            User.objects.create_user(username=cls._username.format(i), password=cls._password)

    @classmethod
    def _create_data_clients(cls):
        tags = []
        for i in range(1, 4):
            tags.append(Tag(name=f'tag{i}', description=f'Description{i}'))
        Tag.objects.bulk_create(tags)

        codes = []
        code = 300
        for i in range(1, 4):
            codes.append(OperatorCode(code=f'{code + i}'))
        OperatorCode.objects.bulk_create(codes)

        clients = []
        for i in range(10, 26):
            code = random.choice(codes)
            tag = random.choice(tags)
            client = Client(phone=f'7{code.code}56721{i}', code=code,
                            tag=tag, time_zone='Europe/Minsk')
            clients.append(client)
        Client.objects.bulk_create(clients)


class ClientTest(AuthAPITestCase):
    __url_client = reverse('client-list')
    __url_client_code = reverse('client-code')
    __name_url_client_detail = 'client-detail'

    @classmethod
    def setUpTestData(cls):
        cls._create_users()
        cls._create_data_clients()

    def test_endpoints_client_if_logout(self):
        response = self.client.get(self.__url_client)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_endpoints_client_if_login_user(self):
        client = self._authorization(self._username.format(1))
        response = client.get(self.__url_client)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_endpoints_client_if_login_admin(self):
        client = self._authorization(self._username_admin)
        response = client.get(self.__url_client)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post_endpoints_client(self):
        client = self._authorization(self._username_admin)
        tag = Tag.objects.first()
        data = {'phone': '70281234560', 'tag': tag.id, 'time_zone': 'Europe/Minsk'}
        code_cnt = OperatorCode.objects.count()
        client_cnt = Client.objects.count()
        response = client.post(self.__url_client, data=data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(code_cnt + 1, OperatorCode.objects.count())
        self.assertEqual(client_cnt + 1, Client.objects.count())

    def test_patch_endpoints_client(self):
        client = self._authorization(self._username_admin)
        code_cnt = OperatorCode.objects.count()
        client_obj = Client.objects.first()

        data = {'phone': '79281234560'}
        url = reverse(self.__name_url_client_detail, kwargs={'pk': client_obj.id})
        response = client.patch(url, data=data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(code_cnt + 1, OperatorCode.objects.count())

    def test_get_endpoints_client_code(self):
        client = self._authorization(self._username_admin)
        response = client.get(self.__url_client_code)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
