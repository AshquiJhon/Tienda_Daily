from django.shortcuts import redirect,render
from decimal import Decimal
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

from .models import Producto, Cliente
from .models import Producto, Cliente, Venta, DetalleVenta, SerieFolio, AbonoVenta, CajaCierre
from django.contrib.auth.decorators import login_required
from django.db.models.functions import TruncDate
#importando la libreria para mensajes de confirmacion
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, time
# Vista principal
@login_required
def index(request):
    hoy = timezone.localdate()

    inicio = datetime.combine(hoy, time.min)
    fin = datetime.combine(hoy, time.max)

    ventas_hoy = Venta.objects.filter(
        creado_en__range=(inicio, fin),
        estado=Venta.Estado.PAGADA  # opcional pero recomendado
    )

    total_ventas_hoy = ventas_hoy.aggregate(total=Sum('total'))['total'] or 0
    num_ventas_hoy = ventas_hoy.count()
    total_clientes = Cliente.objects.count()

    ventas_recientes = Venta.objects.order_by('-creado_en')[:5]

    productos_top = (
        DetalleVenta.objects
        .values('producto__nombre')
        .annotate(total=Sum('cantidad'))
        .order_by('-total')[:9]
    )
    cierres = CajaCierre.objects.order_by('-fecha')[:7]  # últimos 7 cierres
    cierres = list(reversed(cierres))

    labels = []
    data = []

    for c in cierres:
        labels.append(c.fecha.strftime('%d/%m'))
        data.append(float(c.total_ingresos))

    context = {
        'total_ventas_hoy': total_ventas_hoy,
        'num_ventas_hoy': num_ventas_hoy,
        'total_clientes': total_clientes,
        'ventas_recientes': ventas_recientes,
        'productos_top': productos_top,
        'labels': labels,
        'data': data,
    }

    return render(request, 'index.html', context)
@login_required
def productos_lista(request):
    productos = Producto.objects.all().order_by("-id")
    return render(request, "productos/lista.html", {"productos": productos})

@login_required
def producto_crear(request):
    return render(request, "productos/crear.html")


def producto_guardar(request):
    if request.method != "POST":
        return redirect("productos_lista")

    codigo = request.POST.get("txt_codigo", "").strip()
    nombre = request.POST.get("txt_nombre", "").strip()
    precio = request.POST.get("txt_precio", "0").strip()
    stock = request.POST.get("txt_cantidad", "0").strip()
    activo = True if request.POST.get("chk_activo") == "1" else False

    # Validaciones mínimas
    if not codigo or not nombre:
        messages.error(request, "❌ Código y nombre son obligatorios.")
        return redirect("producto_crear")

    # Evitar duplicados por código de barras
    producto_existente = Producto.objects.filter(codigo_barras=codigo).first()

    if producto_existente:
        if not producto_existente.activo:
            # 🔥 REACTIVAR Y ACTUALIZAR
            producto_existente.activo = True
            producto_existente.nombre = nombre
            producto_existente.precio = precio
            producto_existente.stock = stock
            producto_existente.save()

            messages.success(request, "🔄 Producto reactivado y actualizado correctamente.")
            return redirect("productos_lista")

        else:
            # 🔴 YA EXISTE ACTIVO
            messages.error(request, "❌ Ya existe un producto activo con ese código.")
            return redirect("producto_crear")

    try:
        precio = Decimal(precio)
        stock = Decimal(stock)
    except:
        messages.error(request, "❌ Precio/Stock inválidos.")
        return redirect("producto_crear")

    Producto.objects.create(
        codigo_barras=codigo,
        nombre=nombre,
        precio=precio,
        stock=stock,
        activo=activo,
    )

    messages.success(request, "✅ Producto guardado correctamente.")
    return redirect("productos_lista")

@login_required
def producto_editar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    return render(request, "productos/editar.html", {"producto": producto})


