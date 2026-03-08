from django.contrib import admin

from .models import (
    # Terceros
    Cliente,
    Proveedor,

    # Catálogo
    CategoriaProducto,
    Producto,
    VarianteProducto,

    # Inventario / Materiales
    CategoriaMaterial,
    Material,
    Almacen,
    ItemInventario,
    MovimientoInventario,

    # Compras
    Compra,
    DetalleCompra,

    # Producción (Fórmulas)
    Formula,
    DetalleFormula,
    LoteProduccion,

    # Ventas
    Venta,
    DetalleVenta,

    # Finanzas
    CategoriaGasto,
    Gasto,
    CuentaPorCobrar,
    CuentaPorPagarCompra,
    CuentaPorPagarGasto,
    Pago,
)


# =========================
# TERCEROS
# =========================
@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "telefono", "email", "activo", "actualizado")
    list_filter = ("activo",)
    search_fields = ("nombre", "telefono", "email")
    ordering = ("nombre",)


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ("nombre", "telefono", "email", "activo", "actualizado")
    list_filter = ("activo",)
    search_fields = ("nombre", "telefono", "email")
    ordering = ("nombre",)


# =========================
# CATÁLOGO
# =========================
@admin.register(CategoriaProducto)
class CategoriaProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "activa", "actualizada")
    list_filter = ("activa",)
    search_fields = ("nombre",)
    ordering = ("nombre",)


class VarianteProductoInline(admin.TabularInline):
    model = VarianteProducto
    extra = 1


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "precio_venta_defecto", "controla_inventario", "activo", "actualizado")
    list_filter = ("categoria", "controla_inventario", "activo")
    search_fields = ("nombre", "categoria__nombre")
    ordering = ("nombre",)
    inlines = [VarianteProductoInline]


@admin.register(VarianteProducto)
class VarianteProductoAdmin(admin.ModelAdmin):
    list_display = ("sku", "producto", "nombre", "precio_venta_efectivo", "modo_costo", "costo_unitario_fijo", "activa")
    list_filter = ("modo_costo", "activa", "producto__categoria")
    search_fields = ("sku", "nombre", "producto__nombre")
    ordering = ("producto__nombre", "nombre")


# =========================
# MATERIALES / INVENTARIO
# =========================
@admin.register(CategoriaMaterial)
class CategoriaMaterialAdmin(admin.ModelAdmin):
    list_display = ("nombre", "activa", "actualizada")
    list_filter = ("activa",)
    search_fields = ("nombre",)
    ordering = ("nombre",)


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "unidad", "costo_defecto", "activo", "actualizado")
    list_filter = ("categoria", "activo")
    search_fields = ("nombre", "categoria__nombre", "unidad")
    ordering = ("nombre",)


@admin.register(Almacen)
class AlmacenAdmin(admin.ModelAdmin):
    list_display = ("nombre", "activo", "actualizado")
    list_filter = ("activo",)
    search_fields = ("nombre",)
    ordering = ("nombre",)


@admin.register(ItemInventario)
class ItemInventarioAdmin(admin.ModelAdmin):
    list_display = ("almacen", "tipo", "material", "variante_producto", "punto_reorden", "activo", "actualizado")
    list_filter = ("almacen", "tipo", "activo")
    search_fields = ("almacen__nombre", "material__nombre", "variante_producto__sku", "variante_producto__producto__nombre")
    ordering = ("almacen__nombre", "tipo")
    autocomplete_fields = ("material", "variante_producto")


@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = ("creado", "tipo", "item", "cantidad", "costo_unitario", "referencia", "referencia_id")
    list_filter = ("tipo", "referencia", "creado")
    search_fields = (
        "item__almacen__nombre",
        "item__material__nombre",
        "item__variante_producto__sku",
        "item__variante_producto__producto__nombre",
        "referencia",
    )
    ordering = ("-creado",)
    autocomplete_fields = ("item",)


# =========================
# COMPRAS
# =========================
class DetalleCompraInline(admin.TabularInline):
    model = DetalleCompra
    extra = 1
    autocomplete_fields = ("material",)


@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = ("id", "proveedor", "fecha", "estado", "estado_pago", "actualizado")
    list_filter = ("estado", "estado_pago", "fecha")
    search_fields = ("proveedor__nombre", "id")
    ordering = ("-fecha", "-id")
    autocomplete_fields = ("proveedor",)
    inlines = [DetalleCompraInline]


@admin.register(DetalleCompra)
class DetalleCompraAdmin(admin.ModelAdmin):
    list_display = ("compra", "material", "cantidad", "costo_unitario")
    list_filter = ("compra__fecha",)
    search_fields = ("compra__id", "material__nombre")
    autocomplete_fields = ("compra", "material")


# =========================
# PRODUCCIÓN (FÓRMULAS)
# =========================
class DetalleFormulaInline(admin.TabularInline):
    model = DetalleFormula
    extra = 1
    autocomplete_fields = ("material",)


