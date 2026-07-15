from django.urls import path
from . import views

app_name = 'trucks'

urlpatterns = [
    path('', views.vehiculo_list, name='vehiculo_list'),
    path('<int:pk>/', views.vehiculo_detail, name='vehiculo_detail'),
    path('add/', views.vehiculo_create, name='vehiculo_create'),
    path('<int:pk>/edit/', views.vehiculo_update, name='vehiculo_update'),
    path('<int:pk>/dar-baja/', views.vehiculo_dar_baja, name='vehiculo_dar_baja'),
    path('<int:pk>/delete/', views.vehiculo_delete, name='vehiculo_delete'),
]
