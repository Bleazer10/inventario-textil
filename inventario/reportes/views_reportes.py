from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from inventario.reportes.utils_pdf import pdf_tabla
from inventario.reportes.utils_excel import excel_reporte
from inventario.models import Venta, DetalleVenta, Compra, DetalleCompra, ItemInventario
from datetime import datetime
from decimal import Decimal
from django.db.models import Q, Sum, Min, Max, ExpressionWrapper, F, DecimalField, Case, When, Value
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

@login_required
def reporte_compras(request):
    fi = _parse_date(request.GET.get("fi", ""))
    ff = _parse_date(request.GET.get("ff", ""))
    q = (request.GET.get("q", "") or "").strip()
    estado = (request.GET.get("estado", "") or "").strip()
    estado_pago = (request.GET.get("estado_pago", "") or "").strip()

    qs = Compra.objects.select_related("proveedor").all()

    if fi:
        qs = qs.filter(fecha__gte=fi)
    if ff:
        qs = qs.filter(fecha__lte=ff)
    if estado:
        qs = qs.filter(estado=estado)
    if estado_pago:
        qs = qs.filter(estado_pago=estado_pago)
    if q:
        qs = qs.filter(Q(proveedor__nombre__icontains=q) | Q(id__icontains=q))

    qs = qs.order_by("-fecha", "-id")

    # Total por compra = suma(detalle.cantidad * detalle.costo_unitario)
    total_expr = ExpressionWrapper(
        F("detalles__cantidad") * F("detalles__costo_unitario"),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )

    agg = qs.aggregate(
        total=Coalesce(Sum(total_expr), Decimal("0.00")),
    )

    resumen = {
        "cantidad": qs.count(),
        "total": agg["total"].quantize(Decimal("0.01")),
    }

    limite_vista = 500
    compras = qs[:limite_vista]

    return render(request, "reportes/compras.html", {
        "compras": compras,
        "resumen": resumen,
        "limite_vista": limite_vista,

        "fi": fi.strftime("%Y-%m-%d") if fi else "",
        "ff": ff.strftime("%Y-%m-%d") if ff else "",
        "q": q,
        "estado": estado,
        "estado_pago": estado_pago,

        "estado_choices": Compra.Estado.choices,
        "estado_pago_choices": Compra.EstadoPago.choices,
    })


@login_required
def reporte_compras_pdf(request):
    fi = _parse_date(request.GET.get("fi", ""))
    ff = _parse_date(request.GET.get("ff", ""))
    q = (request.GET.get("q", "") or "").strip()
    estado = (request.GET.get("estado", "") or "").strip()
    estado_pago = (request.GET.get("estado_pago", "") or "").strip()

    qs = Compra.objects.select_related("proveedor").all()

    if fi:
        qs = qs.filter(fecha__gte=fi)
    if ff:
        qs = qs.filter(fecha__lte=ff)
    if estado:
        qs = qs.filter(estado=estado)
    if estado_pago:
        qs = qs.filter(estado_pago=estado_pago)
    if q:
        qs = qs.filter(Q(proveedor__nombre__icontains=q) | Q(id__icontains=q))

    qs = qs.order_by("-fecha", "-id")

    total_expr = ExpressionWrapper(
        F("detalles__cantidad") * F("detalles__costo_unitario"),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )

    total_compras = qs.aggregate(s=Coalesce(Sum(total_expr), Decimal("0.00")))["s"]
    cant = qs.count()

    resumen = [
        ["Cantidad de compras", str(cant)],
        ["Total comprado", f"${total_compras.quantize(Decimal('0.01'))}"],
    ]

    periodo = _build_periodo_text(fi, ff, qs)
    fecha_emision = timezone.localdate()

    filtros = []
    if periodo:
        filtros.append(periodo)
    filtros.append(f"Fecha de emisión: {_fmt_fecha(fecha_emision)}")

    columnas = ["#Compra", "Fecha", "Proveedor", "Estado", "Estado pago", "Total"]

    # Para calcular total por compra sin hacer 1 query por fila:
    # anotamos total_compra
    qs = qs.annotate(
        total_compra=Coalesce(Sum(total_expr), Decimal("0.00"))
    )

    filas = []
    for c in qs[:5000]:
        filas.append([
            c.id,
            str(c.fecha),
            c.proveedor.nombre,
            c.get_estado_display(),
            c.get_estado_pago_display(),
            f"${c.total_compra}",
        ])

    col_widths = [
    18*mm,  # #Compra
    22*mm,  # Fecha
    55*mm,  # Proveedor  ✅ más ancho
    26*mm,  # Estado
    28*mm,  # Estado pago
    22*mm,  # Total
]

    return pdf_tabla(
        "reporte_compras",
        "Reporte de Compras",
        None,
        columnas,
        filas,
        resumen=resumen,
        filtros=filtros,
        titulo_datos=None,
        repeat_header=True,                 # ✅ multi-página: repite solo líneas arriba
        col_widths=col_widths,              # proveedor más ancho
        logo_relpath="img/logo-bemore.jpeg",
        nombre_empresa="BEMORE",
    )


