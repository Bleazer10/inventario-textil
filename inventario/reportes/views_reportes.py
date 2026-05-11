from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from inventario.reportes.utils_pdf import pdf_tabla
from inventario.reportes.utils_excel import excel_reporte
from inventario.models import Venta, DetalleVenta
from datetime import datetime
from decimal import Decimal
from django.db.models import Q, Sum, Min, Max
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from reportlab.lib.units import mm
from django.utils import timezone

def _parse_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except:
        return None


def _build_periodo_text(fi, ff, qs):
    if fi or ff:
        desde = _fmt_fecha(fi) if fi else ""
        hasta = _fmt_fecha(ff) if ff else ""
        if desde and hasta:
            return f"Periodo: desde {desde} al {hasta}"
        if desde:
            return f"Periodo: desde {desde}"
        if hasta:
            return f"Periodo: hasta {hasta}"
        return None

    agregados = qs.aggregate(
        min_fecha=Min("fecha"),
        max_fecha=Max("fecha"),
    )
    min_fecha = agregados["min_fecha"]
    max_fecha = agregados["max_fecha"]
    if min_fecha and max_fecha:
        return f"Periodo: desde {_fmt_fecha(min_fecha)} al {_fmt_fecha(max_fecha)}"
    if min_fecha:
        return f"Periodo: desde {_fmt_fecha(min_fecha)}"
    if max_fecha:
        return f"Periodo: hasta {_fmt_fecha(max_fecha)}"
    return None


@login_required
def reporte_ventas(request):
    fi = _parse_date(request.GET.get("fi", ""))
    ff = _parse_date(request.GET.get("ff", ""))
    q = (request.GET.get("q", "") or "").strip()

    qs = Venta.objects.select_related("cliente").all()

    if fi:
        qs = qs.filter(fecha__gte=fi)
    if ff:
        qs = qs.filter(fecha__lte=ff)
    if q:
        qs = qs.filter(Q(cliente__nombre__icontains=q) | Q(id__icontains=q))

    qs = qs.order_by("-fecha", "-id")

    # ✅ Resumen (para mostrar en pantalla)
    agg = qs.aggregate(
        total=Coalesce(Sum("total"), Decimal("0.00")),
        pagado=Coalesce(Sum("monto_pagado"), Decimal("0.00")),
        saldo=Coalesce(Sum("saldo_pendiente"), Decimal("0.00")),
    )

    resumen = {
        "cantidad": qs.count(),
        "total": agg["total"].quantize(Decimal("0.01")),
        "pagado": agg["pagado"].quantize(Decimal("0.01")),
        "saldo": agg["saldo"].quantize(Decimal("0.01")),
    }

    limite_vista = 500
    ventas = qs[:limite_vista]

    return render(request, "reportes/ventas.html", {
        "ventas": ventas,
        "resumen": resumen,
        "limite_vista": limite_vista,

        # filtros para inputs y export links
        "fi": fi.strftime("%Y-%m-%d") if fi else "",
        "ff": ff.strftime("%Y-%m-%d") if ff else "",
        "q": q,
    })


