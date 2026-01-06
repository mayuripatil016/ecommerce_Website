# app.py  (updated / final)
from flask import Flask, render_template, redirect, request, url_for, jsonify, flash, session
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, IntegerField
from wtforms.validators import DataRequired, length, NumberRange
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from datetime import datetime
from db_create import CartItem
from db_create import Order, OrderItem
from base64 import b64encode
import smtplib

# import SINGLE db and models from db_create
from db_create import db, Customer, Item, CartItem, Wishlist, Review, Order

# ---------------- APP SETUP ----------------
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop.db'
app.config['SECRET_KEY'] = ''

# attach db to app (do NOT create a second SQLAlchemy object)
db.init_app(app)

# login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# simple email send function (optional)
gmail_account = ''
gmail_password = ''
def send_mail(recipient):
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(gmail_account, gmail_password)
        server.sendmail(gmail_account, recipient, 'Congratulations for signing up!!!')
    except:
        pass

# ---------------- FORMS ----------------
class SignUpForm(FlaskForm):
    username = StringField(validators=[DataRequired(), length(min=3)])
    email = StringField(validators=[DataRequired(), length(min=4)])
    password1 = PasswordField(validators=[DataRequired(), length(min=6)])
    password2 = PasswordField(validators=[DataRequired(), length(min=6)])
    submit = SubmitField('Sign up')

class LogInForm(FlaskForm):
    email = StringField(validators=[DataRequired()])
    password = PasswordField(validators=[DataRequired()])
    submit = SubmitField('Log in')

class ShopItemsForm(FlaskForm):
    name = StringField('Name of item', validators=[DataRequired()])
    current_price = IntegerField(validators=[DataRequired()])
    previous_price = IntegerField(validators=[DataRequired()])
    remaining = IntegerField(validators=[NumberRange(min=1)])
    quantity = IntegerField(validators=[DataRequired(), NumberRange(min=1)])
    update_cart = SubmitField('Update')
    add_item = SubmitField('Add item')

# user loader
@login_manager.user_loader
def load_user(user_id):
    return Customer.query.get(int(user_id))

# ---------------- FLASH PRODUCTS (in-memory) ----------------
flash_products = {
    1: ("Spago", 400, "images/1.jpg"),
    2: ("Android smartphone", 20000, "images/1 (1).jpg"),
    3: ("Wireless headphone", 3000, "images/1 (2).jpg"),
    4: ("Smart TV", 40000, "images/1 (3).jpg"),
    5: ("Music system", 5000, "images/1 (4).jpg"),
    6: ("Bluetooth", 1000, "images/1 (5).jpg"),
    7: ("Smart Watch", 1500, "images/1 (6).jpg"),
    8: ("Toys", 1000, "images/toys.jpg"),
    9: ("Cloths buy 2 get 1 free", 900, "images/cloths.jpg"),
    10: ("Makeup product", 1000, "images/makeup.jpg"),
    11: ("Grocery items", 3000, "images/grocery.jpg"),
    12: ("Shoes", 1200, "images/shoes.jpg"),
    13: ("Useful product", 600, "images/bproduct.jpg"),
    14: ("Showpiece", 900, "images/show.jpg")
}

# simple FlashProduct wrapper for in-memory products
class FlashProduct:
    def __init__(self, pid, name, price, image):
        self.id = pid
        self.name = name
        self.current_price = price
        self.previous_price = price
        self.remaining = 10
        self.image = image

# ---------------- ROUTES ----------------
@app.route('/', methods=['GET','POST'])
def login():
    form = LogInForm()
    if form.validate_on_submit():
        customer = Customer.query.filter_by(email=form.email.data).first()
        if customer and check_password_hash(customer.password_hash, form.password.data):
            login_user(customer)
            return redirect('/amazon/')
        else:
            flash('Wrong email or password', 'error')
    return render_template('login.html', form=form)


