from django.db import models


class CategoriaProducto(models.Model):
    nombre = models.CharField("Nombre", max_length=120, unique=True)
    activa = models.BooleanField("Activa", default=True)

    creada = models.DateTimeField("Creada", auto_now_add=True)
    actualizada = models.DateTimeField("Actualizada", auto_now=True)

    class Meta:
        verbose_name = "Categoría de producto"
        verbose_name_plural = "Categorías de productos"
        ordering = ["nombre"]

    def __str__(self) -> str:
        return self.nombre


class Producto(models.Model):
    categoria = models.ForeignKey(
        CategoriaProducto,
        on_delete=models.PROTECT,
        related_name="productos",
        verbose_name="Categoría",
    )

    nombre = models.CharField("Nombre", max_length=150)
    descripcion = models.TextField("Descripción", blank=True, null=True)

    precio_venta_defecto = models.DecimalField(
        "Precio de venta (por defecto)",
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    controla_inventario = models.BooleanField("Controla inventario", default=True)
    activo = models.BooleanField("Activo", default=True)

    creado = models.DateTimeField("Creado", auto_now_add=True)
    actualizado = models.DateTimeField("Actualizado", auto_now=True)

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(fields=["categoria", "nombre"], name="uq_producto_categoria_nombre"),
        ]
        indexes = [
            models.Index(fields=["nombre"]),
            models.Index(fields=["activo"]),
        ]

    def __str__(self) -> str:
        return self.nombre


class VarianteProducto(models.Model):
    class ModoCosto(models.TextChoices):
        FIJO = "FIJO", "Costo fijo"
        FORMULA = "FORMULA", "Por fórmula"

    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name="variantes",
        verbose_name="Producto",
    )

    sku = models.CharField("SKU", max_length=60, unique=True)
    nombre = models.CharField("Nombre de variante", max_length=160)  # Ej: "Talla M", "Niño", etc.

    precio_venta = models.DecimalField(
        "Precio de venta",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Si lo dejas vacío, se usa el precio por defecto del producto.",
    )

    modo_costo = models.CharField(
        "Modo de costo",
        max_length=10,
        choices=ModoCosto.choices,
        default=ModoCosto.FIJO,
    )

    costo_unitario_fijo = models.DecimalField(
        "Costo unitario fijo",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Solo aplica si el modo de costo es 'Costo fijo'.",
    )

    activa = models.BooleanField("Activa", default=True)

    creada = models.DateTimeField("Creada", auto_now_add=True)
    actualizada = models.DateTimeField("Actualizada", auto_now=True)

    class Meta:
        verbose_name = "Variante de producto"
        verbose_name_plural = "Variantes de productos"
        ordering = ["producto__nombre", "nombre"]
        constraints = [
            models.UniqueConstraint(fields=["producto", "nombre"], name="uq_variante_producto_nombre"),
        ]
        indexes = [
            models.Index(fields=["sku"]),
            models.Index(fields=["activa"]),
        ]

    def __str__(self) -> str:
        return f"{self.producto.nombre} - {self.nombre}"

    @property
    def precio_venta_efectivo(self):
        """Precio final: si la variante no tiene precio, usa el del producto."""
        return self.precio_venta if self.precio_venta is not None else self.producto.precio_venta_defecto