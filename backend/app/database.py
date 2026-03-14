import psycopg2

def get_connection():
    conn = psycopg2.connect(
        host="localhost",
        database="sprintworks",
        user="postgres",
        password="lorrander2004"
    )
    return conn


# teste de conexão
if __name__ == "__main__":
    try:
        conn = get_connection()
        print("Conexão com o banco realizada com sucesso!")
        conn.close()
    except Exception as e:
        print("Erro ao conectar:", e)
