import json
from decimal import Decimal
from datetime import date, timedelta, datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from django.db.models import Q
from .forms import ProductoForm, VarianteProductoForm, CategoriaProductoForm, CategoriaMaterialForm, MaterialForm, AlmacenForm
from .models import Producto, VarianteProducto, CategoriaProducto, Venta, Gasto, CuentaPorCobrar, CuentaPorPagarCompra, CuentaPorPagarGasto, MovimientoInventario, Almacen, CategoriaMaterial, Material, Almacen

from django.db.models import Sum


from .models import (
    Cliente,
    VarianteProducto,
    Venta,
    DetalleVenta,
    CategoriaGasto,
    Gasto,
)

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

        for variante, cantidad, precio_unitario, subtotal in detalles_a_crear:
            DetalleVenta.objects.create(
                venta=venta,
                variante_producto=variante,
                cantidad=cantidad,
                precio_unitario=precio_unitario,
                descuento=Decimal("0.00"),
                subtotal=subtotal,
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

    fi = request.GET.get("fi", "")
    ff = request.GET.get("ff", "")

    # Rango por defecto: últimos 30 días
    hoy = datetime.now().date()
    if not fi:
        fi_date = hoy - timedelta(days=30)
    else:
        try:
            fi_date = datetime.strptime(fi, "%Y-%m-%d").date()
        except:
            fi_date = hoy - timedelta(days=30)

    if not ff:
        ff_date = hoy
    else:
        try:
            ff_date = datetime.strptime(ff, "%Y-%m-%d").date()
        except:
            ff_date = hoy

    movimientos = (
        MovimientoInventario.objects
        .select_related(
            "item",
            "item__almacen",
            "item__material",
            "item__variante_producto",
            "item__variante_producto__producto",
        )
        .filter(creado__date__gte=fi_date, creado__date__lte=ff_date)
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
        "movimientos": movimientos[:300],  # límite visual para no cargar demasiado
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