def producto_actualizar(request, pk):
    if request.method != "POST":
        return redirect("productos_lista")

    producto = get_object_or_404(Producto, pk=pk)

    codigo = request.POST.get("txt_codigo", "").strip()
    nombre = request.POST.get("txt_nombre", "").strip()
    precio = request.POST.get("txt_precio", "0").strip()
    stock = request.POST.get("txt_cantidad", "0").strip()
    activo = True if request.POST.get("chk_activo") == "1" else False

    if not codigo or not nombre:
        messages.error(request, "❌ Código y nombre son obligatorios.")
        return redirect("producto_editar", pk=pk)

    # Si cambia el código, validar que no exista en otro producto
    if Producto.objects.filter(codigo_barras=codigo).exclude(pk=pk).exists():
        messages.error(request, "❌ Ese código ya está usado por otro producto.")
        return redirect("producto_editar", pk=pk)

    try:
        producto.precio = Decimal(precio)
        producto.stock = Decimal(stock)
    except:
        messages.error(request, "❌ Precio/Stock inválidos.")
        return redirect("producto_editar", pk=pk)

    producto.codigo_barras = codigo
    producto.nombre = nombre
    producto.activo = activo
    producto.save()

    messages.success(request, "✅ Producto actualizado.")
    return redirect("productos_lista")


def producto_eliminar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)

    if request.method == "POST":
        # 🔥 en vez de eliminar → desactivar
        producto.activo = False
        producto.save()

        messages.success(request, "Producto eliminado correctamente.")
    
    return redirect("productos_lista")

def producto_restaurar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)

    if request.method == "POST":
        producto.activo = True
        producto.save()

        messages.success(request, "Producto restaurado correctamente.")

    return redirect("productos_lista")

@login_required
def clientes_lista(request):
    clientes = Cliente.objects.order_by("-id")
    return render(request, "clientes/lista.html", {"clientes": clientes})

@login_required
def cliente_crear(request):
    return render(request, "clientes/crear.html")


def cliente_guardar(request):
    if request.method != "POST":
        return redirect("clientes_lista")

    nombres = (request.POST.get("txt_nombres") or "").strip()
    celular = (request.POST.get("txt_celular") or "").strip()
    direccion = (request.POST.get("txt_direccion") or "").strip()
    correo = (request.POST.get("txt_correo") or "").strip()
    activo = True if request.POST.get("chk_activo") == "1" else False

    # Obligatorio: nombres
    if not nombres:
        messages.error(request, "Faltan datos: nombres es obligatorio.")
        return redirect("cliente_crear")

    # Celular opcional: si viene, evitar duplicado
    if celular and Cliente.objects.filter(celular=celular).exists():
        messages.error(request, "Ya existe un cliente con ese número de celular.")
        return redirect("cliente_crear")

    Cliente.objects.create(
        nombres_apellidos=nombres,
        celular=celular if celular else None,
        direccion=direccion,
        correo=correo if correo else None,
        activo=activo
    )

    messages.success(request, "Cliente registrado correctamente.")
    return redirect("clientes_lista")

