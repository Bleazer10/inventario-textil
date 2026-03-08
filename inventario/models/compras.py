from django.db import models
from .terceros import Proveedor
from .inventario import Material


class Compra(models.Model):
    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        RECIBIDA = "RECIBIDA", "Recibida"
        ANULADA = "ANULADA", "Anulada"

    class EstadoPago(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        PARCIAL = "PARCIAL", "Parcial"
        PAGADA = "PAGADA", "Pagada"

    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.PROTECT,
        related_name="compras",
        verbose_name="Proveedor",
    )

    fecha = models.DateField("Fecha")
    estado = models.CharField("Estado", max_length=20, choices=Estado.choices, default=Estado.BORRADOR)

    estado_pago = models.CharField("Estado de pago", max_length=20, choices=EstadoPago.choices, default=EstadoPago.PENDIENTE)

    notas = models.TextField("Notas", blank=True, null=True)

    creado = models.DateTimeField("Creado", auto_now_add=True)
    actualizado = models.DateTimeField("Actualizado", auto_now=True)

    class Meta:
        verbose_name = "Compra"
        verbose_name_plural = "Compras"
        ordering = ["-fecha", "-creado"]
        indexes = [
            models.Index(fields=["fecha"]),
            models.Index(fields=["estado"]),
            models.Index(fields=["estado_pago"]),
        ]

    def __str__(self) -> str:
        return f"Compra #{self.id} - {self.proveedor.nombre} - {self.fecha}"


class DetalleCompra(models.Model):
    compra = models.ForeignKey(
        Compra,
        on_delete=models.CASCADE,
        related_name="detalles",
        verbose_name="Compra",
    )

    material = models.ForeignKey(
        Material,
        on_delete=models.PROTECT,
        related_name="detalles_compra",
        verbose_name="Material",
    )

    cantidad = models.DecimalField("Cantidad", max_digits=12, decimal_places=2)
    costo_unitario = models.DecimalField("Costo unitario", max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = "Detalle de compra"
        verbose_name_plural = "Detalles de compra"

    def __str__(self) -> str:
        return f"{self.material} x {self.cantidad}"