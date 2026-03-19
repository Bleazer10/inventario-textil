import json
from decimal import Decimal
from datetime import date, timedelta, datetime, time

from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required
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
    AjusteInventarioForm,
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
    CuentaPorPagarGasto,

    # Inventario
    CategoriaMaterial,
    Material,
    Almacen,
    ItemInventario,
    MovimientoInventario,
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
            cantidad = Decimal(str(it.get("cantidad", "0")))

            if not variante_id or cantidad <= 0:
                continue

            variante = get_object_or_404(VarianteProducto, id=variante_id)
            precio_unitario = Decimal(str(variante.precio_venta_efectivo))
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
            # Solo descuenta si el producto controla inventario
            if not variante.producto.controla_inventario:
                continue

            # Crear o buscar ItemInventario del producto terminado en el almacén Principal
            item, _ = ItemInventario.objects.get_or_create(
                almacen=almacen_principal,
                tipo=ItemInventario.TipoItem.PRODUCTO,
                variante_producto=variante,
                defaults={"punto_reorden": 0, "activo": True},
            )

            # Registrar salida por venta
            MovimientoInventario.objects.create(
                item=item,
                tipo=MovimientoInventario.TipoMovimiento.SALIDA,
                cantidad=cantidad,
                costo_unitario=None,
                referencia="VENTA",
                referencia_id=venta.id,
                nota="Salida automática por venta",
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
            monto_dec = Decimal(monto).quantize(Decimal("0.01"))
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
        # lunes a domingo
        fecha_inicio = hoy - timedelta(days=hoy.weekday())
        fecha_fin = fecha_inicio + timedelta(days=6)
    elif filtro == "mes":
        fecha_inicio = hoy.replace(day=1)
        # fin de mes
        if fecha_inicio.month == 12:
            fecha_fin = fecha_inicio.replace(year=fecha_inicio.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            fecha_fin = fecha_inicio.replace(month=fecha_inicio.month + 1, day=1) - timedelta(days=1)
    else:
        # rango personalizado
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
    )
    ventas_total = ventas_qs.aggregate(s=Sum("total"))["s"] or Decimal("0.00")

    # Gastos en rango (todos)
    gastos_qs = Gasto.objects.filter(
        fecha__gte=fecha_inicio,
        fecha__lte=fecha_fin,
    )
    gastos_total = gastos_qs.aggregate(s=Sum("monto"))["s"] or Decimal("0.00")

    balance = (ventas_total - gastos_total).quantize(Decimal("0.01"))

    # Por cobrar / Por pagar (saldo)
    por_cobrar_total = (CuentaPorCobrar.objects.filter(estado=CuentaPorCobrar.Estado.ABIERTA)
                        .aggregate(s=Sum("saldo"))["s"] or Decimal("0.00"))

    por_pagar_compras_total = (CuentaPorPagarCompra.objects.filter(estado=CuentaPorPagarCompra.Estado.ABIERTA)
                              .aggregate(s=Sum("saldo"))["s"] or Decimal("0.00"))

    por_pagar_gastos_total = (CuentaPorPagarGasto.objects.filter(estado=CuentaPorPagarGasto.Estado.ABIERTA)
                             .aggregate(s=Sum("saldo"))["s"] or Decimal("0.00"))

    por_pagar_total = (por_pagar_compras_total + por_pagar_gastos_total).quantize(Decimal("0.01"))

    # Listas para pestañas (últimos registros del rango)
    ventas_lista = ventas_qs.order_by("-fecha", "-id")[:20]
    gastos_lista = gastos_qs.order_by("-fecha", "-id")[:20]

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