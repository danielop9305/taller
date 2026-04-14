from app import app, db
from models import Venta, Servicio, Inventario
from datetime import datetime, timedelta

def safe_create(model, **kwargs):
    """Crea una instancia del modelo usando solo columnas válidas."""
    valid_keys = {c.name for c in model.__table__.columns}
    filtered = {k: v for k, v in kwargs.items() if k in valid_keys}
    return model(**filtered)

with app.app_context():
    # Reiniciar BD
    db.drop_all()
    db.create_all()

    # Inventario de prueba (igual que antes)
    inventario_items = [
        safe_create(Inventario, nombre="Aceite Motul", categoria="Lubricante",
                    cantidad=10, stock_maximo=20, precio_unitario=370, costo_unitario=250),
        safe_create(Inventario, nombre="Filtro de aire", categoria="Motor",
                    cantidad=5, stock_maximo=15, precio_unitario=120, costo_unitario=80),
        safe_create(Inventario, nombre="Bujía NGK", categoria="Encendido",
                    cantidad=8, stock_maximo=20, precio_unitario=90, costo_unitario=50),
    ]

    # Servicios de prueba
    servicios_items = [
        safe_create(Servicio, tipo="Motor", nombre="Cambio de aceite", importe=300),
        safe_create(Servicio, tipo="Suspensión", nombre="Ajuste de amortiguadores", importe=450),
        safe_create(Servicio, tipo="Dirección", nombre="Alineación", importe=250),
    ]

    # Ventas de prueba: 3 semanas (lunes a viernes)
    ventas_items = []
    start_date = datetime(2026, 4, 13)  # lunes inicial
    for week in range(3):  # 3 semanas
        for day_offset in range(5):  # lunes a viernes
            fecha = start_date + timedelta(days=week*7 + day_offset)
            # Ejemplo: cada día se venden un servicio y una refacción
            ventas_items.append(
                safe_create(Venta, fecha=fecha, descripcion="Cambio de aceite",
                            tipo="servicio", cantidad_vendida=1, monto=300)
            )
            ventas_items.append(
                safe_create(Venta, fecha=fecha, descripcion="Aceite Motul",
                            tipo="refaccion", cantidad_vendida=1, monto=370)
            )

    # Guardar todo
    db.session.add_all(inventario_items + servicios_items + ventas_items)
    db.session.commit()

    print("✅ Base de datos de 3 SEMANAS creada correctamente.")