@app.route('/signup/', methods=['GET','POST'])
def signup():
    form = SignUpForm()
    if form.validate_on_submit():
        if form.password1.data != form.password2.data:
            flash('Passwords do not match', 'error')
        else:
            new_customer = Customer(
                username=form.username.data,
                email=form.email.data,
                password_hash=generate_password_hash(form.password1.data)
            )
            db.session.add(new_customer)
            db.session.commit()
            send_mail(new_customer.email)
            flash('Account created successfully', 'success')
            return redirect('/')
    return render_template('signup.html', form=form)

@app.route('/profile')
@login_required
def profile():
    return render_template("profile.html", user=current_user)


@app.route('/logout')
@login_required
def log_out():
    logout_user()
    flash('Logged out', 'success')
    return redirect('/')

@app.route('/amazon/')
@login_required
def amazon():
    items = Item.query.order_by(Item.date_added).all()
    return render_template('shop.html', items_list=items)


@app.route('/shopitems/', methods=['GET','POST'])
@login_required
def shop_items():
    if request.method == 'POST':
        name = request.form.get('name')
        current_price = request.form.get('current_price') or 0
        previous_price = request.form.get('previous_price') or 0
        remaining = request.form.get('remaining') or 0
        image = request.form.get('image')  # optional field in form
        new_item = Item(name=name, current_price=current_price, previous_price=previous_price, remaining=remaining, image=image)
        try:
            db.session.add(new_item)
            db.session.commit()
            return redirect('/shopitems/')
        except Exception as e:
            flash('Error adding item', 'error')
    items = Item.query.order_by(Item.date_added).all()
    return render_template('shopitems.html', items=items)

@app.route('/product/<int:pid>')
@login_required
def product_detail(pid):
    # flash product
    if pid in flash_products:
        name, price, image = flash_products[pid]
        product = FlashProduct(pid, name, price, image)
        reviews = []     # flash-products don't have DB reviews
        avg_rating = None
        saved = False
        similar = []     # no similar for flash products
    else:
        product = Item.query.get_or_404(pid)

        # ensure product.image exists (fallback)
        if not getattr(product, 'image', None):
            product.image = 'images/default.png'  # place a default image in static/images

        reviews = Review.query.filter_by(item_id=pid).order_by(Review.created_at.desc()).all()
        avg_rating = None
        if reviews:
            avg_rating = sum(r.rating for r in reviews) / len(reviews)

        saved = Wishlist.query.filter_by(customer_id=current_user.id, item_id=pid).first() is not None
        similar = Item.query.filter(Item.id != pid).limit(6).all()
        # add image fallback for similar items
        for s in similar:
            if not getattr(s, 'image', None):
                s.image = 'images/default.png'

    return render_template('product_detail.html',
                           product=product,
                           reviews=reviews,
                           avg_rating=avg_rating,
                           saved=saved,
                           similar=similar)
                           #flash_products=flash_products

@app.route('/wishlist/toggle/<int:pid>', methods=['POST'])
@login_required
def toggle_wishlist(pid):
    # works only for DB items (not flash products)
    if pid in flash_products:
        return jsonify({'status': 'error', 'msg': 'not allowed for flash products'}), 400

    saved = Wishlist.query.filter_by(customer_id=current_user.id, item_id=pid).first()
    if saved:
        db.session.delete(saved)
        db.session.commit()
        return jsonify({'status': 'removed'})
    else:
        new = Wishlist(customer_id=current_user.id, item_id=pid)
        db.session.add(new)
        db.session.commit()
        return jsonify({'status': 'added'})

@app.route('/product/<int:pid>/review', methods=['POST'])
@login_required
def add_review(pid):
    # only for DB items
    if pid in flash_products:
        flash('Cannot review flash products', 'error')
        return redirect(url_for('product_detail', pid=pid))

    rating = int(request.form.get('rating', 0))
    comment = request.form.get('comment', '').strip()
    if rating < 1 or rating > 5:
        flash('Invalid rating', 'error')
        return redirect(url_for('product_detail', pid=pid))

    new_review = Review(customer_id=current_user.id, item_id=pid, rating=rating, comment=comment)
    db.session.add(new_review)
    db.session.commit()
    flash('Review added!', 'success')
    return redirect(url_for('product_detail', pid=pid))

