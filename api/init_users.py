# create_users.py
from app import app, db
from models import User
from werkzeug.security import generate_password_hash

def create_initial_users():
    with app.app_context():
        # Vérifier si des utilisateurs existent déjà
        if User.query.count() > 0:
            print("Des utilisateurs existent déjà dans la base de données.")
            return
        
        # Créer un utilisateur standard
        user = User(
            username="yassine",
            email="yassineGI@supmti.com",
            role="user",
            rfid_card="USER001YS"
        )
        user.password = "admin123"  # Le setter s'occupera du hashage
        
        # Créer un utilisateur admin
        admin = User(
            username="rachid",
            email="rachidGI@supmti.com",
            role="admin",
            rfid_card="ADMIN001RC"
        )
        admin.password = "user123"
        
        # Ajouter les utilisateurs à la base de données
        db.session.add(admin)
        db.session.add(user)
        db.session.commit()
        
        print("Utilisateurs créés avec succès!")

if __name__ == "__main__":
    create_initial_users()