@login_required
def reporte_ventas_excel(request):
    fi = _parse_date(request.GET.get("fi", ""))
    ff = _parse_date(request.GET.get("ff", ""))
    q = (request.GET.get("q", "") or "").strip()

    qs = Venta.objects.select_related("cliente").all()

    if fi:
        qs = qs.filter(fecha__gte=fi)
    if ff:
        qs = qs.filter(fecha__lte=ff)
    if q:
        qs = qs.filter(Q(cliente__nombre__icontains=q) | Q(id__icontains=q))

    qs = qs.order_by("-fecha", "-id")[:20000]

    # ✅ Resumen (igual que PDF)
    agg = qs.aggregate(
        total=Coalesce(Sum("total"), Decimal("0.00")),
        pagado=Coalesce(Sum("monto_pagado"), Decimal("0.00")),
        saldo=Coalesce(Sum("saldo_pendiente"), Decimal("0.00")),
    )

    resumen = [
        ["Cantidad de ventas", str(qs.count())],
        ["Total vendido", f"${agg['total'].quantize(Decimal('0.01'))}"],
        ["Total pagado", f"${agg['pagado'].quantize(Decimal('0.01'))}"],
        ["Saldo pendiente", f"${agg['saldo'].quantize(Decimal('0.01'))}"],
    ]

    periodo = _build_periodo_text(fi, ff, qs)
    fecha_emision = timezone.localdate()
    filtros = []
    if periodo:
        filtros.append(periodo)
    filtros.append(f"Fecha de emisión: {_fmt_fecha(fecha_emision)}")

    columnas = ["#Venta", "Fecha", "Cliente", "Tipo pago", "Total", "Pagado", "Saldo", "Estado"]

    filas = []
    for v in qs:
        filas.append([
            v.id,
            str(v.fecha),
            v.cliente.nombre if v.cliente else "General",
            v.get_tipo_pago_display(),
            float(v.total),
            float(v.monto_pagado),
            float(v.saldo_pendiente),
            v.get_estado_display(),
        ])

    # columnas de dinero: Total, Pagado, Saldo => indices 4,5,6 (0-based)
    return excel_reporte(
        nombre_archivo="reporte_ventas",
        hoja="Ventas",
        titulo="Reporte de Ventas",
        columnas=columnas,
        filas=filas,
        filtros=filtros,
        resumen=resumen,
        logo_relpath="img/logo-bemore.jpeg",
        nombre_empresa="BEMORE",
        formato_moneda_cols=[4, 5, 6],
    )

@login_required
def reporte_ventas_pdf(request):
    fi = _parse_date(request.GET.get("fi", ""))
    ff = _parse_date(request.GET.get("ff", ""))
    q = (request.GET.get("q", "") or "").strip()

    qs = Venta.objects.select_related("cliente").all()

    if fi:
        qs = qs.filter(fecha__gte=fi)
    if ff:
        qs = qs.filter(fecha__lte=ff)
    if q:
        qs = qs.filter(Q(cliente__nombre__icontains=q) | Q(id__icontains=q))

    qs = qs.order_by("-fecha", "-id")

    total_ventas = qs.aggregate(s=Coalesce(Sum("total"), Decimal("0.00")))["s"]
    cant = qs.count()

    resumen = [
        ["Cantidad de ventas", str(cant)],
        ["Total vendido", f"${total_ventas.quantize(Decimal('0.01'))}"],
    ]

    periodo = _build_periodo_text(fi, ff, qs)
    fecha_emision = timezone.localdate()
    filtros = []
    if periodo:
        filtros.append(periodo)
    filtros.append(f"Fecha de emisión: {_fmt_fecha(fecha_emision)}")

    columnas = ["#Venta", "Fecha", "Cliente", "Tipo pago", "Total", "Pagado", "Saldo", "Estado"]
    filas = []

    for v in qs[:5000]:
        filas.append([
            v.id,
            str(v.fecha),
            v.cliente.nombre if v.cliente else "General",
            v.get_tipo_pago_display(),
            f"${v.total}",
            f"${v.monto_pagado}",
            f"${v.saldo_pendiente}",
            v.get_estado_display(),
        ])

    subt = None

    return pdf_tabla(
        "reporte_ventas",
        "Reporte de Ventas",
        subt,
        columnas,
        filas,
        resumen=resumen,
        filtros=filtros,
        titulo_datos=None,
        repeat_header=True,
        logo_relpath="img/logo-bemore.jpeg",
        nombre_empresa="BEMORE",
    )

def _fmt_fecha(d):
    return d.strftime("%d/%m/%Y") if d else ""


