# app.py
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from models import db, User, Product, Category, Zone, Inventory, Sensor, SensorData,Customer, Alert, Order, OrderPrediction
from datetime import datetime
from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt 
from flask_cors import CORS
# login
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import timedelta
from werkzeug.security import generate_password_hash
from flask_jwt_extended import verify_jwt_in_request, get_jwt
from generate_alerts import generate_all_alerts  
from apscheduler.schedulers.background import BackgroundScheduler
import serial
import threading
from flask import jsonify, request
import time

# Initialisation de l'application
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:4200"}})  # Remplacez par l'URL de votre frontend
CORS(app, origins=["http://localhost:4200"], supports_credentials=True)

# Configuration JWT après l'initialisation de l'application
app.config['JWT_SECRET_KEY'] = 'KEY00155'  # Changez ceci en production!
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)  # Token valide pour 24 heures
jwt = JWTManager(app)

# Configuration de la base de données MySQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root@localhost/stock_genius'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'KEY00155'  # Important pour la sécurité

# Initialisation de la base de données avec l'application
db.init_app(app)

# Route pour créer les tables dans la base de données 
@app.route('/init-db')
def init_db():
    with app.app_context():
        db.drop_all()
        db.create_all()
    return jsonify({"message": "Base de données initialisée avec succès!"})

# Verification role
def role_required(roles):
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            if claims.get("role") in roles:
                return fn(*args, **kwargs)
            else:
                return jsonify({"error": "Unauthorized access"}), 403
        return decorator
    return wrapper

# Route d'authentification - login
@app.route('/api/auth/login', methods=['POST'])
def login():
    if not request.is_json:
        return jsonify({"error": "Missing JSON in request"}), 400
    
    username = request.json.get('username', None)
    password = request.json.get('password', None)
    
    if not username or not password:
        return jsonify({"error": "Missing username or password"}), 400
    
    user = User.query.filter_by(username=username).first()
    
    if not user or not user.verify_password(password):
        return jsonify({"error": "Invalid username or password"}), 401
    
    # Création du token avec les informations utiles
    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={
            'username': user.username,
            'email': user.email,
            'role': user.role
        }
    )
    
    return jsonify({
        'message': 'Login successful',
        'access_token': access_token,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role
        }
    }), 200

# Route pour s'enregistrer - register
@app.route('/api/auth/register', methods=['POST'])
def register():
    if not request.is_json:
        return jsonify({"error": "Missing JSON in request"}), 400
    
    username = request.json.get('username', None)
    email = request.json.get('email', None)
    password = request.json.get('password', None)
    role = request.json.get('role', 'user')  # Par défaut, un nouvel utilisateur a le rôle "user"
    
    if not username or not email or not password:
        return jsonify({"error": "Missing required fields"}), 400
    
    # Vérifier si l'utilisateur ou l'email existe déjà
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 409
    
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already exists"}), 409
    
    # Créer un nouvel utilisateur
    new_user = User(
        username=username,
        email=email,
        role=role,
        rfid_card=request.json.get('rfid_card')
    )
    new_user.password = password  # Utilise le setter pour hasher le mot de passe
    
    db.session.add(new_user)
    db.session.commit()
    
    # Créer un token pour le nouvel utilisateur
    access_token = create_access_token(
        identity=str(new_user.id),
        additional_claims={
            'username': new_user.username,
            'email': new_user.email,
            'role': new_user.role
        }
    )
    
    return jsonify({
        'message': 'User registered successfully',
        'access_token': access_token,
        'user': {
            'id': new_user.id,
            'username': new_user.username,
            'email': new_user.email,
            'role': new_user.role
        }
    }), 201

# Route protégée d'exemple
@app.route('/api/protected', methods=['GET'])
@jwt_required()
def protected():
    # Récupérer l'identité de l'utilisateur à partir du token JWT
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    return jsonify({
        'message': f'Hello {user.username}! This is a protected route.',
        'user_id': current_user_id,
        'role': user.role
    }), 200

# Routes pour les utilisateurs
@app.route('/api/users', methods=['GET'])
def get_users():
    users = User.query.all()
    result = []
    for user in users:
        user_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role
        }
        result.append(user_data)
    return jsonify(result)

