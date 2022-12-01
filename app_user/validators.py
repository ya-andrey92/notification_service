from django.core.exceptions import ValidationError
import zoneinfo


def validate_time_zone(value):
    if value not in zoneinfo.available_timezones():
        raise ValidationError('Please enter a valid time zone, e.g. Europe/Minsk')
