from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from datetime import datetime
from models import db, Inventario, Compatibilidad, Venta, Cliente, Servicio, Pago, Moto, Caja, Presupuesto, RefaccionCliente


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
        if password == "1602":
            session["admin_autorizado"] = True
            flash("Acceso de administrador concedido", "success")
        else:
            flash("Contraseña incorrecta", "error")
        return redirect(url_for("inventario_categoria", categoria=categoria))


    @app.route("/cerrar_admin", methods=["POST"])
    def cerrar_admin():
        session.pop("admin_autorizado", None)
        flash("Sesión de administrador cerrada", "info")
        return redirect(url_for("inventario"))

# ==========================
#   GRUPO: CARRITO
# ==========================

    @app.route("/agregar_carrito", methods=["POST"])
    def agregar_al_carrito():
        """
        Agrega un producto del inventario al carrito.
        - Valida existencia y stock del producto.
        - Calcula total y lo añade a la sesión.
        - Confirma con mensaje flash.
        """
        producto_id = request.form.get("producto_id", type=int)
        cantidad    = request.form.get("cantidad", type=int, default=0)

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

        carrito = session.get("carrito", [])
        carrito.append({
            "id": len(carrito) + 1,
            "producto_id": producto.id,
            "nombre": producto.nombre,
            "cantidad": cantidad,
            "precio_unitario": precio_unitario,
            "total": total,
            "tipo": "refaccion"
        })
        session["carrito"] = carrito

        flash("Producto agregado al carrito", "success")
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
        Elimina un ítem del carrito.
        - Recibe el ID interno del ítem.
        - Filtra la lista y actualiza la sesión.
        - Redirige a la vista de carrito.
        """
        session["carrito"] = []
        session.pop("recibido", None)
        session.pop("cambio", None)
        return redirect(url_for("carrito"))

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
        """
        Agrega una nueva pieza al inventario.
        - Recibe datos desde el formulario (categoría, nombre, cantidad, precio).
        - Valida que los campos sean correctos y que no exista duplicado.
        - Calcula stock máximo mínimo de 3 unidades.
        - Guarda el registro en la base de datos y confirma con mensaje flash.
        """
        categoria   = request.form.get("categoria", "").strip().title()
        nombre      = request.form.get("nombre", "").strip().title()
        cantidad    = request.form.get("cantidad", type=int, default=0)
        precio      = request.form.get("precio", type=float, default=0.0)

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
            precio_unitario = precio
        )
        db.session.add(nueva)
        db.session.commit()
        flash("Pieza agregada correctamente", "success")
        return redirect(url_for("inventario"))


    @app.route("/editar_inventario/<int:id>", methods=["GET", "POST"])
    def editar_inventario(id):
        """
        Edita los datos de una pieza existente en el inventario.
        - Verifica autorización de administrador.
        - Permite modificar nombre y precio.
        - Valida que los campos sean correctos.
        - Actualiza la base de datos y confirma con mensaje flash.
        """
        if not session.get("admin_autorizado"):
            flash("Acción restringida. Ingresa contraseña de admin.", "error")
            return redirect(url_for("inventario"))

        pieza = Inventario.query.get_or_404(id)

        if request.method == "POST":
            nuevo_nombre = request.form.get("nombre", "").strip().title()
            nuevo_precio = request.form.get("precio", type=float)

            if not nuevo_nombre or nuevo_precio <= 0:
                flash("Error: nombre y precio válidos son obligatorios", "error")
                return redirect(url_for("editar_inventario", id=id))

            pieza.nombre = nuevo_nombre
            pieza.precio_unitario = nuevo_precio
            db.session.commit()
            flash("Pieza editada correctamente", "success")
            return redirect(url_for("inventario_categoria", categoria=pieza.categoria.capitalize()))

        return render_template("editar_inventario.html", pieza=pieza)


    @app.route("/eliminar_inventario/<int:id>", methods=["POST"])
    def eliminar_inventario(id):
        """
        Elimina una pieza del inventario.
        - Verifica autorización de administrador.
        - Obtiene la pieza por su ID.
        - Borra el registro de la base de datos.
        - Redirige a la categoría correspondiente con mensaje flash.
        """
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
        """
        Muestra el inventario agrupado por categorías.
        - Obtiene todas las categorías distintas.
        - Calcula el estado de cada categoría según stock.
        - Renderiza la plantilla inventario.html con los datos.
        """
        categorias = []
        todas = db.session.query(Inventario.categoria).distinct().all()
        for c in todas:
            nombre_cat = c[0].capitalize()
            piezas = Inventario.query.filter_by(categoria=c[0]).all()

            # Calcular estado de la categoría
            estado = "green"
            for p in piezas:
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
        """
        Muestra las piezas de una categoría específica.
        - Obtiene las piezas filtradas por categoría.
        - Renderiza la plantilla inventario_categoria.html con los datos.
        """
        piezas = Inventario.query.filter_by(categoria=categoria.title()).all()
        return render_template("inventario_categoria.html", categoria=categoria.title(), piezas=piezas)


    @app.route("/restock/<int:id>", methods=["POST"])
    def restock(id):
        """
        Actualiza el stock de una pieza en el inventario.
        - Verifica autorización de administrador.
        - Recibe cantidad desde el formulario.
        - Suma al stock actual y ajusta stock máximo si es necesario.
        - Confirma la operación con mensaje flash.
        """
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
                    inv.cantidad -= p.cantidad   # ← único lugar donde se descuenta
                    inv.reservado -= p.cantidad  # ← liberar reserva
                else:
                    flash(f"Stock insuficiente para {p.producto}, se registró igualmente.", "warning")

            nueva_venta = Venta(
                producto_id      = inv.id if inv else None,
                tipo             = "refaccion" if inv else "servicio",
                cantidad_vendida = p.cantidad,
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
        - Renderiza la plantilla motos.html con la información del cliente.
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
            ratio = p.cantidad / p.stock_maximo if p.stock_maximo > 0 else 0
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
                "categoria": s.categoria.capitalize(),
                "nombre": s.nombre.capitalize(),
                "estado": "green",  # servicios no tienen stock
                "leyenda": "",
                "seleccionable": True,
                "tipo": "servicio",
                "precio": float(s.precio_base)
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
                precio_base=0.0          # se podrá actualizar después
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
        - Si el producto existe en Inventario o Servicios, lo usa directamente.
        - Si no existe, lo agrega como entrada libre (el modal ya gestiona la opción de añadirlo a listas).
        """

        moto = Moto.query.get_or_404(moto_id)

        producto     = request.form.get("producto", "").strip()
        cantidad_str = request.form.get("cantidad", "").strip()
        precio_str   = request.form.get("precio_unitario", "").strip()

        # Validaciones básicas
        if not producto or not cantidad_str:
            flash("Error: producto o cantidad vacíos", "error")
            return redirect(url_for("motos", cliente_id=moto.cliente_id))

        try:
            cantidad = int(cantidad_str)
        except ValueError:
            flash("Error: cantidad inválida", "error")
            return redirect(url_for("motos", cliente_id=moto.cliente_id))

        if not precio_str:
            precio_unitario = 0.0
        else:
            try:
                precio_unitario = float(precio_str)
            except ValueError:
                flash("Error: precio inválido", "error")
                return redirect(url_for("motos", cliente_id=moto.cliente_id))

        # Buscar si el producto existe en Inventario
        inv = Inventario.query.filter_by(nombre=producto).first()
        if inv:
            disponible = inv.cantidad - inv.reservado
            if disponible >= cantidad:
                inv.reservado += cantidad
            else:
               flash("Advertencia: stock insuficiente, se agregó igualmente", "warning")

        serv = Servicio.query.filter_by(nombre=producto).first()

        # Crear registro de presupuesto con total calculado
        nuevo = Presupuesto(
            moto_id        = moto.id,
            producto       = producto,
            cantidad       = cantidad,
            precio_unitario = precio_unitario,
            total          = cantidad * precio_unitario
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

        nuevo = Servicio(tipo=tipo, nombre=nombre, importe=float(importe))
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
        servicios = Servicio.query.all()
        servicios_por_tipo = {}
        for s in servicios:
            if s.tipo not in servicios_por_tipo:
                servicios_por_tipo[s.tipo] = []
            servicios_por_tipo[s.tipo].append(s)
        return render_template("servicios.html", servicios_por_tipo=servicios_por_tipo)

# ==========================
#   GRUPO: PRODUCTO
# ==========================

    @app.route("/buscar_producto")
    def buscar_producto():
        """
        Busca productos y servicios según un término.
        - Recibe el término desde parámetros de la URL.
        - Filtra coincidencias en Inventario y Servicios.
        - Devuelve resultados en formato JSON con datos relevantes.
        """
        termino = request.args.get("q", "").strip()
        resultados = []

        if termino:
            # Buscar en inventario
            inventario = Inventario.query.filter(Inventario.nombre.ilike(f"%{termino}%")).all()
            for item in inventario:
                resultados.append({
                    "id": item.id,
                    "nombre": item.nombre,
                    "precio": item.precio_unitario,
                    "stock": item.stock,
                    "tipo": "refaccion"
                })

            # Buscar en servicios
            servicios = Servicio.query.filter(Servicio.nombre.ilike(f"%{termino}%")).all()
            for s in servicios:
                resultados.append({
                    "id": None,
                    "nombre": s.nombre,
                    "precio": s.precio,
                    "stock": None,
                    "tipo": "servicio"
                })

        return jsonify(resultados)

# ==========================
#   GRUPO: VENTAS
# ==========================

    @app.route("/cerrar_caja", methods=["POST"])
    def cerrar_caja():
        """
        Cierra la caja y reinicia las ventas.
        - Verifica la contraseña de administrador.
        - Si es correcta, elimina todos los registros de la tabla Venta.
        - Confirma la operación con un mensaje flash.
        """
        password = request.form.get("admin_pass")
        if password != "1602":
            flash("Contraseña incorrecta", "error")
            return redirect("/ventas")

        # Reiniciar tabla Ventas
        Venta.query.delete()
        db.session.commit()

        flash("Caja cerrada y ventas reiniciadas", "info")
        return redirect("/ventas")


    @app.route("/ventas")
    def ventas():
        # Totales por tipo
        total_refacciones = db.session.query(db.func.sum(Venta.monto)).filter_by(tipo="refaccion").scalar() or 0
        total_servicios   = db.session.query(db.func.sum(Venta.monto)).filter_by(tipo="servicio").scalar() or 0
        total_general     = total_refacciones + total_servicios

        nomina = total_servicios * 0.20
        lista = Venta.query.all()

        return render_template(
            "ventas.html",
            lista=lista,
            total_refacciones=total_refacciones,
            total_servicios=total_servicios,
            total_general=total_general,
            nomina=nomina
        )

    @app.route("/ventas_resumen")
    def mostrar_ventas():
        """
        Muestra todas las ventas registradas con total general.
        - Consulta todos los registros de la tabla Venta.
        - Calcula el total de ventas sin desglose por tipo.
        - Renderiza la plantilla ventas.html con los datos.
        """
        ventas = Venta.query.all()
        total = sum(v.monto for v in ventas)
        return render_template("ventas.html",
                           ventas=ventas,
                           total_ventas=total)
