from flask import Blueprint, Flask, render_template, request, redirect, url_for, session, jsonify, flash
from datetime import datetime
from models import db, Inventario, Compatibilidad, Venta, Cliente, Servicio, Pago, Moto, Caja, Presupuesto, RefaccionCliente
import pandas as pd
from sqlalchemy import text
import os
from openpyxl import load_workbook

# Para envío de correos
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

#INICIO y HOME
def init_app(app):
    @app.route("/")
    def home():
        return render_template("home.html")
    
    @app.route("/reset_sesion")
    def reset_sesion():
        session.clear()
        flash("Sesión borrada")
        return redirect("/caja")

# ==========================
#   GRUPO: ADMINISTRADOR
# ==========================
 
    @app.route("/validar_admin", methods=["POST"])
    def validar_admin():
        password = request.form.get("admin_pass")
        categoria = request.form.get("categoria")  # capturamos la categoría actual
        origen = request.form.get("origen")

        if password == "1602":
            session["admin_autorizado"] = True
            flash("Acceso de administrador concedido", "success")
        else:
            flash("Contraseña incorrecta", "error")

        if origen == "servicios":
            return redirect(url_for("servicios"))
        else:    
            return redirect(url_for("inventario_categoria", categoria=categoria))

    @app.route("/cerrar_admin", methods=["POST"])
    def cerrar_admin():
        session.pop("admin_autorizado", None)
        flash("Sesión de administrador cerrada", "info")
        origen = request.form.get("origen")
        if origen == "servicios":
            return redirect(url_for("servicios"))
        else:
            return redirect(url_for("inventario"))
    