# Modifier la route de création d'utilisateur pour utiliser le hash de mot de passe
@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.get_json()
    
    # Vérifier si l'email ou le username existe déjà
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Cet email est déjà utilisé'}), 400
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Ce nom d\'utilisateur est déjà utilisé'}), 400
    
    new_user = User(
        username=data['username'],
        email=data['email'],
        role=data['role'],
        rfid_card=data.get('rfid_card')
    )
    new_user.password = data['password']  # Utilise le setter pour hasher le mot de passe
    
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({
        'message': 'Utilisateur créé avec succès',
        'user': {
            'id': new_user.id,
            'username': new_user.username,
            'email': new_user.email,
            'role': new_user.role
        }
    }), 201

# ---------------------- ROUTES POUR CLIENTS ----------------------

# Obtenir tous les clients
@app.route('/api/customers', methods=['GET'])
@jwt_required()
def get_customers():
    customers = Customer.query.all()
    result = []
    for customer in customers:
        result.append({
            'id': customer.id,
            'name': customer.name,
            'email': customer.email,
            'phone': customer.phone,
            'address': customer.address
        })
    return jsonify(result), 200

# Créer un client
@app.route('/api/customers', methods=['POST'])
@jwt_required()
def create_customer():
    data = request.get_json()
    if not data.get('name') or not data.get('email'):
        return jsonify({'error': 'Le nom et l\'email sont obligatoires'}), 400

    if Customer.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Un client avec cet email existe déjà'}), 409

    new_customer = Customer(
        name=data['name'],
        email=data['email'],
        phone=data.get('phone'),
        address=data.get('address')
    )
    db.session.add(new_customer)
    db.session.commit()
    return jsonify({'message': 'Client créé avec succès'}), 201

# Modifier un client
@app.route('/api/customers/<int:customer_id>', methods=['PUT'])
@jwt_required()
def update_customer(customer_id):
    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({'error': 'Client non trouvé'}), 404

    data = request.get_json()
    customer.name = data.get('name', customer.name)
    customer.email = data.get('email', customer.email)
    customer.phone = data.get('phone', customer.phone)
    customer.address = data.get('address', customer.address)
    db.session.commit()
    return jsonify({'message': 'Client mis à jour avec succès'}), 200

# Supprimer un client
@app.route('/api/customers/<int:customer_id>', methods=['DELETE'])
@jwt_required()
def delete_customer(customer_id):
    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({'error': 'Client non trouvé'}), 404
    db.session.delete(customer)
    db.session.commit()
    return jsonify({'message': 'Client supprimé avec succès'}), 200


# GET all orders
@app.route('/api/orders', methods=['GET'])
@jwt_required()
def get_orders():
    orders = Order.query.all()
    result = []
    for order in orders:
        result.append({
            'id': order.id,
            'customer_id': order.customer_id,
            'status': order.status,
            'created_at': order.created_at,
            'delivered_at': order.delivered_at,
            'returned_at':order.returned_at,
            'user_id':order.user_id,
            'quantity':order.quantity,
            'product_id':order.product_id
            
        })
    return jsonify(result), 200

# GET one order by ID
@app.route('/api/orders/<int:order_id>', methods=['GET'])
@jwt_required()
def get_order(order_id):
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'error': 'Commande non trouvée'}), 404
    return jsonify({
        'id': order.id,
        'customer_id': order.customer_id,
        'status': order.status,
        'created_at': order.created_at,
        'delivered_at': order.delivered_at,
        'returned_at':order.returned_at,
        'user_id':order.user_id,
        'quantity':order.quantity,
        'product_id':order.product_id
    }), 200

@app.route('/api/orders', methods=['POST'])
@jwt_required()
def create_order():
    data = request.get_json()
    if not data or 'customer_id' not in data or 'product_id' not in data or 'quantity' not in data:
        return jsonify({'error': 'customer_id, product_id et quantity sont requis'}), 400

    user_id = get_jwt_identity()  # Si tu utilises JWT pour identifier l'utilisateur connecté

    new_order = Order(
        customer_id=data['customer_id'],
        product_id=data['product_id'],
        quantity=data['quantity'],
        status=data.get('status', 'en attente'),
        user_id=user_id
    )
    db.session.add(new_order)
    db.session.commit()
    return jsonify({'message': 'Commande créée avec succès', 'order_id': new_order.id}), 201
