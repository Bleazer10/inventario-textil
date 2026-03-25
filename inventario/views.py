import json
from decimal import Decimal
from datetime import date, timedelta, datetime, time

from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect, get_object_or_404

from django.db.models import Q, Sum, Case, When, F, Value, DecimalField
from django.db.models.functions import Coalesce

from .forms import (
    ProductoForm,
    VarianteProductoForm,
    CategoriaProductoForm,
    CategoriaMaterialForm,
    MaterialForm,
    AlmacenForm,
    ItemInventarioForm,
    AjusteInventarioForm, ClienteForm, ProveedorForm, DetalleFormulaForm, FormulaForm, LoteProduccionForm
)

from .models import (
    # Catálogo
    CategoriaProducto,
    Producto,
    VarianteProducto,

    # Ventas / Gastos
    Cliente,
    Venta,
    DetalleVenta,
    CategoriaGasto,
    Gasto,

    # Finanzas
    CuentaPorCobrar,
    CuentaPorPagarCompra,
    CuentaPorPagarGasto, Pago,

    # Inventario
    CategoriaMaterial,
    Material,
    Almacen,
    ItemInventario,
    MovimientoInventario, Compra, DetalleCompra, Proveedor, Formula, DetalleFormula, LoteProduccion
)

def obtener_almacen_principal():
    almacen, _ = Almacen.objects.get_or_create(
        nombre="Principal",
        defaults={"activo": True},
    )
    return almacen

@login_required
def lista_categorias_producto(request):
    q = request.GET.get("q", "").strip()
    categorias = CategoriaProducto.objects.all().order_by("nombre")

    if q:
        categorias = categorias.filter(nombre__icontains=q)

    return render(request, "categorias_producto/lista.html", {
        "categorias": categorias,
        "q": q,
    })


@login_required
def nueva_categoria_producto(request):
    if request.method == "POST":
        form = CategoriaProductoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Categoría creada correctamente.")
            return redirect("lista_categorias_producto")
        messages.error(request, "Revisa los datos del formulario.")
    else:
        form = CategoriaProductoForm()

    return render(request, "categorias_producto/form.html", {
        "form": form,
        "modo": "nueva",
    })


@login_required
def editar_categoria_producto(request, categoria_id):
    categoria = get_object_or_404(CategoriaProducto, id=categoria_id)

    if request.method == "POST":
        form = CategoriaProductoForm(request.POST, instance=categoria)
        if form.is_valid():
            form.save()
            messages.success(request, "Categoría actualizada correctamente.")
            return redirect("lista_categorias_producto")
        messages.error(request, "Revisa los datos del formulario.")
    else:
        form = CategoriaProductoForm(instance=categoria)

    return render(request, "categorias_producto/form.html", {
        "form": form,
        "modo": "editar",
        "categoria": categoria,
    })

@login_required
def lista_productos(request):
    q = request.GET.get("q", "").strip()

    productos = (
        Producto.objects
        .select_related("categoria")
        .order_by("nombre")
    )

    if q:
        productos = productos.filter(
            Q(nombre__icontains=q) |
            Q(categoria__nombre__icontains=q) |
            Q(variantes__sku__icontains=q) |
            Q(variantes__nombre__icontains=q)
        ).distinct()

    return render(request, "productos/lista_productos.html", {
        "productos": productos,
        "q": q,
    })


@login_required
def nuevo_producto(request):
    if request.method == "POST":
        form = ProductoForm(request.POST)
        if form.is_valid():
            producto = form.save()
            messages.success(request, "Producto creado correctamente.")
            return redirect("detalle_producto", producto_id=producto.id)
        messages.error(request, "Revisa los datos del formulario.")
    else:
        form = ProductoForm()

    return render(request, "productos/nuevo_producto.html", {"form": form})


@login_required
def detalle_producto(request, producto_id):
    producto = get_object_or_404(Producto.objects.select_related("categoria"), id=producto_id)
    variantes = producto.variantes.order_by("nombre")

    return render(request, "productos/detalle_producto.html", {
        "producto": producto,
        "variantes": variantes,
    })


@login_required
def nueva_variante(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)

    if request.method == "POST":
        form = VarianteProductoForm(request.POST)
        if form.is_valid():
            variante = form.save(commit=False)
            variante.producto = producto
            variante.save()
            messages.success(request, "Variante creada correctamente.")
            return redirect("detalle_producto", producto_id=producto.id)
        messages.error(request, "Revisa los datos del formulario.")
    else:
        form = VarianteProductoForm()

    return render(request, "productos/nueva_variante.html", {
        "producto": producto,
        "form": form,
    })


@login_required
def nueva_venta(request):
    clientes = Cliente.objects.filter(activo=True).order_by("nombre")
    variantes = (
        VarianteProducto.objects
        .filter(activa=True, producto__activo=True)
        .select_related("producto", "producto__categoria")
        .order_by("producto__nombre", "nombre")
    )

    if request.method == "POST":
        fecha = request.POST.get("fecha") or str(date.today())
        tipo_pago = request.POST.get("tipo_pago", "CONTADO")  # CONTADO / CREDITO
        cliente_id = request.POST.get("cliente") or None
        items_json = request.POST.get("items_json", "[]")

        try:
            items = json.loads(items_json)
        except json.JSONDecodeError:
            items = []

        if not items:
            messages.error(request, "Agrega al menos un producto para guardar la venta.")
            return redirect("nueva_venta")

        cliente = None
        if cliente_id:
            cliente = get_object_or_404(Cliente, id=cliente_id)

        total = Decimal("0.00")
        detalles_a_crear = []

        for it in items:
            variante_id = it.get("variante_id")
            cantidad = Decimal(str(it.get("cantidad", "0")).replace(",", "."))

            if not variante_id or cantidad <= 0:
                continue

            variante = get_object_or_404(VarianteProducto, id=variante_id)
            precio_unitario = Decimal(str(variante.precio_venta_efectivo)).quantize(Decimal("0.01"))
            subtotal = (precio_unitario * cantidad).quantize(Decimal("0.01"))

            total += subtotal
            detalles_a_crear.append((variante, cantidad, precio_unitario, subtotal))

        total = total.quantize(Decimal("0.01"))

        if total <= 0 or not detalles_a_crear:
            messages.error(request, "Los productos agregados no son válidos. Revisa cantidades.")
            return redirect("nueva_venta")

        # Montos según tipo de pago
        if tipo_pago == "CONTADO":
            monto_pagado = total
            saldo_pendiente = Decimal("0.00")
        else:
            monto_pagado = Decimal("0.00")
            saldo_pendiente = total

        venta = Venta.objects.create(
            cliente=cliente,
            fecha=fecha,
            estado=Venta.Estado.CONFIRMADA,
            tipo_pago=tipo_pago,
            total=total,
            monto_pagado=monto_pagado,
            saldo_pendiente=saldo_pendiente,
        )

        # Guardar detalles
        for variante, cantidad, precio_unitario, subtotal in detalles_a_crear:
            DetalleVenta.objects.create(
                venta=venta,
                variante_producto=variante,
                cantidad=cantidad,
                precio_unitario=precio_unitario,
                descuento=Decimal("0.00"),
                subtotal=subtotal,
            )

        # ✅ DESCONTAR INVENTARIO (1 almacén: Principal)
        almacen_principal = obtener_almacen_principal()

        for variante, cantidad, precio_unitario, subtotal in detalles_a_crear:
            if not variante.producto.controla_inventario:
                continue

            item, _ = ItemInventario.objects.get_or_create(
                almacen=almacen_principal,
                tipo=ItemInventario.TipoItem.PRODUCTO,
                variante_producto=variante,
                defaults={"punto_reorden": 0, "activo": True},
            )

            MovimientoInventario.objects.create(
                item=item,
                tipo=MovimientoInventario.TipoMovimiento.SALIDA,
                cantidad=cantidad,
                costo_unitario=None,
                referencia="VENTA",
                referencia_id=venta.id,
                nota="Salida automática por venta",
            )

        # ✅ SI ES CRÉDITO → CREAR CUENTA POR COBRAR
        if tipo_pago == "CREDITO":
            CuentaPorCobrar.objects.create(
                cliente=cliente,
                venta=venta,
                monto_total=total,
                monto_pagado=Decimal("0.00"),
                saldo=total,
                estado=CuentaPorCobrar.Estado.ABIERTA,
            )

        messages.success(request, f"Venta #{venta.id} guardada correctamente. Total: ${total}")
        return redirect("dashboard")

    return render(request, "ventas/nueva_venta.html", {
        "clientes": clientes,
        "variantes": variantes,
    })