# ==========================
#   GRUPO: CARRITO
# ==========================

    @app.route("/agregar_carrito", methods=["POST"])
    def agregar_al_carrito():
        """
        Agrega un producto o servicio al carrito.
        - Si recibe producto_id: valida existencia y stock en Inventario.
        - Si recibe servicio_id: valida existencia en Servicios.
        - Calcula total y lo añade a la sesión.
        - Confirma con mensaje flash.
        """
        producto_id = request.form.get("producto_id", type=int)
        servicio_id = request.form.get("servicio_id", type=int)
        cantidad    = request.form.get("cantidad", type=int, default=1)

        carrito = session.get("carrito", [])

        # Caso producto
        if producto_id:
            producto = Inventario.query.get(producto_id)
            if not producto:
                flash("Producto no encontrado en inventario", "error")
                return redirect(url_for("carrito"))

            if producto.cantidad <= 0:
                flash("Error: producto sin inventario", "error")
                return redirect(url_for("carrito"))

            if cantidad <= 0:
                flash("Error: cantidad inválida", "error")
                return redirect(url_for("carrito"))

            if cantidad > producto.cantidad:
                flash("Error: no hay suficiente stock", "error")
                return redirect(url_for("carrito"))

            precio_unitario = float(producto.precio_unitario)
            total = precio_unitario * cantidad

            carrito.append({
                "id": len(carrito) + 1,
                "producto_id": producto.id,
                "nombre": producto.nombre,
                "cantidad": cantidad,
                "precio_unitario": precio_unitario,
                "total": total,
                "tipo": "refaccion"
            })
            flash("Producto agregado al carrito", "success")

        # Caso servicio
        elif servicio_id:
            servicio = Servicio.query.get(servicio_id)
            if not servicio:
                flash("Servicio no encontrado", "error")
                return redirect(url_for("carrito"))

            carrito.append({
                "id": len(carrito) + 1,
                "producto_id": None,
                "nombre": servicio.nombre,
                "cantidad": 1,
                "precio_unitario": servicio.importe,
                "total": servicio.importe,
                "tipo": "servicio"
            })
            flash("Servicio agregado al carrito", "success")

        else:
            flash("Error: no seleccionaste producto ni servicio", "error")

        session["carrito"] = carrito
        return redirect(url_for("carrito"))

    @app.route("/agregar_servicio_carrito/<int:servicio_id>")
    def agregar_servicio_carrito(servicio_id):
        """
        Agrega un servicio individual al carrito.
        - Obtiene el servicio por su ID.
        - Lo añade a la sesión de carrito.
        - Confirma con mensaje flash.
        """
        servicio = Servicio.query.get(servicio_id)
        if not servicio:
            flash("Servicio no encontrado", "error")
            return redirect("/servicios")

        carrito = session.get("carrito", [])
        carrito.append({
            "id": len(carrito) + 1,
            "producto_id": None,
            "nombre": servicio.nombre,
            "cantidad": 1,
            "precio_unitario": servicio.importe,
            "total": servicio.importe,
            "tipo": "servicio"
        })
        session["carrito"] = carrito

        flash("Servicio agregado al carrito", "success")
        return redirect("/carrito")


    @app.route("/agregar_servicios_carrito", methods=["POST"])
    def agregar_servicios_carrito():
        """
        Agrega múltiples servicios seleccionados al carrito.
        - Recibe lista de IDs desde el formulario.
        - Añade cada servicio válido a la sesión.
        - Confirma con mensaje flash.
        """
        seleccionados = request.form.getlist("servicios_seleccionados")
        if not seleccionados:
            flash("No seleccionaste ningún servicio", "error")
            return redirect("/servicios")

        carrito = session.get("carrito", [])
        for sid in seleccionados:
            servicio = Servicio.query.get(int(sid))
            if servicio:
                carrito.append({
                    "id": len(carrito) + 1,
                    "producto_id": None,
                    "nombre": servicio.nombre,
                    "cantidad": 1,
                    "precio_unitario": servicio.importe,
                    "total": servicio.importe,
                    "tipo": "servicio"
                })
        session["carrito"] = carrito

        flash("Servicios agregados al carrito", "success")
        return redirect("/carrito")


    @app.route("/cancelar_carrito", methods=["POST"])
    def cancelar_carrito():
        """
        Cancela el carrito actual.
        - Limpia la sesión de carrito.
        - Limpia recibido y cambio.
        - Redirige a la vista de carrito.
        """
        session["carrito"] = []
        session.pop("recibido", None)
        session.pop("cambio", None)
        flash("Carrito cancelado correctamente", "info")
        return redirect(url_for("carrito"))



    @app.route("/carrito")
    def carrito():
        """
        Muestra el contenido del carrito.
        - Obtiene los productos/servicios de la sesión.
        - Calcula el total.
        - Renderiza la plantilla carrito.html.
        """
        carrito = session.get("carrito", [])
        total_carrito = sum(item["total"] for item in carrito)

        recibido = session.get("recibido")
        cambio = session.get("cambio")

        return render_template(
            "carrito.html",
            carrito=carrito,
            total_carrito=total_carrito,
            recibido=recibido,
            cambio=cambio
        )

    @app.route("/confirmar_venta", methods=["POST"])
    def confirmar_venta():
        """
        Confirma la venta del carrito.
        - Valida que el carrito no esté vacío.
        - Verifica monto recibido y calcula cambio.
        - Registra ventas en la base de datos.
        - Actualiza inventario.
        - Limpia el carrito y confirma con mensaje flash.
        """
        carrito = session.get("carrito", [])
        if not carrito:
            flash("Error: carrito vacío", "error")
            return redirect("/carrito")

        recibido = request.form.get("recibido")
        if not recibido:
            flash("Error: cantidad recibida vacía", "error")
            return redirect("/carrito")

        recibido = float(recibido)
        total = sum(float(item["total"]) for item in carrito)

        if recibido < total:
            flash(f"Error: recibido insuficiente. Falta ${total - recibido:.2f}", "error")
            return redirect("/carrito")

        cambio = recibido - total
        session["recibido"] = recibido
        session["cambio"] = cambio

        for item in carrito:
            if item["tipo"] == "refaccion" and item["producto_id"]:
                producto = Inventario.query.get(item["producto_id"])
                if producto:
                    producto.cantidad = max(producto.cantidad - int(item["cantidad"]), 0)

            venta = Venta(
                producto_id=item["producto_id"],
                tipo=item["tipo"],
                cantidad_vendida=item["cantidad"],
                descripcion=item["nombre"],
                monto=item["total"],
                fecha=datetime.utcnow()
            )
            db.session.add(venta)

        db.session.commit()
        session["carrito"] = []

        flash(f"Venta registrada con éxito. Cambio: ${cambio:.2f}", "success")
        return redirect("/ventas")

    @app.route("/eliminar_del_carrito/<int:id>", methods=["POST"])
    def eliminar_del_carrito(id):
        """
        Elimina un ítem específico del carrito.
        """
        carrito = session.get("carrito", [])
        carrito = [item for item in carrito if item["id"] != id]
        session["carrito"] = carrito
        flash("Ítem eliminado del carrito", "info")
        return redirect(url_for("carrito"))

    @app.route("/sugerir_producto_inventario")
    def sugerir_producto_inventario():
        """
        Devuelve coincidencias de productos del inventario para el autocompletado.
        - Busca por nombre en la tabla Inventario.
        - Retorna JSON con id, nombre, categoría y estado dinámico según stock.
        """
        q = request.args.get("q", "").strip()
        resultados = []
        if q:
            productos = Inventario.query.filter(Inventario.nombre.ilike(f"%{q}%")).all()
            for p in productos:
                # Calcular ratio de stock
                ratio = p.cantidad / p.stock_maximo if p.stock_maximo and p.stock_maximo > 0 else 0
                if p.cantidad <= 3 or ratio <= 0.33:
                    color = "red"
                    leyenda = "Stock crítico"
                elif ratio <= 0.66:
                    color = "orange"
                    leyenda = "Stock medio"
                else:
                    color = "green"
                    leyenda = "Stock suficiente"

                resultados.append({
                    "id": p.id,
                    "nombre": p.nombre,
                    "categoria": p.categoria,
                    "estado": color,
                    "leyenda": leyenda,
                    "seleccionable": p.cantidad > 0
                })
        return jsonify(resultados)

    @app.route("/sugerir_servicio")
    def sugerir_servicio():
        q = request.args.get("q", "").strip()
        resultados = []
        if q:
            servicios = Servicio.query.filter(Servicio.nombre.ilike(f"%{q}%")).all()
            for s in servicios:
                resultados.append({
                    "id": s.id,
                    "nombre": s.nombre,
                    "tipo": s.tipo
                })
        return jsonify(resultados)