# UPDATE an order
@app.route('/api/orders/<int:order_id>', methods=['PUT'])
@jwt_required()
def update_order(order_id):
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'error': 'Commande non trouvée'}), 404

    data = request.get_json()
    order.status = data.get('status', order.status)
    order.quantity = data.get('quantity', order.quantity)
    order.delivered_at = data.get('delivered_at', order.delivered_at)
    order.returned_at = data.get('returned_at', order.returned_at)
    # Tu peux aussi permettre de changer product_id ou customer_id si besoin
    db.session.commit()
    return jsonify({'message': 'Commande mise à jour avec succès'}), 200


# DELETE an order
@app.route('/api/orders/<int:order_id>', methods=['DELETE'])
@jwt_required()
def delete_order(order_id):
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'error': 'Commande non trouvée'}), 404

    try:
        db.session.delete(order)
        db.session.commit()
        return jsonify({'message': 'Commande supprimée avec succès'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Erreur lors de la suppression', 'details': str(e)}), 500



# Routes pour les produits
@app.route('/api/products', methods=['GET'])
def get_products():
    products = Product.query.all()
    result = []
    for product in products:
        product_data = {
            'id': product.id,
            'designation': product.designation,
            'description': product.description,
            'category': product.category.name,
            'min_threshold': product.min_threshold,
            'max_threshold': product.max_threshold,
            'rfid_tag': product.rfid_tag
        }
        result.append(product_data)
    return jsonify(result)

@app.route('/api/products', methods=['POST'])
def create_product():
    data = request.get_json()
    
    # Vérifier si la catégorie existe
    category = Category.query.get(data['category_id'])
    if not category:
        return jsonify({'error': 'Catégorie non trouvée'}), 404
        
    new_product = Product(
        designation=data['designation'],
        description=data.get('description'),
        category_id=data['category_id'],
        min_threshold=data['min_threshold'],
        max_threshold=data['max_threshold'],
        rfid_tag=data.get('rfid_tag')
    )
    
    db.session.add(new_product)
    db.session.commit()
    
    return jsonify({
        'message': 'Produit créé avec succès',
        'product': {
            'id': new_product.id,
            'designation': new_product.designation,
            'description': new_product.description,
            'category': category.name
        }
    }), 201

# Routes pour les catégories
@app.route('/api/categories', methods=['GET'])
def get_categories():
    categories = Category.query.all()
    result = []
    for category in categories:
        category_data = {
            'id': category.id,
            'name': category.name,
            'description': category.description
        }
        result.append(category_data)
    return jsonify(result)

@app.route('/api/categories', methods=['POST'])
def create_category():
    data = request.get_json()
    
    new_category = Category(
        name=data['name'],
        description=data.get('description')
    )
    
    db.session.add(new_category)
    db.session.commit()
    
    return jsonify({
        'message': 'Catégorie créée avec succès',
        'category': {
            'id': new_category.id,
            'name': new_category.name,
            'description': new_category.description
        }
    }), 201
#Supprimer un produit
@app.route('/api/products/<int:product_id>', methods=['DELETE'])
@jwt_required()
def delete_product(product_id):
    # Vérifier si le produit existe
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'error': 'Produit non trouvé'}), 404
    
    # Supprimer le produit
    db.session.delete(product)
    db.session.commit()
    
    return jsonify({'message': 'Produit supprimé avec succès'}), 200
