from flask import Flask, render_template, request, redirect, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import random

app = Flask(__name__)
app.secret_key = "supersecret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///todo.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# -------------------- MODELLER --------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    reset_code = db.Column(db.String(10), nullable=True)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    baslik = db.Column(db.String(200), nullable=False)
    aciklama = db.Column(db.String(500), nullable=True)
    durum = db.Column(db.String(20), default="Beklemede")
    tarih = db.Column(db.Date, nullable=True)
    renk = db.Column(db.String(20), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

# -------------------- YARDIMCI FONKSİYONLAR --------------------
def current_user():
    if "user_id" in session:
        return User.query.get(session["user_id"])
    return None

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user():
            return redirect("/login")
        return f(*args, **kwargs)
    return wrapper

# -------------------- ROUTES --------------------
@app.route("/")
@login_required
def index():
    user = current_user()
    gorevler = Task.query.filter_by(user_id=user.id).all()
    return render_template("index.html", gorevler=gorevler, current_user=user)

@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    if request.method == "POST":
        user = current_user()
        tarih = request.form.get("tarih")
        tarih_obj = datetime.strptime(tarih, "%Y-%m-%d").date() if tarih else None
        t = Task(
            baslik=request.form.get("baslik"),
            aciklama=request.form.get("aciklama"),
            tarih=tarih_obj,
            renk=request.form.get("renk"),
            user_id=user.id
        )
        db.session.add(t)
        db.session.commit()
        return redirect("/")
    return render_template("add.html", current_user=current_user())

@app.route("/sil/<int:id>")
@login_required
def sil(id):
    g = Task.query.get(id)
    if g and g.user_id == current_user().id:
        db.session.delete(g)
        db.session.commit()
    return redirect("/")

@app.route("/takvim")
@login_required
def takvim():
    return render_template("takvim.html", current_user=current_user())

@app.route("/api/gorevler")
@login_required
def api_gorevler():
    user = current_user()
    gorevler = Task.query.filter_by(user_id=user.id).all()
    events = []
    for g in gorevler:
        if g.tarih:
            events.append({
                "id": g.id,
                "title": g.baslik,
                "start": g.tarih.isoformat(),
                "color": g.renk if g.renk else "#3788d8"
            })
    return jsonify(events)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form.get("username")).first()
        if user and check_password_hash(user.password, request.form.get("password")):
            session["user_id"] = user.id
            return redirect("/")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        u = User(
            username=request.form.get("username"),
            password=generate_password_hash(request.form.get("password"))
        )
        db.session.add(u)
        db.session.commit()
        return redirect("/login")
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/reset", methods=["GET", "POST"])
def reset():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form.get("username")).first()
        if user:
            code = str(random.randint(10000, 99999))
            user.reset_code = code
            db.session.commit()
            print("Sıfırlama Kodu:", code)
            return redirect("/reset/confirm")
    return render_template("reset.html")

@app.route("/reset/confirm", methods=["GET", "POST"])
def reset_confirm():
    if request.method == "POST":
        code = request.form.get("code")
        newpass = request.form.get("newpass")
        user = User.query.filter_by(reset_code=code).first()
        if user:
            user.password = generate_password_hash(newpass)
            user.reset_code = None
            db.session.commit()
            return redirect("/login")
    return render_template("reset_confirm.html")


@app.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit(id):
    task = Task.query.get_or_404(id)
    if task.user_id != current_user().id:
        return redirect("/")

    if request.method == "POST":
        task.baslik = request.form.get("baslik")
        task.aciklama = request.form.get("aciklama")
        tarih = request.form.get("tarih")
        task.tarih = datetime.strptime(tarih, "%Y-%m-%d").date() if tarih else None
        task.renk = request.form.get("renk")
        db.session.commit()
        return redirect("/")

    return render_template("edit.html", current_user=current_user(), task=task)

# -------------------- MAIN --------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