# ==========================
#   GRUPO: CLIENTES
# ==========================

    @app.route("/agregar_cliente", methods=["POST"])
    def agregar_cliente():
        """
        Registra un nuevo cliente en el sistema.
        - Recibe datos desde el formulario (nombre, celular, modelo, anticipo, fechas, descripción).
        - Valida la hora de entrega (entre 11:00 y 17:00).
        - Crea un registro en la tabla Cliente y su moto asociada.
        - Confirma la operación con un mensaje flash.
        """
        nombre   = request.form["nombre"].strip()
        celular  = request.form["celular"].strip()
        modelo   = request.form["modelo"].strip()

        anticipo             = request.form.get("anticipo", 0.0)
        fecha_dia            = request.form.get("fecha_entrega_dia")
        fecha_hora           = request.form.get("fecha_entrega_hora")
        descripcion_problema = request.form.get("descripcion_problema", "").strip()
        problemas_ocultos    = "problemas_ocultos" in request.form

        # 🔹 Construir fecha completa de entrega
        fecha_entrega = None
        if fecha_dia and fecha_hora:
            fecha_entrega = datetime.fromisoformat(f"{fecha_dia}T{fecha_hora}")

            # 🔹 Validar que esté dentro del rango 11:00 - 17:00
            if fecha_entrega.hour < 11 or fecha_entrega.hour > 17:
                flash("La hora de entrega debe estar entre 11:00 y 17:00", "error")
                return redirect(url_for("clientes"))

        nuevo_cliente = Cliente(
            nombre              = nombre,
            celular             = celular,
            anticipo            = float(anticipo) if anticipo else 0.0,
            fecha_ingreso       = datetime.now(),   # 🔹 Hora automática
            fecha_entrega       = fecha_entrega,
            descripcion_problema= descripcion_problema,
            problemas_ocultos   = problemas_ocultos
        )
        db.session.add(nuevo_cliente)
        db.session.commit()

        nueva_moto = Moto(
            modelo      = modelo,
            cliente_id  = nuevo_cliente.id,
            estado      = 1,
            confirmado  = False
        )
        db.session.add(nueva_moto)
        db.session.commit()

        flash("Cliente registrado correctamente", "success")
        return redirect(url_for("clientes"))


    @app.route("/clientes")
    def clientes():
        print("Ruta de templates usada:", app.template_folder)
        print("Ruta absoluta de clientes.html:", os.path.join(app.template_folder, "clientes.html"))

        """
        Muestra la lista de clientes registrados.
        - Consulta todos los registros de la tabla Cliente.
        - Renderiza la plantilla clientes.html con la lista.
        """
        lista = Cliente.query.all()
        return render_template("clientes.html", clientes=lista)


    @app.route("/eliminar_cliente/<int:id>", methods=["POST"])
    def eliminar_cliente(id):
        """
        Elimina un cliente existente.
        - Recibe el ID del cliente.
        - Borra el registro de la base de datos.
        - Confirma la operación con un mensaje flash.
        """
        cliente = Cliente.query.get_or_404(id)
        db.session.delete(cliente)
        db.session.commit()
        flash("Cliente eliminado", "success")
        return redirect(url_for("clientes"))

# ==========================
#   GRUPO: COMPATIBILIDAD
# ==========================

    @app.route("/agregar_compatibilidad/<int:id>", methods=["POST"])
    def agregar_compatibilidad(id):
        """
        Agrega un modelo de moto compatible con una refacción.
        - Verifica que el usuario tenga autorización de administrador.
        - Obtiene la pieza desde Inventario por su ID.
        - Recibe el modelo de moto desde el formulario.
        - Crea y guarda un registro de compatibilidad en la base de datos.
        - Redirige a la categoría correspondiente con mensaje de éxito.
        """
        if not session.get("admin_autorizado"):
            flash("Acción restringida. Ingresa contraseña de admin.", "error")
            return redirect(url_for("inventario"))

        pieza = Inventario.query.get_or_404(id)
        modelo = request.form.get("moto_modelo", "").strip().upper()

        if modelo:
            nueva = Compatibilidad(refaccion_id=pieza.id, moto_modelo=modelo)
            db.session.add(nueva)
            db.session.commit()
            flash("Compatibilidad añadida correctamente", "success")

        return redirect(url_for("inventario_categoria", categoria=pieza.categoria.capitalize()))


    @app.route("/eliminar_compatibilidad/<int:id>", methods=["POST"])
    def eliminar_compatibilidad(id):
        """
        Elimina un registro de compatibilidad existente.
        - Verifica que el usuario tenga autorización de administrador.
        - Obtiene la compatibilidad por su ID.
        - Borra el registro de la base de datos.
        - Redirige a la categoría correspondiente con mensaje de éxito.
        """
        if not session.get("admin_autorizado"):
            flash("Acción restringida. Ingresa contraseña de admin.", "error")
            return redirect(url_for("inventario"))

        comp = Compatibilidad.query.get_or_404(id)
        categoria = comp.refaccion.categoria.capitalize()
        db.session.delete(comp)
        db.session.commit()
        flash("Compatibilidad eliminada correctamente", "success")

        return redirect(url_for("inventario_categoria", categoria=categoria))

# ==========================
#   GRUPO: DASHBOARD
# ==========================

    @app.route("/dashboard")
    def dashboard():
        """
        Muestra el panel principal con métricas generales.
        - Calcula el total de ventas y pagos.
        - Obtiene piezas con stock bajo (<5).
        - Renderiza la plantilla dashboard.html con los datos.
        """
        total_ventas = sum([v.monto for v in Venta.query.all()])
        total_pagos = sum([p.monto for p in Pago.query.all()])
        stock_bajo = Inventario.query.filter(Inventario.cantidad < 5).all()
        return render_template("dashboard.html", ventas=total_ventas, pagos=total_pagos, stock=stock_bajo)