#Modifier un Produit
@app.route('/api/products/<int:product_id>', methods=['PUT'])
@jwt_required()
def update_product(product_id):
    # Vérifier si le produit existe
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'error': 'Produit non trouvé'}), 404
    
    # Récupérer les données JSON envoyées dans la requête
    data = request.get_json()
    
    # Mettre à jour les champs du produit
    product.designation = data.get('designation', product.designation)
    product.description = data.get('description', product.description)
    product.category_id = data.get('category_id', product.category_id)
    product.min_threshold = data.get('min_threshold', product.min_threshold)
    product.max_threshold = data.get('max_threshold', product.max_threshold)
    product.rfid_tag = data.get('rfid_tag', product.rfid_tag)
    
    # Valider que la catégorie existe (si elle est modifiée)
    if 'category_id' in data:
        category = Category.query.get(data['category_id'])
        if not category:
            return jsonify({'error': 'Catégorie non trouvée'}), 404
    
    # Sauvegarder les modifications dans la base de données
    db.session.commit()
    
    return jsonify({
        'message': 'Produit mis à jour avec succès',
        'product': {
            'id': product.id,
            'designation': product.designation,
            'description': product.description,
            'category': Category.query.get(product.category_id).name,
            'min_threshold': product.min_threshold,
            'max_threshold': product.max_threshold,
            'rfid_tag': product.rfid_tag
        }
    }), 200
# Routes pour les zones
@app.route('/api/zones', methods=['GET'])
def get_zones():
    zones = Zone.query.all()
    result = []
    for zone in zones:
        zone_data = {
            'id': zone.id,
            'name': zone.name,
            'description': zone.description
        }
        result.append(zone_data)
    return jsonify(result)

@app.route('/api/zones', methods=['POST'])
def create_zone():
    data = request.get_json()
    
    new_zone = Zone(
        name=data['name'],
        description=data.get('description')
    )
    
    db.session.add(new_zone)
    db.session.commit()
    
    return jsonify({
        'message': 'Zone créée avec succès',
        'zone': {
            'id': new_zone.id,
            'name': new_zone.name,
            'description': new_zone.description
        }
    }), 201

# Routes pour l'inventaire
@app.route('/api/inventory', methods=['GET'])
def get_inventory():
    inventory_items = Inventory.query.all()
    result = []
    for item in inventory_items:
        item_data = {
            'product_id': item.product_id,
            'product_name': item.product.designation,
            'zone_id': item.zone_id,
            'zone_name': item.zone.name,
            'quantity': item.quantity,
            'last_update_at': item.last_update_at
        }
        result.append(item_data)
    return jsonify(result)

@app.route('/api/inventory', methods=['POST'])
def create_inventory():
    data = request.get_json()
    
    # Vérifier si le produit et la zone existent
    product = Product.query.get(data['product_id'])
    zone = Zone.query.get(data['zone_id'])
    if not product:
        return jsonify({'error': 'Produit non trouvé'}), 404
    if not zone:
        return jsonify({'error': 'Zone non trouvée'}), 404
    
    # Vérifier si l'entrée d'inventaire existe déjà
    existing_inventory = Inventory.query.filter_by(
        product_id=data['product_id'],
        zone_id=data['zone_id']
    ).first()
    
    if existing_inventory:
        # Mettre à jour l'inventaire existant
        existing_inventory.quantity = data['quantity']
        existing_inventory.last_update_at = datetime.utcnow()
        db.session.commit()
        return jsonify({
            'message': 'Inventaire mis à jour avec succès',
            'inventory': {
                'product_id': existing_inventory.product_id,
                'zone_id': existing_inventory.zone_id,
                'quantity': existing_inventory.quantity
            }
        }), 200
    else:
        # Créer un nouvel inventaire
        new_inventory = Inventory(
            product_id=data['product_id'],
            zone_id=data['zone_id'],
            quantity=data['quantity']
        )
        
        db.session.add(new_inventory)
        db.session.commit()
        
        return jsonify({
            'message': 'Inventaire créé avec succès',
            'inventory': {
                'product_id': new_inventory.product_id,
                'zone_id': new_inventory.zone_id,
                'quantity': new_inventory.quantity
            }
        }), 201

