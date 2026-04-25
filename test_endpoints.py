from app import app

# Usamos el test client de Flask
with app.test_client() as client:
    # Probar sugerir producto
    resp_prod = client.get("/sugerir_producto_inventario?q=aceite")
    print("Respuesta sugerir_producto_inventario:", resp_prod.status_code, resp_prod.json)

    # Probar sugerir servicio
    resp_serv = client.get("/sugerir_servicio?q=lavado")
    print("Respuesta sugerir_servicio:", resp_serv.status_code, resp_serv.json)
