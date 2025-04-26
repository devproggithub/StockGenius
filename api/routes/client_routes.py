from flask import Blueprint, request, jsonify
from app import db
from models.client import Client

client_bp = Blueprint('client_bp', __name__)

# Créer un client
@client_bp.route('/api/clients', methods=['POST'])
def create_client():
    data = request.get_json()
    new_client = Client(
        name=data['name'],
        email=data['email'],
        phone=data.get('phone'),
        address=data.get('address')
    )
    db.session.add(new_client)
    db.session.commit()
    return jsonify({"message": "Client créé avec succès", "client": new_client.to_dict()}), 201

# Lire tous les clients
@client_bp.route('/api/clients', methods=['GET'])
def get_clients():
    clients = Client.query.all()
    return jsonify([client.to_dict() for client in clients]), 200

# Lire un client
@client_bp.route('/api/clients/<int:client_id>', methods=['GET'])
def get_client(client_id):
    client = Client.query.get_or_404(client_id)
    return jsonify(client.to_dict()), 200

# Modifier un client
@client_bp.route('/api/clients/<int:client_id>', methods=['PUT'])
def update_client(client_id):
    client = Client.query.get_or_404(client_id)
    data = request.get_json()
    client.name = data.get('name', client.name)
    client.email = data.get('email', client.email)
    client.phone = data.get('phone', client.phone)
    client.address = data.get('address', client.address)
    db.session.commit()
    return jsonify({"message": "Client mis à jour", "client": client.to_dict()}), 200

# Supprimer un client
@client_bp.route('/api/clients/<int:client_id>', methods=['DELETE'])
def delete_client(client_id):
    client = Client.query.get_or_404(client_id)
    db.session.delete(client)
    db.session.commit()
    return jsonify({"message": "Client supprimé avec succès"}), 200