#alerte
# Route pour obtenir les alertes résolues
@app.route('/api/alerts/resolved', methods=['GET'])
@jwt_required()
def get_resolved_alerts():
    resolved_alerts = Alert.query.filter_by(status="résolu").all()
    result = []
    for alert in resolved_alerts:
        # Récupérer les informations du produit associé
        product_info = None
        if alert.product_id:
            product = Product.query.get(alert.product_id)
            if product:
                product_info = {
                    'id': product.id,
                    'designation': product.designation
                }
        
        # Récupérer les informations de l'utilisateur associé
        user_info = None
        if alert.user_id:
            user = User.query.get(alert.user_id)
            if user:
                user_info = {
                    'id': user.id,
                    'username': user.username
                }
        
        result.append({
            'id': alert.id,
            'type': alert.type,
            'status': alert.status,
            'created_at': alert.created_at,
            'product': product_info,
            'user': user_info
        })
    
    return jsonify(result), 200

# Route pour obtenir les alertes non résolues
@app.route('/api/alerts/unresolved', methods=['GET'])
@jwt_required()
def get_unresolved_alerts():
    unresolved_alerts = Alert.query.filter(Alert.status != "résolu").all()
    result = []
    for alert in unresolved_alerts:
        # Récupérer les informations du produit associé
        product_info = None
        if alert.product_id:
            product = Product.query.get(alert.product_id)
            if product:
                product_info = {
                    'id': product.id,
                    'designation': product.designation
                }
        
        # Récupérer les informations de l'utilisateur associé
        user_info = None
        if alert.user_id:
            user = User.query.get(alert.user_id)
            if user:
                user_info = {
                    'id': user.id,
                    'username': user.username
                }
        
        result.append({
            'id': alert.id,
            'type': alert.type,
            'status': alert.status,
            'created_at': alert.created_at,
            'product': product_info,
            'user': user_info
        })
    
    return jsonify(result), 200

# Route pour obtenir toutes les alertes avec filtrage par statut
@app.route('/api/alerts', methods=['GET'])
@jwt_required()
def get_alerts():
    # Récupérer le paramètre de requête 'status' s'il existe
    status = request.args.get('status')
    
    # Construire la requête en fonction du paramètre
    query = Alert.query
    if status:
        query = query.filter_by(status=status)
    
    alerts = query.all()
    result = []
    for alert in alerts:
        # Récupérer les informations du produit associé
        product_info = None
        if alert.product_id:
            product = Product.query.get(alert.product_id)
            if product:
                product_info = {
                    'id': product.id,
                    'designation': product.designation
                }
        
        # Récupérer les informations de l'utilisateur associé
        user_info = None
        if alert.user_id:
            user = User.query.get(alert.user_id)
            if user:
                user_info = {
                    'id': user.id,
                    'username': user.username
                }
        
        result.append({
            'id': alert.id,
            'type': alert.type,
            'status': alert.status,
            'created_at': alert.created_at,
            'product': product_info,
            'user': user_info
        })
    
    return jsonify(result), 200
@app.route('/api/alerts/<int:alert_id>/resolve', methods=['POST'])
@jwt_required()
def resolve_alert(alert_id):
    """
    Route pour marquer une alerte comme résolue
    """
    # Récupérer l'alerte
    alert = Alert.query.get(alert_id)
    if not alert:
        return jsonify({'error': 'Alerte non trouvée'}), 404
    
    # Mettre à jour le statut de l'alerte
    alert.status = "résolu"
    
    # Enregistrer les modifications
    db.session.commit()
    
    return jsonify({
        'message': 'Alerte résolue avec succès',
        'alert': {
            'id': alert.id,
            'type': alert.type,
            'status': alert.status
        }
    }), 200
# 👇 Démarrer le scheduler
def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=generate_alerts_job, trigger="interval", minutes=7)#minutes
    scheduler.start()

# 👇 Wrapper pour exécuter les alertes dans le contexte Flask
def generate_alerts_job():
    with app.app_context():
        generate_all_alerts()
        print("✅ Alertes générées automatiquement")
   
#CODE ARDUINO /////////////////////////////////////////////////////////////////////
# Configuration du port série Arduino (à ajuster selon votre configuration)
SERIAL_PORT = 'COM13'  # Changez selon votre port Arduino
BAUD_RATE = 9600
arduino_serial = None

