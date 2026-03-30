from datetime import date, timedelta
from decimal import Decimal
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from inventario.models import (
    Venta, Gasto, CuentaPorCobrar, CuentaPorPagarCompra, CuentaPorPagarGasto, Pago
)

@login_required
def dashboard(request):
    hoy = date.today()

    # Ventas hoy (confirmadas)
    ventas_hoy = (
        Venta.objects
        .filter(fecha=hoy, estado=Venta.Estado.CONFIRMADA)
        .aggregate(s=Coalesce(Sum("total"), Decimal("0.00")))["s"]
    ).quantize(Decimal("0.01"))

    # Gastos hoy
    gastos_hoy = (
        Gasto.objects
        .filter(fecha=hoy)
        .aggregate(s=Coalesce(Sum("monto"), Decimal("0.00")))["s"]
    ).quantize(Decimal("0.01"))

    # Por cobrar (saldo abierto)
    por_cobrar = (
        CuentaPorCobrar.objects
        .filter(estado=CuentaPorCobrar.Estado.ABIERTA)
        .aggregate(s=Coalesce(Sum("saldo"), Decimal("0.00")))["s"]
    ).quantize(Decimal("0.01"))

    # Por pagar (saldo abierto compras + gastos)
    por_pagar_compras = (
        CuentaPorPagarCompra.objects
        .filter(estado=CuentaPorPagarCompra.Estado.ABIERTA)
        .aggregate(s=Coalesce(Sum("saldo"), Decimal("0.00")))["s"]
    ).quantize(Decimal("0.01"))

    por_pagar_gastos = (
        CuentaPorPagarGasto.objects
        .filter(estado=CuentaPorPagarGasto.Estado.ABIERTA)
        .aggregate(s=Coalesce(Sum("saldo"), Decimal("0.00")))["s"]
    ).quantize(Decimal("0.01"))

    por_pagar = (por_pagar_compras + por_pagar_gastos).quantize(Decimal("0.01"))

    # Movimientos recientes (últimos 7 días)
    fi = hoy - timedelta(days=7)

    ultimas_ventas = (
        Venta.objects
        .filter(fecha__gte=fi, fecha__lte=hoy, estado=Venta.Estado.CONFIRMADA)
        .select_related("cliente")
        .order_by("-fecha", "-id")[:5]
    )

    ultimos_gastos = (
        Gasto.objects
        .filter(fecha__gte=fi, fecha__lte=hoy)
        .select_related("categoria", "proveedor")
        .order_by("-fecha", "-id")[:5]
    )

    ultimos_pagos = (
        Pago.objects
        .filter(fecha__gte=fi, fecha__lte=hoy)
        .order_by("-fecha", "-id")[:5]
    )

    return render(request, "dashboard.html", {
        "ventas_hoy": ventas_hoy,
        "gastos_hoy": gastos_hoy,
        "por_cobrar": por_cobrar,
        "por_pagar": por_pagar,

        "ultimas_ventas": ultimas_ventas,
        "ultimos_gastos": ultimos_gastos,
        "ultimos_pagos": ultimos_pagos,
    })