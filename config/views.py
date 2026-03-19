from datetime import date
from decimal import Decimal
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from inventario.models import (
    Venta, Gasto, CuentaPorCobrar, CuentaPorPagarCompra, CuentaPorPagarGasto
)

@login_required
def dashboard(request):
    hoy = date.today()

    ventas_hoy = (
        Venta.objects
        .filter(fecha=hoy, estado=Venta.Estado.CONFIRMADA)
        .aggregate(v=Coalesce(Sum("total"), Decimal("0.00")))["v"]
    )

    gastos_hoy = (
        Gasto.objects
        .filter(fecha=hoy)
        .aggregate(g=Coalesce(Sum("monto"), Decimal("0.00")))["g"]
    )

    por_cobrar = (
        CuentaPorCobrar.objects
        .filter(estado=CuentaPorCobrar.Estado.ABIERTA)
        .aggregate(s=Coalesce(Sum("saldo"), Decimal("0.00")))["s"]
    )

    por_pagar = (
        CuentaPorPagarCompra.objects
        .filter(estado=CuentaPorPagarCompra.Estado.ABIERTA)
        .aggregate(s=Coalesce(Sum("saldo"), Decimal("0.00")))["s"]
        +
        CuentaPorPagarGasto.objects
        .filter(estado=CuentaPorPagarGasto.Estado.ABIERTA)
        .aggregate(s=Coalesce(Sum("saldo"), Decimal("0.00")))["s"]
    )

    return render(request, "dashboard.html", {
        "ventas_hoy": ventas_hoy,
        "gastos_hoy": gastos_hoy,
        "por_cobrar": por_cobrar,
        "por_pagar": por_pagar,
    })