# Fonction pour initialiser la connexion série avec Arduino
def init_arduino_serial():
    global arduino_serial
    try:
        arduino_serial = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"✅ Connexion établie avec Arduino sur {SERIAL_PORT}")
        return True
    except serial.SerialException as e:
        print(f"❌ Erreur de connexion au port série: {e}")
        return False

# Fonction pour lire les données RFID en continu
def read_rfid_data():
    global arduino_serial
    
    while True:
        try:
            if arduino_serial and arduino_serial.is_open and arduino_serial.in_waiting:
                # Lire une ligne depuis Arduino
                data_str = arduino_serial.readline().decode('utf-8').strip()
                
                # Ignorer les lignes vides
                if not data_str:
                    continue
                
                print(f"📡 Données reçues: {data_str}")
                
                # Traiter les données RFID
                try:
                    import json
                    
                    # Essayer de parser en JSON si c'est au format JSON
                    if data_str.startswith('{') and data_str.endswith('}'):
                        data = json.loads(data_str)
                        
                        # Vérifier s'il y a un UID et des données supplémentaires
                        if 'uid' in data and 'data' in data:
                            uid = data['uid']
                            card_data = data['data']
                            
                            print(f"✅ UID: {uid}")
                            print(f"✅ Données de la carte: {card_data}")
                            
                            # Stocker dans la base de données
                            with app.app_context():
                                # Si card_data est un objet, le convertir en string limité à 255 caractères
                                if isinstance(card_data, dict):
                                    value_str = json.dumps(card_data)[:255]  # Limiter à 255 caractères
                                else:
                                    value_str = str(card_data)[:255]
                                
                                new_sensor_data = SensorData(
                                    sensor_id=1,  # ID du capteur RFID
                                    value=value_str
                                )
                                db.session.add(new_sensor_data)
                                db.session.commit()
                                
                                # Si les données contiennent un ID produit, mettre à jour le produit
                                if isinstance(card_data, dict) and ('product_id' in card_data or 'id' in card_data):
                                    product_id = card_data.get('product_id', card_data.get('id'))
                                   #update_product_with_rfid_data(product_id, card_data, uid)
                        else:
                            # Seulement UID
                            print(f"⚠️ Seulement UID reçu: {data.get('uid', 'Non spécifié')}")
                            # Stocker quand même l'UID
                            with app.app_context():
                                new_sensor_data = SensorData(
                                    sensor_id=1,
                                    value=f"UID: {data.get('uid', 'Non spécifié')}"[:255]
                                )
                                db.session.add(new_sensor_data)
                                db.session.commit()
                    else:
                        # Format non-JSON, probablement juste un UID
                        print(f"⚠️ Données non-JSON: {data_str}")
                        with app.app_context():
                            new_sensor_data = SensorData(
                                sensor_id=1,
                                value=data_str[:255]
                            )
                            db.session.add(new_sensor_data)
                            db.session.commit()
                
                except json.JSONDecodeError as je:
                    print(f"❌ Erreur de décodage JSON: {je}")
                    # Stocker les données brutes
                    with app.app_context():
                        new_sensor_data = SensorData(
                            sensor_id=1,
                            value=data_str[:255]
                        )
                        db.session.add(new_sensor_data)
                        db.session.commit()
                except Exception as e:
                    print(f"❌ Erreur de traitement des données: {e}")
            
            time.sleep(0.1)  # Pause pour éviter une utilisation CPU excessive
            
        except Exception as e:
            print(f"❌ Erreur lors de la lecture RFID: {e}")
            time.sleep(1)  # Attendre avant de réessayer

# Fonction auxiliaire pour mettre à jour un produit avec les données RFID
def update_product_with_rfid_data(product_id, card_data, uid):
    try:
        product = Product.query.get(product_id)
        if product:
            # Mettre à jour le produit avec les données de la carte
            if 'name' in card_data:
                product.designation = card_data['name']
            if 'description' in card_data:
                product.description = card_data['description']
            # Ajouter d'autres champs selon vos besoins
            
            # Mettre à jour le tag RFID si ce n'est pas déjà fait
            if not product.rfid_tag and uid:
                product.rfid_tag = uid
                
            db.session.commit()
            print(f"✅ Produit ID {product_id} mis à jour avec les données RFID")
        else:
            print(f"⚠️ Produit ID {product_id} non trouvé dans la base de données")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erreur lors de la mise à jour du produit: {e}")
