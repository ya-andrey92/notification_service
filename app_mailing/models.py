from django.db import models
from app_user.models import Client, OperatorCode, Tag


class Mailing(models.Model):
    """Рассылка"""
    STATUS_CHOICES = ((0, 'PENDING'), (1, 'STARTED'), (2, 'SUCCESS'),
                      (3, 'REVOKED BY TIME'), (4, 'REVOKED'))

    start_date = models.DateTimeField()
    finish_date = models.DateTimeField()
    text = models.TextField()
    tag = models.ManyToManyField(Tag, blank=True, related_name='mailing')
    code = models.ManyToManyField(OperatorCode, blank=True, related_name='mailing')
    status = models.PositiveSmallIntegerField(choices=STATUS_CHOICES, default=0)
    task_uuid = models.UUIDField(null=True, editable=False)

    def __str__(self):
        return f'{self.id}: {self.start_date}-{self.finish_date}'

    class Meta:
        ordering = ['-id']


class Message(models.Model):
    """Сообщение"""
    STATUS_CHOICES = ((0, 'Not sent'), (1, 'Sent'))

    send_date = models.DateTimeField()
    status = models.IntegerField(choices=STATUS_CHOICES, blank=True, null=True)
    mailing = models.ForeignKey(Mailing, on_delete=models.PROTECT, related_name='message')
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, related_name='message')

    def __str__(self):
        return f'{self.id}: {self.status}'

    class Meta:
        ordering = ['-id']
