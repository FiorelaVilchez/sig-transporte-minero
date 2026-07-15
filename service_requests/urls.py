from django.urls import path
from . import views

app_name = 'service_requests'

urlpatterns = [
    path('', views.solicitud_list, name='solicitud_list'),
    path('add/', views.solicitud_create, name='solicitud_create'),
    path('<int:pk>/edit/', views.solicitud_update, name='solicitud_update'),
]
