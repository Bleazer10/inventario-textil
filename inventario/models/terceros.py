from django.db import models


class Cliente(models.Model):
    nombre = models.CharField("Nombre", max_length=150)
    telefono = models.CharField("Teléfono", max_length=30, blank=True, null=True)
    email = models.EmailField("Email", blank=True, null=True)
    notas = models.TextField("Notas", blank=True, null=True)

    activo = models.BooleanField("Activo", default=True)

    creado = models.DateTimeField("Creado", auto_now_add=True)
    actualizado = models.DateTimeField("Actualizado", auto_now=True)

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["nombre"]
        indexes = [
            models.Index(fields=["nombre"]),
            models.Index(fields=["activo"]),
        ]

    def __str__(self) -> str:
        return self.nombre


class Proveedor(models.Model):
    nombre = models.CharField("Nombre", max_length=150)
    telefono = models.CharField("Teléfono", max_length=30, blank=True, null=True)
    email = models.EmailField("Email", blank=True, null=True)
    notas = models.TextField("Notas", blank=True, null=True)

    activo = models.BooleanField("Activo", default=True)

    creado = models.DateTimeField("Creado", auto_now_add=True)
    actualizado = models.DateTimeField("Actualizado", auto_now=True)

    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        ordering = ["nombre"]
        indexes = [
            models.Index(fields=["nombre"]),
            models.Index(fields=["activo"]),
        ]

    def __str__(self) -> str:
        return self.nombre