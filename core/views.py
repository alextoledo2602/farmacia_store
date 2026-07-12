from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum, Count, Q, F
from products.models import Producto, Categoria, Venta, VentaItem
from datetime import datetime, timedelta
from decimal import Decimal
import json


def home(request):
    productos_destacados = Producto.objects.filter(
        activo=True, 
        cantidad_existente__gt=0
    )[:12]
    
    categorias = Categoria.objects.all()
    
    context = {
        'productos': productos_destacados,
        'categorias': categorias,
        'titulo': 'Bienvenido a la Farmacia Online'
    }
    return render(request, 'pages/home.html', context)


def listar_productos(request):
    productos = Producto.objects.filter(activo=True)
    
    categoria_id = request.GET.get('categoria')
    if categoria_id:
        productos = productos.filter(categoria_id=categoria_id)
    
    q = request.GET.get('q')
    if q:
        productos = productos.filter(nombre__icontains=q)
    
    context = {
        'productos': productos,
        'categorias': Categoria.objects.all()
    }
    return render(request, 'pages/productos_lista.html', context)


# ===== CARRITO DE COMPRAS =====
def ver_carrito(request):
    carrito = request.session.get('carrito', [])
    
    productos_carrito = []
    total = 0
    
    for item in carrito:
        producto = get_object_or_404(Producto, id=item['producto_id'])
        subtotal = producto.precio * item['cantidad']
        total += subtotal
        productos_carrito.append({
            'producto': producto,
            'cantidad': item['cantidad'],
            'subtotal': subtotal
        })
    
    context = {
        'productos_carrito': productos_carrito,
        'total': total,
        'total_items': sum(item['cantidad'] for item in carrito)
    }
    return render(request, 'pages/carrito.html', context)


def agregar_al_carrito(request):
    if request.method == 'POST':
        producto_id = request.POST.get('producto_id')
        cantidad = int(request.POST.get('cantidad', 1))
        
        producto = get_object_or_404(Producto, id=producto_id, activo=True)
        
        if producto.cantidad_existente < cantidad:
            return JsonResponse({
                'success': False,
                'error': f'Stock insuficiente. Disponible: {producto.cantidad_existente}'
            })
        
        carrito = request.session.get('carrito', [])
        
        encontrado = False
        for item in carrito:
            if item['producto_id'] == producto_id:
                if producto.cantidad_existente < (item['cantidad'] + cantidad):
                    return JsonResponse({
                        'success': False,
                        'error': f'Stock insuficiente. Disponible: {producto.cantidad_existente}'
                    })
                item['cantidad'] += cantidad
                encontrado = True
                break
        
        if not encontrado:
            carrito.append({
                'producto_id': producto_id,
                'cantidad': cantidad
            })
        
        request.session['carrito'] = carrito
        request.session.modified = True
        
        total_items = sum(item['cantidad'] for item in carrito)
        
        return JsonResponse({
            'success': True,
            'message': f'{producto.nombre} agregado al carrito',
            'total_items': total_items
        })
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)


def eliminar_del_carrito(request):
    if request.method == 'POST':
        producto_id = request.POST.get('producto_id')
        
        carrito = request.session.get('carrito', [])
        carrito = [item for item in carrito if item['producto_id'] != producto_id]
        
        request.session['carrito'] = carrito
        request.session.modified = True
        
        total_items = sum(item['cantidad'] for item in carrito)
        
        return JsonResponse({
            'success': True,
            'total_items': total_items
        })
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)


def actualizar_cantidad(request):
    if request.method == 'POST':
        producto_id = request.POST.get('producto_id')
        cantidad = int(request.POST.get('cantidad', 1))
        
        if cantidad <= 0:
            return eliminar_del_carrito(request)
        
        producto = get_object_or_404(Producto, id=producto_id)
        
        if producto.cantidad_existente < cantidad:
            return JsonResponse({
                'success': False,
                'error': f'Stock insuficiente. Disponible: {producto.cantidad_existente}'
            })
        
        carrito = request.session.get('carrito', [])
        
        for item in carrito:
            if item['producto_id'] == producto_id:
                item['cantidad'] = cantidad
                break
        
        request.session['carrito'] = carrito
        request.session.modified = True
        
        total = 0
        for item in carrito:
            prod = get_object_or_404(Producto, id=item['producto_id'])
            total += prod.precio * item['cantidad']
        
        return JsonResponse({
            'success': True,
            'total': float(total),
            'total_items': sum(item['cantidad'] for item in carrito)
        })
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)


