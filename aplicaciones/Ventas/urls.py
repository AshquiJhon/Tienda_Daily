from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
urlpatterns=[
   # Vista principal
   path("", views.index, name="index"),  # (opcional) para que base.html use 'inicio'

   # PRODUCTOS
   path("productos/", views.productos_lista, name="productos_lista"),
   path("productos/nuevo/", views.producto_crear, name="producto_crear"),
   path("productos/guardar/", views.producto_guardar, name="producto_guardar"),
   path("productos/<int:pk>/editar/", views.producto_editar, name="producto_editar"),
   path("productos/<int:pk>/actualizar/", views.producto_actualizar, name="producto_actualizar"),
   path("productos/<int:pk>/eliminar/", views.producto_eliminar, name="producto_eliminar"),
   path("productos/<int:pk>/restaurar/", views.producto_restaurar, name="producto_restaurar"),
   # CLIENTES
   path("clientes/", views.clientes_lista, name="clientes_lista"),
   path("clientes/nuevo/", views.cliente_crear, name="cliente_crear"),
   path("clientes/guardar/", views.cliente_guardar, name="cliente_guardar"),
   path("clientes/<int:pk>/editar/", views.cliente_editar, name="cliente_editar"),
   path("clientes/<int:pk>/actualizar/", views.cliente_actualizar, name="cliente_actualizar"),
   #path("clientes/<int:pk>/eliminar/", views.cliente_eliminar, name="cliente_eliminar"),
   path("clientes/<int:pk>/eliminar/", views.cliente_eliminar, name="cliente_eliminar"),
   path("clientes/<int:pk>/restaurar/", views.cliente_restaurar, name="cliente_restaurar"),
   # VENTAS (POS)
   path("ventas/nuevo/", views.venta_nueva, name="venta_nueva"),
   path("ventas/buscar-producto/", views.buscar_producto_codigo, name="buscar_producto_codigo"),

   path("ventas/guardar/", views.venta_guardar, name="venta_guardar"),

   path("ventas/buscar-productos/", views.buscar_productos, name="buscar_productos"),

   path("ventas/", views.ventas_lista, name="ventas_lista"),
   path("ventas/<uuid:pk>/detalle/", views.venta_detalle, name="venta_detalle"),



    path("fiados/", views.fiados_lista, name="fiados_lista"),
    path("pagados/", views.pagados_lista, name="pagados_lista"),

    path("fiados/clientes/", views.deuda_por_cliente, name="deuda_por_cliente"),
    path("fiados/clientes/<int:cliente_id>/", views.deuda_cliente_detalle, name="deuda_cliente_detalle"),

    # --- ABONAR A UNA VENTA FIADA ---
    path("fiados/<uuid:venta_id>/abonar/", views.fiado_abonar, name="fiado_abonar"),

    path("comprobantes/<uuid:pk>/", views.comprobante_publico, name="comprobante_publico"),
   path("resumen_caja/", views.resumen_caja, name="resumen_caja"),
   path("caja/historial/", views.caja_historial, name="caja_historial"),
   path("caja/<int:id>/excel/", views.caja_exportar_excel, name="caja_exportar_excel"),
   path("caja/<int:pk>/", views.caja_detalle, name="caja_detalle"),
   path("caja/cerrar/", views.caja_cerrar, name="caja_cerrar"),
   path("caja/backup-fiados/", views.descargar_backup_fiados, name="backup_fiados"),
   
   path('login/', auth_views.LoginView.as_view(template_name='login/login.html'), name='login'),

   path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

]