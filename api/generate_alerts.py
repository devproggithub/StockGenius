# api/generate_alerts.py
from datetime import datetime, timedelta
from models import db, Inventory, Sensor, SensorData, Product, Alert, Order,User,Zone
from sqlalchemy import func
from flask import Flask, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt, verify_jwt_in_request
from functools import wraps
import logging
from sqlalchemy.exc import IntegrityError


# Config log
logging.basicConfig(level=logging.INFO)
# --- Décorateur rôle ---
def role_required(required_role):
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            if claims.get("role") != required_role:
                return jsonify(msg="Accès refusé: rôle requis = {}".format(required_role)), 403
            return fn(*args, **kwargs)
        return decorator
    return wrapper
# Fonction pour créer des alertes dans la base de données
def create_alert(product_id, alert_type, status="non traité", user_id=None, zone_id=None):
    
    """
    Cette fonction crée une nouvelle alerte dans la base de données.
    - product_id : ID du produit concerné par l'alerte.
    - alert_type : Type de l'alerte.
    - status : Statut de l'alerte (par défaut "non traité").
    - user_id : (optionnel) ID de l'utilisateur associé à l'alerte.
    """
   # Récupérer un utilisateur spécifique basé sur la zone ou le rôle
    if user_id is None:
        if zone_id:
            # Rechercher un utilisateur responsable de la zone
            responsible_user = User.query.join(User.zones).filter(
                Zone.id == zone_id,
                User.role.in_(["responsable_zone", "admin"])  # Filtrer par rôle
            ).first()
            user_id = responsible_user.id if responsible_user else None
        else:
            # Sinon, utiliser un administrateur par défaut
            admin_user = User.query.filter_by(role='admin').first()
            user_id = admin_user.id if admin_user else None
   # Vérifier si une alerte identique existe déjà dans les dernières 24 heures
    existing_alert = Alert.query.filter(
        Alert.product_id == product_id,
        Alert.type == alert_type,
        Alert.status != "résolu" # Ne cherche que les alertes actives
        
    ).first()
    if not existing_alert:
        # Créer une nouvelle alerte
        alert = Alert(
            product_id=product_id,
            type=alert_type,
            status=status,
            created_at=datetime.utcnow(),
            user_id=user_id
        )
        try:
            db.session.add(alert)
            db.session.commit()
            logging.info(f"✅ Alerte générée : {alert_type} (Produit ID: {product_id})")
            return alert
        except IntegrityError:
            db.session.rollback()
            logging.warning(f"⚠️ Échec de création de l'alerte : Doublon détecté pour {alert_type} (Produit ID: {product_id})")
            return None
    else:
        logging.warning(f"⚠️ Alerte déjà existante : {alert_type} (Produit ID: {product_id})")
        return None
# Fonction pour générer des alertes sur les stocks
# --- Alerte sur stock ---
def generate_stock_alerts():
    """
    Cette fonction génère des alertes liées aux écarts de stocks, comme les différences entre le stock théorique et mesuré.
    """
    inventories = Inventory.query.all()  # Récupérer tous les inventaires
    for inventory in inventories:
        product = inventory.product  # Récupérer le produit associé à l'inventaire
        theoretical_stock = inventory.quantity  # Récupérer le stock théorique

        # Récupérer les dernières données de capteur dans la même zone
        last_sensor_data = SensorData.query.join(Sensor).filter(
            Sensor.zone_id == inventory.zone_id
        ).order_by(SensorData.saved_at.desc()).first()

        # Si des données de capteur sont disponibles
        if last_sensor_data:
            try:
                measured_stock = int(last_sensor_data.value)  # Convertir la valeur mesurée en stock
                # Si l'écart entre le stock théorique et mesuré est supérieur à 5, créer une alerte
                if abs(theoretical_stock - measured_stock) > 5:
                    create_alert(product.id, f"Écart de stock : Théorique={theoretical_stock}, Mesuré={measured_stock}")
            except ValueError:
                pass  # Si une erreur se produit lors de la conversion, ignorer

        # Si le stock théorique est inférieur au seuil minimum du produit, créer une alerte pour rupture de stock
        if theoretical_stock < product.min_threshold:
            create_alert(product.id, "Rupture de stock prévue")
        # Si le stock théorique est supérieur au seuil maximum du produit, créer une alerte pour surplus de stock
        elif theoretical_stock > product.max_threshold:
            create_alert(product.id, "Surplus de stock prévu")


