from flask import Flask, render_template, request, redirect, url_for, session
import json
import os
from datetime import datetime

app = Flask(__name__)

# chave da sessão (não é a senha do dono)
app.secret_key = "2112miami"

ARQUIVO_DADOS = "avaliacoes.json"

# -------- CARREGAR DADOS --------
if os.path.exists(ARQUIVO_DADOS):
    try:
        with open(ARQUIVO_DADOS, "r", encoding="utf-8") as f:
            reviews = json.load(f)
    except json.JSONDecodeError:
        reviews = []
else:
    reviews = []


def salvar_dados():
    with open(ARQUIVO_DADOS, "w", encoding="utf-8") as f:
        json.dump(reviews, f, indent=4, ensure_ascii=False)


def calcular_estatisticas():
    total_reviews = len(reviews)

    # média geral
    media_indicacao = None
    if total_reviews > 0:
        soma = 0
        for r in reviews:
            soma += r.get("indicacao", 0)
        media_indicacao = soma / total_reviews

    # estatísticas por colaborador
    por_colab = {}
    for r in reviews:
        nome = r.get("colaborador") or "Não informado"
        if nome not in por_colab:
            por_colab[nome] = {"quantidade": 0, "soma": 0, "qtd_notas": 0}
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
        estatisticas_colab.append(
            {"nome": nome, "quantidade": dados["quantidade"], "media": media}
        )

    # contagem por critério
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

    return total_reviews, media_indicacao, estatisticas_colab, indicadores


# -------- PÁGINA DO CLIENTE --------
@app.route("/", methods=["GET", "POST"])
def index():
    global reviews

    if request.method == "POST":
        indicacao_str = request.form.get("indicacao") or "0"
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

    total_reviews, media_indicacao, estatisticas_colab, indicadores = (
        calcular_estatisticas()
    )

    return render_template(
        "index.html",
        reviews=reviews,
        media_indicacao=media_indicacao,
        total_reviews=total_reviews,
        estatisticas_colab=estatisticas_colab,
        indicadores=indicadores,
    )


# -------- DASHBOARD COM LOGIN --------
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    # login
    if not session.get("autenticado"):
        if request.method == "POST":
            senha = request.form.get("senha")
            # SENHA DO DONO
            if senha == "2112miami":
                session["autenticado"] = True
                return redirect(url_for("dashboard"))
            else:
                return render_template("login.html", erro="Senha incorreta")

        return render_template("login.html")

    # já autenticado → mostra painel
    total_reviews, media_indicacao, estatisticas_colab, indicadores = (
        calcular_estatisticas()
    )

    return render_template(
        "dashboard.html",
        total_reviews=total_reviews,
        media_indicacao=media_indicacao,
        estatisticas_colab=estatisticas_colab,
        indicadores=indicadores,
        reviews=reviews,
    )


# -------- LOGOUT --------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("dashboard"))


# -------- EXCLUIR MÚLTIPLAS --------
@app.route("/delete_selected", methods=["POST"])
def delete_selected():
    if not session.get("autenticado"):
        return redirect(url_for("dashboard"))

    indices = request.form.getlist("indices")
    if not indices:
        return redirect(url_for("dashboard"))

    indices_int = []
    for idx in indices:
        try:
            indices_int.append(int(idx))
        except ValueError:
            pass

    # remove de trás pra frente
    for idx in sorted(set(indices_int), reverse=True):
        if 0 <= idx < len(reviews):
            reviews.pop(idx)

    salvar_dados()
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run()