@admin.register(Formula)
class FormulaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "variante_producto", "activa", "costo_mano_obra_unitario", "costo_indirecto_unitario", "actualizada")
    list_filter = ("activa", "variante_producto__producto__categoria")
    search_fields = ("nombre", "variante_producto__sku", "variante_producto__producto__nombre")
    ordering = ("variante_producto__producto__nombre", "nombre")
    autocomplete_fields = ("variante_producto",)
    inlines = [DetalleFormulaInline]


@admin.register(DetalleFormula)
class DetalleFormulaAdmin(admin.ModelAdmin):
    list_display = ("formula", "material", "cantidad_por_unidad", "merma_porcentaje")
    list_filter = ("formula",)
    search_fields = ("formula__nombre", "material__nombre")
    autocomplete_fields = ("formula", "material")


@admin.register(LoteProduccion)
class LoteProduccionAdmin(admin.ModelAdmin):
    list_display = ("id", "formula", "fecha", "cantidad_producida", "estado", "costo_unitario_resultado", "actualizado")
    list_filter = ("estado", "fecha")
    search_fields = ("id", "formula__nombre", "formula__variante_producto__sku", "formula__variante_producto__producto__nombre")
    ordering = ("-fecha", "-id")
    autocomplete_fields = ("formula",)


# =========================
# VENTAS
# =========================
class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 1
    autocomplete_fields = ("variante_producto",)


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ("id", "fecha", "cliente", "estado", "tipo_pago", "total", "monto_pagado", "saldo_pendiente", "actualizado")
    list_filter = ("estado", "tipo_pago", "fecha")
    search_fields = ("id", "cliente__nombre")
    ordering = ("-fecha", "-id")
    autocomplete_fields = ("cliente",)
    inlines = [DetalleVentaInline]


@admin.register(DetalleVenta)
class DetalleVentaAdmin(admin.ModelAdmin):
    list_display = ("venta", "variante_producto", "cantidad", "precio_unitario", "descuento", "subtotal")
    list_filter = ("venta__fecha",)
    search_fields = ("venta__id", "variante_producto__sku", "variante_producto__producto__nombre")
    autocomplete_fields = ("venta", "variante_producto")


# =========================
# FINANZAS
# =========================
@admin.register(CategoriaGasto)
class CategoriaGastoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "activa", "actualizada")
    list_filter = ("activa",)
    search_fields = ("nombre",)
    ordering = ("nombre",)


@admin.register(Gasto)
class GastoAdmin(admin.ModelAdmin):
    list_display = ("id", "fecha", "categoria", "proveedor", "monto", "estado_pago", "actualizado")
    list_filter = ("estado_pago", "fecha", "categoria")
    search_fields = ("id", "categoria__nombre", "proveedor__nombre")
    ordering = ("-fecha", "-id")
    autocomplete_fields = ("categoria", "proveedor")


@admin.register(CuentaPorCobrar)
class CuentaPorCobrarAdmin(admin.ModelAdmin):
    list_display = ("id", "cliente", "venta", "monto_total", "monto_pagado", "saldo", "estado", "fecha_vencimiento", "actualizada")
    list_filter = ("estado", "fecha_vencimiento")
    search_fields = ("id", "cliente__nombre", "venta__id")
    ordering = ("-id",)
    autocomplete_fields = ("cliente", "venta")


@admin.register(CuentaPorPagarCompra)
class CuentaPorPagarCompraAdmin(admin.ModelAdmin):
    list_display = ("id", "proveedor", "compra", "monto_total", "monto_pagado", "saldo", "estado", "fecha_vencimiento", "actualizada")
    list_filter = ("estado", "fecha_vencimiento")
    search_fields = ("id", "proveedor__nombre", "compra__id")
    ordering = ("-id",)
    autocomplete_fields = ("proveedor", "compra")


@admin.register(CuentaPorPagarGasto)
class CuentaPorPagarGastoAdmin(admin.ModelAdmin):
    list_display = ("id", "proveedor", "gasto", "monto_total", "monto_pagado", "saldo", "estado", "fecha_vencimiento", "actualizada")
    list_filter = ("estado", "fecha_vencimiento")
    search_fields = ("id", "proveedor__nombre", "gasto__id")
    ordering = ("-id",)
    autocomplete_fields = ("proveedor", "gasto")


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "direccion",
        "fecha",
        "monto",
        "metodo",
        "cuenta_por_cobrar",
        "cuenta_por_pagar_compra",
        "cuenta_por_pagar_gasto",
        "creado",
    )
    list_filter = ("direccion", "fecha")
    search_fields = ("id", "metodo", "nota")
    ordering = ("-fecha", "-id")
    autocomplete_fields = ("cuenta_por_cobrar", "cuenta_por_pagar_compra", "cuenta_por_pagar_gasto")