@login_required
def nuevo_gasto(request):
    categorias = CategoriaGasto.objects.filter(activa=True).order_by("nombre")

    if request.method == "POST":
        fecha = request.POST.get("fecha") or str(date.today())
        categoria_id = request.POST.get("categoria")
        monto = request.POST.get("monto", "0")
        descripcion = request.POST.get("descripcion", "")
        estado_pago = request.POST.get("estado_pago", Gasto.EstadoPago.PENDIENTE)

        if not categoria_id:
            messages.error(request, "Selecciona una categoría.")
            return redirect("nuevo_gasto")

        try:
            monto_dec = Decimal(monto.replace(",", ".")).quantize(Decimal("0.01"))
        except:
            messages.error(request, "Monto inválido.")
            return redirect("nuevo_gasto")

        if monto_dec <= 0:
            messages.error(request, "El monto debe ser mayor a 0.")
            return redirect("nuevo_gasto")

        categoria = get_object_or_404(CategoriaGasto, id=categoria_id)

        gasto = Gasto.objects.create(
            categoria=categoria,
            fecha=fecha,
            monto=monto_dec,
            estado_pago=estado_pago,
            descripcion=descripcion,
        )

        # ✅ SI QUEDA PENDIENTE O PARCIAL → CREAR CUENTA POR PAGAR (GASTO)
        if gasto.estado_pago in [Gasto.EstadoPago.PENDIENTE, Gasto.EstadoPago.PARCIAL]:
            CuentaPorPagarGasto.objects.create(
                gasto=gasto,
                proveedor=gasto.proveedor,  # puede ser None
                monto_total=gasto.monto,
                monto_pagado=Decimal("0.00"),
                saldo=gasto.monto,
                estado=CuentaPorPagarGasto.Estado.ABIERTA,
            )

        messages.success(request, f"Gasto #{gasto.id} guardado correctamente.")
        return redirect("dashboard")

    return render(request, "gastos/nuevo_gasto.html", {"categorias": categorias})

