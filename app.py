import os
import sqlite3
from datetime import datetime
from urllib.parse import urlparse

from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "2112miami"  # chave da sessão

ADMIN_PASSWORD = "2112miami"  # senha do dashboard


# ---------------- DB (Postgres no Render / SQLite local) ----------------
def get_db():
    """
    - Se existir DATABASE_URL (Render/Postgres), usa Postgres via psycopg2
    - Senão, usa SQLite local (dev)
    """
    db_url = os.environ.get("DATABASE_URL")

    if db_url:
        # Render usa postgres:// ou postgresql://
        import psycopg2

        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)

        parsed = urlparse(db_url)
        conn = psycopg2.connect(
            dbname=parsed.path[1:],
            user=parsed.username,
            password=parsed.password,
            host=parsed.hostname,
            port=parsed.port,
            sslmode="require",
        )
        return conn, "postgres"

    # SQLite local
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn, "sqlite"


def init_db():
    conn, kind = get_db()
    cur = conn.cursor()

    if kind == "postgres":
        cur.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id SERIAL PRIMARY KEY,
                created_at TIMESTAMP NOT NULL,
                nome_cliente TEXT,
                telefone_cliente TEXT,
                colaborador TEXT NOT NULL,
                educacao TEXT NOT NULL,
                clareza TEXT NOT NULL,
                transparencia TEXT NOT NULL,
                organizacao TEXT NOT NULL,
                finalizacao TEXT NOT NULL,
                indicacao INTEGER NOT NULL,
                melhoria TEXT
            );
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                nome_cliente TEXT,
                telefone_cliente TEXT,
                colaborador TEXT NOT NULL,
                educacao TEXT NOT NULL,
                clareza TEXT NOT NULL,
                transparencia TEXT NOT NULL,
                organizacao TEXT NOT NULL,
                finalizacao TEXT NOT NULL,
                indicacao INTEGER NOT NULL,
                melhoria TEXT
            );
        """)

    conn.commit()
    conn.close()


def fetch_reviews():
    conn, kind = get_db()
    cur = conn.cursor()

    if kind == "postgres":
        cur.execute("""
            SELECT id, created_at, nome_cliente, telefone_cliente, colaborador,
                   educacao, clareza, transparencia, organizacao, finalizacao,
                   indicacao, melhoria
            FROM reviews
            ORDER BY created_at DESC;
        """)
        rows = cur.fetchall()
        conn.close()

        # psycopg2 retorna tuple; vamos padronizar em dict
        reviews = []
        for row in rows:
            reviews.append({
                "id": row[0],
                "data": row[1].strftime("%Y-%m-%d %H:%M"),
                "nome_cliente": row[2] or "",
                "telefone_cliente": row[3] or "",
                "colaborador": row[4],
                "educacao": row[5],
                "clareza": row[6],
                "transparencia": row[7],
                "organizacao": row[8],
                "finalizacao": row[9],
                "indicacao": int(row[10]),
                "melhoria": row[11] or "",
            })
        return reviews

    # sqlite
    cur.execute("""
        SELECT id, created_at, nome_cliente, telefone_cliente, colaborador,
               educacao, clareza, transparencia, organizacao, finalizacao,
               indicacao, melhoria
        FROM reviews
        ORDER BY id DESC;
    """)
    rows = cur.fetchall()
    conn.close()

    reviews = []
    for row in rows:
        reviews.append({
            "id": row["id"],
            "data": row["created_at"],
            "nome_cliente": row["nome_cliente"] or "",
            "telefone_cliente": row["telefone_cliente"] or "",
            "colaborador": row["colaborador"],
            "educacao": row["educacao"],
            "clareza": row["clareza"],
            "transparencia": row["transparencia"],
            "organizacao": row["organizacao"],
            "finalizacao": row["finalizacao"],
            "indicacao": int(row["indicacao"]),
            "melhoria": row["melhoria"] or "",
        })
    return reviews


def insert_review(data):
    conn, kind = get_db()
    cur = conn.cursor()

    if kind == "postgres":
        cur.execute("""
            INSERT INTO reviews
            (created_at, nome_cliente, telefone_cliente, colaborador,
             educacao, clareza, transparencia, organizacao, finalizacao,
             indicacao, melhoria)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            datetime.now(),
            data["nome_cliente"],
            data["telefone_cliente"],
            data["colaborador"],
            data["educacao"],
            data["clareza"],
            data["transparencia"],
            data["organizacao"],
            data["finalizacao"],
            data["indicacao"],
            data["melhoria"],
        ))
    else:
        cur.execute("""
            INSERT INTO reviews
            (created_at, nome_cliente, telefone_cliente, colaborador,
             educacao, clareza, transparencia, organizacao, finalizacao,
             indicacao, melhoria)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            data["data"],
            data["nome_cliente"],
            data["telefone_cliente"],
            data["colaborador"],
            data["educacao"],
            data["clareza"],
            data["transparencia"],
            data["organizacao"],
            data["finalizacao"],
            data["indicacao"],
            data["melhoria"],
        ))

    conn.commit()
    conn.close()


def delete_reviews_by_ids(ids):
    if not ids:
        return

    conn, kind = get_db()
    cur = conn.cursor()

    ids = list(set(ids))

    if kind == "postgres":
        cur.execute("DELETE FROM reviews WHERE id = ANY(%s)", (ids,))
    else:
        placeholders = ",".join(["?"] * len(ids))
        cur.execute(f"DELETE FROM reviews WHERE id IN ({placeholders})", ids)

    conn.commit()
    conn.close()


def calcular_estatisticas(reviews):
    total_reviews = len(reviews)
    media_indicacao = None
    if total_reviews > 0:
        media_indicacao = sum(r.get("indicacao", 0) for r in reviews) / total_reviews

    por_colab = {}
    for r in reviews:
        nome = r.get("colaborador") or "Não informado"
        por_colab.setdefault(nome, {"quantidade": 0, "soma": 0, "qtd": 0})
        por_colab[nome]["quantidade"] += 1
        nota = r.get("indicacao")
        if isinstance(nota, int):
            por_colab[nome]["soma"] += nota
            por_colab[nome]["qtd"] += 1

    estatisticas_colab = []
    for nome, d in por_colab.items():
        estatisticas_colab.append({
            "nome": nome,
            "quantidade": d["quantidade"],
            "media": (d["soma"] / d["qtd"]) if d["qtd"] else None
        })

    def contar(campo):
        base = {"excelente": 0, "regular": 0, "ruim": 0}
        for r in reviews:
            v = r.get(campo)
            if v in base:
                base[v] += 1
        return base

    indicadores = {
        "educacao": contar("educacao"),
        "clareza": contar("clareza"),
        "transparencia": contar("transparencia"),
        "organizacao": contar("organizacao"),
        "finalizacao": contar("finalizacao"),
    }

    return total_reviews, media_indicacao, estatisticas_colab, indicadores


# inicializa DB ao subir
init_db()


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        indicacao_str = request.form.get("indicacao") or "0"
        try:
            indicacao = int(indicacao_str)
        except ValueError:
            indicacao = 0

        review = {
            "data": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "nome_cliente": request.form.get("nome_cliente") or "",
            "telefone_cliente": request.form.get("telefone_cliente") or "",
            "colaborador": request.form.get("colaborador") or "",
            "educacao": request.form.get("educacao") or "",
            "clareza": request.form.get("clareza") or "",
            "transparencia": request.form.get("transparencia") or "",
            "organizacao": request.form.get("organizacao") or "",
            "finalizacao": request.form.get("finalizacao") or "",
            "indicacao": indicacao,
            "melhoria": request.form.get("melhoria") or "",
        }
        insert_review(review)
        return redirect(url_for("index"))

    reviews = fetch_reviews()
    total_reviews, media_indicacao, estatisticas_colab, indicadores = calcular_estatisticas(reviews)

    return render_template(
        "index.html",
        media_indicacao=media_indicacao,
        total_reviews=total_reviews
    )


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if not session.get("autenticado"):
        if request.method == "POST":
            senha = request.form.get("senha")
            if senha == ADMIN_PASSWORD:
                session["autenticado"] = True
                return redirect(url_for("dashboard"))
            return render_template("login.html", erro="Senha incorreta")
        return render_template("login.html")

    reviews = fetch_reviews()
    total_reviews, media_indicacao, estatisticas_colab, indicadores = calcular_estatisticas(reviews)

    return render_template(
        "dashboard.html",
        total_reviews=total_reviews,
        media_indicacao=media_indicacao,
        estatisticas_colab=estatisticas_colab,
        indicadores=indicadores,
        reviews=reviews,
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("dashboard"))


@app.route("/delete_selected", methods=["POST"])
def delete_selected():
    if not session.get("autenticado"):
        return redirect(url_for("dashboard"))

    ids = request.form.getlist("ids")
    ids_int = []
    for x in ids:
        try:
            ids_int.append(int(x))
        except ValueError:
            pass

    delete_reviews_by_ids(ids_int)
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(debug=True)