from django.contrib import admin
from django.utils.html import format_html
from .models import Categoria, Producto, Venta, VentaItem

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'created_at']
    search_fields = ['nombre']
    

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = [
        'nombre', 'precio', 'cantidad_existente', 
        'categoria', 'activo', 'requiere_receta', 'stock_status'
    ]
    list_filter = ['activo', 'requiere_receta', 'categoria']
    search_fields = ['nombre', 'descripcion']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Información Principal', {
            'fields': ('nombre', 'descripcion', 'categoria')
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
            'description': 'Enlace personalizado de WhatsApp para este producto'
        }),
        ('Estado y Metadatos', {
            'fields': ('activo', 'created_at', 'updated_at')
        })
    )
    
    def stock_status(self, obj):
        if obj.cantidad_existente == 0:
            return format_html('<span style="color: red; font-weight: bold;">Sin Stock</span>')
        elif obj.cantidad_existente <= obj.cantidad_minima:
            return format_html('<span style="color: orange; font-weight: bold;">Stock Bajo ({})</span>', obj.cantidad_existente)
        else:
            return format_html('<span style="color: green;">Disponible ({})</span>', obj.cantidad_existente)
    stock_status.short_description = 'Estado Stock'


class VentaItemInline(admin.TabularInline):
    model = VentaItem
    extra = 1
    autocomplete_fields = ['producto']
    fields = ['producto', 'cantidad', 'precio_unitario', 'subtotal']
    readonly_fields = ['subtotal']
    can_delete = True


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