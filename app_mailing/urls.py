from django.urls import path, include
from rest_framework import routers
from .views import MailingViewSet, StatisticsViewSet

router = routers.DefaultRouter()
router.register('mailing', MailingViewSet)
router.register('statistics', StatisticsViewSet, basename='statistics')

urlpatterns = [
    path('', include(router.urls))
]