@login_required
def movimientos(request):
    filtro = request.GET.get("filtro", "hoy")  # hoy | semana | mes | rango
    hoy = date.today()

    # Determinar rango de fechas
    if filtro == "hoy":
        fecha_inicio = hoy
        fecha_fin = hoy
    elif filtro == "semana":
        fecha_inicio = hoy - timedelta(days=hoy.weekday())  # lunes
        fecha_fin = fecha_inicio + timedelta(days=6)
    elif filtro == "mes":
        fecha_inicio = hoy.replace(day=1)
        if fecha_inicio.month == 12:
            fecha_fin = fecha_inicio.replace(year=fecha_inicio.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            fecha_fin = fecha_inicio.replace(month=fecha_inicio.month + 1, day=1) - timedelta(days=1)
    else:
        fi = request.GET.get("fi")
        ff = request.GET.get("ff")
        try:
            fecha_inicio = datetime.strptime(fi, "%Y-%m-%d").date() if fi else hoy
            fecha_fin = datetime.strptime(ff, "%Y-%m-%d").date() if ff else hoy
        except:
            fecha_inicio = hoy
            fecha_fin = hoy

    # Ventas confirmadas en rango
    ventas_qs = Venta.objects.filter(
        fecha__gte=fecha_inicio,
        fecha__lte=fecha_fin,
        estado=Venta.Estado.CONFIRMADA,
    ).select_related("cliente").order_by("-fecha", "-id")

    ventas_total = (
        ventas_qs.aggregate(s=Coalesce(Sum("total"), Decimal("0.00")))["s"]
    ).quantize(Decimal("0.01"))

    # Gastos en rango
    gastos_qs = Gasto.objects.filter(
        fecha__gte=fecha_inicio,
        fecha__lte=fecha_fin,
    ).select_related("categoria", "proveedor").order_by("-fecha", "-id")

    gastos_total = (
        gastos_qs.aggregate(s=Coalesce(Sum("monto"), Decimal("0.00")))["s"]
    ).quantize(Decimal("0.01"))

    balance = (ventas_total - gastos_total).quantize(Decimal("0.01"))

    # Totales por cobrar / por pagar (saldo)
    por_cobrar_total = (
        CuentaPorCobrar.objects
        .filter(estado=CuentaPorCobrar.Estado.ABIERTA)
        .aggregate(s=Coalesce(Sum("saldo"), Decimal("0.00")))["s"]
    ).quantize(Decimal("0.01"))

    por_pagar_compras_total = (
        CuentaPorPagarCompra.objects
        .filter(estado=CuentaPorPagarCompra.Estado.ABIERTA)
        .aggregate(s=Coalesce(Sum("saldo"), Decimal("0.00")))["s"]
    ).quantize(Decimal("0.01"))

    por_pagar_gastos_total = (
        CuentaPorPagarGasto.objects
        .filter(estado=CuentaPorPagarGasto.Estado.ABIERTA)
        .aggregate(s=Coalesce(Sum("saldo"), Decimal("0.00")))["s"]
    ).quantize(Decimal("0.01"))

    por_pagar_total = (por_pagar_compras_total + por_pagar_gastos_total).quantize(Decimal("0.01"))

    # Listas para pestañas (últimos registros del rango)
    ventas_lista = ventas_qs[:20]
    gastos_lista = gastos_qs[:20]

    # ✅ NUEVO: listas para pestañas de CxC / CxP (las dejamos por estado ABIERTA)
    cxc_lista = (
        CuentaPorCobrar.objects
        .filter(estado=CuentaPorCobrar.Estado.ABIERTA)
        .select_related("cliente", "venta")
        .order_by("-creada")[:20]
    )

    cxp_compras_lista = (
        CuentaPorPagarCompra.objects
        .filter(estado=CuentaPorPagarCompra.Estado.ABIERTA)
        .select_related("proveedor", "compra")
        .order_by("-creada")[:20]
    )

    cxp_gastos_lista = (
        CuentaPorPagarGasto.objects
        .filter(estado=CuentaPorPagarGasto.Estado.ABIERTA)
        .select_related("proveedor", "gasto")
        .order_by("-creada")[:20]
    )

    # ✅ OPCIONAL: pagos en rango (si quieres pestaña Pagos)
    pagos_lista = (
        Pago.objects
        .filter(fecha__gte=fecha_inicio, fecha__lte=fecha_fin)
        .order_by("-fecha", "-id")[:30]
    )

    return render(request, "movimientos/movimientos.html", {
        "filtro": filtro,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,

        "ventas_total": ventas_total,
        "gastos_total": gastos_total,
        "balance": balance,

        "por_cobrar_total": por_cobrar_total,
        "por_pagar_total": por_pagar_total,

        "ventas_lista": ventas_lista,
        "gastos_lista": gastos_lista,

        "cxc_lista": cxc_lista,
        "cxp_compras_lista": cxp_compras_lista,
        "cxp_gastos_lista": cxp_gastos_lista,

        "pagos_lista": pagos_lista,
    })

@login_required
def movimientos_inventario(request):
    tipo = request.GET.get("tipo", "").strip()        # ENTRADA / SALIDA / AJUSTE / TRASLADO
    almacen_id = request.GET.get("almacen", "").strip()
    q = request.GET.get("q", "").strip()

    fi = request.GET.get("fi", "").strip()
    ff = request.GET.get("ff", "").strip()

    # Rango por defecto: últimos 30 días
    hoy = timezone.localdate()

    # Calcular fi_date
    if fi:
        try:
            fi_date = datetime.strptime(fi, "%Y-%m-%d").date()
        except ValueError:
            fi_date = hoy - timedelta(days=30)
    else:
        fi_date = hoy - timedelta(days=30)

    # Calcular ff_date
    if ff:
        try:
            ff_date = datetime.strptime(ff, "%Y-%m-%d").date()
        except ValueError:
            ff_date = hoy
    else:
        ff_date = hoy

    # Convertimos a datetimes (inicio del día y fin del día exclusivo)
    inicio_dt = timezone.make_aware(datetime.combine(fi_date, time.min))
    fin_dt = timezone.make_aware(datetime.combine(ff_date + timedelta(days=1), time.min))

    movimientos = (
        MovimientoInventario.objects
        .select_related(
            "item",
            "item__almacen",
            "item__material",
            "item__variante_producto",
            "item__variante_producto__producto",
        )
        .filter(creado__gte=inicio_dt, creado__lt=fin_dt)
        .order_by("-creado")
    )

    if tipo:
        movimientos = movimientos.filter(tipo=tipo)

    if almacen_id:
        movimientos = movimientos.filter(item__almacen_id=almacen_id)

    if q:
        movimientos = movimientos.filter(
            Q(item__material__nombre__icontains=q) |
            Q(item__variante_producto__sku__icontains=q) |
            Q(item__variante_producto__producto__nombre__icontains=q) |
            Q(item__variante_producto__nombre__icontains=q) |
            Q(referencia__icontains=q)
        )

    almacenes = Almacen.objects.filter(activo=True).order_by("nombre")

    return render(request, "inventario/movimientos_inventario.html", {
        "movimientos": movimientos[:300],
        "almacenes": almacenes,

        "tipo": tipo,
        "almacen_id": almacen_id,
        "q": q,
        "fi": fi_date.strftime("%Y-%m-%d"),
        "ff": ff_date.strftime("%Y-%m-%d"),
    })

@login_required
def lista_categorias_material(request):
    q = request.GET.get("q", "").strip()
    categorias = CategoriaMaterial.objects.all().order_by("nombre")
    if q:
        categorias = categorias.filter(nombre__icontains=q)

    return render(request, "materiales/categorias_lista.html", {
        "categorias": categorias,
        "q": q,
    })


@login_required
def nueva_categoria_material(request):
    if request.method == "POST":
        form = CategoriaMaterialForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Categoría de material creada correctamente.")
            return redirect("lista_categorias_material")
        messages.error(request, "Revisa los datos del formulario.")
    else:
        form = CategoriaMaterialForm()

    return render(request, "materiales/categorias_form.html", {"form": form, "modo": "nueva"})


@login_required
def editar_categoria_material(request, categoria_id):
    categoria = get_object_or_404(CategoriaMaterial, id=categoria_id)

    if request.method == "POST":
        form = CategoriaMaterialForm(request.POST, instance=categoria)
        if form.is_valid():
            form.save()
            messages.success(request, "Categoría de material actualizada correctamente.")
            return redirect("lista_categorias_material")
        messages.error(request, "Revisa los datos del formulario.")
    else:
        form = CategoriaMaterialForm(instance=categoria)

    return render(request, "materiales/categorias_form.html", {
        "form": form,
        "modo": "editar",
        "categoria": categoria,
    })

@login_required
def lista_materiales(request):
    q = request.GET.get("q", "").strip()
    materiales = Material.objects.select_related("categoria").order_by("nombre")

    if q:
        materiales = materiales.filter(
            Q(nombre__icontains=q) |
            Q(categoria__nombre__icontains=q) |
            Q(unidad__icontains=q)
        )

    return render(request, "materiales/materiales_lista.html", {"materiales": materiales, "q": q})


@login_required
def nuevo_material(request):
    if request.method == "POST":
        form = MaterialForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Material creado correctamente.")
            return redirect("lista_materiales")
        messages.error(request, "Revisa los datos del formulario.")
    else:
        form = MaterialForm()

    return render(request, "materiales/materiales_form.html", {"form": form, "modo": "nueva"})


@login_required
def editar_material(request, material_id):
    material = get_object_or_404(Material, id=material_id)

    if request.method == "POST":
        form = MaterialForm(request.POST, instance=material)
        if form.is_valid():
            form.save()
            messages.success(request, "Material actualizado correctamente.")
            return redirect("lista_materiales")
        messages.error(request, "Revisa los datos del formulario.")
    else:
        form = MaterialForm(instance=material)

    return render(request, "materiales/materiales_form.html", {"form": form, "modo": "editar", "material": material})

@login_required
def lista_almacenes(request):
    q = request.GET.get("q", "").strip()
    almacenes = Almacen.objects.all().order_by("nombre")
    if q:
        almacenes = almacenes.filter(nombre__icontains=q)

    return render(request, "almacenes/lista.html", {"almacenes": almacenes, "q": q})


@login_required
def nuevo_almacen(request):
    if request.method == "POST":
        form = AlmacenForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Almacén creado correctamente.")
            return redirect("lista_almacenes")
        messages.error(request, "Revisa los datos del formulario.")
    else:
        form = AlmacenForm()

    return render(request, "almacenes/form.html", {"form": form, "modo": "nueva"})


@login_required
def editar_almacen(request, almacen_id):
    almacen = get_object_or_404(Almacen, id=almacen_id)

    if request.method == "POST":
        form = AlmacenForm(request.POST, instance=almacen)
        if form.is_valid():
            form.save()
            messages.success(request, "Almacén actualizado correctamente.")
            return redirect("lista_almacenes")
        messages.error(request, "Revisa los datos del formulario.")
    else:
        form = AlmacenForm(instance=almacen)

    return render(request, "almacenes/form.html", {"form": form, "modo": "editar", "almacen": almacen})

@login_required
def lista_items_inventario(request):
    q = request.GET.get("q", "").strip()

    items = (
        ItemInventario.objects
        .select_related("almacen", "material", "variante_producto", "variante_producto__producto")
        .order_by("almacen__nombre", "tipo")
    )

    if q:
        items = items.filter(
            Q(material__nombre__icontains=q) |
            Q(variante_producto__sku__icontains=q) |
            Q(variante_producto__producto__nombre__icontains=q) |
            Q(variante_producto__nombre__icontains=q) |
            Q(almacen__nombre__icontains=q)
        )

    return render(request, "items_inventario/lista.html", {"items": items, "q": q})


@login_required
def nuevo_item_inventario(request):
    if request.method == "POST":
        form = ItemInventarioForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Ítem de inventario creado correctamente.")
            return redirect("lista_items_inventario")
        messages.error(request, "Revisa los datos del formulario.")
    else:
        form = ItemInventarioForm()

    return render(request, "items_inventario/form.html", {"form": form, "modo": "nueva"})


@login_required
def editar_item_inventario(request, item_id):
    item = get_object_or_404(ItemInventario, id=item_id)

    if request.method == "POST":
        form = ItemInventarioForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, "Ítem de inventario actualizado correctamente.")
            return redirect("lista_items_inventario")
        messages.error(request, "Revisa los datos del formulario.")
    else:
        form = ItemInventarioForm(instance=item)

    return render(request, "items_inventario/form.html", {"form": form, "modo": "editar", "item": item})

