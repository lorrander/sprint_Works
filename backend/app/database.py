import psycopg2
from dotenv import load_dotenv
from pathlib import Path
import os

env_path = Path(__file__).resolve().parents[2] / '.env'
load_dotenv(dotenv_path=env_path)

def get_connection():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME", "sprintworks"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT", "5432"),
        connect_timeout=5
    )
    return conn

if __name__ == "__main__":
    try:
        conn = get_connection()
        print("Conexão com o banco realizada com sucesso!")
        conn.close()
    except Exception as e:
        print("Erro ao conectar:", e)