# ==========================
#   GRUPO: INVENTARIO
# ==========================

    @app.route("/agregar_pieza", methods=["POST"])
    def agregar_pieza():
        categoria   = request.form.get("categoria", "").strip().title()
        nombre      = request.form.get("nombre", "").strip().title()
        cantidad    = request.form.get("cantidad", type=int, default=0)
        precio      = request.form.get("precio", type=float, default=0.0)
        costo       = request.form.get("costo", type=float, default=0.0)

        if not nombre or cantidad < 0 or precio <= 0:
            flash("Error: todos los campos son obligatorios y válidos", "error")
            return redirect(url_for("inventario"))

        existente = Inventario.query.filter(Inventario.nombre.ilike(nombre)).first()
        if existente:
            flash("Error: ya existe una refacción con ese nombre", "error")
            return redirect(url_for("inventario"))

        stock_maximo = cantidad if cantidad >= 3 else 3
        nueva = Inventario(
            categoria       = categoria,
            nombre          = nombre,
            cantidad        = cantidad,
            stock_maximo    = stock_maximo,
            precio_unitario = precio,
            costo_unitario  = costo
        )
        db.session.add(nueva)
        db.session.commit()
        flash("Pieza agregada correctamente", "success")
        return redirect(url_for("inventario"))

    @app.route("/editar_inventario/<int:id>", methods=["POST"])
    def editar_inventario(id):
        if not session.get("admin_autorizado"):
            flash("Acción restringida. Ingresa contraseña de admin.", "error")
            return redirect(url_for("inventario"))

        pieza = Inventario.query.get_or_404(id)

        # Recibir valores como texto
        nuevo_nombre = request.form.get("nombre", "").strip()
        nuevo_precio = request.form.get("precio", "").strip()
        nuevo_costo  = request.form.get("costo", "").strip()
        nuevo_margen = request.form.get("margen", "").strip()

        # Nombre
        if nuevo_nombre:
            pieza.nombre = nuevo_nombre.title()

        # Precio
        if nuevo_precio:
            try:
                pieza.precio_unitario = float(nuevo_precio)
            except Exception:
                flash("⚠️ Precio inválido, no se actualizó", "warning")

        # Costo
        if nuevo_costo:
            try:
                pieza.costo_unitario = float(nuevo_costo)
            except Exception:
                flash("⚠️ Costo inválido, no se actualizó", "warning")

        # Margen
        if nuevo_margen:
            try:
                margen_float = float(nuevo_margen)
                if pieza.costo_unitario and pieza.costo_unitario > 0:
                    precio_calculado = pieza.costo_unitario * (1 + margen_float / 100)
                    pieza.precio_unitario = round(precio_calculado / 5) * 5
            except Exception:
                flash("⚠️ Margen inválido, no se actualizó", "warning")

        # 🔹 Siempre recalcular margen real si hay costo y precio
        if pieza.costo_unitario and pieza.costo_unitario > 0 and pieza.precio_unitario:
            try:
                margen_real = ((pieza.precio_unitario - pieza.costo_unitario) / pieza.costo_unitario) * 100
                flash(f"✅ Cambios guardados. Margen real: {round(margen_real, 2)}% (Precio: ${pieza.precio_unitario})", "success")
            except Exception:
                flash("✅ Cambios guardados (no se pudo calcular margen)", "success")
        else:
            flash("✅ Cambios guardados", "success")

        db.session.commit()
        return redirect(url_for("inventario_categoria", categoria=pieza.categoria.capitalize()))


    @app.route("/eliminar_inventario/<int:id>", methods=["POST"])
    def eliminar_inventario(id):
        if not session.get("admin_autorizado"):
            flash("Acción restringida. Ingresa contraseña de admin.", "error")
            return redirect(url_for("inventario"))

        pieza = Inventario.query.get_or_404(id)
        categoria = pieza.categoria.capitalize()
        db.session.delete(pieza)
        db.session.commit()
        flash("Pieza eliminada correctamente", "success")
        return redirect(url_for("inventario_categoria", categoria=categoria))

    @app.route("/inventario")
    def inventario():
        categorias = []
        todas = db.session.query(Inventario.categoria).distinct().all()
        for c in todas:
            if not c[0]:
                continue
            nombre_cat = c[0].capitalize()
            piezas = Inventario.query.filter_by(categoria=c[0]).all()

            estado = "green"
            for p in piezas:
                if not p.stock_maximo or p.stock_maximo <= 0:
                    continue
                ratio = p.cantidad / p.stock_maximo if p.stock_maximo > 0 else 0
                if p.cantidad <= 3 or ratio <= 0.33:
                    estado = "red"
                    break
                elif ratio <= 0.66 and estado != "red":
                    estado = "orange"
            categorias.append((nombre_cat, estado))

        return render_template("inventario.html", categorias=categorias)

    @app.route("/inventario/<categoria>")
    def inventario_categoria(categoria):
        piezas = Inventario.query.filter(Inventario.categoria.ilike(categoria)).all()

        # Calcular margen dinámico
        for p in piezas:
            if p.costo_unitario and p.costo_unitario > 0:
                p.margen = round(((p.precio_unitario - p.costo_unitario) / p.costo_unitario) * 100, 2)
            else:
                p.margen = 0

        return render_template("inventario_categoria.html",
                               categoria=categoria.capitalize(),
                               piezas=piezas)

    @app.route("/restock/<int:id>", methods=["POST"])
    def restock(id):
        if not session.get("admin_autorizado"):
            flash("Acción restringida. Ingresa contraseña de admin.", "error")
            return redirect(url_for("inventario"))

        pieza = Inventario.query.get_or_404(id)
        cantidad = int(request.form.get("cantidad", 0))

        if cantidad < 0:
            flash("Error: la cantidad no puede ser negativa", "error")
            return redirect(url_for("inventario"))

        pieza.cantidad += cantidad
        if pieza.cantidad > pieza.stock_maximo:
            pieza.stock_maximo = pieza.cantidad

        db.session.commit()
        flash("Stock actualizado correctamente", "success")
        return redirect(url_for("inventario_categoria", categoria=pieza.categoria.capitalize()))

    @app.route("/editar_margen/<int:pieza_id>", methods=["POST"])
    def editar_margen(pieza_id):
        """
        Edita el margen de ganancia de una pieza.
        - Recibe el porcentaje de margen desde el formulario.
        - Calcula el nuevo precio unitario en base al costo.
        - Redondea el precio al múltiplo de 5 más cercano.
        - Recalcula el margen real después del redondeo.
        - Actualiza la base de datos y confirma con mensaje flash.
        """
        pieza = Inventario.query.get_or_404(pieza_id)
        try:
            nuevo_margen = float(request.form["margen"])
            if pieza.costo_unitario and pieza.costo_unitario > 0:
                # Calcular nuevo precio en base al margen
                precio_calculado = pieza.costo_unitario * (1 + nuevo_margen / 100)

                # Redondear al múltiplo de 5 más cercano
                precio_redondeado = round(precio_calculado / 5) * 5

                # Actualizar precio_unitario
                pieza.precio_unitario = precio_redondeado

                # Recalcular margen real después del redondeo
                margen_real = ((pieza.precio_unitario - pieza.costo_unitario) / pieza.costo_unitario) * 100

                db.session.commit()
                flash(f"✅ Margen ajustado: {round(margen_real, 2)}% (Precio: ${pieza.precio_unitario})")
            else:
                flash("❌ Error: la pieza no tiene costo válido", "error")
        except Exception as e:
            flash(f"❌ Error al actualizar margen: {e}", "error")

        return redirect(url_for("inventario_categoria", categoria=pieza.categoria.capitalize()))

