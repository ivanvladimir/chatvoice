#!/usr/bin/python
import MySQLdb
import re

def checkUser(user):
    db = MySQLdb.connect(host="localhost",  # your host 
                     user="root",       # username
                     passwd="root",     # password
                     db="ahorrindb")   # name of the database
 
    # Create a Cursor object to execute queries.
    cur = db.cursor()
 
    # Select data from table using SQL query.
    cur.execute("SELECT nombre FROM usuario")
    existe = False;
    # print the first and second columns      
    for row in cur.fetchall() :
        if(row[0].lower()==user.lower()):
            return 'say "Bienvenido '+str(row[0])+'"'
    
    return 'set_slot usuario "nulo"'


def addUser(user):
    db = MySQLdb.connect(host="localhost",  # your host 
                     user="root",       # username
                     passwd="root",     # password
                     db="ahorrindb")   # name of the database
    cur = db.cursor()
    cur.execute("""INSERT INTO usuario (nombre,contrasena,ingreso_mensual,gasto_mensual) VALUES(%s,"nula",0,0)""", [user])
    db.commit();

def setGastos(gasto,user):
    gasto=re.sub("[^0-9]", "",gasto)

    db = MySQLdb.connect(host="localhost",  # your host 
                     user="root",       # username
                     passwd="root",     # password
                     db="ahorrindb")   # name of the database
    cur = db.cursor()
    cur.execute("""UPDATE usuario SET gasto_mensual=%s WHERE nombre=%s""", [gasto,user])
    db.commit()
    return "set_slot gastosM "+str(gasto)

def setIngresos(ingreso,user):
    ingreso=re.sub("[^0-9]", "",ingreso)
    db = MySQLdb.connect(host="localhost",  # your host 
                     user="root",       # username
                     passwd="root",     # password
                     db="ahorrindb")   # name of the database
    cur = db.cursor()
    cur.execute("""UPDATE usuario SET ingreso_mensual=%s WHERE nombre=%s""", [ingreso,user])
    db.commit()
    return "set_slot ingresosM "+str(ingreso)
    



