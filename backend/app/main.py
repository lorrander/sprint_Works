from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.database import get_connection
from google import genai
from dotenv import load_dotenv
from pathlib import Path
import threading
import os

env_path = Path(__file__).resolve().parents[2] / '.env'
load_dotenv(dotenv_path=env_path)

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"message": "Sprint Works API funcionando"}


@app.get("/produtos")
def listar_produtos():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM produtos")
    produtos = cursor.fetchall()
    cursor.close()
    conn.close()
    return produtos


@app.get("/estoque")
def ver_estoque():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT nome, estoque FROM produtos ORDER BY estoque ASC")
    produtos = cursor.fetchall()
    cursor.close()
    conn.close()
    return [{"produto": p[0], "estoque": p[1]} for p in produtos]


@app.get("/estoque-alerta")
def estoque_alerta(minimo: int = 20):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT nome, estoque FROM produtos WHERE estoque <= %s ORDER BY estoque ASC", (minimo,))
    produtos = cursor.fetchall()
    cursor.close()
    conn.close()

    if not produtos:
        return {"mensagem": f"Nenhum produto com estoque abaixo de {minimo} unidades ✅"}

    return {
        "alerta": f"Produtos com estoque abaixo de {minimo} unidades",
        "produtos": [{"produto": p[0], "estoque": p[1]} for p in produtos]
    }


@app.get("/metas")
def ver_metas(mes: int = None, ano: int = None):
    conn = get_connection()
    cursor = conn.cursor()

    if mes and ano:
        cursor.execute("SELECT vendedor, meta_mensal, mes, ano FROM metas WHERE mes = %s AND ano = %s", (mes, ano))
    else:
        cursor.execute("SELECT vendedor, meta_mensal, mes, ano FROM metas ORDER BY ano DESC, mes DESC")

    metas = cursor.fetchall()
    cursor.close()
    conn.close()
    return [{"vendedor": m[0], "meta_mensal": m[1], "mes": m[2], "ano": m[3]} for m in metas]


@app.get("/metas-desempenho")
def metas_desempenho(mes: int = None, ano: int = None):
    from datetime import datetime
    mes = mes or datetime.now().month
    ano = ano or datetime.now().year

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT vendedor, meta_mensal FROM metas WHERE mes = %s AND ano = %s", (mes, ano))
    metas = cursor.fetchall()

    cursor.execute("""
    SELECT vendedor, SUM(valor_total) as total_vendido
    FROM vendas
    WHERE EXTRACT(MONTH FROM data) = %s AND EXTRACT(YEAR FROM data) = %s
    GROUP BY vendedor
    """, (mes, ano))
    vendas = cursor.fetchall()

    cursor.close()
    conn.close()

    vendas_dict = {v[0]: v[1] for v in vendas}

    resultado = []
    for m in metas:
        vendedor = m[0]
        meta = float(m[1])
        vendido = float(vendas_dict.get(vendedor, 0))
        percentual = round((vendido / meta * 100), 1) if meta > 0 else 0
        status = "✅ Meta atingida" if vendido >= meta else "⚠️ Abaixo da meta"

        resultado.append({
            "vendedor": vendedor,
            "meta": meta,
            "vendido": vendido,
            "percentual": f"{percentual}%",
            "status": status
        })

    return {"mes": mes, "ano": ano, "desempenho": resultado}


@app.post("/metas")
def criar_meta(vendedor: str, meta_mensal: float, mes: int, ano: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO metas (vendedor, meta_mensal, mes, ano) VALUES (%s, %s, %s, %s)
    """, (vendedor, meta_mensal, mes, ano))
    conn.commit()
    cursor.close()
    conn.close()
    return {"mensagem": f"Meta de R${meta_mensal} criada para {vendedor} em {mes}/{ano}"}


@app.get("/relatorio")
def relatorio_vendas(data_inicio: str, data_fim: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT p.nome, SUM(v.quantidade) as total_qtd, SUM(v.valor_total) as total_valor
    FROM vendas v
    JOIN produtos p ON v.produto_id = p.id
    WHERE DATE(v.data) BETWEEN %s AND %s
    GROUP BY p.nome
    ORDER BY total_valor DESC
    """, (data_inicio, data_fim))
    por_produto = cursor.fetchall()

    cursor.execute("""
    SELECT vendedor, COUNT(*) as total_vendas, SUM(valor_total) as receita
    FROM vendas
    WHERE DATE(data) BETWEEN %s AND %s
    GROUP BY vendedor
    ORDER BY receita DESC
    """, (data_inicio, data_fim))
    por_vendedor = cursor.fetchall()

    cursor.execute("""
    SELECT COUNT(*) as total_vendas, SUM(valor_total) as receita_total
    FROM vendas
    WHERE DATE(data) BETWEEN %s AND %s
    """, (data_inicio, data_fim))
    totais = cursor.fetchone()

    cursor.close()
    conn.close()

    return {
        "periodo": {"inicio": data_inicio, "fim": data_fim},
        "totais": {"total_vendas": totais[0], "receita_total": totais[1]},
        "por_produto": [{"produto": p[0], "quantidade": p[1], "valor": p[2]} for p in por_produto],
        "por_vendedor": [{"vendedor": v[0], "total_vendas": v[1], "receita": v[2]} for v in por_vendedor]
    }


