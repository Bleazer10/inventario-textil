from django.urls import path
from inventario.reportes import views_reportes as vr

urlpatterns = [
    path("ventas/", vr.reporte_ventas, name="reporte_ventas"),
    path("ventas/pdf/", vr.reporte_ventas_pdf, name="reporte_ventas_pdf"),
    path("ventas/excel/", vr.reporte_ventas_excel, name="reporte_ventas_excel"),
    path("ventas/<int:venta_id>/pdf/", vr.reporte_venta_factura_pdf, name="reporte_venta_factura_pdf"),
    path("ventas/<int:venta_id>/excel/", vr.reporte_venta_factura_excel, name="reporte_venta_factura_excel"),
]