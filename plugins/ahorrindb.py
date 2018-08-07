#!/usr/bin/python
import MySQLdb
import re
from datetime import date
import datetime
import math
from datetime import timedelta


def conectiondb():
   db = MySQLdb.connect(host="localhost",  # your host 
                     user="root",       # username
                     passwd="root",     # password
                     db="ahorrindb")   # name of the database
   return db

def compareDate(user,objetivo):
    # Create a Cursor object to execute queries.
    db = conectiondb()
    cur = db.cursor()
    # Select data from table using SQL query.
    cur.execute("""SELECT id_usuario FROM usuario WHERE nombre=%s""",[user])
    for us in cur.fetchall():
        ide = us[0];
    cur.execute("""SELECT fecha FROM metas WHERE id_usuario=%s AND nombre=%s""",[ide,objetivo])
    for us in cur.fetchall():
        if us[0] != date.today():
            return 'set_slot nuevoDia "si"'
        else:
            return 'set_slot nuevoDia "no"'




##########################################GASTOS-INGRESOS DIARIOS - 

def balanceDeAyer(user,objetivoo):
    # Create a Cursor object to execute queries.
    db = conectiondb()
    cur = db.cursor()
    # Select data from table using SQL query.
    cur.execute("""SELECT id_usuario FROM usuario WHERE nombre=%s""",[user])
    for us in cur.fetchall():
        idee = us[0];
    cur.execute("""SELECT id_meta,monto_diario,monto_meta,monto_ahorrado,terminacion FROM metas WHERE id_usuario=%s AND nombre=%s""",[idee,objetivoo])
    for us in cur.fetchall():
        ide = us[0]
        monto = us[1]
        objetivo = us[2]
        ahorrado = us[3]
        terminacion = us[4]
    cur.execute("""SELECT monto FROM ingresos_diarios WHERE id_meta=%s AND fecha=%s""",[ide,date.today() - timedelta(days=1)])
    balance=0;
    for us in cur.fetchall():
        balance = balance + us[0]
    cur.execute("""SELECT monto FROM gastos_diarios WHERE id_meta=%s AND fecha=%s""",[ide,date.today() - timedelta(days=1)])
    for us in cur.fetchall():
        balance = balance - us[0]
    ahorrado=ahorrado+balance
    montoAyer=monto
    diario=int(int(objetivo)-int(ahorrado))/int((terminacion-date.today()).days)
    cur.execute("""UPDATE metas SET monto_ahorrado=%s ,monto_diario=%s,fecha=%s WHERE id_usuario=%s AND nombre=%s""",[ahorrado,diario,date.today(),idee,objetivoo])
    db.commit()
    if balance < int(montoAyer):
        return 'set_slot cumplioAhorro "no"'
    else:
        return 'set_slot cumplioAhorro "si"'
    
def addGasto(user,objetivo,concepto,monto):
    # Create a Cursor object to execute queries.
    db = conectiondb()
    cur = db.cursor()
    # Select data from table using SQL query.
    cur.execute("""SELECT id_usuario FROM usuario WHERE nombre=%s""",[user])
    for us in cur.fetchall():
        ide = us[0];
    cur.execute("""SELECT id_meta FROM metas WHERE id_usuario=%s AND nombre=%s""",[ide,objetivo])
    for us in cur.fetchall():
        ide = us[0];
    monto = re.sub("[^0-9]", "",monto)
    cur.execute("""INSERT INTO gastos_diarios (id_meta,concepto,monto,fecha) VALUES(%s,%s,%s,%s)""", [ide,concepto,monto,date.today()])
    db.commit();

def addIngreso(user,objetivo,concepto,monto):
    # Create a Cursor object to execute queries.
    db = conectiondb()
    cur = db.cursor()
    # Select data from table using SQL query.
    cur.execute("""SELECT id_usuario FROM usuario WHERE nombre=%s""",[user])
    for us in cur.fetchall():
        ide = us[0];
    cur.execute("""SELECT id_meta FROM metas WHERE id_usuario=%s AND nombre=%s""",[ide,objetivo])
    for us in cur.fetchall():
        ide = us[0];
    monto = re.sub("[^0-9]", "",monto)
    cur.execute("""INSERT INTO ingresos_diarios (id_meta,concepto,monto,fecha) VALUES(%s,%s,%s,%s)""", [ide,concepto,monto,date.today()])
    db.commit();









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
    diario=int(int(monto)-int(ahorro))/int((s-date.today()).days)
    diario=math.ceil(diario)
    cur.execute("""INSERT INTO metas (id_usuario,inicio,terminacion,monto_meta,monto_ahorrado,nombre,monto_diario,fecha) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)""", [ide,date.today(),s,monto,ahorro,goal,diario,date.today()])
    db.commit();
    return 'set_slot montoDiario '+str(diario)

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

def setDiario(user,objetivo):
    # Create a Cursor object to execute queries.
    db = conectiondb()
    cur = db.cursor()
    # Select data from table using SQL query.
    cur.execute("""SELECT id_usuario FROM usuario WHERE nombre=%s""",[user])
    for us in cur.fetchall():
        ide = us[0];
    cur.execute("""SELECT monto_diario FROM metas WHERE id_usuario=%s AND nombre=%s""",[ide,objetivo])
    for us in cur.fetchall():
        monto = us[0];
    return 'set_slot montoDiario "'+str(monto)+'"'

















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
    



