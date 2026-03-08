from django.db import models
from django.core.exceptions import ValidationError

from .terceros import Cliente, Proveedor
from .ventas import Venta
from .compras import Compra


class CategoriaGasto(models.Model):
    nombre = models.CharField("Nombre", max_length=120, unique=True)
    activa = models.BooleanField("Activa", default=True)

    creada = models.DateTimeField("Creada", auto_now_add=True)
    actualizada = models.DateTimeField("Actualizada", auto_now=True)

    class Meta:
        verbose_name = "Categoría de gasto"
        verbose_name_plural = "Categorías de gastos"
        ordering = ["nombre"]

    def __str__(self) -> str:
        return self.nombre


class Gasto(models.Model):
    class EstadoPago(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        PARCIAL = "PARCIAL", "Parcial"
        PAGADO = "PAGADO", "Pagado"

    categoria = models.ForeignKey(
        CategoriaGasto,
        on_delete=models.PROTECT,
        related_name="gastos",
        verbose_name="Categoría",
    )

    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.PROTECT,
        related_name="gastos",
        verbose_name="Proveedor",
        null=True,
        blank=True,
    )

    fecha = models.DateField("Fecha")
    monto = models.DecimalField("Monto", max_digits=12, decimal_places=2)

    estado_pago = models.CharField(
        "Estado de pago",
        max_length=20,
        choices=EstadoPago.choices,
        default=EstadoPago.PENDIENTE,
    )

    descripcion = models.TextField("Descripción", blank=True, null=True)

    creado = models.DateTimeField("Creado", auto_now_add=True)
    actualizado = models.DateTimeField("Actualizado", auto_now=True)

    class Meta:
        verbose_name = "Gasto"
        verbose_name_plural = "Gastos"
        ordering = ["-fecha", "-creado"]
        indexes = [
            models.Index(fields=["fecha"]),
            models.Index(fields=["estado_pago"]),
        ]

    def __str__(self) -> str:
        return f"Gasto #{self.id} - {self.fecha} - {self.monto}"


class CuentaPorCobrar(models.Model):
    class Estado(models.TextChoices):
        ABIERTA = "ABIERTA", "Abierta"
        CERRADA = "CERRADA", "Cerrada"
        VENCIDA = "VENCIDA", "Vencida"

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name="cuentas_por_cobrar",
        verbose_name="Cliente",
        null=True,
        blank=True,
    )

    venta = models.OneToOneField(
        Venta,
        on_delete=models.PROTECT,
        related_name="cuenta_por_cobrar",
        verbose_name="Venta",
        null=True,
        blank=True,
    )

    monto_total = models.DecimalField("Monto total", max_digits=12, decimal_places=2)
    monto_pagado = models.DecimalField("Monto pagado", max_digits=12, decimal_places=2, default=0)
    saldo = models.DecimalField("Saldo", max_digits=12, decimal_places=2)

    fecha_vencimiento = models.DateField("Fecha vencimiento", null=True, blank=True)
    estado = models.CharField("Estado", max_length=20, choices=Estado.choices, default=Estado.ABIERTA)

    notas = models.TextField("Notas", blank=True, null=True)

    creada = models.DateTimeField("Creada", auto_now_add=True)
    actualizada = models.DateTimeField("Actualizada", auto_now=True)

    class Meta:
        verbose_name = "Cuenta por cobrar"
        verbose_name_plural = "Cuentas por cobrar"
        ordering = ["-creada"]
        indexes = [
            models.Index(fields=["estado"]),
            models.Index(fields=["fecha_vencimiento"]),
        ]

    def __str__(self) -> str:
        return f"CxC #{self.id} - Saldo: {self.saldo}"


# =========================
# OPCIÓN B: DOS TABLAS POR PAGAR
# =========================
class CuentaPorPagarCompra(models.Model):
    class Estado(models.TextChoices):
        ABIERTA = "ABIERTA", "Abierta"
        CERRADA = "CERRADA", "Cerrada"
        VENCIDA = "VENCIDA", "Vencida"

    compra = models.OneToOneField(
        Compra,
        on_delete=models.PROTECT,
        related_name="cuenta_por_pagar",
        verbose_name="Compra",
    )

    # Opcional (pero útil para listar rápido). Lo puedes autollenar luego desde la compra.
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.PROTECT,
        related_name="cuentas_por_pagar_compra",
        verbose_name="Proveedor",
        null=True,
        blank=True,
    )

    monto_total = models.DecimalField("Monto total", max_digits=12, decimal_places=2)
    monto_pagado = models.DecimalField("Monto pagado", max_digits=12, decimal_places=2, default=0)
    saldo = models.DecimalField("Saldo", max_digits=12, decimal_places=2)

    fecha_vencimiento = models.DateField("Fecha vencimiento", null=True, blank=True)
    estado = models.CharField("Estado", max_length=20, choices=Estado.choices, default=Estado.ABIERTA)

    notas = models.TextField("Notas", blank=True, null=True)

    creada = models.DateTimeField("Creada", auto_now_add=True)
    actualizada = models.DateTimeField("Actualizada", auto_now=True)

    class Meta:
        verbose_name = "Cuenta por pagar (Compra)"
        verbose_name_plural = "Cuentas por pagar (Compras)"
        ordering = ["-creada"]
        indexes = [
            models.Index(fields=["estado"]),
            models.Index(fields=["fecha_vencimiento"]),
        ]

    def __str__(self) -> str:
        return f"CxP Compra #{self.id} - Saldo: {self.saldo}"

    def clean(self):
        # Si quieres obligar proveedor cuando hay compra, lo activas.
        # if self.proveedor is None:
        #     raise ValidationError("Proveedor es requerido para cuentas por pagar de compras.")
        pass