def vaciar_carrito(request):
    if request.method == 'POST':
        request.session['carrito'] = []
        request.session.modified = True
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)


def enviar_pedido_whatsapp(request):
    if request.method == 'POST':
        carrito = request.session.get('carrito', [])
        
        if not carrito:
            return JsonResponse({'success': False, 'error': 'El carrito está vacío'})
        
        cliente_nombre = request.POST.get('cliente_nombre', 'Cliente')
        cliente_telefono = request.POST.get('cliente_telefono', '')
        
        mensaje = f"🛒 *Nuevo Pedido - Farmacia Cienfuegos*\n\n"
        mensaje += f"👤 *Cliente:* {cliente_nombre}\n"
        mensaje += f"📱 *Teléfono:* {cliente_telefono}\n"
        mensaje += f"📅 *Fecha:* {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
        mensaje += "*📋 Productos:*\n"
        
        total = 0
        for item in carrito:
            producto = get_object_or_404(Producto, id=item['producto_id'])
            subtotal = producto.precio * item['cantidad']
            total += subtotal
            mensaje += f"  • {producto.nombre} x {item['cantidad']} = ${subtotal:.2f}\n"
        
        mensaje += f"\n💰 *Total: ${total:.2f}*"
        
        numero_admin = "5491123456789"
        
        from urllib.parse import quote
        mensaje_codificado = quote(mensaje)
        url_whatsapp = f"https://wa.me/{numero_admin}?text={mensaje_codificado}"
        
        request.session['pedido_pendiente'] = {
            'cliente_nombre': cliente_nombre,
            'cliente_telefono': cliente_telefono,
            'productos': carrito,
            'total': float(total)
        }
        request.session.modified = True
        
        return JsonResponse({
            'success': True,
            'whatsapp_url': url_whatsapp
        })
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)


