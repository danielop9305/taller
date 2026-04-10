import sqlite3

conn = sqlite3.connect("instance/taller.db")
conn.execute("DROP TABLE IF EXISTS _alembic_tmp_moto")
conn.commit()
conn.close()

print("Tabla temporal eliminada correctamente.")
