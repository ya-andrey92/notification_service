from django.db import models
from django.core.validators import MinLengthValidator, RegexValidator
from .validators import validate_time_zone


class Client(models.Model):
    """Клиент"""
    phone = models.CharField(
        max_length=11, unique=True,
        validators=[MinLengthValidator(limit_value=11),
                    RegexValidator(r'7\d{10}',
                                   message='The phone number must be in the format 7ХХХХХХХХ')]
    )
    code = models.ForeignKey('OperatorCode', on_delete=models.PROTECT, related_name='client')
    tag = models.ForeignKey('Tag', on_delete=models.SET_NULL, null=True, related_name='client')
    time_zone = models.CharField(max_length=100, validators=[validate_time_zone])

    def __str__(self):
        return f'{self.id}: {self.phone}'

    class Meta:
        ordering = ['id']


class OperatorCode(models.Model):
    """Код мобильного оператора"""
    code = models.CharField(max_length=3, unique=True, validators=[MinLengthValidator(limit_value=3)])

    def __str__(self):
        return f'{self.id}: {self.code}'

    class Meta:
        ordering = ['id']


class Tag(models.Model):
    """Тэг"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f'{self.id}: {self.name}'

    class Meta:
        ordering = ['id']
