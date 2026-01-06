# db_create.py  (updated / final)
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# single db instance used by app.py
db = SQLAlchemy()

# ---------------- CUSTOMER ----------------
class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    date_joined = db.Column(db.DateTime, default=datetime.utcnow)

    # REQUIRED BY FLASK-LOGIN
    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)


# ---------------- ITEM / PRODUCTS ----------------
class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    current_price = db.Column(db.Integer, nullable=False)
    previous_price = db.Column(db.Integer, nullable=False)
    remaining = db.Column(db.Integer, nullable=False)
    image = db.Column(db.String(300))   # ← ADD THIS LINE
    date_added = db.Column(db.DateTime, default=datetime.utcnow)

# ---------------- CART ITEMS ----------------
class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_link = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    item_name = db.Column(db.String(150), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    

# ---------------- WISHLIST ----------------
class Wishlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer)
    item_id = db.Column(db.Integer)

# ---------------- REVIEWS ----------------
class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1–5
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    total_amount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(30), default="Processing")  # Processing, Shipped, Out for Delivery, Delivered
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship("OrderItem", back_populates="order", cascade="all, delete")

    def __repr__(self):
        return f'<Order {self.id}>'

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Integer, default=1)
    price = db.Column(db.Integer, nullable=False)

    order = db.relationship("Order", back_populates="items")




