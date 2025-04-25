# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from . import db


# Initialisation de SQLAlchemy
db = SQLAlchemy()

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f'<Customer {self.name}>'
    
  

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), default='en attente')  # ou "pending"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)  # Renommer pour clarifier que c'est un hash
    email = db.Column(db.String(255), nullable=False, unique=True)
    role = db.Column(db.String(50), nullable=False)
    rfid_card = db.Column(db.String(100))
    # Pas besoin de stocker le token JWT dans la base de données
    
    # Relations
    orders = db.relationship('Order', backref='user', lazy=True)
    alerts = db.relationship('Alert', backref='user', lazy=True)
    
    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')
        
    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    
    # Relations
    products = db.relationship('Product', backref='category', lazy=True)
    
    def __repr__(self):
        return f'<Category {self.name}>'

class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    designation = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    min_threshold = db.Column(db.Float, nullable=False)
    max_threshold = db.Column(db.Float, nullable=False)
    rfid_tag = db.Column(db.String(100))
    
    # Relations
    inventories = db.relationship('Inventory', backref='product', lazy=True)
    orders = db.relationship('Order', backref='product', lazy=True)
    alerts = db.relationship('Alert', backref='product', lazy=True)
    predictions = db.relationship('OrderPrediction', backref='product', lazy=True)
    
    def __repr__(self):
        return f'<Product {self.designation}>'

class Zone(db.Model):
    __tablename__ = 'zones'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    
    # Relations
    inventories = db.relationship('Inventory', backref='zone', lazy=True)
    sensors = db.relationship('Sensor', backref='zone', lazy=True)
    
    def __repr__(self):
        return f'<Zone {self.name}>'

class Inventory(db.Model):
    __tablename__ = 'inventory'
    
    # Clé primaire composite
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), primary_key=True)
    zone_id = db.Column(db.Integer, db.ForeignKey('zones.id'), primary_key=True)
    
    # Autres attributs
    quantity = db.Column(db.Integer, nullable=False, default=0)
    last_update_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Inventory product_id={self.product_id}, zone_id={self.zone_id}>'

class Sensor(db.Model):
    __tablename__ = 'sensors'
    
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(100), nullable=False)
    zone_id = db.Column(db.Integer, db.ForeignKey('zones.id'), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    last_reading = db.Column(db.DateTime)
    
    # Relations
    sensor_data = db.relationship('SensorData', backref='sensor', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Sensor {self.id} type={self.type}>'

class SensorData(db.Model):
    __tablename__ = 'sensor_data'
    
    id = db.Column(db.Integer, primary_key=True)
    sensor_id = db.Column(db.Integer, db.ForeignKey('sensors.id'), nullable=False)
    value = db.Column(db.String(255), nullable=False)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<SensorData {self.id} sensor_id={self.sensor_id}>'

class Alert(db.Model):
    __tablename__ = 'alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # La personne assignée à l'alerte
    
    def __repr__(self):
        return f'<Alert {self.id} type={self.type}>'

class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    delivered_at = db.Column(db.DateTime)
    returned_at = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # L'utilisateur qui a créé la commande
    
    def __repr__(self):
        return f'<Order {self.id} product_id={self.product_id}>'

class OrderPrediction(db.Model):
    __tablename__ = 'order_predictions'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    predicted_quantity = db.Column(db.Float, nullable=False)
    prediction_period = db.Column(db.String(50), nullable=False)  # daily, weekly, monthly
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    start_prediction = db.Column(db.DateTime, nullable=False)  # Date de début de la période prédite
    finish_prediction = db.Column(db.DateTime, nullable=False)  # Date de fin de la période prédite
    
    # Relation avec les commandes qui ont été créées à partir de cette prédiction
    orders = db.relationship('Order', secondary='prediction_orders', backref='prediction')
    
    def __repr__(self):
        return f'<OrderPrediction {self.id} product_id={self.product_id}>'

# Table d'association entre prédictions et commandes (relation many-to-many)
prediction_orders = db.Table('prediction_orders',
    db.Column('prediction_id', db.Integer, db.ForeignKey('order_predictions.id'), primary_key=True),
    db.Column('order_id', db.Integer, db.ForeignKey('orders.id'), primary_key=True)
)