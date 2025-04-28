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

# Initialisation de l'application
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:4200"}})  # Remplacez par l'URL de votre frontend


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
   

# Lancement de l'application
if __name__ == '__main__':
     with app.app_context():
        generate_all_alerts()  # Première exécution immédiate
        start_scheduler()      # Démarrage du scheduler toutes les 7 secondes
        app.run(debug=True)