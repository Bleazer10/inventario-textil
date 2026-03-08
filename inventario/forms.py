from django import forms
from .models import CategoriaProducto, Producto, VarianteProducto

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ["categoria", "nombre", "descripcion", "precio_venta_defecto", "controla_inventario", "activo"]
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 3}),
        }

class VarianteProductoForm(forms.ModelForm):
    class Meta:
        model = VarianteProducto
        fields = ["sku", "nombre", "precio_venta", "modo_costo", "costo_unitario_fijo", "activa"]

class CategoriaProductoForm(forms.ModelForm):
    class Meta:
        model = CategoriaProducto
        fields = ["nombre", "activa"]