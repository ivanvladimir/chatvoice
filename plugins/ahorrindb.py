#!/usr/bin/python
import MySQLdb

def checkUser(user):
    db = MySQLdb.connect(host="localhost",  # your host 
                     user="root",       # username
                     passwd="root",     # password
                     db="ahorrindb")   # name of the database
 
    # Create a Cursor object to execute queries.
    cur = db.cursor()
 
    # Select data from table using SQL query.
    cur.execute("SELECT nombre FROM usuario")
 
    # print the first and second columns      
    for row in cur.fetchall() :
        if(row[0].lower()==user.lower()):
            return 'say "Bienvenido"',str(row[0]),''
        else:
            return 'say "Nuevo usuario"' 