@login_required
def reporte_venta_factura_pdf(request, venta_id):
    venta = get_object_or_404(
        Venta.objects.select_related("cliente"),
        id=venta_id
    )

    detalles = (
        DetalleVenta.objects
        .filter(venta=venta)
        .select_related("variante_producto", "variante_producto__producto")
        .order_by("id")
    )

    fecha_emision = timezone.localdate()

    # ✅ Cabecera de factura en 3 filas x 2 columnas, cada celda con etiqueta + valor
    cliente_nombre = venta.cliente.nombre if venta.cliente else "General"
    filtros = [
        [("#Venta", str(venta.id)), ("Fecha", _fmt_fecha(venta.fecha))],
        [("Tipo de pago", venta.get_tipo_pago_display()), ("Estado", venta.get_estado_display())],
        [("Cliente", cliente_nombre), ("Emisión Factura", _fmt_fecha(fecha_emision))],
    ]

    # ✅ Resumen en un solo cuadro vertical (una columna, tres filas)
    resumen = [
        [f"Total: ${float(venta.total):.2f}\nPagado: ${float(venta.monto_pagado):.2f}\nSaldo: ${float(venta.saldo_pendiente):.2f}"],
    ]

    # ✅ Tabla detalle (agrandamos Producto para que no se corte)
    columnas = ["SKU", "Producto", "Variante", "Cant.", "Precio", "Desc.", "Subtotal"]
    filas = []

    for d in detalles:
        vp = d.variante_producto
        filas.append([
            vp.sku,
            vp.producto.nombre,
            vp.nombre,
            float(d.cantidad),
            f"${float(d.precio_unitario):.2f}",
            f"${float(d.descuento):.2f}",
            f"${float(d.subtotal):.2f}",
        ])

    # Anchos personalizados (Producto más ancho)
    col_widths = [
        22 * mm,  # SKU
        60 * mm,  # Producto  ✅ más ancho
        35 * mm,  # Variante
        16 * mm,  # Cant
        20 * mm,  # Precio
        20 * mm,  # Desc
        23 * mm,  # Subtotal
    ]

    return pdf_tabla(
        nombre_archivo=f"factura_venta_{venta.id}",
        titulo="Factura / Detalle de Venta",
        subtitulo=None,
        columnas=columnas,
        filas=filas,
        filtros=filtros,
        resumen=resumen,

        # ✅ Cambios para el diseño (sin repetición de página)
        titulo_datos=None,              # quita “Filtros aplicados”
        resumen_en_una_linea=True,      # resumen en una sola celda
        col_widths=col_widths,          # producto más ancho
        repeat_header=False,

        logo_relpath="img/logo-bemore.jpeg",
        nombre_empresa="BEMORE",
    )

@login_required
def reporte_venta_factura_excel(request, venta_id):
    venta = get_object_or_404(
        Venta.objects.select_related("cliente"),
        id=venta_id
    )

    detalles = (
        DetalleVenta.objects
        .filter(venta=venta)
        .select_related("variante_producto", "variante_producto__producto")
        .order_by("id")
    )

    filtros = [
        ["# Venta", str(venta.id)],
        ["Fecha", str(venta.fecha)],
        ["Cliente", venta.cliente.nombre if venta.cliente else "General"],
        ["Tipo de pago", venta.get_tipo_pago_display()],
        ["Estado", venta.get_estado_display()],
    ]

    resumen = [
        ["Total", f"${venta.total:.2f}"],
        ["Pagado", f"${venta.monto_pagado:.2f}"],
        ["Saldo pendiente", f"${venta.saldo_pendiente:.2f}"],
    ]

    columnas = ["SKU", "Producto", "Variante", "Cantidad", "Precio unit.", "Descuento", "Subtotal"]
    filas = []
    for d in detalles:
        vp = d.variante_producto
        filas.append([
            vp.sku,
            vp.producto.nombre,
            vp.nombre,
            float(d.cantidad),
            float(d.precio_unitario),
            float(d.descuento),
            float(d.subtotal),
        ])

    # dinero: precio unit, descuento, subtotal -> indices 4,5,6
    return excel_reporte(
        nombre_archivo=f"factura_venta_{venta.id}",
        hoja="Factura",
        titulo=f"Factura Venta #{venta.id}",
        columnas=columnas,
        filas=filas,
        filtros=filtros,
        resumen=resumen,
        logo_relpath="img/logo-bemore.jpeg",
        nombre_empresa="BEMORE",
        formato_moneda_cols=[4, 5, 6],
    )