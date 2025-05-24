from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from models import db, Zone, Inventory, Product, SensorData, Alert
import json

shelves_bp = Blueprint('shelves', __name__)

@shelves_bp.route('/process-zone-scan', methods=['POST'])
@jwt_required()
def process_zone_scan():
    """
    Traite les données d'un produit scanné au niveau d'une zone et met à jour automatiquement
    le statut 'stored' si un scan récent du même produit avec le même poids existe
    """
    try:
        data = request.get_json()
        if not data or 'rfid_tag' not in data:
            return jsonify({
                'success': False,
                'message': 'Tag RFID requis dans les données'
            }), 400
            
        rfid_tag = data['rfid_tag']
        weight = data.get('weight', None)
        zone_id = data.get('zone_id', None)
        
        # Trouver le produit correspondant
        product = Product.query.filter_by(rfid_tag=rfid_tag).first()
        if not product:
            return jsonify({
                'success': False,
                'message': f'Aucun produit trouvé avec le tag RFID: {rfid_tag}'
            }), 404
        
        # Vérifier s'il existe un scan récent à la porte (moins de 30 minutes)
        recent_time = datetime.utcnow() - timedelta(minutes=30)
        recent_door_scan = SensorData.query.filter(
            SensorData.value.like(f"%{rfid_tag}%"), 
            SensorData.stored == False,
            SensorData.saved_at >= recent_time
        ).order_by(SensorData.saved_at.desc()).first()
        
        # Si un scan récent existe
        if recent_door_scan:
            door_weight = None
            try:
                # Extraire le poids du scan à la porte
                door_data = json.loads(recent_door_scan.value) if isinstance(recent_door_scan.value, str) else recent_door_scan.value
                
                if 'weight' in door_data:
                    door_weight = door_data['weight']
                elif isinstance(door_data.get('data'), dict) and 'weight' in door_data['data']:
                    door_weight = door_data['data']['weight']
            except:
                pass
            
            # Compare weights (if available)
            print(f"Comparaison: Poids porte={door_weight}, Poids zone={weight}")
            
            # Si les poids sont similaires (différence < 50g) ou si les deux sont None
            if (door_weight is None and weight is None) or \
               (door_weight is not None and weight is not None and abs(float(door_weight) - float(weight)) < 0.05):
                # Mettre à jour le scan comme stocké
                recent_door_scan.stored = True
                recent_door_scan.product_id = product.id
                db.session.commit()
                
                # Affecter le produit à la zone spécifiée ou trouver une zone disponible
                if not zone_id:
                    # Trouver une zone disponible
                    zones = Zone.query.all()
                    for zone in zones:
                        inventory_count = Inventory.query.filter_by(zone_id=zone.id).count()
                        if inventory_count < 8:  # 8 emplacements max par zone
                            zone_id = zone.id
                            break
                            
                    if not zone_id:
                        return jsonify({
                            'success': False,
                            'message': 'Aucune zone disponible pour ce produit'
                        }), 400
                
                # Vérifier si la zone existe
                zone = Zone.query.get(zone_id)
                if not zone:
                    return jsonify({
                        'success': False,
                        'message': f'Zone avec ID {zone_id} non trouvée'
                    }), 404
                
                # Créer ou mettre à jour l'inventaire
                existing_inventory = Inventory.query.filter_by(
                    product_id=product.id,
                    zone_id=zone_id
                ).first()
                
                if existing_inventory:
                    existing_inventory.quantity += 1
                    existing_inventory.last_update_at = datetime.utcnow()
                else:
                    new_inventory = Inventory(
                        product_id=product.id,
                        zone_id=zone_id,
                        quantity=1,
                        last_update_at=datetime.utcnow()
                    )
                    db.session.add(new_inventory)
                
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'message': f'Produit {product.designation} assigné à la zone {zone.name} et marqué comme stocké',
                    'stored': True,
                    'zone': {
                        'id': zone.id,
                        'name': zone.name
                    },
                    'product': {
                        'id': product.id,
                        'designation': product.designation,
                        'weight': weight
                    }
                }), 200
            else:
                # Les poids sont différents - générer une alerte
                new_alert = Alert(
                    product_id=product.id,
                    type="écart_poids_porte_zone",
                    status="non_résolu",
                    created_at=datetime.utcnow(),
                    message=f"Écart de poids entre porte ({door_weight} kg) et zone ({weight} kg)"
                )
                db.session.add(new_alert)
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'is_alert': True,
                    'message': f'Alerte générée: écart de poids pour le produit {product.designation}',
                    'alert': {
                        'id': new_alert.id,
                        'type': new_alert.type,
                        'status': new_alert.status,
                        'created_at': new_alert.created_at.isoformat(),
                        'message': new_alert.message,
                        'product': {
                            'id': product.id,
                            'designation': product.designation
                        },
                        'weight_difference': {
                            'door': door_weight,
                            'zone': weight
                        }
                    }
                }), 200
        
        else:
            # Aucun scan récent à la porte - enregistrer le scan à la zone comme nouveau
            new_sensor_data = SensorData(
                value=json.dumps({
                    'uid': rfid_tag,
                    'weight': weight,
                    'zone_id': zone_id
                }),
                stored=True,  # Marquer directement comme stocké
                product_id=product.id,
                saved_at=datetime.utcnow()
            )
            db.session.add(new_sensor_data)
            
            # Ajouter à l'inventaire de la zone spécifiée
            if zone_id:
                zone = Zone.query.get(zone_id)
                
                if not zone:
                    return jsonify({
                        'success': False,
                        'message': f'Zone avec ID {zone_id} non trouvée'
                    }), 404
                    
                # Créer ou mettre à jour l'inventaire
                existing_inventory = Inventory.query.filter_by(
                    product_id=product.id,
                    zone_id=zone_id
                ).first()
                
                if existing_inventory:
                    existing_inventory.quantity += 1
                    existing_inventory.last_update_at = datetime.utcnow()
                else:
                    new_inventory = Inventory(
                        product_id=product.id,
                        zone_id=zone_id,
                        quantity=1,
                        last_update_at=datetime.utcnow()
                    )
                    db.session.add(new_inventory)
                
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'message': f'Nouveau scan de zone enregistré pour le produit {product.designation}',
                    'stored': True,
                    'zone': {
                        'id': zone.id,
                        'name': zone.name
                    },
                    'product': {
                        'id': product.id,
                        'designation': product.designation
                    }
                }), 200
            else:
                # Pas de zone spécifiée - trouver une zone disponible
                zones = Zone.query.all()
                selected_zone = None
                
                for zone in zones:
                    inventory_count = Inventory.query.filter_by(zone_id=zone.id).count()
                    if inventory_count < 8:  # 8 emplacements max par zone
                        selected_zone = zone
                        break
                
                if not selected_zone:
                    return jsonify({
                        'success': False,
                        'message': 'Aucune zone disponible pour ce produit'
                    }), 400
                
                # Créer ou mettre à jour l'inventaire
                existing_inventory = Inventory.query.filter_by(
                    product_id=product.id,
                    zone_id=selected_zone.id
                ).first()
                
                if existing_inventory:
                    existing_inventory.quantity += 1
                    existing_inventory.last_update_at = datetime.utcnow()
                else:
                    new_inventory = Inventory(
                        product_id=product.id,
                        zone_id=selected_zone.id,
                        quantity=1,
                        last_update_at=datetime.utcnow()
                    )
                    db.session.add(new_inventory)
                
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'message': f'Nouveau scan de zone enregistré et produit {product.designation} assigné à la zone {selected_zone.name}',
                    'stored': True,
                    'zone': {
                        'id': selected_zone.id,
                        'name': selected_zone.name
                    },
                    'product': {
                        'id': product.id,
                        'designation': product.designation
                    }
                }), 200
                
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# Route pour obtenir les alertes d'écart de poids entre porte et zone
@shelves_bp.route('/door-zone-weight-alerts', methods=['GET'])
@jwt_required()
def get_door_zone_weight_alerts():
    """
    Renvoie les alertes d'écart de poids entre la porte et la zone
    """
    try:
        # Récupérer les alertes spécifiques
        alerts = Alert.query.filter_by(
            type="écart_poids_porte_zone",
            status="non_résolu"
        ).order_by(Alert.created_at.desc()).all()
        
        result = []
        for alert in alerts:
            # Récupérer les infos du produit
            product = Product.query.get(alert.product_id)
            product_info = None
            if product:
                product_info = {
                    'id': product.id,
                    'designation': product.designation,
                    'category': product.category.name if product.category else None,
                    'rfid_tag': product.rfid_tag
                }
            
            alert_data = {
                'id': alert.id,
                'type': alert.type,
                'status': alert.status,
                'created_at': alert.created_at.isoformat() if alert.created_at else None,
                'message': alert.message,
                'product': product_info
            }
            result.append(alert_data)
        
        return jsonify(result), 200
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# Conservez vos autres routes du blueprint shelves...