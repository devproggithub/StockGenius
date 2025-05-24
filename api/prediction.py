# prediction.py
from flask import Blueprint, jsonify, request
from sqlalchemy import func
from datetime import datetime, timedelta
from models import db, Product, Inventory, Order, Alert

# Créer un blueprint pour les routes de prédiction
prediction_bp = Blueprint('prediction', __name__, url_prefix='/api/prediction')


# Fonctions utilitaires
def calculate_days_to_stockout(product_id, current_stock):
    """Calcule le nombre estimé de jours avant rupture de stock"""
    thirty_days_ago = datetime.now() - timedelta(days=30)
    
    total_ordered = db.session.query(func.sum(Order.quantity))\
        .filter(
            Order.product_id == product_id,
            Order.order_date >= thirty_days_ago
        ).scalar() or 0
    
    daily_consumption = total_ordered / 30 if total_ordered > 0 else 1
    days_left = int(current_stock / daily_consumption) if daily_consumption > 0 else 30
    
    return min(days_left, 30)

def calculate_growth_percentage(product_id):
    """Calcule le pourcentage de croissance des ventes pour un produit"""
    current_period_end = datetime.now()
    current_period_start = current_period_end - timedelta(days=30)
    previous_period_end = current_period_start
    previous_period_start = previous_period_end - timedelta(days=30)
    
    current_sales = db.session.query(func.sum(Order.quantity))\
        .filter(
            Order.product_id == product_id,
            Order.order_date >= current_period_start,
            Order.order_date < current_period_end
        ).scalar() or 0
    
    previous_sales = db.session.query(func.sum(Order.quantity))\
        .filter(
            Order.product_id == product_id,
            Order.order_date >= previous_period_start,
            Order.order_date < previous_period_end
        ).scalar() or 0
    
    if previous_sales > 0:
        growth = ((current_sales - previous_sales) / previous_sales) * 100
    else:
        growth = 100 if current_sales > 0 else 0
    
    return round(growth, 2)

def get_product_recommendation(product_id, current_stock, growth_percentage):
    """Génère une recommandation pour un produit en fonction de ses métriques"""
    product = Product.query.get(product_id)
    
    if current_stock < product.min_threshold:
        return "Réapprovisionnement urgent recommandé"
    
    if growth_percentage > 20 and current_stock < product.max_threshold * 0.7:
        return "Augmenter le stock pour répondre à la demande croissante"
    
    if growth_percentage < -20 and current_stock > product.min_threshold * 1.5:
        return "Réduire les achats, demande en baisse"
    
    return "Stock à un niveau optimal"

# Routes API
@prediction_bp.route('/indicators', methods=['GET'])
def get_prediction_indicators():
    """Récupère toutes les données pour les indicateurs clés de la page Prediction"""
    return jsonify({
        "products_in_alert": get_products_in_alert(),
        "products_at_risk": get_products_at_risk(),
        "potential_products": get_potential_products(),
        "next_event": get_next_event()
    })

def get_products_in_alert():
    """Récupère les produits en alerte (stock < seuil minimal)"""
    alert_products = db.session.query(Product, Inventory)\
        .join(Inventory, Product.id == Inventory.product_id)\
        .filter(Inventory.current_stock < Product.min_threshold)\
        .all()
    
    count = len(alert_products)
    progress_percentage = min(100, int(count / 30 * 100))
    
    products_list = []
    for product, inventory in alert_products[:5]:
        products_list.append({
            "id": product.id,
            "name": product.name,
            "current_stock": inventory.current_stock,
            "min_threshold": product.min_threshold
        })
    
    product_names = [p.name for p, _ in alert_products[:3]]
    displayed_names = ", ".join(product_names) + (" ..." if count > 3 else "")
    
    return {
        "count": count,
        "progress_percentage": progress_percentage,
        "products": products_list,
        "displayed_names": displayed_names
    }

def get_products_at_risk():
    """Récupère les produits à risque de rupture dans les 30 prochains jours"""
    at_risk_products = db.session.query(Product, Inventory)\
        .join(Inventory, Product.id == Inventory.product_id)\
        .filter(Inventory.current_stock < Product.min_threshold * 1.2)\
        .all()
    
    count = len(at_risk_products)
    
    products_list = []
    for product, inventory in at_risk_products[:5]:
        products_list.append({
            "id": product.id,
            "name": product.name,
            "current_stock": inventory.current_stock,
            "estimated_days_left": calculate_days_to_stockout(product.id, inventory.current_stock)
        })
    
    product_names = [p.name for p, _ in at_risk_products[:3]]
    displayed_names = ", ".join(product_names) + (" ..." if count > 3 else "")
    
    return {
        "count": count,
        "products": products_list,
        "displayed_names": displayed_names
    }

