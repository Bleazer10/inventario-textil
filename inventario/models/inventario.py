from django.db import models
from .catalogo import VarianteProducto


class CategoriaMaterial(models.Model):
    nombre = models.CharField("Nombre", max_length=120, unique=True)
    activa = models.BooleanField("Activa", default=True)

    creada = models.DateTimeField("Creada", auto_now_add=True)
    actualizada = models.DateTimeField("Actualizada", auto_now=True)

    class Meta:
        verbose_name = "Categoría de material"
        verbose_name_plural = "Categorías de materiales"
        ordering = ["nombre"]

    def __str__(self) -> str:
        return self.nombre


class Material(models.Model):
    categoria = models.ForeignKey(
        CategoriaMaterial,
        on_delete=models.PROTECT,
        related_name="materiales",
        verbose_name="Categoría",
    )
    nombre = models.CharField("Nombre", max_length=150)
    unidad = models.CharField("Unidad", max_length=50, help_text="Ej: metro, unidad, gramo, litro")
    costo_defecto = models.DecimalField(
        "Costo (por defecto)",
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Costo referencial si no quieres calcularlo desde compras.",
    )

    activo = models.BooleanField("Activo", default=True)

    creado = models.DateTimeField("Creado", auto_now_add=True)
    actualizado = models.DateTimeField("Actualizado", auto_now=True)

    class Meta:
        verbose_name = "Material"
        verbose_name_plural = "Materiales"
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(fields=["categoria", "nombre"], name="uq_material_categoria_nombre"),
        ]
        indexes = [
            models.Index(fields=["nombre"]),
            models.Index(fields=["activo"]),
        ]

    def __str__(self) -> str:
        return self.nombre


class Almacen(models.Model):
    nombre = models.CharField("Nombre", max_length=120, unique=True)
    activo = models.BooleanField("Activo", default=True)

    creado = models.DateTimeField("Creado", auto_now_add=True)
    actualizado = models.DateTimeField("Actualizado", auto_now=True)

    class Meta:
        verbose_name = "Almacén"
        verbose_name_plural = "Almacenes"
        ordering = ["nombre"]

    def __str__(self) -> str:
        return self.nombre


class ItemInventario(models.Model):
    class TipoItem(models.TextChoices):
        MATERIAL = "MATERIAL", "Material"
        PRODUCTO = "PRODUCTO", "Producto terminado"

    almacen = models.ForeignKey(
        Almacen,
        on_delete=models.PROTECT,
        related_name="items",
        verbose_name="Almacén",
    )

    tipo = models.CharField("Tipo", max_length=20, choices=TipoItem.choices)

    # Solo uno de estos debe estar seteado según tipo:
    material = models.ForeignKey(
        Material,
        on_delete=models.PROTECT,
        related_name="items_inventario",
        verbose_name="Material",
        null=True,
        blank=True,
    )
    variante_producto = models.ForeignKey(
        VarianteProducto,
        on_delete=models.PROTECT,
        related_name="items_inventario",
        verbose_name="Variante de producto",
        null=True,
        blank=True,
    )

    punto_reorden = models.DecimalField(
        "Punto de reorden",
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Cantidad mínima para alertas (opcional).",
    )

    activo = models.BooleanField("Activo", default=True)

    creado = models.DateTimeField("Creado", auto_now_add=True)
    actualizado = models.DateTimeField("Actualizado", auto_now=True)

    class Meta:
        verbose_name = "Ítem de inventario"
        verbose_name_plural = "Ítems de inventario"
        ordering = ["tipo", "almacen__nombre"]
        constraints = [
            # Evita duplicados por almacén + material o almacén + variante
            models.UniqueConstraint(
                fields=["almacen", "material"],
                name="uq_iteminventario_almacen_material",
            ),
            models.UniqueConstraint(
                fields=["almacen", "variante_producto"],
                name="uq_iteminventario_almacen_variante",
            ),
        ]

    def __str__(self) -> str:
        if self.tipo == self.TipoItem.MATERIAL and self.material:
            return f"{self.almacen} - Material: {self.material}"
        if self.tipo == self.TipoItem.PRODUCTO and self.variante_producto:
            return f"{self.almacen} - Producto: {self.variante_producto}"
        return f"{self.almacen} - Item ({self.tipo})"

    def clean(self):
        """Validación simple: según el tipo, debe existir material o variante_producto."""
        from django.core.exceptions import ValidationError

        if self.tipo == self.TipoItem.MATERIAL:
            if not self.material or self.variante_producto:
                raise ValidationError("Si el tipo es MATERIAL, debe tener material y NO variante_producto.")
        if self.tipo == self.TipoItem.PRODUCTO:
            if not self.variante_producto or self.material:
                raise ValidationError("Si el tipo es PRODUCTO, debe tener variante_producto y NO material.")


class MovimientoInventario(models.Model):
    class TipoMovimiento(models.TextChoices):
        ENTRADA = "ENTRADA", "Entrada"
        SALIDA = "SALIDA", "Salida"
        AJUSTE = "AJUSTE", "Ajuste"
        TRASLADO = "TRASLADO", "Traslado"

    item = models.ForeignKey(
        ItemInventario,
        on_delete=models.PROTECT,
        related_name="movimientos",
        verbose_name="Ítem",
    )

    tipo = models.CharField("Tipo", max_length=20, choices=TipoMovimiento.choices)
    cantidad = models.DecimalField("Cantidad", max_digits=12, decimal_places=2)

    costo_unitario = models.DecimalField(
        "Costo unitario",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Para ENTRADAS suele ser obligatorio. Para SALIDAS es opcional si calculas COGS aparte.",
    )

    referencia = models.CharField(
        "Referencia",
        max_length=50,
        blank=True,
        null=True,
        help_text="Ej: COMPRA, VENTA, PRODUCCION, AJUSTE",
    )
    referencia_id = models.PositiveIntegerField("ID referencia", blank=True, null=True)

    nota = models.TextField("Nota", blank=True, null=True)

    creado = models.DateTimeField("Creado", auto_now_add=True)

    class Meta:
        verbose_name = "Movimiento de inventario"
        verbose_name_plural = "Movimientos de inventario"
        ordering = ["-creado"]
        indexes = [
            models.Index(fields=["tipo"]),
            models.Index(fields=["referencia", "referencia_id"]),
            models.Index(fields=["creado"]),
        ]

    def __str__(self) -> str:
        return f"{self.tipo} - {self.item} - {self.cantidad}"