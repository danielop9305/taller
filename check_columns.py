import sqlite3

# Conectar a tu base
conn = sqlite3.connect("instance/taller.db")
cursor = conn.cursor()

# Ejecutar el PRAGMA
cursor.execute("PRAGMA table_info(presupuesto);")
columns = cursor.fetchall()

# Mostrar columnas
for col in columns:
    print(col)

conn.close()