@app.route('/cart/')
@login_required
def cart():
    items = CartItem.query.filter_by(customer_link=current_user.id).all()
    for item in items:
        for pid, data in flash_products.items():
            pname, price, image = data
            if item.item_name == pname:
                item.image = image
                break
    total = sum(i.price * i.quantity for i in items)
    return render_template('cart.html', items=items, total=total)


@app.route('/add_to_cart/<int:id>')
@login_required
def add_to_cart(id):

    # FLASH SALE PRODUCTS = NAME, PRICE, IMAGE
    if id in flash_products:
        name, price, image = flash_products[id]

        cart_item = CartItem.query.filter_by(
            customer_link=current_user.id,
            item_name=name
        ).first()

        if cart_item:
            cart_item.quantity += 1
        else:
            cart_item = CartItem(
                customer_link=current_user.id,
                item_name=name,
                price=price,
                quantity=1
            )

            # 🔥 SAVE IMAGE PATH IN SESSION DICTIONARY
            # Image DB me save nahi hoti, but runtime me use hogi
            cart_item.temp_image = image

            db.session.add(cart_item)

        db.session.commit()
        return redirect('/cart/')

    return "Product not found", 404



@app.route('/increase_qty/<int:id>')
@login_required
def increase_qty(id):
    item = CartItem.query.get_or_404(id)
    item.quantity += 1
    db.session.commit()
    return redirect('/cart/')

@app.route('/decrease_qty/<int:id>')
@login_required
def decrease_qty(id):
    item = CartItem.query.get_or_404(id)
    if item.quantity > 1:
        item.quantity -= 1
    else:
        db.session.delete(item)
    db.session.commit()
    return redirect('/cart/')


# update cart item
@app.route('/updatecart/<int:id>', methods=['POST', 'GET'])
def update_item(id):
    item = CartItem.query.get_or_404(id)
    quantity = None
    form = ShopItemsForm()
    if form.validate_on_submit():
        item.quantity = form.quantity.data
        try:
            db.session.commit()
            return redirect('/cart/')
        except:
            flash('There was an error updating your cart', category='error')
    return render_template('updatecart.html', form=form, quantity=quantity)


# removing items from current user cart
@app.route('/remove/<int:id>', methods=['POST', 'GET'])
def remove_item(id):
    item_to_remove = CartItem.query.get_or_404(id)
    try:
        db.session.delete(item_to_remove)
        db.session.commit()
        return redirect('/cart/')
    except:
        return 'Item not deleted'



    # Database item add karna hai
    product = Item.query.get_or_404(id)
    new_item = CartItem(
        customer_link=current_user.id,
        item_name=product.name,
        price=product.current_price,
        quantity=1
    )
    db.session.add(new_item)
    db.session.commit()
    return redirect('/cart/')

@app.route('/add_to_wishlist/<int:product_id>')
@login_required
def add_to_wishlist(product_id):

    user_id = current_user.id   # ✔ correct
    
    # ✔ Correct field name: item_id
    existing = Wishlist.query.filter_by(customer_id=user_id, item_id=product_id).first()
    if existing:
        flash("Already in Wishlist", "info")
        return redirect('/amazon')

    # ✔ Insert using item_id
    new_item = Wishlist(customer_id=user_id, item_id=product_id)
    db.session.add(new_item)
    db.session.commit()
    
    flash("Added to wishlist!", "success")
    return redirect('/amazon')

@app.route('/remove_wishlist/<int:pid>')
@login_required
def remove_wishlist(pid):
    # pid = actual product id (Item.id)
    user_id = current_user.id

    entry = Wishlist.query.filter_by(customer_id=user_id, item_id=pid).first()

    if entry:
        db.session.delete(entry)
        db.session.commit()
        flash("Removed from wishlist!", "success")
    else:
        flash("Item not found!", "error")

    return redirect('/wishlist')