@login_required
def cliente_editar(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    return render(request, "clientes/editar.html", {"cliente": cliente})


def cliente_actualizar(request, pk):
    if request.method != "POST":
        return redirect("clientes_lista")

    cliente = get_object_or_404(Cliente, pk=pk)

    nombres = (request.POST.get("txt_nombres") or "").strip()
    celular = (request.POST.get("txt_celular") or "").strip()
    direccion = (request.POST.get("txt_direccion") or "").strip()
    correo = (request.POST.get("txt_correo") or "").strip()
    activo = True if request.POST.get("chk_activo") == "1" else False

    if not nombres:
        messages.error(request, "Faltan datos: nombres es obligatorio.")
        return redirect("cliente_editar", pk=pk)

    # Celular opcional: si viene, evitar duplicado (excepto este mismo)
    if celular and Cliente.objects.filter(celular=celular).exclude(pk=pk).exists():
        messages.error(request, "Ya existe otro cliente con ese número de celular.")
        return redirect("cliente_editar", pk=pk)

    cliente.nombres_apellidos = nombres
    cliente.celular = celular if celular else None
    cliente.direccion = direccion
    cliente.correo = correo if correo else None
    cliente.activo = activo
    cliente.save()

    messages.success(request, "Cliente actualizado correctamente.")
    return redirect("clientes_lista")


#def cliente_eliminar(request, pk):
    #if request.method != "POST":
    #    return redirect("clientes_lista")

    #cliente = get_object_or_404(Cliente, pk=pk)
    #cliente.delete()

    #messages.success(request, "Cliente eliminado correctamente.")
    #return redirect("clientes_lista")

def cliente_eliminar(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)

    if request.method == "POST":
        cliente.activo = False  # 🔥 DESACTIVA
        cliente.save()

        messages.success(request, "Cliente desactivado correctamente.")

    return redirect("clientes_lista")
def cliente_restaurar(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)

    if request.method == "POST":
        cliente.activo = True
        cliente.save()

        messages.success(request, "Cliente restaurado correctamente.")

    return redirect("clientes_lista")




from django.db import transaction
@login_required
def venta_nueva(request):
    clientes = Cliente.objects.filter(activo=True).order_by("nombres_apellidos")
    return render(request, "ventas/nueva.html", {"clientes": clientes})

@login_required
def buscar_producto_codigo(request):
    # endpoint AJAX: /ventas/buscar-producto/?codigo=123
    codigo = (request.GET.get("codigo") or "").strip()
    if not codigo:
        return JsonResponse({"ok": False, "msg": "Código vacío"})

    try:
        p = Producto.objects.get(codigo_barras=codigo, activo=True)
    except Producto.DoesNotExist:
        return JsonResponse({"ok": False, "msg": "Producto no encontrado o inactivo"})

    return JsonResponse({
        "ok": True,
        "producto": {
            "id": p.id,
            "nombre": p.nombre,
            "codigo": p.codigo_barras,
            "precio": str(p.precio),
            "stock": float(p.stock),
        }
    })


from decimal import Decimal
from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect
from django.utils import timezone
from .models import Venta, DetalleVenta, Producto, Cliente, SerieFolio

@transaction.atomic
def venta_guardar(request):
    if request.method != "POST":
        return redirect("venta_nueva")

    prod_ids = request.POST.getlist("prod_id[]")
    cants = request.POST.getlist("cant[]")

    tipo_pago = request.POST.get("tipo_pago", "CONTADO")
    cliente_id = request.POST.get("cliente_id") or None
    fecha_venc = request.POST.get("fecha_vencimiento") or None

    if not prod_ids:
        messages.warning(request, "Agrega al menos 1 producto.")
        return redirect("venta_nueva")

    if tipo_pago == "FIADO" and not cliente_id:
        messages.warning(request, "Selecciona un cliente para ventas FIADAS.")
        return redirect("venta_nueva")

    # Bloqueo de productos para evitar ventas simultáneas que rompan stock
    productos = (
        Producto.objects
        .select_for_update()
        .filter(id__in=prod_ids, activo=True)
    )
    prod_map = {str(p.id): p for p in productos}

    # Validación stock
    carrito = []
    for pid, cant in zip(prod_ids, cants):
        try:
            cant_int = int(cant)
        except:
            cant_int = 0

        if cant_int < 1:
            messages.warning(request, "Cantidad inválida.")
            return redirect("venta_nueva")

        p = prod_map.get(str(pid))
        if not p:
            messages.warning(request, "Producto no encontrado o inactivo.")
            return redirect("venta_nueva")

        stock_actual = int(p.stock)
        if cant_int > stock_actual:
            messages.warning(request, f"Stock insuficiente para {p.nombre}. Disponible: {stock_actual}")
            return redirect("venta_nueva")

        carrito.append((p, cant_int))

    # Folio (simple)
    serie = SerieFolio.objects.filter(activo=True).first()
    if not serie:
        serie = SerieFolio.objects.create(prefijo="VTA", siguiente_numero=1, activo=True)

    numero = serie.siguiente_numero
    comprobante = serie.formatear(numero)
    serie.siguiente_numero = numero + 1
    serie.save()

    cliente = None
    if cliente_id:
        cliente = Cliente.objects.filter(id=cliente_id).first()

    venta = Venta.objects.create(
        serie_folio=serie,
        numero_folio=numero,
        comprobante=comprobante,
        cliente=cliente,
        usuario=request.user if request.user.is_authenticated else None,
        tipo_pago=tipo_pago,
        fecha_vencimiento=fecha_venc,
        estado=Venta.Estado.PAGADA,  # luego puedes manejar ANULADA
        total_pagado=Decimal("0.00"),
        saldo=Decimal("0.00"),
        estado_cobro=Venta.EstadoCobro.PENDIENTE if tipo_pago == "FIADO" else Venta.EstadoCobro.COBRADO,
    )

    # Crear detalles + descontar stock
    subtotal = Decimal("0.00")
    for p, cant_int in carrito:
        precio = Decimal(str(p.precio))  # precio oficial del producto
        sub = (precio * Decimal(cant_int)).quantize(Decimal("0.01"))
        subtotal += sub

        DetalleVenta.objects.create(
            venta=venta,
            producto=p,
            cantidad=Decimal(cant_int),
            precio_unitario=precio,
            porcentaje_iva=Decimal("0.00"),
        )

        # DESCONTAR STOCK
        p.stock = Decimal(int(p.stock) - cant_int)
        p.save()

    venta.subtotal = subtotal
    venta.iva = Decimal("0.00")
    venta.total = subtotal

    if tipo_pago == "CONTADO":
        venta.total_pagado = venta.total
        venta.saldo = Decimal("0.00")
        venta.estado_cobro = Venta.EstadoCobro.COBRADO
    else:
        venta.total_pagado = Decimal("0.00")
        venta.saldo = venta.total
        venta.estado_cobro = Venta.EstadoCobro.PENDIENTE

    venta.save()

    messages.success(request, f"Venta guardada: {venta.comprobante}")
    return redirect("venta_nueva")


from django.db.models import Q
from django.utils import timezone
from django.core.paginator import Paginator
@login_required
def ventas_lista(request):
    hoy = timezone.localdate()

    q = (request.GET.get("q") or "").strip()
    fecha = request.GET.get("fecha")
    cobro = (request.GET.get("cobro") or "TODOS").strip()

    ventas = Venta.objects.select_related("cliente", "usuario").order_by("-creado_en")

    # Filtro fecha
    if fecha:
        ventas = ventas.filter(creado_en__date=fecha)

    # Buscar
    if q:
        ventas = ventas.filter(
            Q(comprobante__icontains=q) |
            Q(cliente__nombres_apellidos__icontains=q) |
            Q(cliente__celular__icontains=q)
        )

    # Cobro
    if cobro == "FIADOS":
        ventas = ventas.filter(tipo_pago=Venta.TipoPago.FIADO)
    elif cobro == "CONTADO":
        ventas = ventas.filter(tipo_pago=Venta.TipoPago.CONTADO)
    elif cobro in ["PENDIENTE", "PARCIAL", "COBRADO"]:
        ventas = ventas.filter(
            tipo_pago=Venta.TipoPago.FIADO,
            estado_cobro=cobro
        )

    # 🔥 PAGINACIÓN
    paginator = Paginator(ventas, 10)  # 10 por página
    page_number = request.GET.get("page")
    ventas_page = paginator.get_page(page_number)

    return render(request, "ventas/lista.html", {
        "ventas": ventas_page,
        "q": q,
        "fecha": fecha,
        "cobro": cobro,
        "today": hoy
    })
@login_required
def venta_detalle(request, pk):
    venta = (
        Venta.objects
        .select_related("cliente", "usuario")
        .prefetch_related("items__producto", "abonos")
        .get(pk=pk)
    )
    return render(request, "ventas/detalle.html", {"venta": venta})
from django.db.models import Q
from django.http import JsonResponse
from .models import Producto

def buscar_productos(request):
    q = (request.GET.get("q") or "").strip()

    if len(q) < 2:
        return JsonResponse({"ok": True, "results": []})

    productos = (
        Producto.objects
        .filter(activo=True)
        .filter(Q(nombre__icontains=q) | Q(codigo_barras__icontains=q))
        .order_by("nombre")[:10]
    )

    results = []
    for p in productos:
        results.append({
            "id": p.id,
            "nombre": p.nombre,
            "codigo": p.codigo_barras,
            "precio": str(p.precio),
            "stock": float(p.stock),
        })

    return JsonResponse({"ok": True, "results": results})

@login_required
def fiados_lista(request):
    fiados = (Venta.objects
              .select_related("cliente")
              .filter(tipo_pago=Venta.TipoPago.FIADO)
              .exclude(estado_cobro=Venta.EstadoCobro.COBRADO)
              .order_by("-creado_en"))
    return render(request, "fiados/lista.html", {"fiados": fiados})
@login_required
def pagados_lista(request):
    pagados = (Venta.objects
               .select_related("cliente")
               .filter(tipo_pago=Venta.TipoPago.FIADO, estado_cobro=Venta.EstadoCobro.COBRADO)
               .order_by("-creado_en"))
    return render(request, "pagados/lista.html", {"pagados": pagados})
from django.db import transaction
@transaction.atomic
def fiado_abonar(request, venta_id):
    venta = (Venta.objects
             .select_for_update()
             .get(id=venta_id))

    if venta.tipo_pago != Venta.TipoPago.FIADO:
        messages.warning(request, "Esta venta no es FIADO.")
        return redirect("fiados_lista")

    if request.method == "POST":
        monto_txt = (request.POST.get("monto") or "").strip()
        try:
            monto = Decimal(monto_txt)
        except:
            monto = Decimal("0.00")

        if monto <= 0:
            messages.warning(request, "Monto inválido.")
            return redirect("fiado_detalle", venta_id=venta.id)

        # No permitir pagar más de lo que debe
        if monto > venta.saldo:
            messages.warning(request, f"No puedes abonar más de la deuda. Saldo: {venta.saldo}")
            return redirect("fiado_detalle", venta_id=venta.id)

        AbonoVenta.objects.create(
            venta=venta,
            monto=monto,
            metodo=request.POST.get("metodo", AbonoVenta.Metodo.EFECTIVO),
            referencia=(request.POST.get("referencia") or "").strip(),
            nota=(request.POST.get("nota") or "").strip(),
        )

        venta.total_pagado = (venta.total_pagado + monto)
        venta.actualizar_saldo()   # tu método del model ✅
        venta.save()

        messages.success(request, "Abono registrado.")
        return redirect("fiado_detalle", venta_id=venta.id)

    return redirect("fiado_detalle", venta_id=venta.id)

from django.db.models import Q, Sum, Count, Max
from django.db.models.functions import Coalesce
def deuda_por_cliente(request):
   
    q = (request.GET.get("q") or "").strip()
    estado = (request.GET.get("estado") or "con_deuda").strip()  # con_deuda | al_dia | todos
    desde = request.GET.get("desde") or ""
    hasta = request.GET.get("hasta") or ""

    # clientes + anotaciones
    qs = (Cliente.objects
          .annotate(
              deuda_total=Coalesce(
                  Sum(
                      "ventas__saldo",
                      filter=Q(ventas__tipo_pago=Venta.TipoPago.FIADO) &
                             ~Q(ventas__estado_cobro=Venta.EstadoCobro.COBRADO)
                  ),
                  Decimal("0.00")
              ),
              fiados_abiertos=Coalesce(
                  Count(
                      "ventas",
                      filter=Q(ventas__tipo_pago=Venta.TipoPago.FIADO) &
                             ~Q(ventas__estado_cobro=Venta.EstadoCobro.COBRADO)
                  ),
                  0
              ),
              ultimo_fiado=Max(
                  "ventas__creado_en",
                  filter=Q(ventas__tipo_pago=Venta.TipoPago.FIADO)
              )
          ))

    # filtro texto
    if q:
        qs = qs.filter(
            Q(nombres_apellidos__icontains=q) |
            Q(celular__icontains=q)
        )

    # filtro por estado
    if estado == "con_deuda":
        qs = qs.filter(deuda_total__gt=0)
    elif estado == "al_dia":
        qs = qs.filter(deuda_total=0)

    # filtros por fecha (basado en fecha de ventas FIADO)
    # OJO: esto filtra clientes que tuvieron fiados en el rango
    if desde:
        qs = qs.filter(ventas__tipo_pago=Venta.TipoPago.FIADO, ventas__creado_en__date__gte=desde)
    if hasta:
        qs = qs.filter(ventas__tipo_pago=Venta.TipoPago.FIADO, ventas__creado_en__date__lte=hasta)

    qs = qs.distinct().order_by("-deuda_total", "nombres_apellidos")

    return render(request, "fiados/clientes_lista.html", {
        "clientes": qs,
        "f": {"q": q, "estado": estado, "desde": desde, "hasta": hasta},
    })

@login_required
def deuda_cliente_detalle(request, cliente_id):
    """
    Detalle del cliente:
    - lista sus ventas FIADO (abiertas y cerradas)
    - muestra deuda actual (sum saldo abierto)
    """
    cliente = get_object_or_404(Cliente, id=cliente_id)

    ventas = (Venta.objects
              .select_related("cliente")
              .filter(cliente=cliente, tipo_pago=Venta.TipoPago.FIADO)
              .order_by("-creado_en"))

    deuda_actual = (ventas
                    .exclude(estado_cobro=Venta.EstadoCobro.COBRADO)
                    .aggregate(x=Coalesce(Sum("saldo"), Decimal("0.00")))["x"])

    return render(request, "fiados/cliente_detalle.html", {
        "cliente": cliente,
        "ventas": ventas,
        "deuda_actual": deuda_actual
    })


def fiado_abonar(request, venta_id):

    venta = Venta.objects.get(id=venta_id)

    if venta.tipo_pago != Venta.TipoPago.FIADO:
        messages.warning(request, "Esta venta no es FIADO.")
        return redirect("deuda_por_cliente")

    if request.method == "POST":
        monto_txt = (request.POST.get("monto") or "").strip()

        try:
            monto = Decimal(monto_txt)
        except:
            monto = Decimal("0.00")

        if monto <= 0:
            messages.warning(request, "Monto inválido.")
            return redirect("deuda_por_cliente")

        if monto > venta.saldo:
            messages.warning(request, f"No puedes abonar más de la deuda. Saldo: {venta.saldo}")
            return redirect("deuda_por_cliente")

        AbonoVenta.objects.create(
            venta=venta,
            monto=monto,
            metodo=request.POST.get("metodo", AbonoVenta.Metodo.EFECTIVO),
            referencia=(request.POST.get("referencia") or "").strip(),
            nota=(request.POST.get("nota") or "").strip(),
        )

        venta.total_pagado += monto
        venta.actualizar_saldo()
        venta.save()

        messages.success(request, "✅ Abono registrado correctamente.")

        # 🔥 AQUÍ EL CAMBIO CLAVE
        return redirect("deuda_por_cliente")

    return redirect("deuda_por_cliente")
def comprobante_publico(request, pk):
    venta = get_object_or_404(Venta, pk=pk)
    return render(request, "ventas/comprobante_publico.html", {"venta": venta})



@login_required
def resumen_caja(request):
    hoy = timezone.localdate()

    cierre_hoy = CajaCierre.objects.filter(fecha=hoy).first()

    # calcular "desde" = último cierre o inicio de hoy
    ultimo = CajaCierre.objects.order_by("-cerrado_en").first()
    ahora = timezone.now()

    if ultimo:
        desde = ultimo.cerrado_en
    else:
        lt = timezone.localtime(ahora)
        desde = lt.replace(hour=0, minute=0, second=0, microsecond=0)

    # si ya cerraste hoy, muestra ese cierre
    if cierre_hoy:
        return render(request, "caja/resumen.html", {
            "cierre": cierre_hoy,
            "ya_cerrado": True,
        })

    # PREVIEW (lo que se cerrará si presionas cerrar)
    ventas_contado_qs = (
        Venta.objects
        .filter(creado_en__gte=desde, creado_en__lt=ahora, tipo_pago=Venta.TipoPago.CONTADO)
        .exclude(estado=Venta.Estado.ANULADA)
    )
    abonos_qs = (
        AbonoVenta.objects
        .filter(creado_en__gte=desde, creado_en__lt=ahora, venta__tipo_pago=Venta.TipoPago.FIADO)
        .exclude(venta__estado=Venta.Estado.ANULADA)
    )

    total_contado = ventas_contado_qs.aggregate(x=Sum("total"))["x"] or Decimal("0.00")
    total_abonos = abonos_qs.aggregate(x=Sum("monto"))["x"] or Decimal("0.00")

    ctx = {
        "ya_cerrado": False,
        "desde": desde,
        "hasta": ahora,
        "total_contado": total_contado,
        "total_abonos": total_abonos,
        "total_ingresos": (total_contado + total_abonos).quantize(Decimal("0.01")),
        "num_ventas_contado": ventas_contado_qs.count(),
        "num_abonos_fiado": abonos_qs.count(),
    }
    return render(request, "caja/resumen.html", ctx)
from openpyxl import Workbook
from django.http import HttpResponse
from django.utils import timezone
from django.shortcuts import redirect
from django.contrib import messages
from django.db import transaction
from decimal import Decimal
from django.db.models import Sum

from .models import Venta, AbonoVenta, CajaCierre


# 🔥 GENERAR EXCEL PARA DESCARGA
def generar_backup_fiados_response():
    from .models import Venta

    fiados = Venta.objects.filter(
        tipo_pago="FIADO",
        estado_cobro__in=["PENDIENTE", "PARCIAL"]
    )

    resumen = {}

    for v in fiados:
        if v.cliente:
            nombre = v.cliente.nombres_apellidos
            deuda = float(v.saldo)  # 🔥 AQUÍ EL CAMBIO
            resumen[nombre] = resumen.get(nombre, 0) + deuda

    wb = Workbook()
    ws = wb.active
    ws.title = "Fiados"

    ws.append(["Cliente", "Total Deuda"])

    for cliente, total in resumen.items():
        ws.append([cliente, total])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    fecha = timezone.now().strftime("%Y-%m-%d_%H-%M-%S")
    nombre_archivo = f"fiados_{fecha}.xlsx"

    response["Content-Disposition"] = f'attachment; filename="{nombre_archivo}"'

    wb.save(response)

    return response
# 🔥 VIEW PARA DESCARGAR
def descargar_backup_fiados(request):
    return generar_backup_fiados_response()


# 🔥 CIERRE DE CAJA
@login_required
@transaction.atomic
def caja_cerrar(request):
    if request.method != "POST":
        return redirect("resumen_caja")

    hoy = timezone.localdate()
    ahora = timezone.now()

    # Evitar doble cierre
    if CajaCierre.objects.filter(fecha=hoy).exists():
        messages.warning(request, "Ya se realizó el cierre de caja de hoy.")
        return redirect("resumen_caja")

    ultimo = CajaCierre.objects.order_by("-cerrado_en").first()
    if ultimo:
        desde = ultimo.cerrado_en
    else:
        lt = timezone.localtime(ahora)
        desde = lt.replace(hour=0, minute=0, second=0, microsecond=0)

    ventas_contado_qs = (
        Venta.objects
        .filter(creado_en__gte=desde, creado_en__lt=ahora, tipo_pago=Venta.TipoPago.CONTADO)
        .exclude(estado=Venta.Estado.ANULADA)
    )

    abonos_qs = (
        AbonoVenta.objects
        .filter(creado_en__gte=desde, creado_en__lt=ahora, venta__tipo_pago=Venta.TipoPago.FIADO)
        .exclude(venta__estado=Venta.Estado.ANULADA)
    )

    total_contado = ventas_contado_qs.aggregate(x=Sum("total"))["x"] or Decimal("0.00")
    total_abonos = abonos_qs.aggregate(x=Sum("monto"))["x"] or Decimal("0.00")

    cierre = CajaCierre.objects.create(
        fecha=hoy,
        abierto_desde=desde,
        cerrado_en=ahora,
        usuario=request.user if request.user.is_authenticated else None,
        total_ventas_contado=total_contado,
        total_abonos_fiado=total_abonos,
        total_ingresos=(total_contado + total_abonos).quantize(Decimal("0.01")),
        num_ventas_contado=ventas_contado_qs.count(),
        num_abonos_fiado=abonos_qs.count(),
        nota=(request.POST.get("nota") or "").strip()
    )

    messages.success(
        request,
        f"✅ Cierre realizado.\n💰 Total: ${cierre.total_ingresos}"
    )
    return redirect(f"/caja/{cierre.id}/?descargar=1")
@login_required
def caja_historial(request):
    cierres = CajaCierre.objects.order_by("-cerrado_en")[:200]
    return render(request, "caja/historial.html", {"cierres": cierres})
@login_required
@login_required
def caja_detalle(request, pk):
    cierre = CajaCierre.objects.get(pk=pk)

    return render(request, "caja/detalle.html", {
        "cierre": cierre
    })
@login_required
def caja_exportar_excel(request, id):
    cierre = get_object_or_404(CajaCierre, id=id)
    
    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = f'attachment; filename="caja_{id}.xlsx"'

    # generar excel aquí...

    return response