@login_required
def ajuste_inventario(request):
    if request.method == "POST":
        form = AjusteInventarioForm(request.POST)
        if form.is_valid():
            item = form.cleaned_data["item"]
            tipo = form.cleaned_data["tipo"]
            cantidad = form.cleaned_data["cantidad"]
            costo_unitario = form.cleaned_data.get("costo_unitario")
            nota = form.cleaned_data.get("nota") or ""

            MovimientoInventario.objects.create(
                item=item,
                tipo=tipo,
                cantidad=cantidad,
                costo_unitario=costo_unitario if costo_unitario is not None else None,
                referencia="AJUSTE_MANUAL",
                referencia_id=None,
                nota=nota,
            )

            messages.success(request, "Movimiento creado correctamente.")
            return redirect("movimientos_inventario")
        messages.error(request, "Revisa los datos del formulario.")
    else:
        form = AjusteInventarioForm()

    return render(request, "inventario/ajuste_inventario.html", {"form": form})

@login_required
def existencias(request):
    almacen_id = request.GET.get("almacen", "").strip()
    tipo_item = request.GET.get("tipo", "").strip()  # MATERIAL / PRODUCTO / ""
    q = request.GET.get("q", "").strip()

    items = (
        ItemInventario.objects
        .select_related("almacen", "material", "variante_producto", "variante_producto__producto")
        .filter(activo=True)
    )

    if almacen_id:
        items = items.filter(almacen_id=almacen_id)

    if tipo_item:
        items = items.filter(tipo=tipo_item)

    if q:
        items = items.filter(
            Q(material__nombre__icontains=q) |
            Q(variante_producto__sku__icontains=q) |
            Q(variante_producto__producto__nombre__icontains=q) |
            Q(variante_producto__nombre__icontains=q) |
            Q(almacen__nombre__icontains=q)
        )

    # Stock = sum( +cantidad si ENTRADA/AJUSTE, -cantidad si SALIDA )
    items = items.annotate(
        stock=Coalesce(
            Sum(
                Case(
                    When(movimientos__tipo="SALIDA", then=F("movimientos__cantidad") * Value(Decimal("-1"))),
                    When(movimientos__tipo="ENTRADA", then=F("movimientos__cantidad")),
                    When(movimientos__tipo="AJUSTE", then=F("movimientos__cantidad")),
                    # TRASLADO lo dejamos fuera por ahora (o suma 0)
                    default=Value(Decimal("0.00")),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                )
            ),
            Value(Decimal("0.00")),
        )
    ).order_by("almacen__nombre", "tipo")

    almacenes = Almacen.objects.filter(activo=True).order_by("nombre")

    return render(request, "inventario/existencias.html", {
        "items": items,
        "almacenes": almacenes,
        "almacen_id": almacen_id,
        "tipo_item": tipo_item,
        "q": q,
    })

@login_required
def lista_compras(request):
    q = (request.GET.get("q") or "").strip()
    estado = (request.GET.get("estado") or "").strip()
    estado_pago = (request.GET.get("estado_pago") or "").strip()

    compras = Compra.objects.select_related("proveedor").order_by("-fecha", "-creado")

    if estado:
        compras = compras.filter(estado=estado)

    if estado_pago:
        compras = compras.filter(estado_pago=estado_pago)

    if q:
        compras = compras.filter(
            Q(proveedor__nombre__icontains=q) |
            Q(id__icontains=q)
        )

    return render(request, "compras/lista.html", {
        "compras": compras,
        "q": q,
        "estado": estado,
        "estado_pago": estado_pago,
        "estados": Compra.Estado.choices,
        "estados_pago": Compra.EstadoPago.choices,
    })


@login_required
def nueva_compra(request):
    proveedores = Proveedor.objects.filter(activo=True).order_by("nombre")
    materiales = (
        Material.objects
        .filter(activo=True)
        .select_related("categoria")
        .order_by("nombre")
    )

    if request.method == "POST":
        proveedor_id = request.POST.get("proveedor")
        fecha = request.POST.get("fecha") or str(date.today())
        notas = request.POST.get("notas", "")
        items_json = request.POST.get("items_json", "[]")

        try:
            items = json.loads(items_json)
        except json.JSONDecodeError:
            items = []

        if not proveedor_id:
            messages.error(request, "Selecciona un proveedor.")
            return redirect("nueva_compra")

        if not items:
            messages.error(request, "Agrega al menos un material para guardar la compra.")
            return redirect("nueva_compra")

        proveedor = get_object_or_404(Proveedor, id=proveedor_id)

        compra = Compra.objects.create(
            proveedor=proveedor,
            fecha=fecha,
            estado=Compra.Estado.BORRADOR,
            estado_pago=Compra.EstadoPago.PENDIENTE,
            notas=notas,
        )

        # Crear detalles
        creados = 0
        for it in items:
            material_id = it.get("material_id")
            cantidad = Decimal(str(it.get("cantidad", "0")).replace(",", "."))
            costo_unitario = Decimal(str(it.get("costo_unitario", "0")).replace(",", "."))

            if not material_id or cantidad <= 0 or costo_unitario <= 0:
                continue

            material = get_object_or_404(Material, id=material_id)

            DetalleCompra.objects.create(
                compra=compra,
                material=material,
                cantidad=cantidad,
                costo_unitario=costo_unitario,
            )
            creados += 1

        if creados == 0:
            compra.delete()
            messages.error(request, "No se pudo guardar la compra: revisa cantidades y costos.")
            return redirect("nueva_compra")

        messages.success(request, f"Compra #{compra.id} creada en BORRADOR.")
        return redirect("detalle_compra", compra_id=compra.id)

    return render(request, "compras/nueva.html", {
        "proveedores": proveedores,
        "materiales": materiales,
    })


