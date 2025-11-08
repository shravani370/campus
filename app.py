from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///campus_cart.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

db = SQLAlchemy(app)

ALLOWED_DOMAIN = 'sggs.ac.in'

# ---------------------- MODELS ----------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    photo = db.Column(db.String(200), nullable=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    seller = db.relationship('User', backref=db.backref('items', lazy=True))

with app.app_context():
    db.create_all()

# ---------------------- HELPERS ----------------------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ---------------------- ROUTES ----------------------
@app.route('/')
@login_required
def index():
    user = User.query.filter_by(email=session['user']).first()
    user_items = Item.query.filter_by(seller_id=user.id).all() if user else []
    return render_template('index.html', user_items=user_items)

# ---------- LOGIN ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password'].strip()

        if not email.endswith(ALLOWED_DOMAIN):
            return render_template('login.html', error='Email must end with @sggs.ac.in')

        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(email=email, password=password)
            db.session.add(user)
            db.session.commit()

        if user.password == password:
            session['user'] = email
            session['cart'] = []
            flash('Login successful!')
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Invalid password')

    return render_template('login.html')

# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('cart', None)
    return redirect(url_for('login'))

# ---------- SELL ----------
@app.route('/sell', methods=['GET', 'POST'])
@login_required
def sell():
    if request.method == 'POST':
        name = request.form['name']
        price = int(request.form['price'])
        photo = request.files.get('photo')
        photo_path = None

        if photo and allowed_file(photo.filename):
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            filename = secure_filename(photo.filename)
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            photo.save(photo_path)

        user = User.query.filter_by(email=session['user']).first()
        new_item = Item(name=name, price=price, photo=photo_path, seller_id=user.id)
        db.session.add(new_item)
        db.session.commit()
        flash("Item listed successfully!")
        return redirect(url_for('index'))

    return render_template('sell.html')

# ---------- BUY ----------
@app.route('/buy')
@login_required
def buy():
    user = User.query.filter_by(email=session['user']).first()
    items = Item.query.filter(Item.seller_id != user.id).all()
    return render_template('buy.html', items=items)

# ---------- ADD TO CART ----------
@app.route('/add-to-cart/<int:item_id>')
@login_required
def add_to_cart(item_id):
    item = Item.query.get_or_404(item_id)
    if 'cart' not in session:
        session['cart'] = []
    session['cart'].append({'id': item.id, 'name': item.name, 'price': item.price, 'seller': item.seller.email})
    session.modified = True
    flash(f"{item.name} added to cart!")
    return redirect(url_for('buy'))

# ---------- REMOVE FROM CART ----------
@app.route('/remove-from-cart/<int:item_id>')
@login_required
def remove_from_cart(item_id):
    if 'cart' in session:
        session['cart'] = [item for item in session['cart'] if item['id'] != item_id]
        session.modified = True
        flash("Item removed from cart!")
    return redirect(url_for('cart'))

# ---------- CART ----------
@app.route('/cart')
@login_required
def cart():
    cart_items = session.get('cart', [])
    total = sum(item['price'] for item in cart_items)
    return render_template('cart.html', cart=cart_items, total=total)

# ---------- CHECKOUT ----------
@app.route('/checkout', methods=['GET'])
@login_required
def checkout():
    cart_items = session.get('cart', [])
    if not cart_items:
        flash("Cart is empty!")
        return redirect(url_for('buy'))
    total = sum(item['price'] for item in cart_items)
    return render_template('checkout.html', cart=cart_items, total=total)

# ---------- PROCESS ORDER ----------
@app.route('/process_order', methods=['POST'])
@login_required
def process_order():
    cart_items = session.get('cart', [])
    if not cart_items:
        flash("Cart is empty!")
        return redirect(url_for('cart'))

    payment_method = request.form.get('payment_method')
    if not payment_method:
        flash("Please select a payment method!")
        return redirect(url_for('checkout'))

    upi_id = request.form.get('upi_id') if payment_method == 'upi' else None

    order_summary = {
        'items': cart_items,
        'total': sum(item.get('price', 0) for item in cart_items),
        'payment_method': payment_method,
        'upi_id': upi_id
    }

    session['cart'] = []
    flash("Order placed successfully!")

    return render_template('order_confirmation.html', order=order_summary)

# ---------- RUN ----------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
