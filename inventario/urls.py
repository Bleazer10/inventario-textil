from django.urls import path
from . import views

urlpatterns = [
    # Vender
    path("ventas/nueva/", views.nueva_venta, name="nueva_venta"),
    path("gastos/nuevo/", views.nuevo_gasto, name="nuevo_gasto"),

    # Productos
    path("productos/", views.lista_productos, name="lista_productos"),
    path("productos/nuevo/", views.nuevo_producto, name="nuevo_producto"),
    path("productos/<int:producto_id>/", views.detalle_producto, name="detalle_producto"),
    path("productos/<int:producto_id>/variante/nueva/", views.nueva_variante, name="nueva_variante"),

    path("categorias-producto/", views.lista_categorias_producto, name="lista_categorias_producto"),
    path("categorias-producto/nueva/", views.nueva_categoria_producto, name="nueva_categoria_producto"),
    path("categorias-producto/<int:categoria_id>/editar/", views.editar_categoria_producto, name="editar_categoria_producto"),
    ]