@login_required
def detalle_compra(request, compra_id):
    compra = get_object_or_404(
        Compra.objects.select_related("proveedor"),
        id=compra_id
    )

    detalles_qs = compra.detalles.select_related("material", "material__categoria").all()

    detalles = []
    total = Decimal("0.00")

    for d in detalles_qs:
        subtotal = (d.cantidad * d.costo_unitario).quantize(Decimal("0.01"))
        total += subtotal
        detalles.append({
            "material": d.material,
            "cantidad": d.cantidad,
            "costo_unitario": d.costo_unitario,
            "subtotal": subtotal,
        })

    total = total.quantize(Decimal("0.01"))

    return render(request, "compras/detalle.html", {
        "compra": compra,
        "detalles": detalles,
        "total": total,
    })

@require_POST
@login_required
def recibir_compra(request, compra_id):
    compra = get_object_or_404(
        Compra.objects.select_related("proveedor"),
        id=compra_id
    )

    if compra.estado != Compra.Estado.BORRADOR:
        messages.error(request, "Solo puedes recibir compras en estado BORRADOR.")
        return redirect("detalle_compra", compra_id=compra.id)

    almacen_principal = obtener_almacen_principal()
    detalles = compra.detalles.select_related("material").all()

    # Crear ENTRADAS en inventario para cada material
    for d in detalles:
        item, _ = ItemInventario.objects.get_or_create(
            almacen=almacen_principal,
            tipo=ItemInventario.TipoItem.MATERIAL,
            material=d.material,
            defaults={"punto_reorden": 0, "activo": True},
        )

        MovimientoInventario.objects.create(
            item=item,
            tipo=MovimientoInventario.TipoMovimiento.ENTRADA,
            cantidad=d.cantidad,
            costo_unitario=d.costo_unitario,
            referencia="COMPRA",
            referencia_id=compra.id,
            nota=f"Entrada por compra #{compra.id}",
        )

    # Marcar compra como recibida
    compra.estado = Compra.Estado.RECIBIDA
    compra.save(update_fields=["estado"])

    # ✅ CREAR / ACTUALIZAR CUENTA POR PAGAR DE COMPRA (si queda pendiente o parcial)
    total = Decimal("0.00")
    for d in detalles:
        total += (d.cantidad * d.costo_unitario)
    total = total.quantize(Decimal("0.01"))

    if compra.estado_pago in [Compra.EstadoPago.PENDIENTE, Compra.EstadoPago.PARCIAL]:
        CuentaPorPagarCompra.objects.update_or_create(
            compra=compra,
            defaults={
                "proveedor": compra.proveedor,
                "monto_total": total,
                "monto_pagado": Decimal("0.00"),
                "saldo": total,
                "estado": CuentaPorPagarCompra.Estado.ABIERTA,
            }
        )

    messages.success(request, f"Compra #{compra.id} recibida. Inventario actualizado.")
    return redirect("detalle_compra", compra_id=compra.id)

# -------------------------
# CLIENTES
# -------------------------
@login_required
def lista_clientes(request):
    q = request.GET.get("q", "").strip()
    clientes = Cliente.objects.all().order_by("nombre")
    if q:
        clientes = clientes.filter(
            Q(nombre__icontains=q) |
            Q(telefono__icontains=q) |
            Q(email__icontains=q)
        )
    return render(request, "terceros/clientes_lista.html", {"clientes": clientes, "q": q})


@login_required
def nuevo_cliente(request):
    if request.method == "POST":
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Cliente creado correctamente.")
            return redirect("lista_clientes")
        messages.error(request, "Revisa los datos del formulario.")
    else:
        form = ClienteForm()
    return render(request, "terceros/clientes_form.html", {"form": form, "modo": "nueva"})


@login_required
def editar_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)
    if request.method == "POST":
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, "Cliente actualizado correctamente.")
            return redirect("lista_clientes")
        messages.error(request, "Revisa los datos del formulario.")
    else:
        form = ClienteForm(instance=cliente)
    return render(request, "terceros/clientes_form.html", {"form": form, "modo": "editar", "cliente": cliente})


# -------------------------
# PROVEEDORES
# -------------------------
@login_required
def lista_proveedores(request):
    q = request.GET.get("q", "").strip()
    proveedores = Proveedor.objects.all().order_by("nombre")
    if q:
        proveedores = proveedores.filter(
            Q(nombre__icontains=q) |
            Q(telefono__icontains=q) |
            Q(email__icontains=q)
        )
    return render(request, "terceros/proveedores_lista.html", {"proveedores": proveedores, "q": q})


@login_required
def nuevo_proveedor(request):
    if request.method == "POST":
        form = ProveedorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Proveedor creado correctamente.")
            return redirect("lista_proveedores")
        messages.error(request, "Revisa los datos del formulario.")
    else:
        form = ProveedorForm()
    return render(request, "terceros/proveedores_form.html", {"form": form, "modo": "nueva"})


@login_required
def editar_proveedor(request, proveedor_id):
    proveedor = get_object_or_404(Proveedor, id=proveedor_id)
    if request.method == "POST":
        form = ProveedorForm(request.POST, instance=proveedor)
        if form.is_valid():
            form.save()
            messages.success(request, "Proveedor actualizado correctamente.")
            return redirect("lista_proveedores")
        messages.error(request, "Revisa los datos del formulario.")
    else:
        form = ProveedorForm(instance=proveedor)
    return render(request, "terceros/proveedores_form.html", {"form": form, "modo": "editar", "proveedor": proveedor})

@login_required
def lista_formulas(request):
    q = (request.GET.get("q") or "").strip()

    formulas = (
        Formula.objects
        .select_related("variante_producto", "variante_producto__producto")
        .order_by("variante_producto__producto__nombre", "variante_producto__nombre", "nombre")
    )

    if q:
        formulas = formulas.filter(
            Q(nombre__icontains=q) |
            Q(variante_producto__sku__icontains=q) |
            Q(variante_producto__nombre__icontains=q) |
            Q(variante_producto__producto__nombre__icontains=q)
        )

    return render(request, "formulas/lista.html", {"formulas": formulas, "q": q})


@login_required
def nueva_formula(request):
    if request.method == "POST":
        form = FormulaForm(request.POST)
        if form.is_valid():
            formula = form.save()
            messages.success(request, "Fórmula creada correctamente.")
            return redirect("detalle_formula", formula_id=formula.id)
        messages.error(request, "Revisa los datos del formulario.")
    else:
        form = FormulaForm()

    return render(request, "formulas/form.html", {"form": form, "modo": "nueva"})


