from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import Categoria, Producto, Venta, VentaItem

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'created_at']
    search_fields = ['nombre']
    

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = [
        'imagen_preview', 'nombre', 'precio', 'cantidad_existente', 
        'categoria', 'activo', 'stock_status'
    ]
    list_display_links = ['nombre']
    list_filter = ['activo', 'requiere_receta', 'categoria']
    search_fields = ['nombre', 'descripcion']
    readonly_fields = ['created_at', 'updated_at', 'imagen_preview']
    
    fieldsets = (
        ('Información Principal', {
            'fields': ('nombre', 'descripcion', 'categoria', 'imagen', 'imagen_preview')
        }),
        ('Precio y Stock', {
            'fields': ('precio', 'cantidad_existente', 'cantidad_minima')
        }),
        ('Control de Medicamentos', {
            'fields': ('requiere_receta', 'fecha_vencimiento', 'numero_lote')
        }),
        ('WhatsApp', {
            'fields': ('whatsapp_link',),
            'classes': ('collapse',),
        }),
        ('Estado y Metadatos', {
            'fields': ('activo', 'created_at', 'updated_at')
        })
    )
    
    def imagen_preview(self, obj):
        """Muestra una vista previa de la imagen en el admin"""
        if obj.imagen:
            return mark_safe(
                f'<img src="{obj.imagen.url}" width="80" height="80" '
                f'style="object-fit: cover; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);" />'
            )
        return mark_safe(
            '<div style="width: 80px; height: 80px; background: #f0f0f0; '
            'border-radius: 8px; display: flex; align-items: center; justify-content: center; '
            'font-size: 0.8rem; color: #999;">Sin imagen</div>'
        )
    imagen_preview.short_description = 'Imagen'
    
    def stock_status(self, obj):
        """Muestra el estado del stock con colores - Usando mark_safe"""
        if obj.cantidad_existente == 0:
            return mark_safe('<span style="color: red; font-weight: bold;">Sin Stock</span>')
        elif obj.cantidad_existente <= obj.cantidad_minima:
            return mark_safe(
                f'<span style="color: orange; font-weight: bold;">Stock Bajo ({obj.cantidad_existente})</span>'
            )
        else:
            return mark_safe(
                f'<span style="color: green;">Disponible ({obj.cantidad_existente})</span>'
            )
    stock_status.short_description = 'Estado Stock'


class VentaItemInline(admin.TabularInline):
    """Inline para agregar items en la venta"""
    model = VentaItem
    extra = 1
    autocomplete_fields = ['producto']
    fields = ['producto', 'cantidad', 'precio_unitario', 'subtotal']
    readonly_fields = ['subtotal']


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ['id', 'fecha_formateada', 'cliente_nombre', 'cliente_telefono', 'total_items', 'total']
    list_filter = ['fecha']
    search_fields = ['id', 'cliente_nombre', 'cliente_telefono']
    readonly_fields = ['subtotal', 'total', 'created_at', 'updated_at']
    inlines = [VentaItemInline]
    list_per_page = 20
    date_hierarchy = 'fecha'
    
    fieldsets = (
        ('Información de la Venta', {
            'fields': ('usuario', 'cliente_nombre', 'cliente_telefono', 'observaciones')
        }),
        ('Totales', {
            'fields': ('subtotal', 'descuento', 'total')
        }),
        ('Metadatos', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def fecha_formateada(self, obj):
        return obj.fecha.strftime('%d/%m/%Y %H:%M')
    fecha_formateada.short_description = 'Fecha'
    fecha_formateada.admin_order_field = 'fecha'
    
    def total_items(self, obj):
        return obj.get_total_items()
    total_items.short_description = 'Items'
    
    def save_model(self, request, obj, form, change):
        if not obj.usuario:
            obj.usuario = request.user
        super().save_model(request, obj, form, change)
        obj.calcular_total()
    
    def save_formset(self, request, form, formset, change):
        super().save_formset(request, form, formset, change)
        form.instance.calcular_total()


@admin.register(VentaItem)
class VentaItemAdmin(admin.ModelAdmin):
    list_display = ['venta', 'producto', 'cantidad', 'precio_unitario', 'subtotal']
    list_filter = ['venta__fecha']
    search_fields = ['producto__nombre', 'venta__id']
    readonly_fields = ['subtotal']