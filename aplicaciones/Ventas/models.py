from django.db import models
from django.utils import timezone
import uuid
from decimal import Decimal
from django.core.validators import MinValueValidator


class BaseTiempo(models.Model):
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Cliente(BaseTiempo):
    nombres_apellidos = models.CharField(max_length=200)
    celular = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        db_index=True,
        help_text="Ej: +5939XXXXXXX (opcional)"
    )

    direccion = models.CharField(max_length=255, blank=True)
    correo = models.EmailField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombres_apellidos} ({self.celular})"


class Producto(BaseTiempo):
    nombre = models.CharField(max_length=200)

    codigo_barras = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="Código de barras (escáner o manual).",
    )

    precio = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    stock = models.PositiveIntegerField(default=0)


    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} [{self.codigo_barras}]"


class SerieFolio(BaseTiempo):
    """
    Control de folios/comprobantes.
    Ej: prefijo='VTA', siguiente_numero=1  -> VTA-000001, VTA-000002, etc.
    """
    nombre = models.CharField(max_length=60, default="Ventas")
    prefijo = models.CharField(max_length=10, default="VTA", db_index=True)
    relleno = models.PositiveSmallIntegerField(default=6, help_text="Ceros a la izquierda")
    siguiente_numero = models.PositiveIntegerField(default=1)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Serie de folio"
        verbose_name_plural = "Series de folios"

    def __str__(self):
        return f"{self.prefijo} (sig: {self.siguiente_numero})"

    def formatear(self, numero: int) -> str:
        return f"{self.prefijo}-{str(numero).zfill(self.relleno)}"


class Venta(BaseTiempo):
    class Estado(models.TextChoices):
        PAGADA = "PAGADA", "Pagada"
        ANULADA = "ANULADA", "Anulada"

    class TipoPago(models.TextChoices):
        CONTADO = "CONTADO", "Contado"
        FIADO = "FIADO", "Fiado (crédito)"

    class EstadoCobro(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        PARCIAL = "PARCIAL", "Parcial"
        COBRADO = "COBRADO", "Cobrado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Folio
    serie_folio = models.ForeignKey(SerieFolio, on_delete=models.PROTECT, related_name="ventas")
    numero_folio = models.PositiveIntegerField()
    comprobante = models.CharField(max_length=32, db_index=True)  # Ej: VTA-000001

    # Relación
    cliente = models.ForeignKey(
        Cliente, on_delete=models.SET_NULL, null=True, blank=True, related_name="ventas"
    )
    usuario = models.ForeignKey(
        "auth.User",
        on_delete=models.PROTECT,
        related_name="ventas",
        null=True,
        blank=True
    )


    # Estado general
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PAGADA)

    # Totales
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    iva = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    # Fiado / Cobros
    tipo_pago = models.CharField(max_length=10, choices=TipoPago.choices, default=TipoPago.CONTADO)
    fecha_vencimiento = models.DateField(null=True, blank=True, help_text="Si es FIADO, fecha máxima de pago.")

    estado_cobro = models.CharField(max_length=10, choices=EstadoCobro.choices, default=EstadoCobro.COBRADO)

    total_pagado = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    saldo = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    observaciones = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["serie_folio", "numero_folio"], name="uniq_serie_numero_folio"),
        ]

    def __str__(self):
        return f"{self.comprobante} - {self.total}"

    def recalcular_totales(self):
        items = self.items.all()
        subtotal = sum((i.subtotal_linea for i in items), Decimal("0.00"))
        iva = sum((i.iva_linea for i in items), Decimal("0.00"))
        total = (subtotal + iva).quantize(Decimal("0.01"))

        self.subtotal = subtotal.quantize(Decimal("0.01"))
        self.iva = iva.quantize(Decimal("0.01"))
        self.total = total
        return self

    def actualizar_saldo(self):
        pagado = self.total_pagado or Decimal("0.00")
        self.saldo = (self.total - pagado).quantize(Decimal("0.01"))

        if self.saldo <= Decimal("0.00"):
            self.estado_cobro = self.EstadoCobro.COBRADO
            self.saldo = Decimal("0.00")
        elif pagado > Decimal("0.00"):
            self.estado_cobro = self.EstadoCobro.PARCIAL
        else:
            self.estado_cobro = self.EstadoCobro.PENDIENTE

        return self


class DetalleVenta(BaseTiempo):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name="items")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name="detalles_venta")

    cantidad = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=Decimal("1.00"),
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    precio_unitario = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    porcentaje_iva = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=Decimal("0.00"),
        help_text="Ej: 12.00 para 12%",
    )

    @property
    def subtotal_linea(self) -> Decimal:
        return (self.cantidad * self.precio_unitario).quantize(Decimal("0.01"))

    @property
    def iva_linea(self) -> Decimal:
        return (self.subtotal_linea * (self.porcentaje_iva / Decimal("100.00"))).quantize(Decimal("0.01"))

    def __str__(self):
        return f"{self.producto.nombre} x {self.cantidad}"


class AbonoVenta(BaseTiempo):
    """Pagos parciales o totales de una venta FIADA."""
    class Metodo(models.TextChoices):
        EFECTIVO = "EFECTIVO", "Efectivo"
        TRANSFERENCIA = "TRANSFERENCIA", "Transferencia"
        TARJETA = "TARJETA", "Tarjeta"
        OTRO = "OTRO", "Otro"

    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name="abonos")

    monto = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    metodo = models.CharField(max_length=20, choices=Metodo.choices, default=Metodo.EFECTIVO)
    referencia = models.CharField(max_length=80, blank=True)
    nota = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"Abono {self.monto} a {self.venta.comprobante}"


class MensajeWhatsApp(BaseTiempo):
    """
    Registro/cola para:
    - Enviar comprobante de venta
    - Enviar recordatorios (por ejemplo, de FIADO próximo a vencer)
    Tu servicio/API luego leerá estos registros y los enviará.
    """
    class Tipo(models.TextChoices):
        COMPROBANTE = "COMPROBANTE", "Comprobante"
        RECORDATORIO = "RECORDATORIO", "Recordatorio"

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        ENVIADO = "ENVIADO", "Enviado"
        FALLIDO = "FALLIDO", "Fallido"

    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name="mensajes_whatsapp", null=True, blank=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True, related_name="mensajes_whatsapp")

    tipo = models.CharField(max_length=15, choices=Tipo.choices, default=Tipo.COMPROBANTE)
    destino_celular = models.CharField(max_length=20, db_index=True)

    texto = models.TextField(help_text="Contenido del mensaje (o plantilla).")

    programado_para = models.DateTimeField(
        null=True, blank=True,
        help_text="Si es recordatorio, cuándo enviarlo."
    )

    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)

    proveedor = models.CharField(max_length=20, default="meta", help_text="meta / twilio / otro")
    id_proveedor = models.CharField(max_length=128, blank=True)

    enviado_en = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)

    def __str__(self):
        return f"{self.tipo} -> {self.destino_celular} [{self.estado}]"

from django.conf import settings
class CajaCierre(models.Model):
    fecha = models.DateField(unique=True)  # solo 1 por día

    abierto_desde = models.DateTimeField()
    cerrado_en = models.DateTimeField()
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # Totales
    total_ventas_contado = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    total_abonos_fiado = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    total_ingresos = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))]
    )

    # Contadores
    num_ventas_contado = models.PositiveIntegerField(default=0)
    num_abonos_fiado = models.PositiveIntegerField(default=0)

    nota = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"Cierre {self.fecha} - ${self.total_ingresos}"