@login_required
def editar_formula(request, formula_id):
    formula = get_object_or_404(Formula, id=formula_id)

    if request.method == "POST":
        form = FormulaForm(request.POST, instance=formula)
        if form.is_valid():
            form.save()
            messages.success(request, "Fórmula actualizada correctamente.")
            return redirect("detalle_formula", formula_id=formula.id)
        messages.error(request, "Revisa los datos del formulario.")
    else:
        form = FormulaForm(instance=formula)

    return render(request, "formulas/form.html", {"form": form, "modo": "editar", "formula": formula})


def _calcular_costo_estimado_por_unidad(formula: Formula) -> dict:
    """
    Costo estimado por unidad usando:
    - Material.costo_defecto
    - cantidad_por_unidad
    - merma_porcentaje
    + mano de obra unitario
    + indirecto unitario
    """
    detalles = formula.detalles.select_related("material").all()

    costo_materiales = Decimal("0.00")
    alertas = []

    for d in detalles:
        costo_mat = d.material.costo_defecto or Decimal("0.00")
        if costo_mat <= 0:
            alertas.append(f"Material sin costo_defecto: {d.material.nombre}")

        factor_merma = (Decimal("1.00") + (d.merma_porcentaje or Decimal("0.00")) / Decimal("100.00"))
        consumo_real = (d.cantidad_por_unidad * factor_merma)

        costo_materiales += (consumo_real * costo_mat)

    costo_materiales = costo_materiales.quantize(Decimal("0.01"))

    mano_obra = (formula.costo_mano_obra_unitario or Decimal("0.00")).quantize(Decimal("0.01"))
    indirecto = (formula.costo_indirecto_unitario or Decimal("0.00")).quantize(Decimal("0.01"))

    costo_total = (costo_materiales + mano_obra + indirecto).quantize(Decimal("0.01"))

    return {
        "costo_materiales": costo_materiales,
        "mano_obra": mano_obra,
        "indirecto": indirecto,
        "costo_total": costo_total,
        "alertas": alertas,
    }


@login_required
def detalle_formula(request, formula_id):
    formula = get_object_or_404(
        Formula.objects.select_related("variante_producto", "variante_producto__producto"),
        id=formula_id
    )

    detalles = formula.detalles.select_related("material", "material__categoria").order_by("material__nombre")
    costos = _calcular_costo_estimado_por_unidad(formula)

    return render(request, "formulas/detalle.html", {
        "formula": formula,
        "detalles": detalles,
        "costos": costos,
    })


@login_required
def nuevo_detalle_formula(request, formula_id):
    formula = get_object_or_404(Formula, id=formula_id)

    if request.method == "POST":
        form = DetalleFormulaForm(request.POST)
        if form.is_valid():
            detalle = form.save(commit=False)
            detalle.formula = formula
            detalle.save()
            messages.success(request, "Material agregado a la fórmula.")
            return redirect("detalle_formula", formula_id=formula.id)
        messages.error(request, "Revisa los datos del formulario.")
    else:
        form = DetalleFormulaForm()

    return render(request, "formulas/detalle_form.html", {
        "form": form,
        "formula": formula,
        "modo": "nueva",
    })


@login_required
def editar_detalle_formula(request, formula_id, detalle_id):
    formula = get_object_or_404(Formula, id=formula_id)
    detalle = get_object_or_404(DetalleFormula, id=detalle_id, formula=formula)

    if request.method == "POST":
        form = DetalleFormulaForm(request.POST, instance=detalle)
        if form.is_valid():
            form.save()
            messages.success(request, "Material actualizado en la fórmula.")
            return redirect("detalle_formula", formula_id=formula.id)
        messages.error(request, "Revisa los datos del formulario.")
    else:
        form = DetalleFormulaForm(instance=detalle)

    return render(request, "formulas/detalle_form.html", {
        "form": form,
        "formula": formula,
        "detalle": detalle,
        "modo": "editar",
    })


@require_POST
@login_required
def eliminar_detalle_formula(request, formula_id, detalle_id):
    formula = get_object_or_404(Formula, id=formula_id)
    detalle = get_object_or_404(DetalleFormula, id=detalle_id, formula=formula)
    detalle.delete()
    messages.success(request, "Material eliminado de la fórmula.")
    return redirect("detalle_formula", formula_id=formula.id)

def _consumo_material_por_unidad(detalle: DetalleFormula) -> Decimal:
    """
    Devuelve el consumo REAL por unidad incluyendo merma:
    consumo_real = cantidad_por_unidad * (1 + merma/100)
    """
    merma = (detalle.merma_porcentaje or Decimal("0.00"))
    factor = Decimal("1.00") + (merma / Decimal("100.00"))
    return (detalle.cantidad_por_unidad * factor)


def _calcular_costos_lote(lote: LoteProduccion) -> dict:
    """
    Calcula:
    - consumo total por material (según fórmula y cantidad_producida)
    - costo total materiales (usa Material.costo_defecto)
    - costo total lote (materiales + mano_obra_real + indirecto_real)
    - costo unitario resultante
    """
    detalles = lote.formula.detalles.select_related("material").all()
    cantidad = lote.cantidad_producida or Decimal("0.00")

    filas = []
    costo_materiales = Decimal("0.00")
    alertas = []

    for d in detalles:
        consumo_u = _consumo_material_por_unidad(d)  # por unidad
        consumo_total = (consumo_u * cantidad).quantize(Decimal("0.0001"))

        costo_mat = d.material.costo_defecto or Decimal("0.00")
        if costo_mat <= 0:
            alertas.append(f"Material sin costo_defecto: {d.material.nombre}")

        costo_total_mat = (consumo_total * costo_mat).quantize(Decimal("0.01"))
        costo_materiales += costo_total_mat

        filas.append({
            "material": d.material,
            "cantidad_por_unidad": d.cantidad_por_unidad,
            "merma_porcentaje": d.merma_porcentaje,
            "consumo_por_unidad_real": consumo_u.quantize(Decimal("0.0001")),
            "consumo_total": consumo_total,
            "costo_unitario_material": costo_mat.quantize(Decimal("0.01")),
            "costo_total_material": costo_total_mat,
        })

    costo_materiales = costo_materiales.quantize(Decimal("0.01"))
    mano_obra = (lote.costo_mano_obra_real or Decimal("0.00")).quantize(Decimal("0.01"))
    indirecto = (lote.costo_indirecto_real or Decimal("0.00")).quantize(Decimal("0.01"))
    costo_total_lote = (costo_materiales + mano_obra + indirecto).quantize(Decimal("0.01"))

    if cantidad and cantidad > 0:
        costo_unitario = (costo_total_lote / cantidad).quantize(Decimal("0.01"))
    else:
        costo_unitario = Decimal("0.00")

    return {
        "filas": filas,
        "costo_materiales": costo_materiales,
        "mano_obra": mano_obra,
        "indirecto": indirecto,
        "costo_total_lote": costo_total_lote,
        "costo_unitario": costo_unitario,
        "alertas": alertas,
    }