""" def read_rfid_data():
    global arduino_serial
    
    while True:
        try:
            if arduino_serial and arduino_serial.is_open and arduino_serial.in_waiting:
                # Lire une ligne depuis Arduino
                rfid_data = arduino_serial.readline().decode('utf-8').strip()
                
                # Ignorer les lignes qui ne sont pas des données RFID valides
                # Par exemple, ignorer les lignes qui contiennent des instructions comme "w - Écrire"
                if rfid_data and not rfid_data.startswith("r -") and not rfid_data.startswith("w -"):
                    print(f"📡 Données RFID reçues: {rfid_data}")
                    
                    # Vérifier si c'est un UID RFID valide (généralement hexadécimal)
                    import re
                    if re.match(r'^[0-9A-F\s]+$', rfid_data.upper()):
                        process_rfid_data({"uid": rfid_data.upper().replace(" ", "")})
                    elif rfid_data.startswith("{") and rfid_data.endswith("}"):
                        try:
                            import json
                            data = json.loads(rfid_data)
                            process_rfid_data(data)
                        except json.JSONDecodeError:
                            print("❌ Format JSON invalide")
                    else:
                        print(f"⚠️ Ignorer les données non RFID: {rfid_data}")
            
            time.sleep(0.1)  # Pause pour éviter une utilisation CPU excessive
            
        except Exception as e:
            print(f"❌ Erreur lors de la lecture RFID: {e}")
            time.sleep(1)  # Attendre avant de réessayer """
# Fonction pour traiter les données RFID
def process_rfid_data(data):
    with app.app_context():
        uid = data.get("uid", "").upper()  # On récupère toujours l'UID pour l'authentification
        card_data = data.get("data", None)
        
        # Si des données sont stockées sur la carte
        if card_data:
            try:
                # Extraire uniquement les informations importantes
                product_info = {
                    'product_id': card_data.get('id'),
                    'product_name': card_data.get('name'),
                    'price': card_data.get('price'),
                    'quantity': card_data.get('quantity', 0)
                }
                
                print(f"✅ Informations du produit: {product_info}")
                
                # Enregistrer les données dans SensorData
                # Utilisez le bon nom de champ pour l'horodatage dans votre modèle
                new_sensor_data = SensorData(
                    sensor_id=1,  # ID du capteur RFID
                    value=str(product_info),
                    # Si votre modèle a un champ 'created_at' au lieu de 'timestamp'
                    # created_at=datetime.utcnow()
                )
                db.session.add(new_sensor_data)
                db.session.commit()
                
                return product_info  # Retourner uniquement les infos du produit
                
            except Exception as e:
                db.session.rollback()
                print(f"❌ Erreur lors du traitement des données: {e}")
                return None
        
        # Si pas de données sur la carte, on renvoie None
        print("⚠️ Aucune donnée produit trouvée sur cette carte")
        return None
# Route pour démarrer la lecture RFID
@app.route('/api/rfid/start', methods=['POST'])
@jwt_required()
@role_required(['admin'])  # Limiter aux administrateurs
def start_rfid_reader():
    """Démarrer la lecture RFID"""
    global arduino_serial
    
    if arduino_serial and arduino_serial.is_open:
        return jsonify({"message": "Le lecteur RFID est déjà démarré"}), 200
    
    if init_arduino_serial():
        # Démarrer le thread de lecture RFID
        rfid_thread = threading.Thread(target=read_rfid_data, daemon=True)
        rfid_thread.start()
        return jsonify({"message": "Lecteur RFID démarré avec succès"}), 200
    else:
        return jsonify({"error": "Impossible de se connecter au lecteur RFID"}), 500

