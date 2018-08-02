#!/usr/bin/python
import MySQLdb
import re
from datetime import date
import datetime




def conectiondb():
   db = MySQLdb.connect(host="localhost",  # your host 
                     user="root",       # username
                     passwd="root",     # password
                     db="ahorrindb")   # name of the database
   return db




###########################################OBJETIVO-GOAL
def checkGoal(user):
    # Create a Cursor object to execute queries.
    db = conectiondb()
    cur = db.cursor()
 
    # Select data from table using SQL query.
    cur.execute("""SELECT id_usuario FROM usuario WHERE nombre=%s""",[user])
    for us in cur.fetchall():
        ide = us[0];

    cur.execute("""SELECT * FROM metas WHERE id_usuario=%s""",[ide])
    result=cur.fetchall()
    if len(result)==0:
        return 'set_slot objetivo "primero"' 
    else:
        for us in result:
             inicio = us[2]
             fin = us[3]
             if(inicio<=date.today() and fin>=date.today()):
                 return 'set_slot objetivo "'+str(us[6])+'"'

        return 'set_slot objetivo "ninguno"'


def addGoal(goal,user,dia,mes,año,monto,ahorro):
    db = conectiondb()
    cur = db.cursor()
    cur.execute("""SELECT id_usuario FROM usuario WHERE nombre=%s""",[user])
    for us in cur.fetchall():
        ide = us[0];
    dia=re.sub("[^0-9]", "",dia)
    año=re.sub("[^0-9]", "",año)
    monto=re.sub("[^0-9]", "",monto)
    ahorro=re.sub("[^0-9]", "",ahorro)
    s=datetime.date(int(año),int(mes),int(dia))
    
    cur.execute("""INSERT INTO metas (id_usuario,inicio,terminacion,monto_meta,monto_ahorrado,nombre) VALUES(%s,%s,%s,%s,%s,%s)""", [ide,date.today(),s,monto,ahorro,goal])
    db.commit(); 

def setTerminacion(dia,mes,año,goal):
    dia=re.sub("[^0-9]", "",dia)
    año=re.sub("[^0-9]", "",año)
    s=datetime.date(int(año),int(mes),int(dia))
    db = conectiondb()
    cur = db.cursor()
    cur.execute("""UPDATE metas SET terminacion=%s WHERE nombre=%s""", [s,goal])
    db.commit()

def setMonto(user,objetivo):
    # Create a Cursor object to execute queries.
    db = conectiondb()
    cur = db.cursor()
    # Select data from table using SQL query.
    cur.execute("""SELECT id_usuario FROM usuario WHERE nombre=%s""",[user])
    for us in cur.fetchall():
        ide = us[0];
    cur.execute("""SELECT monto_meta FROM metas WHERE id_usuario=%s AND nombre=%s""",[ide,objetivo])
    for us in cur.fetchall():
        monto = us[0];
    return 'set_slot monto "'+str(monto)+'"'

def setAhorro(user,objetivo):
    # Create a Cursor object to execute queries.
    db = conectiondb()
    cur = db.cursor()
    # Select data from table using SQL query.
    cur.execute("""SELECT id_usuario FROM usuario WHERE nombre=%s""",[user])
    for us in cur.fetchall():
        ide = us[0];
    cur.execute("""SELECT monto_ahorrado FROM metas WHERE id_usuario=%s AND nombre=%s""",[ide,objetivo])
    for us in cur.fetchall():
        ahorro = us[0];
    return 'set_slot ahorro "'+str(ahorro)+'"'

###########################################USUARIO-USER
def checkUser(user):
    db = conectiondb()
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
    db = conectiondb()
    cur = db.cursor()
    cur.execute("""INSERT INTO usuario (nombre,contrasena,ingreso_mensual,gasto_mensual) VALUES(%s,"nula",0,0)""", [user])
    db.commit();

def setGastos(gasto,user):
    gasto=re.sub("[^0-9]", "",gasto)

    db = conectiondb()
    cur = db.cursor()
    cur.execute("""UPDATE usuario SET gasto_mensual=%s WHERE nombre=%s""", [gasto,user])
    db.commit()
    return "set_slot gastosM "+str(gasto)

def setIngresos(ingreso,user):
    ingreso=re.sub("[^0-9]", "",ingreso)
    db = conectiondb()
    cur = db.cursor()
    cur.execute("""UPDATE usuario SET ingreso_mensual=%s WHERE nombre=%s""", [ingreso,user])
    db.commit()
    return "set_slot ingresosM "+str(ingreso)
    



