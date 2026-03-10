from django import forms
from .models import CategoriaProducto, Producto, VarianteProducto, CategoriaMaterial, Material, Almacen

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

class CategoriaMaterialForm(forms.ModelForm):
    class Meta:
        model = CategoriaMaterial
        fields = ["nombre", "activa"]

class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = ["categoria", "nombre", "unidad", "costo_defecto", "activo"]

class AlmacenForm(forms.ModelForm):
    class Meta:
        model = Almacen
        fields = ["nombre", "activo"]