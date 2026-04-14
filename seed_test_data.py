from app import app, db
from models import Venta, Servicio, Inventario
from datetime import datetime

# 🔹 Activar el contexto de aplicación
with app.app_context():
    # Crear base de datos limpia
    db.drop_all()
    db.create_all()

    # Inventario de prueba
    inventario_items = [
        Inventario(nombre="Aceite Motul", categoria="Lubricante", cantidad=10, stock_maximo=20,
                   precio_unitario=370, costo_unitario=250),
        Inventario(nombre="Filtro de aire", categoria="Motor", cantidad=5, stock_maximo=15,
                   precio_unitario=120, costo_unitario=80),
        Inventario(nombre="Bujía NGK", categoria="Encendido", cantidad=8, stock_maximo=20,
                   precio_unitario=90, costo_unitario=50)
    ]

    # Servicios de prueba
    servicios_items = [
        Servicio(tipo="Motor", nombre="Cambio de aceite", importe=300),
        Servicio(tipo="Suspensión", nombre="Ajuste de amortiguadores", importe=450),
        Servicio(tipo="Dirección", nombre="Alineación", importe=250)
    ]

    # 🔹 Ventas de prueba (una semana: lunes a viernes)
    ventas_items = [
        Venta(fecha=datetime(2026, 4, 13), descripcion="Cambio de aceite", tipo="servicio", cantidad_vendida=1, monto=300),
        Venta(fecha=datetime(2026, 4, 13), descripcion="Aceite Motul", tipo="refaccion", cantidad_vendida=2, monto=370),

        Venta(fecha=datetime(2026, 4, 14), descripcion="Filtro de aire", tipo="refaccion", cantidad_vendida=1, monto=120),
        Venta(fecha=datetime(2026, 4, 14), descripcion="Alineación", tipo="servicio", cantidad_vendida=1, monto=250),

        Venta(fecha=datetime(2026, 4, 15), descripcion="Bujía NGK", tipo="refaccion", cantidad_vendida=3, monto=90),
        Venta(fecha=datetime(2026, 4, 15), descripcion="Cambio de aceite", tipo="servicio", cantidad_vendida=1, monto=300),

        Venta(fecha=datetime(2026, 4, 16), descripcion="Aceite Motul", tipo="refaccion", cantidad_vendida=1, monto=370),
        Venta(fecha=datetime(2026, 4, 16), descripcion="Ajuste de amortiguadores", tipo="servicio", cantidad_vendida=1, monto=450),

        Venta(fecha=datetime(2026, 4, 17), descripcion="Filtro de aire", tipo="refaccion", cantidad_vendida=2, monto=120),
        Venta(fecha=datetime(2026, 4, 17), descripcion="Cambio de aceite", tipo="servicio", cantidad_vendida=1, monto=300),
    ]

    # Guardar todo
    db.session.add_all(inventario_items + servicios_items + ventas_items)
    db.session.commit()

    print("✅ Base de datos de UNA SEMANA creada correctamente.")
