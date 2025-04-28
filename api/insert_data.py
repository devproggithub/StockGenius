#insert_data.py
from app import app, db
from models import User, Product, Category, Zone, Inventory, Customer,Sensor, SensorData, Alert, Order, OrderPrediction
from datetime import datetime, timedelta

# Initialiser l'application et la base de données
with app.app_context():
    # Nettoyer les données existantes (dans l'ordre pour éviter les problèmes de contraintes de clé étrangère)
    db.session.query(SensorData).delete()
    db.session.query(OrderPrediction).delete()
    db.session.query(Order).delete()
    db.session.query(Alert).delete()
    db.session.query(Inventory).delete()
    db.session.query(Sensor).delete()
    db.session.query(Product).delete()
    db.session.query(Category).delete()
    db.session.query(Zone).delete()
    
    # Vérifier qu'il y a au moins un utilisateur
    user = User.query.first()
    if not user:
        print("Aucun utilisateur trouvé! Exécutez create_users.py d'abord.")
        exit(1)
    
    # Créer des catégories
    category1 = Category(name="Électronique", description="Produits électroniques")
    category2 = Category(name="Alimentation", description="Produits alimentaires")
    db.session.add_all([category1, category2])
    db.session.flush()  # Pour obtenir les IDs générés
    
    # Créer des zones
    zone1 = Zone(name="Zone A1", description="Stockage principal")
    zone2 = Zone(name="Zone B2", description="Stockage secondaire")
    db.session.add_all([zone1, zone2])
    db.session.flush()
    
    # Créer des produits
    product1 = Product(
        designation="Smartphone XYZ",
        description="Smartphone haut de gamme",
        category_id=category1.id,
        min_threshold=10,
        max_threshold=100,
        rfid_tag="RFID-001"
    )
    
    product2 = Product(
        designation="Tablette ABC",
        description="Tablette 10 pouces",
        category_id=category1.id,
        min_threshold=5,
        max_threshold=50,
        rfid_tag="RFID-002"
    )
    
    product3 = Product(
        designation="Chocolat Premium",
        description="Tablette de chocolat noir",
        category_id=category2.id,
        min_threshold=20,
        max_threshold=200,
        rfid_tag="RFID-003"
    )
    
    db.session.add_all([product1, product2, product3])
    db.session.flush()
    
    # Créer des capteurs
    sensor1 = Sensor(
        type="RFID",
        zone_id=zone1.id,
        status="online",
        last_reading=datetime.utcnow()
    )
    
    sensor2 = Sensor(
        type="Temperature",
        zone_id=zone2.id,
        status="online",
        last_reading=datetime.utcnow()
    )
    
    db.session.add_all([sensor1, sensor2])
    db.session.flush()
        # Ajouter capteur hors ligne pour test
    sensor3 = Sensor(
        type="RFID",
        zone_id=zone1.id,  # liée à un produit via inventory1
        status="offline",
        last_reading=datetime.utcnow() - timedelta(hours=13)
    )
    
    db.session.add_all([sensor1, sensor2, sensor3])
    db.session.flush()

    
    # Créer des données de capteurs
    sensor_data1 = SensorData(
        sensor_id=sensor1.id,
        value="40",  # Chaîne comme défini dans le modèle
        saved_at=datetime.utcnow()
    )
    
    sensor_data2 = SensorData(
        sensor_id=sensor2.id,
        value="25",
        saved_at=datetime.utcnow()
    )
    
    db.session.add_all([sensor_data1, sensor_data2])
    db.session.flush()
    #inserer customer
    customer1 =Customer(
  name= "nouvel_utilisateur",
  email= "UUU@example.com",
  phone= "061633773",
  address="nhhhc")
    customer2 =Customer(
  name= "nouvel_utilisateur2",
  email= "FFF@example.com",
  phone= "061633773",
  address="Agadir")
    db.session.add_all([customer1, customer2])
    db.session.flush()
    # Créer des ordres pour l'année précédente (décembre 2024 pour tester les fêtes)
    last_year = datetime.utcnow().year - 1
    # 15 ordres pour Smartphone XYZ (déclenchera une alerte)
    for i in range(15):
        order = Order(
            product_id=product1.id,
            quantity=2,
            status="completed",
            user_id=user.id,
            created_at=datetime(last_year, 12, 10),
            delivered_at=datetime(last_year, 12, 12),
            customer_id=customer1.id
        )
        db.session.add(order)
    # 5 ordres pour Tablette ABC (ne déclenchera pas d'alerte)
    for i in range(5):
        order = Order(
            product_id=product2.id,
            quantity=1,
            status="completed",
            user_id=user.id,
            created_at=datetime(last_year, 12, 15),
            delivered_at=datetime(last_year, 12, 17),
            customer_id=customer2.id
        )
        db.session.add(order)
    # 12 ordres pour Chocolat Premium (déclenchera une alerte)
    for i in range(12):
        order = Order(
            product_id=product3.id,
            quantity=3,
            status="completed",
            user_id=user.id,
            created_at=datetime(last_year, 12, 20),
            delivered_at=datetime(last_year, 12, 22),
            customer_id=customer2.id

        )
        db.session.add(order)
    
    # Créer des ordres
    order1 = Order(
        product_id=product1.id,
        quantity=5,
        status="pending",  # Statut requis
        user_id=user.id,   # ID utilisateur requis
        created_at=datetime.utcnow() - timedelta(days=5),
        customer_id=customer1.id

    )
    
    order2 = Order(
        product_id=product2.id,
        quantity=3,
        status="completed",
        user_id=user.id,
        created_at=datetime.utcnow() - timedelta(days=10),
        delivered_at=datetime.utcnow() - timedelta(days=8),
        customer_id=customer2.id

    )
    
    db.session.add_all([order1, order2])
    db.session.flush()
    
   
    
    # Créer des inventaires
    inventory1 = Inventory(
        product_id=product1.id,
        zone_id=zone1.id,
        quantity=45,
        last_update_at=datetime.utcnow()
    )
    
    inventory2 = Inventory(
        product_id=product2.id,
        zone_id=zone2.id,
        quantity=25,
        last_update_at=datetime.utcnow()
    )
    
    inventory3 = Inventory(
        product_id=product3.id,
        zone_id=zone1.id,
        quantity=150,
        last_update_at=datetime.utcnow()
    )
    
    db.session.add_all([inventory1, inventory2, inventory3])
    
    # Créer une prédiction de commande
    prediction = OrderPrediction(
        product_id=product1.id,
        predicted_quantity=15,
        prediction_period="weekly",
        start_prediction=datetime.utcnow(),
        finish_prediction=datetime.utcnow() + timedelta(days=7)
    )
    
    db.session.add(prediction)
    
    # Valider toutes les modifications
    db.session.commit()

print("Données insérées avec succès.")