def get_potential_products():
    """Récupère les produits les plus demandés/potentiels"""
    ninety_days_ago = datetime.now() - timedelta(days=90)
    
    top_products = db.session.query(
        Product, 
        func.count(Order.id).label('order_count')
    ).join(
        Order, 
        Product.id == Order.product_id
    ).filter(
        Order.order_date >= ninety_days_ago
    ).group_by(
        Product.id
    ).order_by(
        func.count(Order.id).desc()
    ).limit(10).all()
    
    count = len(top_products)
    
    products_list = []
    for product, order_count in top_products[:5]:
        products_list.append({
            "id": product.id,
            "name": product.name,
            "order_count": order_count,
            "growth_percentage": calculate_growth_percentage(product.id)
        })
    
    product_names = [p.name for p, _ in top_products[:3]]
    displayed_names = ", ".join(product_names) + (" ..." if count > 3 else "")
    
    return {
        "count": count,
        "products": products_list,
        "displayed_names": displayed_names
    }

def get_next_event():
    """Récupère les informations sur le prochain événement"""
    next_event = Event.query.filter(
        Event.start_date > datetime.now()
    ).order_by(
        Event.start_date
    ).first()
    
    if next_event:
        if next_event.start_date.month == next_event.end_date.month and next_event.start_date.year == next_event.end_date.year:
            date_display = next_event.start_date.strftime("%B %Y")
        else:
            date_display = f"{next_event.start_date.strftime('%B')}-{next_event.end_date.strftime('%B %Y')}"
        
        return {
            "title": next_event.title,
            "locations": next_event.locations,
            "date": date_display,
            "popular_products": next_event.popular_products
        }
    else:
        return {
            "title": "Aucun événement planifié",
            "locations": "",
            "date": "",
            "popular_products": ""
        }

@prediction_bp.route('/products', methods=['GET'])
def get_prediction_products():
    """Récupère la liste des produits avec des données de prédiction"""
    category_id = request.args.get('category_id', type=int)
    search_term = request.args.get('search', '')
    sort_by = request.args.get('sort_by', 'name')
    
    query = db.session.query(Product, Inventory).\
        join(Inventory, Product.id == Inventory.product_id)
    
    if category_id:
        query = query.filter(Product.category_id == category_id)
    
    if search_term:
        query = query.filter(Product.name.ilike(f'%{search_term}%'))
    
    if sort_by == 'stock':
        query = query.order_by(Inventory.current_stock)
    elif sort_by == 'name':
        query = query.order_by(Product.name)
    elif sort_by == 'risk':
        query = query.order_by(Inventory.current_stock / Product.min_threshold)
    
    products = query.all()
    
    result = []
    for product, inventory in products:
        days_to_stockout = calculate_days_to_stockout(product.id, inventory.current_stock)
        growth_percentage = calculate_growth_percentage(product.id)
        
        result.append({
            "id": product.id,
            "name": product.name,
            "category_id": product.category_id,
            "current_stock": inventory.current_stock,
            "min_threshold": product.min_threshold,
            "max_threshold": product.max_threshold,
            "days_to_stockout": days_to_stockout,
            "status": "alert" if inventory.current_stock < product.min_threshold else 
                     "warning" if days_to_stockout < 30 else "normal",
            "growth_percentage": growth_percentage,
            "recommendation": get_product_recommendation(product.id, inventory.current_stock, growth_percentage)
        })
    
    return jsonify(result)

# Ajoutez d'autres routes selon vos besoins
@prediction_bp.route('/analyze-product', methods=['POST'])
def analyze_product():
    """Analyse un produit spécifique avec l'API Claude"""
    data = request.json
    product_name = data.get('productName', '')
    
    # Implémentez ici l'analyse du produit (comme dans votre code précédent)
    # Ou retournez une réponse factice pour les tests
    return jsonify({
        "isProfitable": True,
        "confidenceScore": 0.85,
        "reason": f"Le produit '{product_name}' montre un potentiel de rentabilité élevé basé sur les tendances actuelles du marché marocain."
    })