@login_required
def lista_lotes(request):
    q = (request.GET.get("q") or "").strip()
    estado = (request.GET.get("estado") or "").strip()

    lotes = (
        LoteProduccion.objects
        .select_related("formula", "formula__variante_producto", "formula__variante_producto__producto")
        .order_by("-fecha", "-creado")
    )

    if estado:
        lotes = lotes.filter(estado=estado)

    if q:
        lotes = lotes.filter(
            Q(formula__nombre__icontains=q) |
            Q(formula__variante_producto__sku__icontains=q) |
            Q(formula__variante_producto__nombre__icontains=q) |
            Q(formula__variante_producto__producto__nombre__icontains=q)
        )

    return render(request, "produccion/lotes_lista.html", {
        "lotes": lotes,
        "q": q,
        "estado": estado,
        "estados": LoteProduccion.Estado.choices,
    })


@login_required
def nuevo_lote(request):
    if request.method == "POST":
        form = LoteProduccionForm(request.POST)
        if form.is_valid():
            lote = form.save(commit=False)
            lote.estado = LoteProduccion.Estado.BORRADOR
            lote.save()
            messages.success(request, f"Lote #{lote.id} creado en BORRADOR.")
            return redirect("detalle_lote", lote_id=lote.id)
        messages.error(request, "Revisa los datos del formulario.")
    else:
        form = LoteProduccionForm(initial={"fecha": date.today()})

    return render(request, "produccion/lote_form.html", {"form": form, "modo": "nueva"})


@login_required
def detalle_lote(request, lote_id):
    lote = get_object_or_404(
        LoteProduccion.objects.select_related(
            "formula", "formula__variante_producto", "formula__variante_producto__producto"
        ),
        id=lote_id
    )

    costos = _calcular_costos_lote(lote)

    # Movimientos ya generados por este lote (si existen)
    movimientos = (
        MovimientoInventario.objects
        .select_related("item", "item__material", "item__variante_producto", "item__almacen", "item__variante_producto__producto")
        .filter(referencia="PRODUCCION", referencia_id=lote.id)
        .order_by("-creado")
    )

    return render(request, "produccion/lote_detalle.html", {
        "lote": lote,
        "costos": costos,
        "movimientos": movimientos,
    })


@require_POST
@login_required
def consumir_materiales_lote(request, lote_id):
    lote = get_object_or_404(LoteProduccion, id=lote_id)

    if lote.estado != LoteProduccion.Estado.BORRADOR:
        messages.error(request, "Solo puedes consumir materiales si el lote está en BORRADOR.")
        return redirect("detalle_lote", lote_id=lote.id)

    if lote.cantidad_producida <= 0:
        messages.error(request, "La cantidad producida debe ser mayor a 0.")
        return redirect("detalle_lote", lote_id=lote.id)

    almacen_principal = obtener_almacen_principal()

    # Calcular consumos
    costos = _calcular_costos_lote(lote)

    # Crear SALIDAS de materiales
    for fila in costos["filas"]:
        material = fila["material"]
        consumo_total = fila["consumo_total"]

        item, _ = ItemInventario.objects.get_or_create(
            almacen=almacen_principal,
            tipo=ItemInventario.TipoItem.MATERIAL,
            material=material,
            defaults={"punto_reorden": 0, "activo": True},
        )

        MovimientoInventario.objects.create(
            item=item,
            tipo=MovimientoInventario.TipoMovimiento.SALIDA,
            cantidad=consumo_total,
            costo_unitario=fila["costo_unitario_material"],  # referencia informativa
            referencia="PRODUCCION",
            referencia_id=lote.id,
            nota=f"Consumo por lote #{lote.id}",
        )

    lote.estado = LoteProduccion.Estado.CONSUMIDO
    lote.save(update_fields=["estado"])

    messages.success(request, "Materiales consumidos. Se registraron SALIDAS en inventario.")
    return redirect("detalle_lote", lote_id=lote.id)


@require_POST
@login_required
def finalizar_lote(request, lote_id):
    lote = get_object_or_404(LoteProduccion, id=lote_id)

    if lote.estado != LoteProduccion.Estado.CONSUMIDO:
        messages.error(request, "Para finalizar, primero debes consumir materiales (estado: Material consumido).")
        return redirect("detalle_lote", lote_id=lote.id)

    almacen_principal = obtener_almacen_principal()
    variante = lote.formula.variante_producto

    # Calcular costo unitario resultante (estimado)
    costos = _calcular_costos_lote(lote)
    costo_unitario = costos["costo_unitario"]

    # Crear ENTRADA de producto terminado
    item_producto, _ = ItemInventario.objects.get_or_create(
        almacen=almacen_principal,
        tipo=ItemInventario.TipoItem.PRODUCTO,
        variante_producto=variante,
        defaults={"punto_reorden": 0, "activo": True},
    )

    MovimientoInventario.objects.create(
        item=item_producto,
        tipo=MovimientoInventario.TipoMovimiento.ENTRADA,
        cantidad=lote.cantidad_producida,
        costo_unitario=costo_unitario,
        referencia="PRODUCCION",
        referencia_id=lote.id,
        nota=f"Entrada producto terminado por lote #{lote.id}",
    )

    lote.costo_unitario_resultado = costo_unitario
    lote.estado = LoteProduccion.Estado.FINALIZADO
    lote.save(update_fields=["costo_unitario_resultado", "estado"])

    messages.success(request, "Lote finalizado. Se registró la ENTRADA del producto terminado.")
    return redirect("detalle_lote", lote_id=lote.id)

# -------------------------
# Helpers pagos
# -------------------------
def _registrar_pago_entrada(cxc: CuentaPorCobrar, monto: Decimal, metodo: str, fecha_pago, nota: str):
    # Crea pago (entrada)
    Pago.objects.create(
        direccion=Pago.Direccion.ENTRADA,
        metodo=metodo or None,
        fecha=fecha_pago,
        monto=monto,
        cuenta_por_cobrar=cxc,
        nota=nota or None,
    )

    # Actualiza montos
    cxc.monto_pagado = (cxc.monto_pagado + monto).quantize(Decimal("0.01"))
    cxc.saldo = (cxc.monto_total - cxc.monto_pagado).quantize(Decimal("0.01"))
    if cxc.saldo <= 0:
        cxc.saldo = Decimal("0.00")
        cxc.estado = CuentaPorCobrar.Estado.CERRADA
    cxc.save(update_fields=["monto_pagado", "saldo", "estado"])


def _registrar_pago_salida_compra(cxp: CuentaPorPagarCompra, monto: Decimal, metodo: str, fecha_pago, nota: str):
    Pago.objects.create(
        direccion=Pago.Direccion.SALIDA,
        metodo=metodo or None,
        fecha=fecha_pago,
        monto=monto,
        cuenta_por_pagar_compra=cxp,
        nota=nota or None,
    )
    cxp.monto_pagado = (cxp.monto_pagado + monto).quantize(Decimal("0.01"))
    cxp.saldo = (cxp.monto_total - cxp.monto_pagado).quantize(Decimal("0.01"))
    if cxp.saldo <= 0:
        cxp.saldo = Decimal("0.00")
        cxp.estado = CuentaPorPagarCompra.Estado.CERRADA
    cxp.save(update_fields=["monto_pagado", "saldo", "estado"])


