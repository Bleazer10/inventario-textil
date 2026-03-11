from django import forms
from .models import CategoriaProducto, Producto, VarianteProducto, CategoriaMaterial, Material, Almacen, ItemInventario

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

class ItemInventarioForm(forms.ModelForm):
    class Meta:
        model = ItemInventario
        fields = ["almacen", "tipo", "material", "variante_producto", "punto_reorden", "activo"]

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get("tipo")
        material = cleaned.get("material")
        variante = cleaned.get("variante_producto")

        if tipo == "MATERIAL":
            if not material:
                raise forms.ValidationError("Si el tipo es MATERIAL, debes seleccionar un material.")
            if variante:
                raise forms.ValidationError("Si el tipo es MATERIAL, no debes seleccionar una variante de producto.")

        if tipo == "PRODUCTO":
            if not variante:
                raise forms.ValidationError("Si el tipo es PRODUCTO, debes seleccionar una variante de producto.")
            if material:
                raise forms.ValidationError("Si el tipo es PRODUCTO, no debes seleccionar un material.")

        return cleaned