from django.db import models
from .terceros import Cliente
from .catalogo import VarianteProducto


class Venta(models.Model):
    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        CONFIRMADA = "CONFIRMADA", "Confirmada"
        ANULADA = "ANULADA", "Anulada"

    class TipoPago(models.TextChoices):
        CONTADO = "CONTADO", "Contado"
        CREDITO = "CREDITO", "Crédito"

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name="ventas",
        verbose_name="Cliente",
        null=True,
        blank=True,
        help_text="Opcional: si no hay cliente, puede ser venta general.",
    )

    fecha = models.DateField("Fecha")
    estado = models.CharField("Estado", max_length=20, choices=Estado.choices, default=Estado.BORRADOR)

    tipo_pago = models.CharField("Tipo de pago", max_length=20, choices=TipoPago.choices, default=TipoPago.CONTADO)

    total = models.DecimalField("Total", max_digits=12, decimal_places=2, default=0)
    monto_pagado = models.DecimalField("Monto pagado", max_digits=12, decimal_places=2, default=0)
    saldo_pendiente = models.DecimalField("Saldo pendiente", max_digits=12, decimal_places=2, default=0)

    notas = models.TextField("Notas", blank=True, null=True)

    creado = models.DateTimeField("Creado", auto_now_add=True)
    actualizado = models.DateTimeField("Actualizado", auto_now=True)

    class Meta:
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        ordering = ["-fecha", "-creado"]
        indexes = [
            models.Index(fields=["fecha"]),
            models.Index(fields=["estado"]),
            models.Index(fields=["tipo_pago"]),
        ]

    def __str__(self) -> str:
        return f"Venta #{self.id} - {self.fecha}"


class DetalleVenta(models.Model):
    venta = models.ForeignKey(
        Venta,
        on_delete=models.CASCADE,
        related_name="detalles",
        verbose_name="Venta",
    )

    variante_producto = models.ForeignKey(
        VarianteProducto,
        on_delete=models.PROTECT,
        related_name="detalles_venta",
        verbose_name="Variante de producto",
    )

    cantidad = models.DecimalField("Cantidad", max_digits=12, decimal_places=2)
    precio_unitario = models.DecimalField("Precio unitario", max_digits=12, decimal_places=2)

    descuento = models.DecimalField("Descuento", max_digits=12, decimal_places=2, default=0)

    subtotal = models.DecimalField("Subtotal", max_digits=12, decimal_places=2, default=0)

    # Para registrar costo al vender (COGS), lo calcularemos luego.
    costo_unitario_al_vender = models.DecimalField(
        "Costo unitario (al vender)",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Detalle de venta"
        verbose_name_plural = "Detalles de venta"
        indexes = [
            models.Index(fields=["variante_producto"]),
        ]

    def __str__(self) -> str:
        return f"{self.variante_producto} x {self.cantidad}"