def _registrar_pago_salida_gasto(cxp: CuentaPorPagarGasto, monto: Decimal, metodo: str, fecha_pago, nota: str):
    Pago.objects.create(
        direccion=Pago.Direccion.SALIDA,
        metodo=metodo or None,
        fecha=fecha_pago,
        monto=monto,
        cuenta_por_pagar_gasto=cxp,
        nota=nota or None,
    )
    cxp.monto_pagado = (cxp.monto_pagado + monto).quantize(Decimal("0.01"))
    cxp.saldo = (cxp.monto_total - cxp.monto_pagado).quantize(Decimal("0.01"))
    if cxp.saldo <= 0:
        cxp.saldo = Decimal("0.00")
        cxp.estado = CuentaPorPagarGasto.Estado.CERRADA
    cxp.save(update_fields=["monto_pagado", "saldo", "estado"])


# -------------------------
# POR COBRAR
# -------------------------
@login_required
def lista_por_cobrar(request):
    q = (request.GET.get("q") or "").strip()
    estado = (request.GET.get("estado") or "").strip()  # ABIERTA/CERRADA/VENCIDA

    qs = (
        CuentaPorCobrar.objects
        .select_related("cliente", "venta")
        .order_by("-creada")
    )

    if estado:
        qs = qs.filter(estado=estado)

    if q:
        qs = qs.filter(
            Q(cliente__nombre__icontains=q) |
            Q(venta__id__icontains=q)
        )

    return render(request, "finanzas/por_cobrar_lista.html", {
        "cuentas": qs,
        "q": q,
        "estado": estado,
        "estados": CuentaPorCobrar.Estado.choices,
    })


@login_required
def cobrar_cxc(request, cxc_id):
    cxc = get_object_or_404(CuentaPorCobrar.objects.select_related("cliente", "venta"), id=cxc_id)

    if request.method == "POST":
        fecha_pago = request.POST.get("fecha") or str(date.today())
        metodo = request.POST.get("metodo", "").strip()
        nota = request.POST.get("nota", "").strip()
        monto_raw = (request.POST.get("monto") or "0").strip().replace(",", ".")

        try:
            monto = Decimal(monto_raw).quantize(Decimal("0.01"))
        except:
            messages.error(request, "Monto inválido.")
            return redirect("cobrar_cxc", cxc_id=cxc.id)

        if monto <= 0:
            messages.error(request, "El monto debe ser mayor a 0.")
            return redirect("cobrar_cxc", cxc_id=cxc.id)

        if monto > cxc.saldo:
            messages.error(request, "El monto no puede ser mayor que el saldo.")
            return redirect("cobrar_cxc", cxc_id=cxc.id)

        _registrar_pago_entrada(cxc, monto, metodo, fecha_pago, nota)
        messages.success(request, "Cobro registrado correctamente.")
        return redirect("lista_por_cobrar")

    return render(request, "finanzas/cobrar_form.html", {"cxc": cxc})


# -------------------------
# POR PAGAR COMPRAS
# -------------------------
@login_required
def lista_por_pagar_compras(request):
    q = (request.GET.get("q") or "").strip()
    estado = (request.GET.get("estado") or "").strip()

    qs = (
        CuentaPorPagarCompra.objects
        .select_related("proveedor", "compra")
        .order_by("-creada")
    )

    if estado:
        qs = qs.filter(estado=estado)

    if q:
        qs = qs.filter(
            Q(proveedor__nombre__icontains=q) |
            Q(compra__id__icontains=q)
        )

    return render(request, "finanzas/por_pagar_compras_lista.html", {
        "cuentas": qs,
        "q": q,
        "estado": estado,
        "estados": CuentaPorPagarCompra.Estado.choices,
    })


@login_required
def pagar_cxp_compra(request, cxp_id):
    cxp = get_object_or_404(CuentaPorPagarCompra.objects.select_related("proveedor", "compra"), id=cxp_id)

    if request.method == "POST":
        fecha_pago = request.POST.get("fecha") or str(date.today())
        metodo = request.POST.get("metodo", "").strip()
        nota = request.POST.get("nota", "").strip()
        monto_raw = (request.POST.get("monto") or "0").strip().replace(",", ".")

        try:
            monto = Decimal(monto_raw).quantize(Decimal("0.01"))
        except:
            messages.error(request, "Monto inválido.")
            return redirect("pagar_cxp_compra", cxp_id=cxp.id)

        if monto <= 0:
            messages.error(request, "El monto debe ser mayor a 0.")
            return redirect("pagar_cxp_compra", cxp_id=cxp.id)

        if monto > cxp.saldo:
            messages.error(request, "El monto no puede ser mayor que el saldo.")
            return redirect("pagar_cxp_compra", cxp_id=cxp.id)

        _registrar_pago_salida_compra(cxp, monto, metodo, fecha_pago, nota)
        messages.success(request, "Pago registrado correctamente.")
        return redirect("lista_por_pagar_compras")

    return render(request, "finanzas/pagar_compra_form.html", {"cxp": cxp})


# -------------------------
# POR PAGAR GASTOS
# -------------------------
@login_required
def lista_por_pagar_gastos(request):
    q = (request.GET.get("q") or "").strip()
    estado = (request.GET.get("estado") or "").strip()

    qs = (
        CuentaPorPagarGasto.objects
        .select_related("proveedor", "gasto")
        .order_by("-creada")
    )

    if estado:
        qs = qs.filter(estado=estado)

    if q:
        qs = qs.filter(
            Q(proveedor__nombre__icontains=q) |
            Q(gasto__id__icontains=q)
        )

    return render(request, "finanzas/por_pagar_gastos_lista.html", {
        "cuentas": qs,
        "q": q,
        "estado": estado,
        "estados": CuentaPorPagarGasto.Estado.choices,
    })


@login_required
def pagar_cxp_gasto(request, cxp_id):
    cxp = get_object_or_404(CuentaPorPagarGasto.objects.select_related("proveedor", "gasto"), id=cxp_id)

    if request.method == "POST":
        fecha_pago = request.POST.get("fecha") or str(date.today())
        metodo = request.POST.get("metodo", "").strip()
        nota = request.POST.get("nota", "").strip()
        monto_raw = (request.POST.get("monto") or "0").strip().replace(",", ".")

        try:
            monto = Decimal(monto_raw).quantize(Decimal("0.01"))
        except:
            messages.error(request, "Monto inválido.")
            return redirect("pagar_cxp_gasto", cxp_id=cxp.id)

        if monto <= 0:
            messages.error(request, "El monto debe ser mayor a 0.")
            return redirect("pagar_cxp_gasto", cxp_id=cxp.id)

        if monto > cxp.saldo:
            messages.error(request, "El monto no puede ser mayor que el saldo.")
            return redirect("pagar_cxp_gasto", cxp_id=cxp.id)

        _registrar_pago_salida_gasto(cxp, monto, metodo, fecha_pago, nota)
        messages.success(request, "Pago registrado correctamente.")
        return redirect("lista_por_pagar_gastos")

    return render(request, "finanzas/pagar_gasto_form.html", {"cxp": cxp})