from django.urls import path, include
from rest_framework import routers
from .views import ClientViewSet, TagViewSet

router = routers.DefaultRouter()
router.register('client', ClientViewSet)
router.register('tag', TagViewSet)

urlpatterns = [
    path('', include(router.urls))
]
