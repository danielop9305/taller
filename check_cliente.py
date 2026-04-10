import sqlite3

# Conexión a tu base
conn = sqlite3.connect("instance/taller.db")

# Consulta de columnas de la tabla cliente
cursor = conn.execute("PRAGMA table_info(cliente)")

print("Columnas en la tabla cliente:")
for row in cursor.fetchall():
    print(row)

conn.close()