# --- Alerte saisonnière et périodes promotionnelles ---
def generate_seasonal_alerts():
    """
    Cette fonction génère des alertes liées aux tendances saisonnières et périodes promotionnelles.
    Elle analyse les données historiques de ventes pour détecter des patterns saisonniers.
    """
    # Obtenir le mois actuel
    current_month = datetime.utcnow().month
    
    # Définir les mois des "saisons" commerciales importantes
    seasonal_periods = {
        12: "Fêtes de fin d'année",
        1: "Soldes d'hiver",
        7: "Soldes d'été",
        9: "Rentrée scolaire",
        # Ajouter d'autres périodes si nécessaire
    }
    
    # Vérifier si nous sommes dans une période saisonnière
    if current_month in seasonal_periods:
        season_name = seasonal_periods[current_month]
        
        # Obtenir tous les produits
        products = Product.query.all()
        
        # Pour chaque produit, vérifier les commandes de l'année précédente pendant cette période
        for product in products:
            # Calculer les dates de l'année précédente pour ce mois
            last_year = datetime.utcnow().year - 1
            start_date = datetime(last_year, current_month, 1)
            
            # Calcul du dernier jour du mois
            if current_month == 12:
                end_date = datetime(last_year, 12, 31)
            else:
                end_date = datetime(last_year, current_month + 1, 1) - timedelta(days=1)
            
            # Compter les commandes pour ce produit l'année dernière pendant cette période
            order_count = Order.query.filter(
                Order.product_id == product.id,
                Order.created_at.between(start_date, end_date)
            ).count()
            
            # Si beaucoup de commandes ont été passées l'année dernière, générer une alerte
            if order_count > 10:  # Seuil arbitraire, à ajuster selon les besoins
                create_alert(
                    product.id, 
                    f"Période saisonnière : {season_name} - Hausse probable de la demande basée sur l'historique",
                    "à planifier"
                )
                logging.info(f"⚠️ Alerte saisonnière pour {product.designation} - Période: {season_name}")


# Fonction pour générer des alertes sur les capteurs hors ligne
def generate_sensor_alerts():
    """
    Cette fonction génère des alertes lorsque des capteurs ne transmettent plus de données depuis une certaine période.
    """
    twelve_hours_ago = datetime.utcnow() - timedelta(hours=12)  # Calculer l'heure il y a 12 heures
    sensors = Sensor.query.all()  # Récupérer tous les capteurs
    for sensor in sensors:
        # Si aucun relevé n'a été fait ou si le dernier relevé est plus vieux que 12 heures
        if not sensor.last_reading or sensor.last_reading < twelve_hours_ago:
            # Récupérer les produits associés à la zone du capteur
            inventories = Inventory.query.filter_by(zone_id=sensor.zone_id).all()
            
            if inventories:
                # Créer une alerte pour chaque produit dans la zone
                for inventory in inventories:
                    create_alert(
                        product_id=inventory.product_id,  
                        alert_type=f"Capteur {sensor.id} hors ligne (Zone {sensor.zone.name})",
                        status="urgent"
                    )
                    logging.info(f"❌ Capteur {sensor.id} hors ligne dans la zone {sensor.zone.name}")
            else:
                # Si aucun produit n'est associé à cette zone, créer une alerte générique
                admin_user = User.query.filter_by(role='admin').first()
                if admin_user:
                    create_alert(
                        product_id=None,  
                        alert_type=f"Capteur {sensor.id} hors ligne (Zone {sensor.zone.name})",
                        status="urgent",
                        user_id=admin_user.id
                    )
                    logging.info(f"❌ Capteur {sensor.id} hors ligne dans la zone {sensor.zone.name}")



# Fonction pour générer des alertes pour les commandes importantes
def generate_order_alerts():
    """
    Génère des alertes pour les commandes importantes nécessitant une validation manuelle.
    """
    big_orders = Order.query.filter(
        Order.quantity > 300,
        Order.status == "en attente"
    ).all()
    
    for order in big_orders:
        # Vérifier si une alerte existe déjà pour cette commande spécifique
        existing_alert = Alert.query.filter(
            Alert.product_id == order.product_id,
            Alert.type.like(f"Validation requise pour commande #{order.id}%"),
            Alert.created_at >= datetime.utcnow() - timedelta(hours=24)
        ).first()
        
        if not existing_alert:
            alert_message = f"Validation requise pour commande #{order.id} de {order.quantity} unités"
            
            create_alert(
                product_id=order.product_id, 
                alert_type=alert_message,
                status="prioritaire",
                user_id=order.user_id
            )
            
            logging.info(f"⚠️ Vérification effectuée pour commande #{order.id} - Quantité: {order.quantity}")
        else:
            logging.info(f"⚠️ Alerte déjà existante pour la commande #{order.id}")