@app.get("/vendas-hoje")
def vendas_hoje():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT COUNT(*) as total_vendas, SUM(valor_total) as receita
    FROM vendas
    WHERE DATE(data) = CURRENT_DATE
    """)
    resultado = cursor.fetchone()
    cursor.close()
    conn.close()
    return {"total_vendas": resultado[0], "receita_hoje": resultado[1]}


@app.get("/ranking-vendedores")
def ranking_vendedores():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT vendedor, COUNT(*) as total_vendas, SUM(valor_total) as receita_total
    FROM vendas
    GROUP BY vendedor
    ORDER BY receita_total DESC
    """)
    resultado = cursor.fetchall()
    cursor.close()
    conn.close()
    return [{"vendedor": r[0], "total_vendas": r[1], "receita_total": r[2]} for r in resultado]


@app.get("/perguntar-ia")
def perguntar_ia(pergunta: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT nome, preco, custo, estoque FROM produtos")
    produtos = cursor.fetchall()

    cursor.execute("""
    SELECT p.nome, v.quantidade, v.valor_total, v.vendedor, v.data
    FROM vendas v
    JOIN produtos p ON v.produto_id = p.id
    ORDER BY v.data DESC
    LIMIT 50
    """)
    vendas = cursor.fetchall()

    cursor.execute("""
    SELECT vendedor, COUNT(*) as total_vendas, SUM(valor_total) as receita_total
    FROM vendas
    GROUP BY vendedor
    ORDER BY receita_total DESC
    """)
    ranking = cursor.fetchall()

    cursor.execute("""
    SELECT COUNT(*) as total_vendas, SUM(valor_total) as receita
    FROM vendas
    WHERE DATE(data) = CURRENT_DATE
    """)
    hoje = cursor.fetchone()

    from datetime import datetime
    mes_atual = datetime.now().month
    ano_atual = datetime.now().year

    cursor.execute("SELECT vendedor, meta_mensal FROM metas WHERE mes = %s AND ano = %s", (mes_atual, ano_atual))
    metas = cursor.fetchall()

    contexto = "Você é um assistente de vendas. Responda em português de forma clara e objetiva.\n\n"

    contexto += "=== PRODUTOS E ESTOQUE ===\n"
    for p in produtos:
        alerta = " ⚠️ ESTOQUE BAIXO" if p[3] <= 20 else ""
        contexto += f"- {p[0]}: preço R${p[1]}, custo R${p[2]}, estoque {p[3]} unidades{alerta}\n"

    contexto += "\n=== METAS DO MÊS ===\n"
    for m in metas:
        contexto += f"- {m[0]}: meta R${m[1]}\n"

    contexto += "\n=== RANKING DE VENDEDORES ===\n"
    for r in ranking:
        contexto += f"- {r[0]}: {r[1]} vendas, receita total R${r[2]}\n"

    contexto += f"\n=== VENDAS HOJE ===\n"
    contexto += f"- Total de vendas: {hoje[0]}, Receita: R${hoje[1]}\n"

    contexto += "\n=== ÚLTIMAS 50 VENDAS ===\n"
    for v in vendas:
        contexto += f"- {v[0]}: {v[1]} unidades, R${v[2]}, vendedor: {v[3]}, data: {v[4]}\n"

    contexto += f"\n=== PERGUNTA ===\n{pergunta}"

    resposta = {"texto": "Erro ao gerar resposta"}

    def chamar_ia():
        try:
            r = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=contexto
            )
            resposta["texto"] = r.text

            conn2 = get_connection()
            cursor2 = conn2.cursor()
            cursor2.execute(
                "INSERT INTO historico_ia (pergunta, resposta) VALUES (%s, %s)",
                (pergunta, resposta["texto"])
            )
            conn2.commit()
            cursor2.close()
            conn2.close()

        except Exception as e:
            resposta["texto"] = str(e)

    thread = threading.Thread(target=chamar_ia)
    thread.start()
    thread.join(timeout=15)

    cursor.close()
    conn.close()

    return {"resposta": resposta["texto"]}


@app.get("/historico-ia")
def historico_ia(limite: int = 10):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT pergunta, resposta, data
    FROM historico_ia
    ORDER BY data DESC
    LIMIT %s
    """, (limite,))
    historico = cursor.fetchall()
    cursor.close()
    conn.close()
    return [{"pergunta": h[0], "resposta": h[1], "data": h[2]} for h in historico]


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
    texto += "\nAnalise e diga qual produto vende mais."

    resposta = {"texto": "Erro ao gerar resposta"}

    def chamar_ia():
        try:
            r = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=texto
            )
            resposta["texto"] = r.text
        except Exception as e:
            resposta["texto"] = str(e)

    thread = threading.Thread(target=chamar_ia)
    thread.start()
    thread.join(timeout=15)

    return {"analise": resposta["texto"]}


@app.get("/modelos")
def listar_modelos():
    modelos = client.models.list()
    return {"modelos": [m.name for m in modelos]}