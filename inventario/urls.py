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

    path("movimientos/", views.movimientos, name="movimientos"),
    path("inventario/movimientos/", views.movimientos_inventario, name="movimientos_inventario"),

    # Materiales
    path("categorias-material/", views.lista_categorias_material, name="lista_categorias_material"),
    path("categorias-material/nueva/", views.nueva_categoria_material, name="nueva_categoria_material"),
    path("categorias-material/<int:categoria_id>/editar/", views.editar_categoria_material, name="editar_categoria_material"),

    path("materiales/", views.lista_materiales, name="lista_materiales"),
    path("materiales/nuevo/", views.nuevo_material, name="nuevo_material"),
    path("materiales/<int:material_id>/editar/", views.editar_material, name="editar_material"),

    path("almacenes/", views.lista_almacenes, name="lista_almacenes"),
    path("almacenes/nuevo/", views.nuevo_almacen, name="nuevo_almacen"),
    path("almacenes/<int:almacen_id>/editar/", views.editar_almacen, name="editar_almacen"),

    path("inventario/items/", views.lista_items_inventario, name="lista_items_inventario"),
    path("inventario/items/nuevo/", views.nuevo_item_inventario, name="nuevo_item_inventario"),
    path("inventario/items/<int:item_id>/editar/", views.editar_item_inventario, name="editar_item_inventario"),
    path("inventario/ajuste/", views.ajuste_inventario, name="ajuste_inventario"),
    path("inventario/existencias/", views.existencias, name="existencias"),

    path("compras/", views.lista_compras, name="lista_compras"),
    path("compras/nueva/", views.nueva_compra, name="nueva_compra"),
    path("compras/<int:compra_id>/", views.detalle_compra, name="detalle_compra"),
    path("compras/<int:compra_id>/recibir/", views.recibir_compra, name="recibir_compra"),

    # Terceros
    path("terceros/clientes/", views.lista_clientes, name="lista_clientes"),
    path("terceros/clientes/nuevo/", views.nuevo_cliente, name="nuevo_cliente"),
    path("terceros/clientes/<int:cliente_id>/editar/", views.editar_cliente, name="editar_cliente"),

    path("terceros/proveedores/", views.lista_proveedores, name="lista_proveedores"),
    path("terceros/proveedores/nuevo/", views.nuevo_proveedor, name="nuevo_proveedor"),
    path("terceros/proveedores/<int:proveedor_id>/editar/", views.editar_proveedor, name="editar_proveedor"),
    
    # Fórmulas
    path("formulas/", views.lista_formulas, name="lista_formulas"),
    path("formulas/nueva/", views.nueva_formula, name="nueva_formula"),
    path("formulas/<int:formula_id>/editar/", views.editar_formula, name="editar_formula"),
    path("formulas/<int:formula_id>/", views.detalle_formula, name="detalle_formula"),

    # Detalles de fórmula (materiales)
    path("formulas/<int:formula_id>/material/nuevo/", views.nuevo_detalle_formula, name="nuevo_detalle_formula"),
    path("formulas/<int:formula_id>/material/<int:detalle_id>/editar/", views.editar_detalle_formula, name="editar_detalle_formula"),
    path("formulas/<int:formula_id>/material/<int:detalle_id>/eliminar/", views.eliminar_detalle_formula, name="eliminar_detalle_formula"),
    ]