# ==========================
#   GRUPO: MOTOS
# ==========================

    @app.route("/agregar_refaccion/<int:cliente_id>", methods=["POST"])
    def agregar_refaccion(cliente_id):
        """
        Registra una refacción asociada a un cliente.
        - Obtiene el cliente por su ID.
        - Recibe datos desde el formulario (nombre, cantidad, estado, firma de recepción).
        - Crea y guarda un registro en la tabla RefaccionCliente.
        - Confirma la operación con un mensaje flash.
        """
        cliente = Cliente.query.get_or_404(cliente_id)
        nombre = request.form["nombre"].strip()
        cantidad = int(request.form["cantidad"])
        estado = request.form.get("estado", "Nueva")
        firma_recepcion = "firma_recepcion" in request.form

        nueva_refaccion = RefaccionCliente(
            cliente_id=cliente.id,
            nombre=nombre,
            cantidad=cantidad,
            estado=estado,
            firma_recepcion=firma_recepcion
        )
        db.session.add(nueva_refaccion)
        db.session.commit()

        flash("Refacción registrada correctamente", "success")
        return redirect(url_for("clientes"))


    @app.route("/avanzar_estado/<int:moto_id>", methods=["POST"])
    def avanzar_estado(moto_id):
        """
        Avanza el estado de una moto según su flujo de eventos.
        - Obtiene la moto por su ID.
        - Si está en estado 1 o 2: avanza y confirma.
        - Si está en estado 3: primer clic confirma presupuesto, segundo clic avanza a entrega.
        - Actualiza la base de datos y muestra mensajes flash.
        """

        moto = Moto.query.get_or_404(moto_id)

        # Eventos 1 y 2: confirmar y avanzar en un solo paso
        if moto.estado in [1, 2]:
            moto.estado += 1
            moto.confirmado = True
            db.session.commit()
            flash("Evento confirmado y avanzando", "success")

        elif moto.estado == 3:
            if not moto.confirmado:
                moto.confirmado = True
                db.session.commit()
                flash("Presupuesto confirmado", "success")
            else:
                # Segundo clic: avanza al 4, inicia sin confirmar
                moto.estado = 4
                moto.confirmado = False
                db.session.commit()
                flash("Avanzando a entrega", "info")

        return redirect(url_for("motos", cliente_id=moto.cliente_id))

    @app.route("/entregar/<int:moto_id>", methods=["POST"])
    def entregar(moto_id):

        """
        Entrega una moto, elimina al cliente asociado y registra la venta.
        - Obtiene la moto y su cliente por ID.
        - Elimina el cliente de la base de datos.
        - Inserta registros en la tabla de ventas con los datos del presupuesto.
        - Descuenta inventario según las partidas del presupuesto.
        - Confirma la operación con un mensaje flash.
        """

        moto    = Moto.query.get_or_404(moto_id)
        cliente = Cliente.query.get_or_404(moto.cliente_id)

        # Eliminar cliente
        db.session.delete(cliente)

        # Registrar cada partida del presupuesto como venta y descontar inventario
        for p in moto.presupuestos:
            # Descontar inventario si existe
            inv = Inventario.query.filter_by(nombre=p.producto).first()
            if inv:
                if inv.cantidad >= p.cantidad:
                    inv.cantidad -= p.cantidad   # ✅ descuenta inventario
                    inv.reservado -= p.cantidad  # ✅ libera reserva
                else:
                    flash(f"Stock insuficiente para {p.producto}, se registró igualmente.", "warning")

            # ✅ Corrección: usar p.tipo y fallback cantidad=1
            nueva_venta = Venta(
                producto_id = None if p.tipo == "Servicio" else inv.id if inv else None,
                tipo             = p.tipo,
                cantidad_vendida = p.cantidad if p.cantidad else 1,
                descripcion      = p.producto,
                monto            = p.total,
                fecha            = datetime.now()
            )
            db.session.add(nueva_venta)

        # Guardar cambios
        db.session.commit()

        flash("Entrega confirmada, cliente eliminado, inventario actualizado y ventas registradas.", "success")
        return redirect(url_for("clientes"))

    @app.route("/motos/<int:cliente_id>")
    def motos(cliente_id):
        """
        Muestra las motos asociadas a un cliente.
        - Obtiene el cliente por su ID.
        - Renderiza la plantilla motos.html con la información del cliente y sus presupuestos.
        """
        cliente = Cliente.query.get_or_404(cliente_id)
        return render_template("motos.html", cliente=cliente)

    @app.route("/sugerir_producto")
    def sugerir_producto():
        """
        Sugerencias inteligentes para la barra de búsqueda.
        - Consulta Inventario y Servicios según el término ingresado.
        - Devuelve coincidencias con estado visual (color), bloqueo si no hay stock,
          y precio unitario/base para autocompletar.
        """
        query = request.args.get("q", "").lower()
        sugerencias = []

        # Buscar en inventario
        inventario = Inventario.query.filter(Inventario.nombre.ilike(f"%{query}%")).all()
        for p in inventario:
            ratio = p.cantidad / p.stock_maximo if p.stock_maximo > 0 else 0  # 🔹 CAMBIO: definir ratio
            estado = "green"
            leyenda = ""
            seleccionable = True

            if p.cantidad <= 0:
                estado = "red"
                leyenda = "SIN INVENTARIO"
                seleccionable = False
            elif p.cantidad <= 3 or ratio <= 0.33:
                estado = "red"
            elif ratio <= 0.66:
                estado = "orange"

            sugerencias.append({
                "id": p.id,
                "categoria": p.categoria.capitalize(),
                "nombre": p.nombre.capitalize(),
                "estado": estado,
                "leyenda": leyenda,
                "seleccionable": seleccionable,
                "tipo": "producto",
                "precio": float(p.precio_unitario)
            })

        # Buscar en servicios
        servicios = Servicio.query.filter(Servicio.nombre.ilike(f"%{query}%")).all()
        for s in servicios:
            sugerencias.append({
                "id": s.id,
                "categoria": s.tipo.capitalize(),
                "nombre": s.nombre.capitalize(),
                "estado": "green",  # servicios no tienen stock
                "leyenda": "",
                "seleccionable": True,
                "tipo": "servicio",
                "precio": float(s.importe)
            })

        return jsonify(sugerencias)



