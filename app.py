import os
from flask import (
    Flask, render_template, request, redirect, url_for, flash, session
)
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this in production

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///campus_cart.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db = SQLAlchemy(app)

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)  # Use hashing in production

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_filename = db.Column(db.String(100), nullable=True)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)
    sold = db.Column(db.Boolean, default=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    seller = db.relationship('User', backref='items')  # Fixed: no trailing space

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def logged_in():
    return 'user_id' in session

def current_user():
    if not logged_in():
        return None
    return User.query.get(session['user_id'])

@app.context_processor
def inject_user():
    return dict(current_user=current_user)

@app.route('/')
def home():
    if not logged_in():
        return redirect(url_for('login'))
    return render_template('home.html', user=current_user())

@app.route('/register', methods=['GET', 'POST'])
def register():
    if logged_in():
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        if not username or not password:
            flash("Please fill in all fields.", "error")
            return render_template('register.html')
        if User.query.filter_by(username=username).first():
            flash("Username already taken.", "error")
            return render_template('register.html')
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        flash("Registration successful! Please login.", "success")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if logged_in():
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            flash(f"Welcome, {user.username}!", "success")
            return redirect(url_for('home'))
        else:
            flash("Invalid username or password.", "error")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for('login'))

@app.route('/sell', methods=['GET', 'POST'])
def sell():
    if not logged_in():
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form['title']
        price = request.form['price']
        category = request.form['category']
        description = request.form['description']
        file = request.files.get('image')

        error = None
        if not title or not price or not category or not description:
            error = "Please fill in all fields."
        else:
            try:
                price = float(price)
            except ValueError:
                error = "Price must be a number."

        filename = None
        if file and file.filename != '':
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            else:
                error = "Invalid image file type. Allowed types: png, jpg, jpeg, gif."

        if error:
            flash(error, "error")
            return render_template('sell.html')

        new_item = Item(
            title=title,
            price=price,
            category=category,
            description=description,
            image_filename=filename,
            seller_id=session['user_id']
        )
        db.session.add(new_item)
        db.session.commit()
        flash("Item posted successfully!", "success")
        return redirect(url_for('home'))

    return render_template('sell.html')

@app.route('/buy')
def buy():
    if not logged_in():
        return redirect(url_for('login'))
    items = Item.query.filter_by(sold=False).order_by(Item.date_posted.desc()).all()
    return render_template('buy.html', items=items)

@app.route('/buy/<int:item_id>', methods=['GET', 'POST'])
def buy_item(item_id):
    if not logged_in():
        return redirect(url_for('login'))
    item = Item.query.get_or_404(item_id)
    if item.sold:
        flash("Sorry, this item is already sold.", "error")
        return redirect(url_for('buy'))

    if request.method == 'POST':
        payment_method = request.form.get('payment_method')
        if payment_method not in ['cod', 'upi', 'qr']:
            flash("Please select a valid payment method.", "error")
            return render_template('payment.html', item=item)
        item.sold = True
        db.session.commit()
        flash(f"You have successfully bought '{item.title}' using {payment_method.upper()}.", "success")
        return redirect(url_for('buy'))

    return render_template('payment.html', item=item)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)