import os
from datetime import datetime, timedelta
from flask import Flask, request, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Configure database from environment
db_url = os.getenv("DATABASE_URL", "sqlite:///local.db")
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# Admin password from environment
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# Voucher model
class Voucher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    vtype = db.Column(db.String(10), nullable=False)  # '15' or '30'
    created = db.Column(db.DateTime, default=datetime.utcnow)

    def days_left(self):
        expiry_days = 15 if self.vtype == '15' else 30
        delta = expiry_days - (datetime.utcnow() - self.created).days
        return max(delta, 0)

# Create tables
with app.app_context():
    db.create_all()

# User home page
@app.route("/", methods=["GET", "POST"])
def index():
    message = ""
    if request.method == "POST":
        code = request.form.get("voucher").strip()
        voucher = Voucher.query.filter_by(code=code).first()
        if voucher:
            days = voucher.days_left()
            if days > 0:
                message = f"✅ Voucher is valid. {days} day(s) remaining."
            else:
                message = "⚠️ Voucher has expired."
        else:
            message = "❌ Invalid voucher code."
    return render_template("index.html", message=message)

# Admin page
@app.route("/admin", methods=["GET", "POST"])
def admin():
    authenticated = False
    vouchers = []
    if request.method == "POST":
        password = request.form.get("password")
        if password == ADMIN_PASSWORD:
            authenticated = True
            vouchers = Voucher.query.all()
    return render_template("admin.html", authenticated=authenticated, vouchers=vouchers)

# Upload single voucher
@app.route("/upload", methods=["POST"])
def upload():
    code = request.form.get("voucher").strip()
    days = request.form.get("days")
    password = request.form.get("password")
    if password != ADMIN_PASSWORD:
        return "Unauthorized", 403
    if not Voucher.query.filter_by(code=code).first():
        new_voucher = Voucher(code=code, vtype=days)
        db.session.add(new_voucher)
        db.session.commit()
    return redirect("/admin")

# Upload via CSV
@app.route("/upload_csv", methods=["POST"])
def upload_csv():
    password = request.form.get("password")
    if password != ADMIN_PASSWORD:
        return "Unauthorized", 403

    file = request.files["file"]
    if file:
        content = file.read().decode("utf-8").splitlines()
        for line in content:
            parts = line.strip().split(",")
            if len(parts) == 2:
                code, vtype = parts[0].strip(), parts[1].strip()
                if not Voucher.query.filter_by(code=code).first():
                    db.session.add(Voucher(code=code, vtype=vtype))
        db.session.commit()
    return redirect("/admin")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