# ==========================
#   GRUPO: PAGOS
# ==========================

    @app.route("/pagos")
    def pagos():
        """
        Muestra la lista de pagos registrados.
        - Consulta todos los registros de la tabla Pago.
        - Renderiza la plantilla pagos.html con la lista.
        """
        lista = Pago.query.all()
        return render_template("pagos.html", lista=lista)


    app.route("/registrar_pago", methods=["POST"])
    def registrar_pago():
        """
        Registra un nuevo pago en el sistema.
        - Recibe datos desde el formulario (tipo, monto, fecha).
        - Crea y guarda un registro en la tabla Pago.
        - Redirige a la vista de pagos.
        """
        tipo = request.form["tipo"]
        monto = float(request.form["monto"])
        fecha = request.form["fecha"]
        nuevo = Pago(tipo=tipo, monto=monto, fecha=fecha)
        db.session.add(nuevo)
        db.session.commit()
        return redirect(url_for("pagos"))

# ==========================
#   GRUPO: PRESUPUESTO
# ==========================

    @app.route("/agregar_a_lista", methods=["POST"])
    def agregar_a_lista():
        """
        Agrega un nuevo producto o servicio a la lista correspondiente.
        - Recibe nombre, tipo (producto/servicio) y categoría.
        - Inserta en Inventario o Servicios según corresponda.
        """
        data = request.get_json()
        nombre = data.get("nombre", "").strip()
        tipo = data.get("tipo", "").strip().lower()
        categoria = data.get("categoria", "").strip()

        if not nombre or not tipo or not categoria:
            return jsonify({"status": "error", "message": "Datos incompletos"}), 400

        if tipo == "producto":
            nuevo = Inventario(
                nombre=nombre,
                categoria=categoria,
                cantidad=0,              # inicia sin stock
                stock_maximo=10,         # valor por defecto, ajusta según tu lógica
                precio_unitario=0.0      # se podrá actualizar después
            )
            db.session.add(nuevo)

        elif tipo == "servicio":
            nuevo = Servicio(
                nombre=nombre,
                categoria=categoria,
                importe=0.0          # se podrá actualizar después
            )
            db.session.add(nuevo)

        else:
            return jsonify({"status": "error", "message": "Tipo inválido"}), 400

        db.session.commit()
        return jsonify({"status": "success", "message": f"{tipo.capitalize()} agregado correctamente"})

    @app.route("/agregar_presupuesto/<int:moto_id>", methods=["POST"])
    def agregar_presupuesto(moto_id):
        """
        Agrega un producto o servicio al presupuesto de la moto.
        - Valida que el precio unitario no esté vacío.
        - Identifica automáticamente si es Refacción (Inventario) o Servicio.
        - Si no existe en ninguna lista, lo agrega como entrada libre.
        """

        moto = Moto.query.get_or_404(moto_id)

        producto     = request.form.get("producto", "").strip()
        cantidad_str = request.form.get("cantidad", "").strip()
        precio_str   = request.form.get("precio_unitario", "").strip()

        # ✅ Cantidad siempre inicializa en 1
        try:
            cantidad = int(cantidad_str) if cantidad_str else 1
        except ValueError:
            cantidad = 1

        # ✅ Validación de producto
        if not producto:
            flash("Error: producto vacío", "error")
            return redirect(url_for("motos", cliente_id=moto.cliente_id))

        # ✅ Precio unitario seguro
        try:
            precio_unitario = float(precio_str) if precio_str else 0.0
        except ValueError:
            flash("Error: precio inválido", "error")
            return redirect(url_for("motos", cliente_id=moto.cliente_id))

        # ✅ Identificación automática
        tipo = None
        inv = Inventario.query.filter_by(nombre=producto).first()
        serv = Servicio.query.filter_by(nombre=producto).first()

        if inv:
            tipo = "Refacción"
            disponible = inv.cantidad - inv.reservado
            if disponible >= cantidad:
                inv.reservado += cantidad
            else:
                flash("Advertencia: stock insuficiente, se agregó igualmente", "warning")
        elif serv:
            tipo = "Servicio"
        else:
            tipo = "Libre"  # entrada manual

        # ✅ Crear registro de presupuesto
        nuevo = Presupuesto(
            moto_id=moto.id,
            producto=producto,
            cantidad=cantidad,
            precio_unitario=precio_unitario,
            tipo=tipo,
            total=cantidad * precio_unitario
        )

        db.session.add(nuevo)
        db.session.commit()

        flash("Producto/servicio agregado al presupuesto", "success")
        return redirect(url_for("motos", cliente_id=moto.cliente_id))

    @app.route("/eliminar_presupuesto/<int:presupuesto_id>", methods=["POST"])
    def eliminar_presupuesto(presupuesto_id):
        """
        Elimina un producto del presupuesto.
        - Obtiene el presupuesto por su ID.
        - Borra el registro de la base de datos.
        - Redirige al presupuesto de la moto correspondiente.
        """
        presupuesto = Presupuesto.query.get_or_404(presupuesto_id)
        moto_id = presupuesto.moto_id
        db.session.delete(presupuesto)
        db.session.commit()
        return redirect(url_for("presupuesto", moto_id=moto_id))


    @app.route("/presupuesto/<int:moto_id>")
    def presupuesto(moto_id):
        """
        Muestra el presupuesto de una moto.
        - Obtiene la moto por su ID.
        - Calcula el total sumando los productos del presupuesto.
        - Renderiza la plantilla presupuesto.html con los datos.
        """
        moto = Moto.query.get_or_404(moto_id)
        total = sum(p.total for p in moto.presupuestos)
        return render_template("presupuesto.html", moto=moto, total=total)