@login_required
def reporte_compras_excel(request):
    fi = _parse_date(request.GET.get("fi", ""))
    ff = _parse_date(request.GET.get("ff", ""))
    q = (request.GET.get("q", "") or "").strip()
    estado = (request.GET.get("estado", "") or "").strip()
    estado_pago = (request.GET.get("estado_pago", "") or "").strip()

    qs = Compra.objects.select_related("proveedor").all()

    if fi:
        qs = qs.filter(fecha__gte=fi)
    if ff:
        qs = qs.filter(fecha__lte=ff)
    if estado:
        qs = qs.filter(estado=estado)
    if estado_pago:
        qs = qs.filter(estado_pago=estado_pago)
    if q:
        qs = qs.filter(Q(proveedor__nombre__icontains=q) | Q(id__icontains=q))

    qs = qs.order_by("-fecha", "-id")[:20000]

    total_expr = ExpressionWrapper(
        F("detalles__cantidad") * F("detalles__costo_unitario"),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )

    total_compras = qs.aggregate(s=Coalesce(Sum(total_expr), Decimal("0.00")))["s"]

    resumen = [
        ["Cantidad de compras", str(qs.count())],
        ["Total comprado", f"${total_compras.quantize(Decimal('0.01'))}"],
    ]

    periodo = _build_periodo_text(fi, ff, qs)
    fecha_emision = timezone.localdate()
    filtros = []
    if periodo:
        filtros.append(periodo)
    filtros.append(f"Fecha de emisión: {_fmt_fecha(fecha_emision)}")

    columnas = ["#Compra", "Fecha", "Proveedor", "Estado", "Estado pago", "Total"]

    qs = qs.annotate(
        total_compra=Coalesce(Sum(total_expr), Decimal("0.00"))
    )

    filas = []
    for c in qs:
        filas.append([
            c.id,
            str(c.fecha),
            c.proveedor.nombre,
            c.get_estado_display(),
            c.get_estado_pago_display(),
            float(c.total_compra),
        ])

    return excel_reporte(
        nombre_archivo="reporte_compras",
        hoja="Compras",
        titulo="Reporte de Compras",
        columnas=columnas,
        filas=filas,
        filtros=filtros,
        resumen=resumen,
        logo_relpath="img/logo-bemore.jpeg",
        nombre_empresa="BEMORE",
        formato_moneda_cols=[5],   # Total (col index 5)
    )

def _fmt_fecha(d):
    return d.strftime("%d/%m/%Y") if d else ""

@login_required
def reporte_compra_factura_pdf(request, compra_id):
    compra = get_object_or_404(
        Compra.objects.select_related("proveedor"),
        id=compra_id
    )

    detalles = (
        DetalleCompra.objects
        .filter(compra=compra)
        .select_related("material", "material__categoria")
        .order_by("id")
    )

    fecha_emision = timezone.localdate()

    # ✅ Datos de cabecera (2 columnas / 3 filas), sin “Filtros aplicados”
    filtros = [
        [f"#Compra: {compra.id}", f"Fecha: {_fmt_fecha(compra.fecha)}"],
        [f"Estado: {compra.get_estado_display()}", f"Estado pago: {compra.get_estado_pago_display()}"],
        [f"Proveedor: {compra.proveedor.nombre}", f"Emisión: {_fmt_fecha(fecha_emision)}"],
    ]

    # Totales
    total = 0.0
    filas = []
    for d in detalles:
        subtotal = float(d.cantidad) * float(d.costo_unitario)
        total += subtotal
        filas.append([
            d.material.nombre,
            d.material.unidad,
            float(d.cantidad),
            f"${float(d.costo_unitario):.2f}",
            f"${subtotal:.2f}",
        ])

    # ✅ Resumen en una sola caja (una fila)
    resumen = [[f"Total: ${total:.2f}"]]

    columnas = ["Material", "Unidad", "Cant.", "Costo unit.", "Subtotal"]

    # ✅ Anchos para que “Proveedor”/Material no se corte
    col_widths = [
        55 * mm,  # Material (más ancho)
        22 * mm,  # Unidad
        18 * mm,  # Cant
        28 * mm,  # Costo unit
        27 * mm,  # Subtotal
    ]

    return pdf_tabla(
        nombre_archivo=f"factura_compra_{compra.id}",
        titulo="Factura / Detalle de Compra",
        subtitulo=None,
        columnas=columnas,
        filas=filas,
        filtros=filtros,
        resumen=resumen,

        titulo_datos=None,          # ✅ no mostrar “Filtros aplicados”
        resumen_en_una_linea=True,  # ✅ caja única
        col_widths=col_widths,
        repeat_header=False,        # factura normalmente 1 página

        logo_relpath="img/logo-bemore.jpeg",
        nombre_empresa="BEMORE",
    )