@app.route('/wishlist')
@login_required
def wishlist_view():
    # current user id
    user_id = current_user.id

    wishlist = Wishlist.query.filter_by(customer_id=user_id).all()

    # yaha se actual products collect karenge
    products = []

    for w in wishlist:
        product = Item.query.get(w.item_id)    # ✔ asli product id se data
        if product:
            products.append(product)

    return render_template('wishlist.html', items=products)





@app.route('/search')
@login_required
def search():
    query = request.args.get('query', '').lower()

    # ==== SEARCH IN DATABASE ====
    db_items = Item.query.filter(
        Item.name.ilike(f"%{query}%")
    ).all()

    # ==== SEARCH IN FLASH SALE PRODUCTS ====
    flash_items = []
    for pid, data in flash_products.items():
        name, price, image = data
        if query in name.lower():
            flash_items.append({
                "id": pid,
                "name": name,
                "price": price,
                "image": image
            })

    return render_template(
        "search_results.html",
        db_items=db_items,
        flash_items=flash_items,
        query=query
    )

# payment page
@app.route('/payment', methods=['POST', 'GET'])
def payment():
    # do payment staff and delete items from current user cart
    return render_template('payment.html')


# stripe / fake payment sample endpoints (kept same)
import stripe
from flask import jsonify
stripe.api_key = ""


# ---------- CARD PAYMENT INTENT ----------
@app.route("/create-card-intent", methods=["POST"])
def create_card_intent():
    intent = stripe.PaymentIntent.create(
        amount=5000,
        currency="inr",
        payment_method_types=["card"]
    )
    return jsonify({"clientSecret": intent.client_secret})

# ---------- FAKE UPI SUCCESS ----------
@app.route("/fake-upi", methods=["POST"])
def fake_upi():
    return jsonify({"status": "success"})


# ---------- FAKE GPAY SUCCESS ----------
@app.route("/fake-gpay", methods=["POST"])
def fake_gpay():
    return jsonify({"status": "success"})

# ---------- SUCCESS PAGE ----------
#@app.route('/success')
#def success():
    #return render_template('success.html')

@app.route('/update_order_status/<int:id>', methods=["POST"])
def update_order_status(id):
    order = Order.query.get_or_404(id)
    new_status = request.form.get("status")
    order.status = new_status
    db.session.commit()
    return redirect('/admin_orders')

@app.route('/admin_orders')
def admin_orders():
    orders = Order.query.order_by(Order.date.desc()).all()
    return render_template('admin_orders.html', orders=orders)


@app.route('/myorders')
@login_required
def myorders():
    orders = Order.query.filter_by(customer_id=current_user.id).order_by(Order.date.desc()).all()
    return render_template('myorders.html', orders=orders)

@app.route('/orders')
@login_required
def orders():
    customer = current_user
    all_orders = Order.query.filter_by(customer_id=customer.id).order_by(Order.id.desc()).all()
    return render_template("orders.html", orders=all_orders)

@app.route('/success')
@login_required
def success():
    items = CartItem.query.filter_by(customer_link=current_user.id).all()

    if items:
        total = sum(i.price * i.quantity for i in items)

        # Create order
        new_order = Order(
            customer_id=current_user.id,
            total_amount=total,
            status="Order Placed"
        )
        db.session.add(new_order)

        # Empty the cart
        for i in items:
            db.session.delete(i)

        db.session.commit()

    return render_template('success.html')

# create DB tables on first run
with app.app_context():
    db.create_all()

 # Insert flash products into DB if not already added
    for pid, (name, price, image) in flash_products.items():
        existing = Item.query.filter_by(name=name).first()
        if not existing:
            new_item = Item(
                name=name,
                current_price=price,
                previous_price=price,
                remaining=10,
                image=image
            )
            db.session.add(new_item)
    db.session.commit()

if __name__ == "__main__":
    app.run(debug=True)
