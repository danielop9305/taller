from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Caja(db.Model):
    __tablename__ = "caja"
    id = db.Column(db.Integer, primary_key=True)
    denominacion = db.Column(db.Integer, nullable=False)
    cantidad = db.Column(db.Integer, default=0)
    # Relación con pagos
    pagos = db.relationship("Pago", backref="caja", cascade="all, delete-orphan")

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    celular = db.Column(db.String(20), nullable=False)

    lista_motos = db.relationship(
        'Moto',
        backref='cliente',
        lazy=True,
        cascade="all, delete-orphan"
    )

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
    # Relación con ventas
    ventas = db.relationship("Venta", backref="producto")

class Moto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    modelo = db.Column(db.String(100))
    estado = db.Column(db.Integer, default=1)
    confirmado = db.Column(db.Boolean, default=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'))

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
    moto_id = db.Column(db.Integer, db.ForeignKey("moto.id"), nullable=False)
    producto = db.Column(db.String(100), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Float, nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey("inventario.id"), nullable=True)

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