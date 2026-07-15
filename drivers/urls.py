from django.urls import path
from . import views

app_name = 'drivers'

urlpatterns = [
    path('', views.conductor_list, name='conductor_list'),
    path('<int:pk>/', views.conductor_detail, name='conductor_detail'),
    path('add/', views.conductor_create, name='conductor_create'),
    path('<int:pk>/edit/', views.conductor_update, name='conductor_update'),
    path('<int:pk>/dar-baja/', views.conductor_dar_baja, name='conductor_dar_baja'),
    path('<int:pk>/delete/', views.conductor_delete, name='conductor_delete'),
]