# Fonction pour générer des alertes sur les tendances de la demande
def generate_demand_trend_alerts():
    """
    Cette fonction génère des alertes lorsque la demande pour un produit augmente de manière significative.
    """
    current_month = datetime.utcnow().month  # Récupérer le mois actuel
    previous_month = current_month - 1 if current_month > 1 else 12  # Calculer le mois précédent
    current_year = datetime.utcnow().year
    previous_year = current_year if previous_month != 12 else current_year - 1  # Ajuster l'année si nécessaire
    
    for product in Product.query.all():  # Récupérer tous les produits
        # Calculer la demande actuelle pour ce produit
        current_demand = db.session.query(func.sum(Order.quantity)).filter(
            func.extract('month', Order.created_at) == current_month,
            func.extract('year', Order.created_at) == current_year,
            Order.product_id == product.id
        ).scalar() or 0

        # Calculer la demande pour le mois précédent
        previous_demand = db.session.query(func.sum(Order.quantity)).filter(
            func.extract('month', Order.created_at) == previous_month,
            func.extract('year', Order.created_at) == previous_year,
            Order.product_id == product.id
        ).scalar() or 1  # Utiliser 1 pour éviter division par zéro

        # Si la demande actuelle a augmenté de plus de 40% par rapport au mois précédent, générer une alerte
        if current_demand > 0 and previous_demand > 0 and (current_demand / previous_demand) > 1.4:
            increase_percentage = int((current_demand - previous_demand) / previous_demand * 100)
            create_alert(
                product.id, 
                f"Demande en hausse : +{increase_percentage}% ce mois-ci",
                "à planifier"
            )
            logging.info(f"📈 Hausse de la demande détectée pour {product.designation}: +{increase_percentage}%")



def generate_storage_optimization_alerts():
    """
    Génère des alertes pour optimiser l'utilisation de l'espace de stockage.
    Retourne le nombre d'alertes créées.
    """
    try:
        # Récupérer les totaux par zone en une seule requête
        zone_totals = db.session.query(
            Inventory.zone_id,
            Zone.name.label('zone_name'),
            func.sum(Inventory.quantity).label('total_quantity')
        ).join(Zone, Zone.id == Inventory.zone_id
        ).group_by(Inventory.zone_id, Zone.name
        ).all()

        alerts_created = 0
        current_time = datetime.utcnow()
        time_threshold = current_time - timedelta(hours=24)

        for zone_id, zone_name, total in zone_totals:
            # Déterminer le type d'alerte
            alert_type = None
            if total < 20:
                alert_type = f"Zone {zone_name} sous-utilisée (Quantité: {total})"
            elif total > 500:
                alert_type = f"Zone {zone_name} surchargée (Quantité: {total})"

            if not alert_type:
                continue

            # Vérifier l'existence d'une alerte similaire
            if Alert.query.filter(
                Alert.type == alert_type,
                Alert.status == "optimisation",
                Alert.created_at >= time_threshold
            ).first():
                logging.info(f"📉 Alerte existante pour {alert_type}. Ignorée.")
                continue

            # Récupérer un produit associé à la zone
            inventory = Inventory.query.filter_by(zone_id=zone_id).first()
            if not inventory:
                logging.warning(f"⚠️ Aucun produit trouvé pour la zone {zone_name}")
                continue

            # Créer l'alerte
            create_alert(
                inventory.product_id,
                alert_type,
                "optimisation"
            )
            alerts_created += 1
            logging.info(f"📈 Alerte créée : {alert_type} pour la zone {zone_name}")

        return alerts_created

    except Exception as e:
        logging.error(f"❌ Erreur lors de la génération des alertes : {str(e)}")
        raise
                    
# Fonction pour générer toutes les alertes en une fois
def generate_all_alerts():
    """
    Cette fonction génère toutes les alertes possibles dans le système.
    """
    generate_stock_alerts()
    generate_seasonal_alerts()
    generate_sensor_alerts()
    generate_order_alerts()
    generate_demand_trend_alerts()
    generate_storage_optimization_alerts()
    db.session.commit()  # Enregistrer toutes les alertes dans la base de données
# --- Route Flask ---
app = Flask(__name__) 
@app.route("/generate_alerts", methods=["POST"])
@jwt_required()
@role_required("admin")  # Si tu as un décorateur de rôles
def trigger_alerts():
    generate_all_alerts()
    return jsonify({"message": "Toutes les alertes ont été générées."}), 200

