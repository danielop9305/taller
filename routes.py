from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from datetime import datetime
from models import db, Inventario, Compatibilidad, Venta, Cliente, Servicio, Pago, Moto, Caja, Presupuesto


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

#ADMINISTRADOR
 
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

     
# CLIENTES
    @app.route("/clientes")
    def clientes():
        lista = Cliente.query.all()
        return render_template("clientes.html", clientes=lista)

    @app.route("/agregar_cliente", methods=["GET", "POST"])
    def agregar_cliente():
        if request.method == "POST":
            nombre = request.form["nombre"].strip()
            celular = request.form["celular"].strip()
            modelo = request.form["modelo"].strip()

            if not nombre or not celular or not modelo:
                flash("Todos los campos son obligatorios", "error")
                return redirect("/clientes")

            nuevo_cliente = Cliente(nombre=nombre, celular=celular)
            db.session.add(nuevo_cliente)
            db.session.commit()

            nueva_moto = Moto(modelo=modelo, cliente_id=nuevo_cliente.id, estado=1, confirmado=False)
            db.session.add(nueva_moto)
            db.session.commit()

            flash("Cliente registrado correctamente", "success")
            return redirect(url_for("clientes"))
        return render_template("agregar_cliente.html")

    @app.route("/eliminar_cliente/<int:id>", methods=["POST"])
    def eliminar_cliente(id):
        cliente = Cliente.query.get_or_404(id)
        db.session.delete(cliente)
        db.session.commit()
        flash("Cliente eliminado", "success")
        return redirect(url_for("clientes"))

#COMPATIBILIDAD
    @app.route("/agregar_compatibilidad/<int:id>", methods=["POST"])
    def agregar_compatibilidad(id):
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
        if not session.get("admin_autorizado"):
            flash("Acción restringida. Ingresa contraseña de admin.", "error")
            return redirect(url_for("inventario"))

        comp = Compatibilidad.query.get_or_404(id)
        categoria = comp.refaccion.categoria.capitalize()
        db.session.delete(comp)
        db.session.commit()
        flash("Compatibilidad eliminada correctamente", "success")

        return redirect(url_for("inventario_categoria", categoria=categoria))



# MOTOS
    @app.route("/motos/<int:cliente_id>")
    def motos(cliente_id):
        cliente = Cliente.query.get_or_404(cliente_id)
        return render_template("motos.html", cliente=cliente)

    @app.route("/avanzar_estado/<int:moto_id>", methods=["POST"])
    def avanzar_estado(moto_id):
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
        moto = Moto.query.get_or_404(moto_id)
        cliente = Cliente.query.get_or_404(moto.cliente_id)

        db.session.delete(cliente)
        db.session.commit()

        flash("Cliente eliminado tras la entrega de la moto", "success")
        return redirect(url_for("clientes"))







#PRESUPUESTO
    @app.route("/presupuesto/<int:moto_id>")
    def presupuesto(moto_id):
        moto = Moto.query.get_or_404(moto_id)
        total = sum(p.total for p in moto.presupuestos)
        return render_template("presupuesto.html", moto=moto, total=total)

    @app.route("/agregar_presupuesto/<int:moto_id>", methods=["POST"])
    def agregar_presupuesto(moto_id):
        moto = Moto.query.get_or_404(moto_id)
        producto_nombre = request.form["producto"].strip()
        cantidad = int(request.form["cantidad"])
        precio_unitario = float(request.form["precio_unitario"])

        # Buscar producto en inventario
        item = Inventario.query.filter_by(nombre=producto_nombre).first()
        if item:
            # Validar stock
            if item.stock < cantidad:
                flash("No hay suficiente stock para este producto", "danger")
                return redirect(url_for("presupuesto", moto_id=moto.id))
            # Usar precio de inventario, no permitir edición
            precio_unitario = item.precio_unitario
            producto_id = item.id
        else:
            # Producto no existe en inventario → permitir precio manual
            producto_id = None

        total = cantidad * precio_unitario

        nuevo = Presupuesto(
            moto=moto,
            producto=producto_nombre,
            cantidad=cantidad,
            total=total,
            producto_id=producto_id
        )
        db.session.add(nuevo)
        db.session.commit()

        flash("Producto agregado al presupuesto", "success")
        return redirect(url_for("presupuesto", moto_id=moto.id))


    @app.route("/eliminar_presupuesto/<int:presupuesto_id>", methods=["POST"])
    def eliminar_presupuesto(presupuesto_id):
        presupuesto = Presupuesto.query.get_or_404(presupuesto_id)
        moto_id = presupuesto.moto_id
        db.session.delete(presupuesto)
        db.session.commit()
        return redirect(url_for("presupuesto", moto_id=moto_id))