@login_required
def reporte_compra_factura_excel(request, compra_id):
    compra = get_object_or_404(
        Compra.objects.select_related("proveedor"),
        id=compra_id
    )

    detalles = (
        DetalleCompra.objects
        .filter(compra=compra)
        .select_related("material", "material__categoria")
        .order_by("id")
    )

    fecha_emision = timezone.localdate()

    filtros = [
        [f"#Compra: {compra.id}", f"Fecha: {_fmt_fecha(compra.fecha)}"],
        [f"Estado: {compra.get_estado_display()}", f"Estado pago: {compra.get_estado_pago_display()}"],
        [f"Emisión: {_fmt_fecha(fecha_emision)}", f"Proveedor: {compra.proveedor.nombre}"],
    ]

    filas = []
    total = 0.0
    for d in detalles:
        subtotal = float(d.cantidad) * float(d.costo_unitario)
        total += subtotal
        filas.append([
            d.material.nombre,
            d.material.unidad,
            float(d.cantidad),
            float(d.costo_unitario),
            float(subtotal),
        ])

    resumen = [
        ["Total", f"${total:.2f}"],
    ]

    columnas = ["Material", "Unidad", "Cantidad", "Costo unit.", "Subtotal"]

    # dinero: costo unit y subtotal -> indices 3,4
    return excel_reporte(
        nombre_archivo=f"factura_compra_{compra.id}",
        hoja="Factura Compra",
        titulo=f"Factura Compra #{compra.id}",
        columnas=columnas,
        filas=filas,
        filtros=filtros,
        resumen=resumen,
        logo_relpath="img/logo-bemore.jpeg",
        nombre_empresa="BEMORE",
        formato_moneda_cols=[3, 4],
    )

