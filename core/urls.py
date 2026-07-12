from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Páginas públicas
    path('', views.home, name='home'),
    path('productos/', views.listar_productos, name='productos'),
    
    # Carrito de compras
    path('carrito/', views.ver_carrito, name='ver_carrito'),
    path('carrito/agregar/', views.agregar_al_carrito, name='agregar_al_carrito'),
    path('carrito/eliminar/', views.eliminar_del_carrito, name='eliminar_del_carrito'),
    path('carrito/actualizar/', views.actualizar_cantidad, name='actualizar_cantidad'),
    path('carrito/vaciar/', views.vaciar_carrito, name='vaciar_carrito'),
    path('carrito/enviar-whatsapp/', views.enviar_pedido_whatsapp, name='enviar_pedido_whatsapp'),
    
    # Dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('dashboard/registrar-venta/', views.registrar_venta, name='registrar_venta'),
    path('api/buscar-productos/', views.buscar_productos, name='buscar_productos'),
]