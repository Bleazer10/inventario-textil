from django.db import models
from .catalogo import VarianteProducto
from .inventario import Material


class Formula(models.Model):
    """Fórmula de producción (antes 'receta'). Define materiales por unidad."""
    variante_producto = models.ForeignKey(
        VarianteProducto,
        on_delete=models.PROTECT,
        related_name="formulas",
        verbose_name="Variante de producto",
    )

    nombre = models.CharField("Nombre", max_length=150, help_text="Ej: Fórmula Franela básica")
    activa = models.BooleanField("Activa", default=True)

    costo_mano_obra_unitario = models.DecimalField(
        "Costo mano de obra (por unidad)",
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Opcional. Si no aplica, déjalo en 0.",
    )
    costo_indirecto_unitario = models.DecimalField(
        "Costo indirecto (por unidad)",
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Opcional. Ej: electricidad, desgaste, etc.",
    )

    creada = models.DateTimeField("Creada", auto_now_add=True)
    actualizada = models.DateTimeField("Actualizada", auto_now=True)

    class Meta:
        verbose_name = "Fórmula"
        verbose_name_plural = "Fórmulas"
        ordering = ["variante_producto__producto__nombre", "nombre"]
        indexes = [
            models.Index(fields=["activa"]),
        ]

    def __str__(self) -> str:
        return f"{self.variante_producto} - {self.nombre}"


class DetalleFormula(models.Model):
    formula = models.ForeignKey(
        Formula,
        on_delete=models.CASCADE,
        related_name="detalles",
        verbose_name="Fórmula",
    )

    material = models.ForeignKey(
        Material,
        on_delete=models.PROTECT,
        related_name="detalles_formula",
        verbose_name="Material",
    )

    cantidad_por_unidad = models.DecimalField(
        "Cantidad por unidad",
        max_digits=12,
        decimal_places=4,
        help_text="Cuánto material se usa para producir 1 unidad del producto.",
    )

    merma_porcentaje = models.DecimalField(
        "Merma (%)",
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Opcional. Ej: 5.00 significa 5% extra.",
    )

    class Meta:
        verbose_name = "Detalle de fórmula"
        verbose_name_plural = "Detalles de fórmula"
        constraints = [
            models.UniqueConstraint(fields=["formula", "material"], name="uq_detalleformula_formula_material"),
        ]

    def __str__(self) -> str:
        return f"{self.material} ({self.cantidad_por_unidad})"


class LoteProduccion(models.Model):
    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        CONSUMIDO = "CONSUMIDO", "Material consumido"
        FINALIZADO = "FINALIZADO", "Finalizado"
        ANULADO = "ANULADO", "Anulado"

    formula = models.ForeignKey(
        Formula,
        on_delete=models.PROTECT,
        related_name="lotes",
        verbose_name="Fórmula",
    )

    fecha = models.DateField("Fecha")
    cantidad_producida = models.DecimalField("Cantidad producida", max_digits=12, decimal_places=2)

    estado = models.CharField("Estado", max_length=20, choices=Estado.choices, default=Estado.BORRADOR)

    costo_mano_obra_real = models.DecimalField("Costo mano de obra (real)", max_digits=12, decimal_places=2, default=0)
    costo_indirecto_real = models.DecimalField("Costo indirecto (real)", max_digits=12, decimal_places=2, default=0)

    costo_unitario_resultado = models.DecimalField(
        "Costo unitario resultante",
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Se calculará cuando implementemos el servicio de producción.",
    )

    notas = models.TextField("Notas", blank=True, null=True)

    creado = models.DateTimeField("Creado", auto_now_add=True)
    actualizado = models.DateTimeField("Actualizado", auto_now=True)

    class Meta:
        verbose_name = "Lote de producción"
        verbose_name_plural = "Lotes de producción"
        ordering = ["-fecha", "-creado"]
        indexes = [
            models.Index(fields=["fecha"]),
            models.Index(fields=["estado"]),
        ]

    def __str__(self) -> str:
        return f"Lote #{self.id} - {self.formula} - {self.fecha}"