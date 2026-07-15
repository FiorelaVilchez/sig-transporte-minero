from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    path('', views.document_list, name='document_list'),
    path('conductor/add/', views.documento_conductor_create, name='documento_conductor_create'),
    path('conductor/<int:pk>/edit/', views.documento_conductor_update, name='documento_conductor_update'),
    path('vehiculo/add/', views.documento_vehiculo_create, name='documento_vehiculo_create'),
    path('vehiculo/<int:pk>/edit/', views.documento_vehiculo_update, name='documento_vehiculo_update'),
]
