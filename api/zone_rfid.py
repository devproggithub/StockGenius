# Add these imports to your app.py file
from flask import Blueprint, jsonify, request
import json
from datetime import timedelta

zonerfid_bp = Blueprint('zone_rfid', __name__)



# Add these routes to your app.py

@zonerfid_bp.route('/api/zone-rfid/start', methods=['POST'])
def start_zone_rfid_reader():
    """Start the Zone RFID reader"""
    global zone_rfid_handler
    
    data = request.get_json() or {}
    port = data.get('port', 'COM5')  # Default to COM5 or use specified port
    
    # Import the handler here to avoid circular imports
    from second_rfid_handler import ZoneRFIDHandler
    
    if zone_rfid_handler is None:
        zone_rfid_handler = ZoneRFIDHandler(port=port)
        
    if zone_rfid_handler.start():
        return jsonify({"message": f"Zone RFID reader started on {port}"}), 200
    else:
        return jsonify({"error": f"Unable to start Zone RFID reader on {port}"}), 500

@zonerfid_bp.route('/api/zone-rfid/stop', methods=['POST'])
def stop_zone_rfid_reader():
    """Stop the Zone RFID reader"""
    global zone_rfid_handler
    
    if zone_rfid_handler:
        zone_rfid_handler.stop()
        return jsonify({"message": "Zone RFID reader stopped successfully"}), 200
    else:
        return jsonify({"message": "Zone RFID reader was not running"}), 200

@zonerfid_bp.route('/api/zone-rfid/data', methods=['POST'])
def receive_zone_rfid_data():
    """Process data from the zone RFID reader"""
    try:
        data = request.json
        
        if not data:
            return jsonify({"error": "Missing JSON data"}), 400
            
        # Extract information
        uid = data.get('uid', '').upper()
        weight = data.get('weight', 0)
        zone_id = data.get('zone_id')
        
        if not uid:
            return jsonify({"error": "Missing RFID UID"}), 400
            
        # Get the last unprocessed sensor data
        last_sensor_data = SensorData.query.filter(
            SensorData.stored == False
        ).order_by(SensorData.saved_at.desc()).first()
        
        if not last_sensor_data:
            return jsonify({
                "status": "warning",
                "message": "No waiting product to verify"
            }), 200
            
        # Try to parse the sensor data value
        try:
            last_data = json.loads(last_sensor_data.value)
            last_uid = last_data.get('uid', '').upper()
            last_weight = last_data.get('weight', 0)
            
            # If we have a zone_id, check product placement
            if zone_id:
                product = Product.query.filter_by(rfid_tag=uid).first()
                
                if product:
                    # Check if this product has inventory in this zone
                    inventory = Inventory.query.filter_by(
                        product_id=product.id,
                        zone_id=zone_id
                    ).first()
                    
                    # Compare UIDs and verify correct placement
                    if uid == last_uid:
                        # Weight tolerance (5% difference allowed)
                        weight_diff_percent = abs(weight - last_weight) / max(last_weight, 1) * 100
                        weight_match = weight_diff_percent <= 5
                        
                        # Update the inventory record
                        if inventory:
                            inventory.quantity += 1
                            db.session.commit()
                        else:
                            # Create new inventory record
                            new_inventory = Inventory(
                                product_id=product.id,
                                zone_id=zone_id,
                                quantity=1
                            )
                            db.session.add(new_inventory)
                            db.session.commit()
                        
                        # Mark the sensor data as stored
                        last_sensor_data.stored = True
                        db.session.commit()
                        
                        return jsonify({
                            "status": "success",
                            "message": "Product correctly placed in zone",
                            "product_id": product.id,
                            "zone_id": zone_id,
                            "weight_verified": weight_match,
                            "weight_diff_percent": round(weight_diff_percent, 2)
                        }), 200
                    else:
                        # RFID doesn't match the last scanned product
                        return jsonify({
                            "status": "error",
                            "message": "Product mismatch! This is not the same product that was scanned at entry.",
                            "entry_uid": last_uid,
                            "zone_uid": uid
                        }), 200
                else:
                    return jsonify({
                        "status": "error", 
                        "message": "Unknown product RFID"
                    }), 200
            else:
                return jsonify({
                    "status": "error",
                    "message": "Missing zone information"
                }), 400
                
        except (json.JSONDecodeError, AttributeError):
            return jsonify({
                "status": "error", 
                "message": "Invalid data format in sensor data",
                "raw_value": last_sensor_data.value
            }), 200
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@zonerfid_bp.route('/zone-rfid/process', methods=['POST'])
def process_zone_rfid():
    """Traiter et affecter un produit détecté par RFID à une zone"""
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "Données manquantes"}), 400
    
    try:
        # Extraire les informations du produit
        rfid_tag = data.get('uid')
        if not rfid_tag:
            return jsonify({"error": "UID RFID manquant"}), 400
        
        # Rechercher le produit par son tag RFID
        product = Product.query.filter_by(rfid_tag=rfid_tag).first()
        if not product:
            return jsonify({"error": f"Aucun produit trouvé avec le tag RFID: {rfid_tag}"}), 404
        
        # Rechercher une zone disponible
        zones = Zone.query.all()
        selected_zone = None
        
        for zone in zones:
            # Vérifier l'espace disponible dans la zone
            inventory_count = Inventory.query.filter_by(zone_id=zone.id).count()
            if inventory_count < 8:  # 8 emplacements par zone
                selected_zone = zone
                break
        
        if not selected_zone:
            return jsonify({"error": "Aucune zone disponible actuellement"}), 400
        
        # Vérifier si le produit est déjà dans cette zone
        existing_inventory = Inventory.query.filter_by(
            product_id=product.id,
            zone_id=selected_zone.id
        ).first()
        
        if existing_inventory:
            # Mettre à jour l'inventaire existant
            existing_inventory.quantity += 1
            existing_inventory.last_update_at = datetime.utcnow()
            db.session.commit()
            
            return jsonify({
                "message": f"Produit {product.designation} ajouté à la zone {selected_zone.name} (quantité: {existing_inventory.quantity})",
                "zone_id": selected_zone.id,
                "product_id": product.id,
                "quantity": existing_inventory.quantity
            }), 200
        else:
            # Créer un nouvel inventaire
            new_inventory = Inventory(
                product_id=product.id,
                zone_id=selected_zone.id,
                quantity=1,
                last_update_at=datetime.utcnow()
            )
            
            db.session.add(new_inventory)
            db.session.commit()
            
            return jsonify({
                "message": f"Produit {product.designation} affecté à la zone {selected_zone.name}",
                "zone_id": selected_zone.id,
                "product_id": product.id,
                "quantity": 1
            }), 201
            
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500