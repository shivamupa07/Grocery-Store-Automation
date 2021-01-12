import mysql.connector
def Connection():
    conn = mysql.connector.connect(host="localhost", user="root",passwd="1234")
    cursor = conn.cursor()
    cursor.execute("show databases")
    try:
        if ('try_veggies',) in cursor:
            con = mysql.connector.connect(host="localhost", user="root",passwd="1234",database="try_veggies")
            return con

    except Exception as e:
        print("Error: ",e)