# Route pour arrêter la lecture RFID
@app.route('/api/rfid/stop', methods=['POST'])
@jwt_required()
@role_required(['admin'])  # Limiter aux administrateurs
def stop_rfid_reader():
    """Arrêter la lecture RFID"""
    global arduino_serial
    
    if arduino_serial and arduino_serial.is_open:
        arduino_serial.close()
        arduino_serial = None
        return jsonify({"message": "Lecteur RFID arrêté avec succès"}), 200
    else:
        return jsonify({"message": "Le lecteur RFID n'était pas démarré"}), 200

# Route pour obtenir les dernières lectures RFID
@app.route('/api/rfid/readings', methods=['GET'])
@jwt_required()
def get_rfid_readings():
    """Obtenir les dernières lectures RFID"""
    # Nombre de lectures à récupérer (par défaut 10)
    limit = request.args.get('limit', 10, type=int)
    
    # Récupérer les données du capteur RFID (sensor_id=1 pour RFID)
    readings = SensorData.query.filter_by(sensor_id=1).order_by(SensorData.timestamp.desc()).limit(limit).all()
    
    result = []
    for reading in readings:
        data = {
            'id': reading.id,
            'value': reading.value,
            'timestamp': reading.timestamp
        }
        
        # Ajouter les informations sur le produit si disponible
        if reading.product_id:
            product = Product.query.get(reading.product_id)
            if product:
                data['product'] = {
                    'id': product.id,
                    'designation': product.designation,
                    'category': product.category.name
                }
        
        result.append(data)
    
    return jsonify(result), 200

# Route pour associer une carte RFID à un produit
@app.route('/api/products/<int:product_id>/assign-rfid', methods=['POST'])
@jwt_required()
@role_required(['admin', 'manager'])
def assign_rfid_to_product(product_id):
    """Associer une carte RFID à un produit"""
    # Vérifier si le produit existe
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'error': 'Produit non trouvé'}), 404
    
    data = request.get_json()
    if not data or 'rfid_tag' not in data:
        return jsonify({'error': 'rfid_tag est requis'}), 400
    
    # Vérifier si le tag RFID est déjà utilisé par un autre produit
    existing_product = Product.query.filter_by(rfid_tag=data['rfid_tag']).first()
    if existing_product and existing_product.id != product_id:
        return jsonify({'error': 'Ce tag RFID est déjà attribué à un autre produit'}), 409
    
    # Mettre à jour le produit
    product.rfid_tag = data['rfid_tag']
    db.session.commit()
    
    return jsonify({
        'message': 'Tag RFID associé avec succès',
        'product': {
            'id': product.id,
            'designation': product.designation,
            'rfid_tag': product.rfid_tag
        }
    }), 200

# Route pour associer une carte RFID à un utilisateur
@app.route('/api/users/<int:user_id>/assign-rfid', methods=['POST'])
@jwt_required()
@role_required(['admin'])
def assign_rfid_to_user(user_id):
    """Associer une carte RFID à un utilisateur"""
    # Vérifier si l'utilisateur existe
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Utilisateur non trouvé'}), 404
    
    data = request.get_json()
    if not data or 'rfid_card' not in data:
        return jsonify({'error': 'rfid_card est requis'}), 400
    
    # Vérifier si la carte RFID est déjà utilisée par un autre utilisateur
    existing_user = User.query.filter_by(rfid_card=data['rfid_card']).first()
    if existing_user and existing_user.id != user_id:
        return jsonify({'error': 'Cette carte RFID est déjà attribuée à un autre utilisateur'}), 409
    
    # Mettre à jour l'utilisateur
    user.rfid_card = data['rfid_card']
    db.session.commit()
    
    return jsonify({
        'message': 'Carte RFID associée avec succès',
        'user': {
            'id': user.id,
            'username': user.username,
            'rfid_card': user.rfid_card
        }
    }), 200








# Lancement de l'application
if __name__ == '__main__':
     with app.app_context():
        generate_all_alerts()  # Première exécution immédiate
        start_scheduler()      # Démarrage du scheduler toutes les 7 secondes
        # Initialiser le lecteur RFID
        if init_arduino_serial():
            rfid_thread = threading.Thread(target=read_rfid_data, daemon=True)
            rfid_thread.start()
            print("✅ Lecteur RFID démarré")
        app.run(debug=True)