#SERVICIOS

    @app.route("/servicios")
    def servicios():
        servicios = Servicio.query.all()
        servicios_por_tipo = {}
        for s in servicios:
            if s.tipo not in servicios_por_tipo:
                servicios_por_tipo[s.tipo] = []
            servicios_por_tipo[s.tipo].append(s)
        return render_template("servicios.html", servicios_por_tipo=servicios_por_tipo)

    @app.route("/agregar_servicio", methods=["POST"])
    def agregar_servicio():
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

    
# -----------------------------------
# INVENTARIO
# -----------------------------------
    @app.route("/inventario")
    def inventario():
        categorias = []
        # Obtener todas las categorías distintas
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
        piezas = Inventario.query.filter_by(categoria=categoria.title()).all()
        return render_template("inventario_categoria.html", categoria=categoria.title(), piezas=piezas)

    @app.route("/agregar_pieza", methods=["POST"])
    def agregar_pieza():
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
    
    @app.route("/editar_inventario/<int:id>", methods=["GET", "POST"])
    def editar_inventario(id):
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





#PAGOS
    @app.route("/pagos")
    def pagos():
        lista = Pago.query.all()
        return render_template("pagos.html", lista=lista)
    
    @app.route("/registrar_pago", methods=["POST"])
    def registrar_pago():
        tipo = request.form["tipo"]
        monto = float(request.form["monto"])
        fecha = request.form["fecha"]
        nuevo = Pago(tipo=tipo, monto=monto, fecha=fecha)
        db.session.add(nuevo)
        db.session.commit()
        return redirect(url_for("pagos"))
    
# -----------------------------------
# Ventas
# -----------------------------------
    @app.route("/ventas")
    def ventas():
        lista = Venta.query.all()

        total_refacciones = sum(v.monto for v in lista if v.tipo == "refaccion")
        total_mano_obra = sum(v.monto for v in lista if v.tipo == "mano_obra")
        total_general = total_refacciones + total_mano_obra

        return render_template(
            "ventas.html",
            lista=lista,
            total_refacciones=total_refacciones,
            total_mano_obra=total_mano_obra,
            total_general=total_general
        )

# -----------------------------------
# Carrito
# -----------------------------------
    @app.route("/carrito")
    def carrito():
        carrito = session.get("carrito", [])
        total_carrito = sum(item["total"] for item in carrito)
        return render_template("carrito.html", carrito=carrito, total_carrito=total_carrito)


    @app.route("/agregar_carrito", methods=["POST"])
    def agregar_al_carrito():
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

        # Actualizar inventario
        producto.cantidad = max(producto.cantidad - cantidad, 0)
        db.session.commit()

        flash("Producto agregado al carrito", "success")
        return redirect(url_for("carrito"))
    
    @app.route("/agregar_servicio_carrito/<int:servicio_id>")
    def agregar_servicio_carrito(servicio_id):
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

    @app.route("/eliminar_del_carrito/<int:id>", methods=["POST"])
    def eliminar_del_carrito(id):
        carrito = session.get("carrito", [])
        carrito = [item for item in carrito if item["id"] != id]
        session["carrito"] = carrito
        return redirect(url_for("carrito"))

    @app.route("/cancelar_carrito", methods=["POST"])
    def cancelar_carrito():
        session["carrito"] = []
        return redirect(url_for("carrito"))

    @app.route("/sugerir_producto")
    def sugerir_producto():
        query = request.args.get("q", "").lower()
        resultados = Inventario.query.filter(Inventario.nombre.ilike(f"%{query}%")).all()

        sugerencias = []
        for p in resultados:
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
                "seleccionable": seleccionable
            })

        return jsonify(sugerencias)

    @app.route("/confirmar_venta", methods=["POST"])
    def confirmar_venta():
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

        for item in carrito:
            # Solo actualizar inventario si es refacción
            if item["tipo"] == "refaccion" and item["producto_id"]:
                producto = Inventario.query.get(item["producto_id"])
                if producto:
                    producto.cantidad = max(producto.cantidad - int(item["cantidad"]), 0)

            # Registrar venta (refacción o servicio)
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


    @app.route("/ventas")
    def mostrar_ventas():
        ventas = Venta.query.all()
        total = sum(v.monto for v in ventas)
        return render_template("ventas.html",
                               ventas=ventas,
                               total_ventas=total)

    @app.route("/cerrar_caja", methods=["POST"])
    def cerrar_caja():
        password = request.form.get("admin_pass")
        if password != "1602":
            flash("Contraseña incorrecta", "error")
            return redirect("/ventas")

        # Reiniciar tabla Ventas
        Venta.query.delete()
        db.session.commit()

        flash("Caja cerrada y ventas reiniciadas", "info")
        return redirect("/ventas")

#PRODUCTO
    @app.route("/buscar_producto")
    def buscar_producto():
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

#DASHBOARD
    @app.route("/dashboard")
    def dashboard():
        total_ventas = sum([v.monto for v in Venta.query.all()])
        total_pagos = sum([p.monto for p in Pago.query.all()])
        stock_bajo = Inventario.query.filter(Inventario.cantidad < 5).all()
        return render_template("dashboard.html", ventas=total_ventas, pagos=total_pagos, stock=stock_bajo)
    
