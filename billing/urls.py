from django.urls import path

from . import views

app_name = 'billing'

urlpatterns = [
    path('', views.valorizacion_list, name='valorizacion_list'),
    path('<int:pk>/', views.valorizacion_detail, name='valorizacion_detail'),
    path('<int:pk>/estado/', views.valorizacion_estado, name='valorizacion_estado'),
    path('<int:pk>/recalcular/', views.valorizacion_recalcular, name='valorizacion_recalcular'),
    path('revisar-cobros/', views.revisar_cobros, name='revisar_cobros'),
]
