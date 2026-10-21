from django.urls import path
from django.contrib.auth import views as auth_views
from . import config_views, usuarios_views, views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.RoleBasedLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('perfil/', views.perfil, name='perfil'),
    path('configuracion/', config_views.configuracion, name='configuracion'),
    path('configuracion/<str:catalogo>/nuevo/', config_views.catalogo_form, name='catalogo_nuevo'),
    path('configuracion/<str:catalogo>/<int:pk>/', config_views.catalogo_form, name='catalogo_editar'),
    path('usuarios/', usuarios_views.usuario_list, name='usuario_list'),
    path('usuarios/nuevo/', usuarios_views.usuario_create, name='usuario_create'),
    path('usuarios/<int:pk>/', usuarios_views.usuario_update, name='usuario_update'),
    path('usuarios/<int:pk>/contrasena/', usuarios_views.usuario_password, name='usuario_password'),
    path('usuarios/<int:pk>/activar/', usuarios_views.usuario_toggle, name='usuario_toggle'),
]