def _stock_annotation():
    # Stock = entradas + ajustes - salidas
    return Coalesce(
        Sum(
            Case(
                When(movimientos__tipo="SALIDA", then=F("movimientos__cantidad") * Value(Decimal("-1"))),
                When(movimientos__tipo="ENTRADA", then=F("movimientos__cantidad")),
                When(movimientos__tipo="AJUSTE", then=F("movimientos__cantidad")),
                default=Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        ),
        Value(Decimal("0.00")),
    )

@login_required
def reporte_existencias(request):
    tipo = (request.GET.get("tipo", "") or "").strip()      # MATERIAL / PRODUCTO / ""
    q = (request.GET.get("q", "") or "").strip()

    items = (
        ItemInventario.objects
        .select_related(
            "almacen",
            "material", "material__categoria",
            "variante_producto", "variante_producto__producto"
        )
        .filter(activo=True)
        .annotate(stock=_stock_annotation())
        .order_by("tipo", "almacen__nombre")
    )

    if tipo:
        items = items.filter(tipo=tipo)

    if q:
        items = items.filter(
            Q(material__nombre__icontains=q) |
            Q(variante_producto__sku__icontains=q) |
            Q(variante_producto__producto__nombre__icontains=q) |
            Q(variante_producto__nombre__icontains=q)
        )

    limite_vista = 500
    lista = items[:limite_vista]

    # Resumen simple
    resumen = {
        "cantidad": items.count(),
        "total_stock": items.aggregate(s=Coalesce(Sum("stock"), Decimal("0.00")))["s"].quantize(Decimal("0.01")),
    }

    return render(request, "reportes/existencias.html", {
        "items": lista,
        "tipo": tipo,
        "q": q,
        "limite_vista": limite_vista,
        "resumen": resumen,
        "tipo_choices": ItemInventario.TipoItem.choices,
    })


@login_required
def reporte_existencias_pdf(request):
    tipo = (request.GET.get("tipo", "") or "").strip()
    q = (request.GET.get("q", "") or "").strip()

    items = (
        ItemInventario.objects
        .select_related(
            "almacen",
            "material", "material__categoria",
            "variante_producto", "variante_producto__producto"
        )
        .filter(activo=True)
        .annotate(stock=_stock_annotation())
        .order_by("tipo", "almacen__nombre")
    )

    if tipo:
        items = items.filter(tipo=tipo)

    if q:
        items = items.filter(
            Q(material__nombre__icontains=q) |
            Q(variante_producto__sku__icontains=q) |
            Q(variante_producto__producto__nombre__icontains=q) |
            Q(variante_producto__nombre__icontains=q)
        )

    # ✅ Emisión (y nada más, como te gusta en reportes generales)
    fecha_emision = timezone.localdate()
    filtros = [f"Fecha de emisión: {_fmt_fecha(fecha_emision)}"]

    # Resumen
    total_stock = items.aggregate(s=Coalesce(Sum("stock"), Decimal("0.00")))["s"]
    resumen = [
        ["Cantidad de ítems", str(items.count())],
        ["Stock total (suma)", f"{total_stock.quantize(Decimal('0.01'))}"],
    ]

    columnas = ["Tipo", "Nombre", "SKU", "Unidad", "Stock", "Pto reorden"]

    filas = []
    for it in items[:8000]:
        if it.tipo == ItemInventario.TipoItem.MATERIAL and it.material:
            nombre = it.material.nombre
            sku = ""
            unidad = it.material.unidad
        else:
            # PRODUCTO
            vp = it.variante_producto
            nombre = f"{vp.producto.nombre} - {vp.nombre}" if vp else ""
            sku = vp.sku if vp else ""
            unidad = ""

        filas.append([
            it.get_tipo_display(),
            nombre,
            sku,
            unidad,
            round(float(it.stock), 2),
            round(float(it.punto_reorden), 2),
        ])

    col_widths = [
        32*mm,  # Tipo (un poquito)
        57*mm,  # Nombre ✅ más ancho
        34*mm,  # SKU
        19*mm,  # Unidad (más pequeño)
        17*mm,  # Stock (más pequeño)
        17*mm,  # Pto reorden (más pequeño)
    ]

    # ✅ Multi-página: en páginas siguientes NO logo, solo líneas (repeat_header=True)
    return pdf_tabla(
        "reporte_existencias",
        "Reporte de Existencias",
        None,
        columnas,
        filas,
        resumen=resumen,
        filtros=filtros,
        titulo_datos=None,
        repeat_header=True,
        col_widths=col_widths,
        logo_relpath="img/logo-bemore.jpeg",
        nombre_empresa="BEMORE",
    )


@login_required
def reporte_existencias_excel(request):
    tipo = (request.GET.get("tipo", "") or "").strip()
    q = (request.GET.get("q", "") or "").strip()

    items = (
        ItemInventario.objects
        .select_related(
            "almacen",
            "material", "material__categoria",
            "variante_producto", "variante_producto__producto"
        )
        .filter(activo=True)
        .annotate(stock=_stock_annotation())
        .order_by("tipo", "almacen__nombre")[:20000]
    )

    if tipo:
        items = items.filter(tipo=tipo)

    if q:
        items = items.filter(
            Q(material__nombre__icontains=q) |
            Q(variante_producto__sku__icontains=q) |
            Q(variante_producto__producto__nombre__icontains=q) |
            Q(variante_producto__nombre__icontains=q)
        )



    fecha_emision = timezone.localdate()
    filtros = [f"Fecha de emisión: {fecha_emision.strftime('%d/%m/%Y')}"]

    total_stock = items.aggregate(s=Coalesce(Sum("stock"), Decimal("0.00")))["s"]
    resumen = [
        ["Cantidad de ítems", str(items.count())],
        ["Stock total (suma)", str(total_stock.quantize(Decimal("0.01")))],
    ]

    columnas = ["Tipo", "Nombre", "SKU", "Unidad", "Stock", "Pto reorden"]

    filas = []
    for it in items:
        if it.tipo == ItemInventario.TipoItem.MATERIAL and it.material:
            nombre = it.material.nombre
            sku = ""
            unidad = it.material.unidad
        else:
            vp = it.variante_producto
            nombre = f"{vp.producto.nombre} - {vp.nombre}" if vp else ""
            sku = vp.sku if vp else ""
            unidad = ""

        filas.append([
            it.get_tipo_display(),
            nombre,
            sku,
            unidad,
            float(it.stock),
            float(it.punto_reorden),
        ])

    # anchos (Nombre más ancho)
    anchos = {1: 28, 2: 40, 3: 16, 4: 14, 5: 12, 6: 14}

    return excel_reporte(
        nombre_archivo="reporte_existencias",
        hoja="Existencias",
        titulo="Reporte de Existencias",
        columnas=columnas,
        filas=filas,
        filtros=filtros,
        resumen=resumen,
        logo_relpath="img/logo-bemore.jpeg",
        nombre_empresa="BEMORE",
        anchos=anchos,
    )