class CuentaPorPagarGasto(models.Model):
    class Estado(models.TextChoices):
        ABIERTA = "ABIERTA", "Abierta"
        CERRADA = "CERRADA", "Cerrada"
        VENCIDA = "VENCIDA", "Vencida"

    gasto = models.OneToOneField(
        Gasto,
        on_delete=models.PROTECT,
        related_name="cuenta_por_pagar",
        verbose_name="Gasto",
    )

    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.PROTECT,
        related_name="cuentas_por_pagar_gasto",
        verbose_name="Proveedor",
        null=True,
        blank=True,
        help_text="Opcional: si el gasto no tiene proveedor, puedes dejarlo vacío.",
    )

    monto_total = models.DecimalField("Monto total", max_digits=12, decimal_places=2)
    monto_pagado = models.DecimalField("Monto pagado", max_digits=12, decimal_places=2, default=0)
    saldo = models.DecimalField("Saldo", max_digits=12, decimal_places=2)

    fecha_vencimiento = models.DateField("Fecha vencimiento", null=True, blank=True)
    estado = models.CharField("Estado", max_length=20, choices=Estado.choices, default=Estado.ABIERTA)

    notas = models.TextField("Notas", blank=True, null=True)

    creada = models.DateTimeField("Creada", auto_now_add=True)
    actualizada = models.DateTimeField("Actualizada", auto_now=True)

    class Meta:
        verbose_name = "Cuenta por pagar (Gasto)"
        verbose_name_plural = "Cuentas por pagar (Gastos)"
        ordering = ["-creada"]
        indexes = [
            models.Index(fields=["estado"]),
            models.Index(fields=["fecha_vencimiento"]),
        ]

    def __str__(self) -> str:
        return f"CxP Gasto #{self.id} - Saldo: {self.saldo}"


class Pago(models.Model):
    class Direccion(models.TextChoices):
        ENTRADA = "ENTRADA", "Entrada (cobro)"
        SALIDA = "SALIDA", "Salida (pago)"

    direccion = models.CharField("Dirección", max_length=20, choices=Direccion.choices)
    metodo = models.CharField("Método", max_length=50, blank=True, null=True, help_text="Efectivo, transferencia, etc.")
    fecha = models.DateField("Fecha")
    monto = models.DecimalField("Monto", max_digits=12, decimal_places=2)

    # Cobros
    cuenta_por_cobrar = models.ForeignKey(
        CuentaPorCobrar,
        on_delete=models.PROTECT,
        related_name="pagos",
        verbose_name="Cuenta por cobrar",
        null=True,
        blank=True,
    )

    # Pagos de compras
    cuenta_por_pagar_compra = models.ForeignKey(
        CuentaPorPagarCompra,
        on_delete=models.PROTECT,
        related_name="pagos",
        verbose_name="Cuenta por pagar (Compra)",
        null=True,
        blank=True,
    )

    # Pagos de gastos
    cuenta_por_pagar_gasto = models.ForeignKey(
        CuentaPorPagarGasto,
        on_delete=models.PROTECT,
        related_name="pagos",
        verbose_name="Cuenta por pagar (Gasto)",
        null=True,
        blank=True,
    )

    nota = models.TextField("Nota", blank=True, null=True)

    creado = models.DateTimeField("Creado", auto_now_add=True)

    class Meta:
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"
        ordering = ["-fecha", "-creado"]
        indexes = [
            models.Index(fields=["fecha"]),
            models.Index(fields=["direccion"]),
        ]

    def __str__(self) -> str:
        return f"{self.direccion} - {self.monto} - {self.fecha}"

    def clean(self):
        """
        Regla:
        - Un Pago debe apuntar a EXACTAMENTE UNA cuenta:
            * cuenta_por_cobrar  (si es ENTRADA)
            * cuenta_por_pagar_compra (si es SALIDA)
            * cuenta_por_pagar_gasto  (si es SALIDA)
        """
        refs = [
            self.cuenta_por_cobrar_id is not None,
            self.cuenta_por_pagar_compra_id is not None,
            self.cuenta_por_pagar_gasto_id is not None,
        ]
        if sum(refs) != 1:
            raise ValidationError("El pago debe vincularse a una sola cuenta (por cobrar o por pagar).")

        if self.direccion == self.Direccion.ENTRADA and self.cuenta_por_cobrar_id is None:
            raise ValidationError("Si la dirección es ENTRADA, debes seleccionar una Cuenta por cobrar.")

        if self.direccion == self.Direccion.SALIDA and self.cuenta_por_cobrar_id is not None:
            raise ValidationError("Si la dirección es SALIDA, no debe tener Cuenta por cobrar.")