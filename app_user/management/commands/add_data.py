from django.core.management.base import BaseCommand
import random
from typing import List
from app_user.models import Client, OperatorCode, Tag


class Command(BaseCommand):
    help = 'add 9000 clients,10 codes and 10 tags'

    def handle(self, *args, **options):
        tags = self._add_tags()
        codes = self._add_codes()
        self._add_client(codes, tags)

    def _add_tags(self) -> List:
        tags = []
        for i in range(1, 11):
            tags.append(Tag(name=f'tag{i}', description=f'Description{i}'))
        Tag.objects.bulk_create(tags)
        self.stdout.write(self.style.SUCCESS('Added tags successfully'))
        return tags

    def _add_codes(self) -> List:
        codes = []
        code = 500
        for i in range(1, 11):
            codes.append(OperatorCode(code=f'{code + i}'))
        OperatorCode.objects.bulk_create(codes)
        self.stdout.write(self.style.SUCCESS('Added operator codes successfully'))
        return codes

    def _add_client(self, codes: List, tags: List) -> None:
        clients = []
        for i in range(1000, 10000):
            code = random.choice(codes)
            tag = random.choice(tags)
            client = Client(phone=f'7{code.code}567{i}', code=code,
                            tag=tag, time_zone='Europe/Minsk')
            clients.append(client)
        Client.objects.bulk_create(clients)
        self.stdout.write(self.style.SUCCESS('Added clients successfully'))
