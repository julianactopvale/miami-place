from flask import Flask, render_template, request, redirect, url_for, session
import json
import os
from datetime import datetime

app = Flask(__name__)

# 🔑 ESTA É A CHAVE DA SESSÃO (NÃO É A SENHA DO DONO)
app.secret_key = "2112miami"  # pode deixar assim ou trocar

ARQUIVO_DADOS = "avaliacoes.json"

# --------- CARREGAR DADOS ---------
if os.path.exists(ARQUIVO_DADOS):
    try:
        with open(ARQUIVO_DADOS, "r", encoding="utf-8") as f:
            reviews = json.load(f)
    except json.JSONDecodeError:
        reviews = []
else:
    reviews = []


def salvar_dados():
    """Salva as avaliações no arquivo JSON."""
    with open(ARQUIVO_DADOS, "w", encoding="utf-8") as f:
        json.dump(reviews, f, indent=4, ensure_ascii=False)


# --------- PÁGINA DE AVALIAÇÃO ---------
@app.route('/', methods=['GET', 'POST'])
def index():
    global reviews

    if request.method == 'POST':
        indicacao_str = request.form.get('indicacao') or "0"
        try:
            indicacao = int(indicacao_str)
        except ValueError:
            indicacao = 0

        nome_cliente = request.form.get("nome_cliente") or ""
        telefone_cliente = request.form.get("telefone_cliente") or ""

        review = {
            "data": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "nome_cliente": nome_cliente,
            "telefone_cliente": telefone_cliente,
            "colaborador": request.form.get("colaborador"),
            "educacao": request.form.get("educacao"),
            "clareza": request.form.get("clareza"),
            "transparencia": request.form.get("transparencia"),
            "organizacao": request.form.get("organizacao"),
            "finalizacao": request.form.get("finalizacao"),
            "indicacao": indicacao,
            "melhoria": request.form.get("melhoria"),
        }

        reviews.append(review)
        salvar_dados()

        return redirect(url_for("index"))

    total_reviews = len(reviews)

    media_indicacao = None
    if total_reviews > 0:
        media_indicacao = sum(r.get("indicacao", 0) for r in reviews) / total_reviews

    return render_template(
        "index.html",
        reviews=reviews,
        media_indicacao=media_indicacao,
        total_reviews=total_reviews,
    )


# --------- DASHBOARD COM SENHA ---------
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    # 🔒 PRIMEIRO: VERIFICA SE ESTÁ LOGADO
    if not session.get("autenticado"):
        if request.method == "POST":
            senha = request.form.get("senha")

            # 👇 AQUI É A SENHA DO DONO
            # Troque "2112miami" para a senha que você quiser
            if senha == "2112miami":
                session["autenticado"] = True
                return redirect(url_for("dashboard"))
            else:
                return render_template("login.html", erro="Senha incorreta")

        # se for GET (primeira vez), mostra tela de login
        return render_template("login.html")

    # 🔓 DAQUI PRA BAIXO É O DASHBOARD MESMO (só entra se estiver autenticado)
    total_reviews = len(reviews)

    # média geral
    media_indicacao = None
    if total_reviews > 0:
        media_indicacao = sum(r.get("indicacao", 0) for r in reviews) / total_reviews

    # estatísticas por colaborador
    por_colab = {}
    for r in reviews:
        nome = r.get("colaborador") or "Não informado"

        if nome not in por_colab:
            por_colab[nome] = {
                "quantidade": 0,
                "soma": 0,
                "qtd_notas": 0
            }

        por_colab[nome]["quantidade"] += 1

        nota = r.get("indicacao")
        if isinstance(nota, int):
            por_colab[nome]["soma"] += nota
            por_colab[nome]["qtd_notas"] += 1

    estatisticas_colab = []
    for nome, dados in por_colab.items():
        media = None
        if dados["qtd_notas"] > 0:
            media = dados["soma"] / dados["qtd_notas"]

        estatisticas_colab.append({
            "nome": nome,
            "quantidade": dados["quantidade"],
            "media": media
        })

    # indicadores por critério
    def contar(campo):
        base = {"excelente": 0, "regular": 0, "ruim": 0}
        for r in reviews:
            valor = r.get(campo)
            if valor in base:
                base[valor] += 1
        return base

    indicadores = {
        "educacao": contar("educacao"),
        "clareza": contar("clareza"),
        "transparencia": contar("transparencia"),
        "organizacao": contar("organizacao"),
        "finalizacao": contar("finalizacao"),
    }

    return render_template(
        "dashboard.html",
        total_reviews=total_reviews,
        media_indicacao=media_indicacao,
        estatisticas_colab=estatisticas_colab,
        indicadores=indicadores,
        reviews=reviews,
    )


if __name__ == "__main__":
    app.run()
    