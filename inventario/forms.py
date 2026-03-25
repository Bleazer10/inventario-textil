from django import forms
from .models import CategoriaProducto, Producto, VarianteProducto, CategoriaMaterial, Material, Almacen, ItemInventario, Cliente, Proveedor, DetalleFormula, Formula, LoteProduccion

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
    
class AjusteInventarioForm(forms.Form):
    item = forms.ModelChoiceField(
        label="Ítem",
        queryset=ItemInventario.objects.select_related(
            "almacen", "material", "variante_producto", "variante_producto__producto"
        ).filter(activo=True).order_by("almacen__nombre"),
        required=True
    )

    tipo = forms.ChoiceField(
        label="Tipo",
        choices=[
            ("ENTRADA", "Entrada"),
            ("AJUSTE", "Ajuste"),
        ],
        required=True
    )

    cantidad = forms.DecimalField(label="Cantidad", max_digits=12, decimal_places=2, required=True)
    costo_unitario = forms.DecimalField(label="Costo unitario (opcional)", max_digits=12, decimal_places=2, required=False)
    nota = forms.CharField(label="Nota (opcional)", required=False, widget=forms.Textarea(attrs={"rows": 2}))

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ["nombre", "telefono", "email", "notas", "activo"]

class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ["nombre", "telefono", "email", "notas", "activo"]

class FormulaForm(forms.ModelForm):
    class Meta:
        model = Formula
        fields = [
            "variante_producto",
            "nombre",
            "activa",
            "costo_mano_obra_unitario",
            "costo_indirecto_unitario",
        ]

class DetalleFormulaForm(forms.ModelForm):
    class Meta:
        model = DetalleFormula
        fields = [
            "material",
            "cantidad_por_unidad",
            "merma_porcentaje",
        ]

class LoteProduccionForm(forms.ModelForm):
    class Meta:
        model = LoteProduccion
        fields = [
            "formula",
            "fecha",
            "cantidad_producida",
            "costo_mano_obra_real",
            "costo_indirecto_real",
            "notas",
        ]