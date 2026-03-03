from flask import Flask, render_template, request, redirect, url_for, session
import json
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "2112miami"

ARQUIVO_DADOS = "avaliacoes.json"

# ---------- CARREGA DADOS ----------
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


# ---------- PÁGINA DE AVALIAÇÃO ----------
@app.route('/', methods=['GET', 'POST'])
def index():
    global reviews

    if request.method == 'POST':
        indicacao_str = request.form.get('indicacao') or "0"
        try:
            indicacao = int(indicacao_str)
        except ValueError:
            indicacao = 0

        review = {
            "data": datetime.now().strftime("%Y-%m-%d %H:%M"),
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


# ---------- DASHBOARD ----------
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    # Se não estiver autenticado
    if not session.get("autenticado"):
        if request.method == "POST":
            senha = request.form.get("senha")
            if senha == "1234":  # <-- TROQUE POR UMA SENHA SUA
                session["autenticado"] = True
                return redirect(url_for("dashboard"))
            else:
                return render_template("login.html", erro="Senha incorreta")
        return render_template("login.html")

    # Se estiver autenticado, mostra o dashboard normal
    total_reviews = len(reviews)

    media_indicacao = None
    if total_reviews > 0:
        media_indicacao = sum(r.get("indicacao", 0) for r in reviews) / total_reviews

    por_colab = {}
    for r in reviews:
        nome = r.get("colaborador") or "Não informado"
        if nome not in por_colab:
            por_colab[nome] = {"quantidade": 0, "soma_indicacao": 0, "qtd_indicacao": 0}
        por_colab[nome]["quantidade"] += 1
        nota = r.get("indicacao")
        if isinstance(nota, int):
            por_colab[nome]["soma_indicacao"] += nota
            por_colab[nome]["qtd_indicacao"] += 1

    estatisticas_colab = []
    for nome, dados in por_colab.items():
        media = None
        if dados["qtd_indicacao"] > 0:
            media = dados["soma_indicacao"] / dados["qtd_indicacao"]
        estatisticas_colab.append(
            {"nome": nome, "quantidade": dados["quantidade"], "media": media}
        )

    colab_labels = [c["nome"] for c in estatisticas_colab]
    colab_medias = [(c["media"] or 0) for c in estatisticas_colab]

    dist_labels = list(range(11))
    dist_values = [0] * 11
    for r in reviews:
        nota = r.get("indicacao")
        if isinstance(nota, int) and 0 <= nota <= 10:
            dist_values[nota] += 1

    return render_template(
        "dashboard.html",
        total_reviews=total_reviews,
        media_indicacao=media_indicacao,
        estatisticas_colab=estatisticas_colab,
        colab_labels=colab_labels,
        colab_medias=colab_medias,
        dist_labels=dist_labels,
        dist_values=dist_values,
    )

if __name__ == "__main__":
    app.run()
    
