from django.db import models
from django.urls import reverse
from django.contrib.auth.models import User
from decimal import Decimal
import os

def producto_imagen_path(instance, filename):
    """
    Genera una ruta única para la imagen del producto.
    Ejemplo: productos/2024/07/nombre-producto_12345.jpg
    """
    from datetime import datetime
    # Obtener extensión del archivo
    ext = filename.split('.')[-1]
    # Crear nombre único con timestamp
    new_filename = f"{instance.nombre.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}"
    # Ruta: productos/año/mes/
    return os.path.join('productos', 
                       str(datetime.now().year), 
                       str(datetime.now().month).zfill(2), 
                       new_filename)

class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    # Información básica
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    categoria = models.ForeignKey(
        Categoria, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='productos'
    )
    
    # ===== IMAGEN DEL PRODUCTO =====
    imagen = models.ImageField(
        upload_to=producto_imagen_path,
        blank=True,
        null=True,
        help_text="Imagen del producto (formatos: JPG, PNG, WebP)"
    )
    
    # Información de stock y precio
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad_existente = models.PositiveIntegerField(default=0)
    cantidad_minima = models.PositiveIntegerField(default=5, help_text="Cantidad mínima para alertar")
    
    # Campos para control de medicamentos
    requiere_receta = models.BooleanField(default=False)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    numero_lote = models.CharField(max_length=50, blank=True)
    
    # Para WhatsApp
    whatsapp_link = models.URLField(max_length=500, blank=True, help_text="Enlace directo de WhatsApp para este producto")
    
    # Metadatos
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['nombre']),
            models.Index(fields=['categoria']),
        ]

    def __str__(self):
        return f"{self.nombre} - ${self.precio}"

    def get_absolute_url(self):
        return reverse('productos:detalle', args=[self.pk])

    def esta_disponible(self):
        return self.activo and self.cantidad_existente > 0

    def tiene_stock_bajo(self):
        return self.cantidad_existente <= self.cantidad_minima

    def reducir_stock(self, cantidad):
        if self.cantidad_existente >= cantidad:
            self.cantidad_existente -= cantidad
            self.save()
            return True
        return False
    
    def get_imagen_url(self):
        """Retorna la URL de la imagen o una imagen por defecto"""
        if self.imagen:
            return self.imagen.url
        # Imagen por defecto (puedes crear una en media/default/)
        return '/media/default/producto-default.png'
    
    def get_imagen_html(self):
        """Retorna la etiqueta HTML de la imagen para el admin"""
        if self.imagen:
            return f'<img src="{self.imagen.url}" width="100" height="100" style="object-fit: cover; border-radius: 8px;" />'
        return '<span style="color: #999;">Sin imagen</span>'
    get_imagen_html.short_description = 'Imagen'
    get_imagen_html.allow_tags = True


class Venta(models.Model):
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, help_text="Administrador que registró la venta")
    
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    descuento = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    cliente_nombre = models.CharField(max_length=200, blank=True, help_text="Nombre del cliente")
    cliente_telefono = models.CharField(max_length=20, blank=True, help_text="Teléfono del cliente")
    observaciones = models.TextField(blank=True, help_text="Observaciones del pedido")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['fecha']),
        ]

    def __str__(self):
        return f"Venta #{self.id} - ${self.total} - {self.fecha.strftime('%d/%m/%Y %H:%M')}"

    def calcular_total(self):
        total = sum(item.subtotal for item in self.items.all())
        self.subtotal = total
        self.total = total - self.descuento
        self.save()
        return self.total

    def get_total_items(self):
        return sum(item.cantidad for item in self.items.all())


class VentaItem(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='items')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='ventas_items')
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Item de Venta"
        verbose_name_plural = "Items de Venta"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.producto.nombre} x {self.cantidad} - ${self.subtotal}"

    def save(self, *args, **kwargs):
        self.subtotal = self.precio_unitario * self.cantidad
        super().save(*args, **kwargs)
        self.producto.reducir_stock(self.cantidad)