# ===== DASHBOARD =====
@staff_member_required
def dashboard_view(request):
    hoy = datetime.now().date()
    inicio_mes = hoy.replace(day=1)
    
    # ===== MÉTRICAS DE PRODUCTOS =====
    total_productos = Producto.objects.count()
    productos_activos = Producto.objects.filter(activo=True).count()
    productos_sin_stock = Producto.objects.filter(cantidad_existente=0, activo=True).count()
    productos_stock_bajo = Producto.objects.filter(
        cantidad_existente__gt=0,
        cantidad_existente__lte=F('cantidad_minima'),
        activo=True
    ).count()
    productos_por_vencer = Producto.objects.filter(
        fecha_vencimiento__isnull=False,
        fecha_vencimiento__lte=hoy + timedelta(days=30),
        fecha_vencimiento__gte=hoy
    ).count()
    
    # ===== MÉTRICAS DE VENTAS =====
    ventas_hoy = Venta.objects.filter(fecha__date=hoy)
    total_ventas_hoy = ventas_hoy.count()
    monto_ventas_hoy = ventas_hoy.aggregate(Sum('total'))['total__sum'] or Decimal('0')
    items_vendidos_hoy = VentaItem.objects.filter(
        venta__fecha__date=hoy
    ).aggregate(Sum('cantidad'))['cantidad__sum'] or 0
    
    ventas_mes = Venta.objects.filter(fecha__date__gte=inicio_mes, fecha__date__lte=hoy)
    total_ventas_mes = ventas_mes.count()
    monto_ventas_mes = ventas_mes.aggregate(Sum('total'))['total__sum'] or Decimal('0')
    
    # ===== GRÁFICOS - PRODUCTOS POR CATEGORÍA =====
    categorias_labels = []
    categorias_data = []
    for categoria in Categoria.objects.annotate(total=Count('productos')).filter(total__gt=0):
        categorias_labels.append(categoria.nombre)
        categorias_data.append(categoria.total)
    
    # ===== GRÁFICOS - STOCK POR CATEGORÍA =====
    stock_labels = []
    stock_data = []
    for categoria in Categoria.objects.annotate(total_stock=Sum('productos__cantidad_existente')).filter(total_stock__gt=0):
        stock_labels.append(categoria.nombre)
        stock_data.append(categoria.total_stock)
    
    # ===== GRÁFICOS - PRODUCTOS POR MES =====
    meses_labels = []
    meses_data = []
    for i in range(5, -1, -1):
        fecha = hoy - timedelta(days=30*i)
        mes_inicio = fecha.replace(day=1)
        if i == 0:
            mes_fin = hoy
        else:
            mes_fin = (mes_inicio + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        meses_labels.append(mes_inicio.strftime('%b %Y'))
        count = Producto.objects.filter(
            created_at__date__gte=mes_inicio,
            created_at__date__lte=mes_fin
        ).count()
        meses_data.append(count)
    
    # ===== GRÁFICOS - ESTADO DEL STOCK =====
    alertas_data = [
        productos_sin_stock,
        productos_stock_bajo,
        Producto.objects.filter(activo=True, cantidad_existente__gt=F('cantidad_minima')).count()
    ]
    alertas_labels = ['Sin Stock', 'Stock Bajo', 'Stock Normal']
    alertas_colors = ['#e74c3c', '#f39c12', '#2ecc71']
    
    # ===== TABLAS =====
    categorias_top = Categoria.objects.annotate(
        total_productos=Count('productos')
    ).filter(total_productos__gt=0).order_by('-total_productos')[:5]
    
    ultimos_productos = Producto.objects.filter(activo=True).order_by('-created_at')[:10]
    
    # ===== VENTAS POR DÍA (últimos 7 días) =====
    dias_labels = []
    dias_ventas = []
    dias_montos = []
    
    for i in range(6, -1, -1):
        fecha = hoy - timedelta(days=i)
        ventas_dia = Venta.objects.filter(fecha__date=fecha)
        dias_labels.append(fecha.strftime('%d/%m'))
        dias_ventas.append(ventas_dia.count())
        monto = ventas_dia.aggregate(Sum('total'))['total__sum'] or Decimal('0')
        dias_montos.append(float(monto))
    
    # ===== VENTAS POR MES (últimos 6 meses) =====
    meses_ventas_labels = []
    meses_ventas_data = []
    meses_ventas_montos = []
    
    for i in range(5, -1, -1):
        fecha = hoy - timedelta(days=30*i)
        mes_inicio = fecha.replace(day=1)
        if i == 0:
            mes_fin = hoy
        else:
            mes_fin = (mes_inicio + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        ventas_mes_periodo = Venta.objects.filter(fecha__date__gte=mes_inicio, fecha__date__lte=mes_fin)
        meses_ventas_labels.append(mes_inicio.strftime('%b %Y'))
        meses_ventas_data.append(ventas_mes_periodo.count())
        monto = ventas_mes_periodo.aggregate(Sum('total'))['total__sum'] or Decimal('0')
        meses_ventas_montos.append(float(monto))
    
    # ===== PRODUCTOS MÁS VENDIDOS =====
    productos_top = VentaItem.objects.values('producto__nombre').annotate(
        total_vendido=Sum('cantidad'),
        total_ingresos=Sum('subtotal')
    ).order_by('-total_vendido')[:5]
    
    # ===== ÚLTIMAS VENTAS =====
    ultimas_ventas = Venta.objects.order_by('-fecha')[:10]
    
    context = {
        # Métricas de productos
        'total_productos': total_productos,
        'productos_activos': productos_activos,
        'productos_sin_stock': productos_sin_stock,
        'productos_stock_bajo': productos_stock_bajo,
        'productos_por_vencer': productos_por_vencer,
        
        # Métricas de ventas
        'total_ventas_hoy': total_ventas_hoy,
        'monto_ventas_hoy': float(monto_ventas_hoy),
        'items_vendidos_hoy': items_vendidos_hoy,
        'total_ventas_mes': total_ventas_mes,
        'monto_ventas_mes': float(monto_ventas_mes),
        
        # Datos para gráficos de productos
        'categorias_labels': json.dumps(categorias_labels),
        'categorias_data': json.dumps(categorias_data),
        'stock_labels': json.dumps(stock_labels),
        'stock_data': json.dumps(stock_data),
        'meses_labels': json.dumps(meses_labels),
        'meses_data': json.dumps(meses_data),
        'alertas_labels': json.dumps(alertas_labels),
        'alertas_data': json.dumps(alertas_data),
        'alertas_colors': json.dumps(alertas_colors),
        
        # Datos para gráficos de ventas
        'dias_labels': json.dumps(dias_labels),
        'dias_ventas': json.dumps(dias_ventas),
        'dias_montos': json.dumps(dias_montos),
        'meses_ventas_labels': json.dumps(meses_ventas_labels),
        'meses_ventas_data': json.dumps(meses_ventas_data),
        'meses_ventas_montos': json.dumps(meses_ventas_montos),
        
        # Tablas
        'categorias_top': categorias_top,
        'ultimos_productos': ultimos_productos,
        'productos_top': productos_top,
        'ultimas_ventas': ultimas_ventas,
    }
    
    return render(request, 'dashboard/dashboard.html', context)


@staff_member_required
def registrar_venta(request):
    if request.method == 'POST':
        productos_ids = request.POST.getlist('productos[]')
        cantidades = request.POST.getlist('cantidades[]')
        cliente_nombre = request.POST.get('cliente_nombre', '')
        cliente_telefono = request.POST.get('cliente_telefono', '')
        observaciones = request.POST.get('observaciones', '')
        
        if not productos_ids or not cantidades:
            return JsonResponse({'error': 'Debe seleccionar al menos un producto'}, status=400)
        
        venta = Venta.objects.create(
            usuario=request.user,
            cliente_nombre=cliente_nombre,
            cliente_telefono=cliente_telefono,
            observaciones=observaciones
        )
        
        total_venta = Decimal('0')
        items_creados = []
        errores = []
        
        for producto_id, cantidad_str in zip(productos_ids, cantidades):
            if not cantidad_str or int(cantidad_str) <= 0:
                continue
                
            cantidad = int(cantidad_str)
            producto = get_object_or_404(Producto, id=producto_id)
            
            if producto.cantidad_existente < cantidad:
                errores.append(f"Stock insuficiente para {producto.nombre}. Disponible: {producto.cantidad_existente}")
                continue
            
            item = VentaItem.objects.create(
                venta=venta,
                producto=producto,
                cantidad=cantidad,
                precio_unitario=producto.precio
            )
            
            items_creados.append({
                'producto': producto.nombre,
                'cantidad': cantidad,
                'subtotal': float(item.subtotal)
            })
            total_venta += item.subtotal
        
        venta.total = total_venta
        venta.subtotal = total_venta
        venta.save()
        
        if errores:
            return JsonResponse({
                'success': True,
                'venta_id': venta.id,
                'total': float(total_venta),
                'items': items_creados,
                'errores': errores,
                'mensaje': 'Venta registrada con advertencias'
            })
        
        return JsonResponse({
            'success': True,
            'venta_id': venta.id,
            'total': float(total_venta),
            'items': items_creados,
            'mensaje': 'Venta registrada exitosamente'
        })
    
    productos = Producto.objects.filter(activo=True, cantidad_existente__gt=0).order_by('nombre')
    context = {
        'productos': productos,
    }
    return render(request, 'dashboard/registrar_venta.html', context)


@staff_member_required
def buscar_productos(request):
    term = request.GET.get('term', '')
    productos = Producto.objects.filter(
        activo=True,
        cantidad_existente__gt=0
    ).filter(
        Q(nombre__icontains=term) | 
        Q(categoria__nombre__icontains=term)
    )[:20]
    
    resultados = [{
        'id': p.id,
        'nombre': p.nombre,
        'precio': float(p.precio),
        'stock': p.cantidad_existente,
        'categoria': p.categoria.nombre if p.categoria else 'Sin categoría'
    } for p in productos]
    
    return JsonResponse(resultados, safe=False)