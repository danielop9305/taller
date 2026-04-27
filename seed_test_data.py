from app import app, db
from models import Venta, Servicio, Inventario, Cliente, Moto, Presupuesto, Pago, RefaccionCliente, Caja
from datetime import datetime, timedelta

def safe_create(model, **kwargs):
    valid_keys = {c.name for c in model.__table__.columns}
    filtered = {k: v for k, v in kwargs.items() if k in valid_keys}
    return model(**filtered)

with app.app_context():
    db.drop_all()
    db.create_all()

    # --- INVENTARIO ---
    inventario_items = [
        safe_create(Inventario, nombre="Aceite Motul", categoria="Lubricante",
                    cantidad=10, stock_maximo=20, precio_unitario=370, costo_unitario=250),
        safe_create(Inventario, nombre="Filtro de aire", categoria="Motor",
                    cantidad=5, stock_maximo=15, precio_unitario=120, costo_unitario=80),
        safe_create(Inventario, nombre="Bujía NGK", categoria="Encendido",
                    cantidad=8, stock_maximo=20, precio_unitario=90, costo_unitario=50),
    ]

    # --- SERVICIOS ---
    servicios_items = [
        safe_create(Servicio, tipo="Motor", nombre="Cambio de aceite", importe=300),
        safe_create(Servicio, tipo="Suspensión", nombre="Ajuste de amortiguadores", importe=450),
        safe_create(Servicio, tipo="Dirección", nombre="Alineación", importe=250),
    ]

    # --- CLIENTES Y MOTOS ---
    clientes_items = [
        safe_create(Cliente, nombre="Juan Pérez", celular="5551234567", descripcion_problema="Cambio de aceite"),
        safe_create(Cliente, nombre="María López", celular="5559876543", descripcion_problema="Falla eléctrica"),
    ]
    motos_items = [
        safe_create(Moto, modelo="Yamaha 125", cliente_id=1),
        safe_create(Moto, modelo="Honda 250", cliente_id=2),
    ]

    # --- PRESUPUESTOS ---
    presupuestos_items = [
        safe_create(Presupuesto, moto_id=1, producto="Cambio de aceite", cantidad=1,
                    precio_unitario=800, total=800, tipo="Servicio"),
        safe_create(Presupuesto, moto_id=2, producto="Reparación eléctrica", cantidad=1,
                    precio_unitario=1500, total=1500, tipo="Servicio"),
    ]

    # --- CAJA ---
    caja_test = safe_create(Caja,
        fecha_apertura=datetime(2026, 4, 26),
        saldo_inicial=5000,
        denominacion="Caja principal",
        cantidad=1
    )
    db.session.add(caja_test)
    db.session.flush()

    # --- PAGOS ---
    pagos_items = [
        safe_create(Pago, tipo="Servicio", monto=500, fecha=datetime(2026, 4, 26), caja_id=caja_test.id),
        safe_create(Pago, tipo="Servicio", monto=1200, fecha=datetime(2026, 4, 26), caja_id=caja_test.id),
    ]

    # --- REFACCIONES ---
    refacciones_items = [
        safe_create(RefaccionCliente, cliente_id=1, nombre="Filtro de aire", cantidad=1),
        safe_create(RefaccionCliente, cliente_id=2, nombre="Batería", cantidad=1),
    ]

    # --- VENTAS (3 semanas) ---
    ventas_items = []
    start_date = datetime(2026, 4, 13)
    for week in range(3):
        for day_offset in range(5):
            fecha = start_date + timedelta(days=week * 7 + day_offset)
            ventas_items.append(
                safe_create(Venta, fecha=fecha, descripcion="Cambio de aceite",
                            tipo="servicio", cantidad_vendida=1, monto=300)
            )
            ventas_items.append(
                safe_create(Venta, fecha=fecha, descripcion="Aceite Motul",
                            tipo="refaccion", cantidad_vendida=1, monto=370)
            )

    db.session.add_all(
        inventario_items + servicios_items + clientes_items + motos_items +
        presupuestos_items + pagos_items + refacciones_items + ventas_items
    )
    db.session.commit()

    print("✅ Base de datos de 3 SEMANAS + datos de prueba creada correctamente.")
