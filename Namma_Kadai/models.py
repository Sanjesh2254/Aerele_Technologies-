from Namma_Kadai import db
from flask_login import UserMixin
from datetime import datetime
import pytz


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    
    companies = db.relationship('Company', backref='user', uselist=False)


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(150), nullable=False)
    qty = db.Column(db.Integer, nullable=False, default=0)
    rate = db.Column(db.Float, nullable=False)  # New field for the rate of the item
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    
    # Relationship to Sales, reference 'Sales' as a string to avoid circular reference issues
    sales = db.relationship('Sales', backref='item_relation', lazy=True)

    


class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(150),unique=True, nullable=False)
    cash_balance = db.Column(db.Float, nullable=False, default=1000.00)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationship with purchases and items
    purchases = db.relationship('Purchase', backref='company_purchase', lazy=True)
    items = db.relationship('Item', backref='company', lazy=True)
    
    # Relationship with sales
    sales = db.relationship('Sales', backref='sales_company', lazy=True)


class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id', ondelete='CASCADE'))
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    qty = db.Column(db.Integer, nullable=False)
    rate = db.Column(db.Float, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('Asia/Kolkata')))
    
    item = db.relationship('Item', backref='purchases')
    
    # Ensure the backref is unique
    company = db.relationship('Company', backref='purchase_records')  # Renamed backref

class StoredPurchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)  # Added ForeignKey for Item
    item_name = db.Column(db.String(100), nullable=False)
    
    qty = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    
    item = db.relationship('Item', backref='stored_purchases')



class Sales(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    qty = db.Column(db.Integer, nullable=False)
    rate = db.Column(db.Float, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('Asia/Kolkata')))
    
    # Relationship with Item and Company
    item = db.relationship('Item', backref='sales_records', lazy=True)
    company = db.relationship('Company', backref='company_sales', lazy=True)


class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    product_name = db.Column(db.String(150), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    available_qty = db.Column(db.Integer, nullable=False)
    purchase_qty = db.Column(db.Integer, nullable=False, default=0)

