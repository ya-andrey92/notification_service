from django.urls import path, include
from rest_framework import routers
from .views import MailingViewSet

router = routers.DefaultRouter()
router.register('mailing', MailingViewSet)

urlpatterns = [
    path('', include(router.urls))
]