# ==========================
#   GRUPO: REPORTES
# ==========================
    def reportes(df_ventas, df_totales, correo_destino=None):
        mes_actual = datetime.now().strftime("%B").capitalize()
        nombre_archivo = f"reportes/Reportes_{mes_actual}.xlsx"
        os.makedirs("reportes", exist_ok=True)

        # ✅ Calcular total en Ventas con cantidad + precio
        df_ventas["total"] = df_ventas["cantidad"] * df_ventas["precio"]

# ==========================
# FORMATO PERSONALIZADO
# ==========================
        with pd.ExcelWriter(nombre_archivo, engine="xlsxwriter") as writer:
            # 🔹 Separar productos y servicios
            df_productos = df_ventas[df_ventas["tipo"] == "refaccion"].copy()
            df_servicios = df_ventas[df_ventas["tipo"] == "servicio"].copy()

            # 🔹 Renombrar hoja Ventas → Productos
            df_productos.to_excel(writer, sheet_name="Productos", index=False)
            df_servicios.to_excel(writer, sheet_name="Nomina", index=False)

            workbook = writer.book
            formato_encabezado = workbook.add_format({
                'bold': True, 'bg_color': '#D9D9D9', 'font_color': 'black',
                'align': 'center', 'valign': 'vcenter'
            })
            formato_fila_par = workbook.add_format({'bg_color': '#FFFFFF'})
            formato_fila_impar = workbook.add_format({'bg_color': '#F2F2F2'})
            formato_numero = workbook.add_format({'num_format': '#,##0.00'})
            formato_fecha = workbook.add_format({'num_format': 'yyyy-mm-dd'})

            # 🔹 Ajuste automático y formato de encabezados
            for hoja, df in [("Productos", df_productos), ("Nomina", df_servicios)]:
                ws = writer.sheets[hoja]
                for col_num, value in enumerate(df.columns):
                    ws.write(0, col_num, str(value).upper(), formato_encabezado)
                    ws.set_column(col_num, col_num, 18)

                # 🔹 Alternar colores de filas
                for row_num in range(1, len(df) + 1):
                    formato = formato_fila_par if row_num % 2 == 0 else formato_fila_impar
                    ws.set_row(row_num, None, formato)

                # 🔹 Fecha solo una vez por día
                fechas = df["fecha"].astype(str).tolist()
                for i in range(1, len(fechas)):
                    if fechas[i] == fechas[i - 1]:
                        ws.write(i + 1, df.columns.get_loc("fecha"), "", formato_fecha)

                # 🔹 Total dinámico al final
                ultima_fila = len(df) + 2
                col_precio = df.columns.get_loc("precio")
                col_total = df.columns.get_loc("total")
                ws.write_formula(ultima_fila, col_precio, f"=SUM(E2:E{ultima_fila-1})", formato_numero)
                ws.write_formula(ultima_fila, col_total, f"=SUM(F2:F{ultima_fila-1})", formato_numero)
                ws.write(ultima_fila, df.columns.get_loc("producto"), "TOTAL GENERAL", formato_encabezado)

            # 🔹 Eliminar hoja Totales si existe
            if "Totales" in writer.sheets:
                del writer.sheets["Totales"]

    # Enviar por correo si aplica
        if correo_destino:
            enviar_reporte_por_correo(nombre_archivo, correo_destino)

# ==========================
#   FUNCIÓN AUXILIAR: envío por correo
# ==========================
    def enviar_reporte_por_correo(nombre_archivo, destinatario):
        remitente = "tu_correo@gmail.com"
        password = "tu_password_app"  # Usa contraseña de aplicación

        msg = MIMEMultipart()
        msg['From'] = remitente
        msg['To'] = destinatario
        msg['Subject'] = "Reporte de Caja"

        with open(nombre_archivo, "rb") as f:
            parte = MIMEBase('application', 'octet-stream')
            parte.set_payload(f.read())
            encoders.encode_base64(parte)
            parte.add_header('Content-Disposition', f'attachment; filename={os.path.basename(nombre_archivo)}')
            msg.attach(parte)

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remitente, password)
        server.sendmail(remitente, destinatario, msg.as_string())
        server.quit()

        print(f"✅ Reporte enviado por correo a {destinatario}")

# ==========================
#   GRUPO: SERVICIOS
# ==========================

    @app.route("/agregar_servicio", methods=["POST"])
    def agregar_servicio():
        """
        Agrega un nuevo servicio al sistema.
        - Recibe datos desde el formulario (tipo, nombre, importe).
        - Valida que todos los campos estén completos.
        - Crea y guarda un registro en la tabla Servicio.
        - Confirma la operación con un mensaje flash.
        """
        tipo = request.form.get("tipo")
        nombre = request.form.get("nombre")
        importe = request.form.get("importe")

        if not tipo or not nombre or not importe:
            flash("Todos los campos son obligatorios", "error")
            return redirect("/servicios")

        try:
            importe = float(importe)
        except ValueError:
            flash("El importe debe ser numérico", "error")
            return redirect("/servicios")

        # 🔹 CAMBIO: validar duplicado antes de insertar
        existente = Servicio.query.filter(Servicio.nombre.ilike(nombre)).first()
        if existente:
            flash("Error: ya existe un servicio con ese nombre", "error")
            return redirect("/servicios")
        
        session["tipo_actual"] = tipo

        nuevo = Servicio(tipo=tipo, nombre=nombre, importe=importe)
        db.session.add(nuevo)
        db.session.commit()
        flash("Servicio agregado correctamente", "success")
        return redirect("/servicios")


    @app.route("/servicios")
    def servicios():
        """
        Muestra la lista de servicios agrupados por tipo.
        - Consulta todos los registros de la tabla Servicio.
        - Agrupa los servicios por su tipo.
        - Renderiza la plantilla servicios.html con los datos.
        """
        # 🔹 CAMBIO: obtener todos los servicios sin usar query ni sugerencias
        lista_servicios = Servicio.query.all()  

        # 🔹 CAMBIO: agrupar por tipo
        servicios_por_tipo = {}
        for s in lista_servicios:
            if s.tipo not in servicios_por_tipo:
                servicios_por_tipo[s.tipo] = []
            servicios_por_tipo[s.tipo].append(s)

        return render_template("servicios.html", servicios_por_tipo=servicios_por_tipo)  # 🔹 CAMBIO: enviar agrupados

    @app.route("/editar_servicio/<int:id>", methods=["POST"])
    def editar_servicio(id):
        if not session.get("admin_autorizado"):
            flash("Acción restringida. Ingresa contraseña de admin.", "error")
            return redirect(url_for("servicios"))

        servicio = Servicio.query.get_or_404(id)

        nuevo_tipo   = request.form.get("tipo", "").strip()
        nuevo_nombre = request.form.get("nombre", "").strip()
        nuevo_importe = request.form.get("importe", "").strip()

        if nuevo_tipo:
            servicio.tipo = nuevo_tipo.capitalize()
        if nuevo_nombre:
            servicio.nombre = nuevo_nombre.title()
        if nuevo_importe:
            try:
                servicio.importe = float(nuevo_importe)
            except Exception:
                flash("⚠️ Importe inválido, no se actualizó", "warning")

        db.session.commit()
        flash("✅ Servicio actualizado correctamente", "success")
        return redirect(url_for("servicios"))


    @app.route("/eliminar_servicio/<int:id>", methods=["POST"])
    def eliminar_servicio(id):
        if not session.get("admin_autorizado"):
            flash("Acción restringida. Ingresa contraseña de admin.", "error")
            return redirect(url_for("servicios"))

        servicio = Servicio.query.get_or_404(id)
        db.session.delete(servicio)
        db.session.commit()
        flash("✅ Servicio eliminado correctamente", "success")
        return redirect(url_for("servicios"))

