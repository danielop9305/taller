from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Anticipo(db.Model):
    __tablename__ = "anticipo"

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

class Caja(db.Model):
    __tablename__ = "caja"
    id = db.Column(db.Integer, primary_key=True)
    denominacion = db.Column(db.Integer, nullable=False)
    cantidad = db.Column(db.Integer, default=0)
    # Relación con pagos
    pagos = db.relationship("Pago", backref="caja", cascade="all, delete-orphan")

class Cliente(db.Model):
    __tablename__ = "clientes"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    celular = db.Column(db.String(20), nullable=False)

    # 🔹 Nuevos campos nivel sencillo
    anticipo = db.Column(db.Float, default=0.0)              # dinero a cuenta
    fecha_ingreso = db.Column(db.DateTime, default=datetime.utcnow)  # fecha de ingreso
    fecha_entrega = db.Column(db.DateTime, nullable=True)    # fecha estimada de entrega
    descripcion_problema = db.Column(db.Text, nullable=True) # descripción detallada del problema
    problemas_ocultos = db.Column(db.Boolean, default=False) # cláusula de problemas ocultos aceptada

    # 🔹 Relación con motos
    lista_motos = db.relationship(
        "Moto",
        backref="cliente",
        lazy=True,
        cascade="all, delete-orphan",
        foreign_keys="Moto.cliente_id"   # ⚠️ CAMBIO: se especifica la FK
    )

    # 🔹 Relación con anticipos (historial)
    anticipos = db.relationship("Anticipo", backref="cliente", lazy=True, cascade="all, delete-orphan")

    # 🔹 Relación con refacciones del cliente
    refacciones_cliente = db.relationship("RefaccionCliente", backref="cliente", lazy=True, cascade="all, delete-orphan")

    # 🔹 Fechas
    fecha_ingreso = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_entrega = db.Column(db.DateTime, nullable=True)

    # 🔹 Tipo siempre forzado a “Servicio”
    tipo = db.Column(db.String(50), nullable=False, default="Servicio")

    def __init__(self, nombre, celular, descripcion_problema=None, problemas_ocultos=False, fecha_ingreso=None, fecha_entrega=None, tipo="Servicio"):
        self.nombre = nombre.strip().title()
        self.celular = celular.strip()
        self.descripcion_problema = descripcion_problema
        self.problemas_ocultos = problemas_ocultos
        self.fecha_ingreso = fecha_ingreso or datetime.utcnow()
        self.fecha_entrega = fecha_entrega
        # 🔹 Validación: nunca guardar “Libre”
        self.tipo = "Servicio" if tipo == "Libre" else tipo



class Compatibilidad(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    refaccion_id = db.Column(db.Integer, db.ForeignKey("inventario.id"), nullable=False)
    moto_modelo = db.Column(db.String(100), nullable=False)

    refaccion = db.relationship("Inventario", backref=db.backref("compatibilidades", lazy=True))

class Inventario(db.Model):
    __tablename__ = "inventario"

    id = db.Column(db.Integer, primary_key=True)
    categoria = db.Column(db.String(50), nullable=False)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    cantidad = db.Column(db.Integer, default=0)
    stock_maximo = db.Column(db.Integer, default=0)
    precio_unitario = db.Column(db.Float, nullable=False)
    costo_unitario = db.Column(db.Float, nullable=True)   # ✅ Nuevo campo
    reservado = db.Column(db.Integer, default=0)

    # Relación con ventas
    ventas = db.relationship("Venta", backref="producto")

class Nomina(db.Model):
    __tablename__ = "nomina"
    id = db.Column(db.Integer, primary_key=True)
    sueldo = db.Column(db.Float, nullable=False)

class Moto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    modelo = db.Column(db.String(100))
    estado = db.Column(db.Integer, default=1)
    confirmado = db.Column(db.Boolean, default=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"), nullable=False)  # ⚠️ CAMBIO


    presupuestos = db.relationship(
        'Presupuesto',
        backref='moto',
        lazy=True,
        cascade="all, delete-orphan"
    )

    @property
    def total_presupuesto(self):
        return sum(p.total for p in self.presupuestos)

class Pago(db.Model):
    __tablename__ = "pago"
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(20), nullable=False)  # efectivo, tarjeta, transferencia
    monto = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    caja_id = db.Column(db.Integer, db.ForeignKey("caja.id"), nullable=False)

class Presupuesto(db.Model):
    __tablename__ = "presupuesto"
    id = db.Column(db.Integer, primary_key=True)
    producto = db.Column(db.String(100), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False, default=1)
    precio_unitario = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)
    tipo = db.Column(db.String(50), default="Servicio")
    moto_id = db.Column(
        db.Integer,
        db.ForeignKey("moto.id", name="fk_presupuesto_moto_id"),
        nullable=False
    )

class RefaccionCliente(db.Model):
    __tablename__ = "refaccion_cliente"

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    cantidad = db.Column(db.Integer, default=1)
    estado = db.Column(db.String(50), nullable=True)
    firma_recepcion = db.Column(db.Boolean, default=False)


class Servicio(db.Model):
    __tablename__ = "servicio"
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(50), nullable=False)   # Motor, Suspensión, Dirección
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    importe = db.Column(db.Float, nullable=False)

class Usuario(db.Model):
    __tablename__ = "usuario"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    rol = db.Column(db.String(20), nullable=False)  # admin, mecanico, cliente

class Venta(db.Model):
    __tablename__ = "venta"
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey("inventario.id"), nullable=True)
    tipo = db.Column(db.String(20), nullable=False)  # refaccion, servicio
    cantidad_vendida = db.Column(db.Integer, nullable=False)
    descripcion = db.Column(db.String(200), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)