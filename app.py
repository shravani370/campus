from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = "secret_key_123"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///campus_cart.db"
app.config["UPLOAD_FOLDER"] = "static/uploads"
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5MB max

ALLOWED_DOMAIN = "sggs.ac.in"

db = SQLAlchemy(app)

# ------------------ MODELS ------------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    price = db.Column(db.Float, nullable=False)
    photo = db.Column(db.String(200), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    seller = db.relationship("User", backref="items")


# ------------------ ROUTES ------------------

@app.route("/")
def home():
    return render_template("listings.html", items=Item.query.all())


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form["email"].strip()
        password = request.form["password"]

        if not email.endswith(f"@{ALLOWED_DOMAIN}"):
            flash("Only SGGS domain emails are allowed.")
            return redirect(url_for("signup"))

        if User.query.filter_by(email=email).first():
            flash("Email already registered.")
            return redirect(url_for("signup"))

        hashed_pw = generate_password_hash(password)
        user = User(email=email, password=hashed_pw)
        db.session.add(user)
        db.session.commit()

        flash("Signup successful! Please log in.")
        return redirect(url_for("login"))
    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["email"] = user.email
            flash("Login successful!")
            return redirect(url_for("home"))
        else:
            flash("Invalid email or password.")
            return redirect(url_for("login"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You’ve been logged out.")
    return redirect(url_for("home"))


@app.route("/sell", methods=["GET", "POST"])
def sell():
    if "user_id" not in session:
        flash("Please log in first.")
        return redirect(url_for("login"))

    if request.method == "POST":
        name = request.form["name"]
        description = request.form["description"]
        price = float(request.form["price"])
        photo = request.files["photo"]

        if photo:
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(photo.filename)}"
            upload_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            photo.save(upload_path)
            photo_path = f"uploads/{filename}"
        else:
            flash("Please upload a photo.")
            return redirect(url_for("sell"))

        new_item = Item(
            name=name,
            description=description,
            price=price,
            photo=photo_path,
            seller_id=session["user_id"]
        )

        db.session.add(new_item)
        db.session.commit()
        flash("Item listed successfully!")
        return redirect(url_for("home"))

    return render_template("sell.html")


@app.route("/buy-now/<int:item_id>")
def buy_now(item_id):
    item = Item.query.get_or_404(item_id)
    session["cart"] = [{
        "id": item.id,
        "name": item.name,
        "price": item.price,
        "seller": item.seller.email
    }]
    flash("Item added to cart. Proceed to buy.")
    return redirect(url_for("buy"))


@app.route("/buy")
def buy():
    cart = session.get("cart", [])
    return render_template("buy.html", cart=cart)


# ------------------ MAIN ------------------

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