# ==========================
#   GRUPO: VENTAS
# ==========================

    @app.route("/cerrar_caja", methods=["POST"])
    def cerrar_caja():
        password = request.form.get("admin_pass")
        if password != "1602":
            flash("Contraseña incorrecta", "error")
            return redirect(url_for("ventas"))  # ✅ CAMBIO

        ventas = Venta.query.all()
        df_ventas = pd.DataFrame([{
            "id": v.id,
            "fecha": v.fecha.strftime("%Y-%m-%d"),
            "producto": v.descripcion,
            "tipo": v.tipo,
            "cantidad": v.cantidad_vendida,
            "precio": v.monto,
            "total": v.monto
        } for v in ventas])

        correo_destino = request.form.get("correo_destino")  # ✅ CAMBIO

        total_refacciones = db.session.query(db.func.sum(Venta.monto))\
            .filter(db.func.lower(db.func.trim(Venta.tipo)) == "refaccion").scalar() or 0
        total_servicios = db.session.query(db.func.sum(Venta.monto))\
            .filter(db.func.lower(db.func.trim(Venta.tipo)) == "servicio").scalar() or 0

        total_general = total_refacciones + total_servicios
        nomina = total_servicios * 0.20

        if total_refacciones == 0 and total_servicios == 0:
            flash("No se encontraron ventas válidas")
            return redirect(url_for("ventas"))

        df_totales = pd.DataFrame([{
            "Total Refacciones": total_refacciones,
            "Total Mano de Obra": total_servicios,
            "Total General": total_general,
            "Nomina": nomina
        }])

        if not ventas:
            flash("No hay ventas registradas")
            return redirect(url_for("ventas"))

        reportes(df_ventas, df_totales, correo_destino)  # ✅ CAMBIO

        Venta.query.delete()
        db.session.commit()

        flash("Caja cerrada y cierre exportado a Excel", "info")
        return render_template("caja.html",
                               mostrar_modal=True,
                               total_ventas=total_general,
                               faltante=False)


    @app.route("/ventas")
    def ventas():
        # ✅ Corrección aplicada: usar "refaccion" en lugar de "producto"
        total_refacciones = db.session.query(db.func.sum(Venta.monto))\
            .filter(db.func.lower(db.func.trim(Venta.tipo)) == "refaccion").scalar() or 0  # 🔹 CAMBIO

        total_servicios = db.session.query(db.func.sum(Venta.monto))\
            .filter(db.func.lower(db.func.trim(Venta.tipo)) == "servicio").scalar() or 0

        total_general = total_refacciones + total_servicios

        # ⚠️ CAMBIO: nómina como cálculo
        nomina = total_servicios * 0.20
        ventas = Venta.query.all()

        df_ventas = pd.DataFrame([{
            "id": v.id,
            "fecha": v.fecha,
            "producto": v.descripcion,
            "cantidad": v.cantidad_vendida,
            "precio": v.monto,
            "total": v.monto
        } for v in ventas])

        # 🔹 CAMBIO: exportar también los totales a Excel (solo para visualización, no creación)
        df_totales = pd.DataFrame([{
            "Total Refacciones": total_refacciones,
            "Total Mano de Obra": total_servicios,
            "Total General": total_general,
            "Nomina": nomina
        }])

        return render_template(
            "ventas.html",
            ventas=ventas,  # 🔹 CAMBIO: enviar como 'ventas' para coincidir con la plantilla
            total_refacciones=total_refacciones,
            total_servicios=total_servicios,
            total_general=total_general,
            nomina=nomina
        )

    @app.route("/ventas_resumen")
    def mostrar_ventas():
        ventas = Venta.query.all()
        total_refacciones = db.session.query(db.func.sum(Venta.monto)).filter_by(tipo="refaccion").scalar() or 0
        total_servicios   = db.session.query(db.func.sum(Venta.monto)).filter_by(tipo="servicio").scalar() or 0
        total_general     = total_refacciones + total_servicios

        # ⚠️ CAMBIO: nómina como cálculo
        nomina = total_servicios * 0.20

        return render_template("ventas.html",
                               lista=ventas,
                               total_refacciones=total_refacciones,
                               total_servicios=total_servicios,
                               total_general=total_general,
                               nomina=nomina)

