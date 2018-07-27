import _mysql

db=_mysql.connect(host="localhost",user="usuario",
                  passwd="root",db="ahorrindb")

db.query("""SELECT nombre,contrasena,ingreso_mensual FROM usuario""")

r=db.store_result()

print(r.fetch_row(maxrows=0))

"""

from sqlalchemy import create_engine

engine = create_engine('mysql://root:root@localhost')

"""



