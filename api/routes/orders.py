from flask import Blueprint, request, jsonify
from yourapp import db # type: ignore
from yourapp.models import Order, User, Product # type: ignore
from flask_jwt_extended import jwt_required

orders_bp = Blueprint('orders', __name__, url_prefix='/api/orders')

# Créer une commande
@orders_bp.route('/', methods=['POST'])
@jwt_required()
def create_order():
    data = request.get_json()
    new_order = Order(
        user_id=data['user_id'],
        product_id=data['product_id'],
        quantity=data['quantity'],
        status=data.get('status', 'pending')
    )
    db.session.add(new_order)
    db.session.commit()
    return jsonify({'message': 'Commande créée avec succès!'}), 201

# Obtenir toutes les commandes
@orders_bp.route('/', methods=['GET'])
@jwt_required()
def get_orders():
    orders = Order.query.all()
    result = []
    for order in orders:
        order_data = {
            'id': order.id,
            'user_id': order.user_id,
            'product_id': order.product_id,
            'quantity': order.quantity,
            'status': order.status,
            'created_at': order.created_at
        }
        result.append(order_data)
    return jsonify(result)

# Modifier une commande
@orders_bp.route('/<int:order_id>', methods=['PUT'])
@jwt_required()
def update_order(order_id):
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'error': 'Commande non trouvée'}), 404

    data = request.get_json()
    order.quantity = data.get('quantity', order.quantity)
    order.status = data.get('status', order.status)
    
    db.session.commit()
    return jsonify({'message': 'Commande mise à jour avec succès'}), 200

# Supprimer une commande
@orders_bp.route('/<int:order_id>', methods=['DELETE'])
@jwt_required()
def delete_order(order_id):
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'error': 'Commande non trouvée'}), 404

    db.session.delete(order)
    db.session.commit()
    return jsonify({'message': 'Commande supprimée avec succès'}), 200
