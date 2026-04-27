from fastapi import FastAPI
from backend.app.database import get_connection
from google import genai
from dotenv import load_dotenv
from pathlib import Path
import threading
import os

# carrega o .env da raiz do projeto
env_path = Path(__file__).resolve().parents[2] / '.env'
load_dotenv(dotenv_path=env_path)

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

app = FastAPI()


# rota inicial
@app.get("/")
def home():
    return {"message": "Sprint Works API funcionando"}


# listar produtos
@app.get("/produtos")
def listar_produtos():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM produtos")
    produtos = cursor.fetchall()
    cursor.close()
    conn.close()
    return produtos


# produto mais vendido
@app.get("/produto-mais-vendido")
def produto_mais_vendido():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT p.nome, SUM(v.quantidade) as total
    FROM vendas v
    JOIN produtos p ON v.produto_id = p.id
    GROUP BY p.nome
    ORDER BY total DESC
    LIMIT 1
    """)
    resultado = cursor.fetchone()
    cursor.close()
    conn.close()

    if resultado:
        return {
            "produto": resultado[0],
            "quantidade_vendida": resultado[1]
        }
    else:
        return {"mensagem": "Nenhuma venda encontrada"}


# IA simples (regras)
@app.get("/perguntar")
def perguntar(pergunta: str):
    pergunta = pergunta.lower()
    conn = get_connection()
    cursor = conn.cursor()

    if "produto" in pergunta and "vend" in pergunta:
        cursor.execute("""
        SELECT p.nome, SUM(v.quantidade) as total
        FROM vendas v
        JOIN produtos p ON v.produto_id = p.id
        GROUP BY p.nome
        ORDER BY total DESC
        LIMIT 1
        """)
        resultado = cursor.fetchone()
        cursor.close()
        conn.close()
        return {
            "resposta": f"O produto mais vendido foi {resultado[0]} com {resultado[1]} unidades"
        }

    cursor.close()
    conn.close()
    return {"resposta": "Não sei responder ainda."}


# IA REAL
@app.get("/ia-vendas")
def ia_vendas():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT p.nome, SUM(v.quantidade) as total
    FROM vendas v
    JOIN produtos p ON v.produto_id = p.id
    GROUP BY p.nome
    ORDER BY total DESC
    LIMIT 5
    """)
    dados = cursor.fetchall()
    cursor.close()
    conn.close()

    if not dados:
        return {"mensagem": "Sem dados de vendas"}

    texto = "Dados de vendas:\n"
    for d in dados:
        texto += f"{d[0]}: {d[1]} unidades\n"
    texto += "\nAnalise e diga qual pessa vende mais."

    resposta = {"texto": "Erro ao gerar resposta"}

    def chamar_ia():
        try:
            r = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=texto
            )
            resposta["texto"] = r.text
        except Exception as e:
            erro = str(e)
            if "429" in erro:
                resposta["texto"] = "IA temporariamente indisponível. Tente novamente em alguns segundos."
            else:
                resposta["texto"] = erro

    thread = threading.Thread(target=chamar_ia)
    thread.start()
    thread.join(timeout=10)

    return {"analise": resposta["texto"]}


# listar modelos disponíveis
@app.get("/modelos")
def listar_modelos():
    modelos = client.models.list()
    return {"modelos": [m.name for m in modelos]}