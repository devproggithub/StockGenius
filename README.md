# 📦 StockGenius

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)  
[![Flask](https://img.shields.io/badge/Flask-2.3-blue)](https://flask.palletsprojects.com/)  
[![MySQL](https://img.shields.io/badge/MySQL-8.0-blue)](https://www.mysql.com/)  

**StockGenius**  is an intelligent web application designed to simplify and optimize inventory management for businesses of all sizes. Built with Flask and powered by a MySQL database, it offers a seamless way to track products, manage stock levels, and handle customer orders efficiently.

The platform provides a clean, user-friendly API structure that allows administrators to effortlessly create, read, update, and delete products and orders. With StockGenius, businesses can maintain full control over their inventory, reduce human errors, and ensure accurate stock forecasting.

Thanks to its modular and scalable architecture, StockGenius is perfect for startups looking for rapid growth and established companies aiming to modernize their operations. Security and performance are core priorities, ensuring that your data is protected while delivering a smooth user experience.


---

## 🚀 Fonctionnalités principales

- Gestion complète des **produits** (CRUD)
- Gestion complète des **commandes** (CRUD)
- Base de données relationnelle **MySQL**
- API RESTful sécurisée et extensible
- Architecture propre et modulaire (Blueprints Flask)
- Prêt pour production (Docker, déploiement cloud, etc.)

---

## 🏛️ Structure du projet

```
StockGenius/
├── app.py
├── config.py
├── models/
│   ├── __init__.py
│   ├── product.py
│   ├── order.py
│   ├── user.py
├── routes/
│   ├── __init__.py
│   ├── product_routes.py
│   ├── order_routes.py
│   ├── auth_routes.py
├── migrations/
├── requirements.txt
├── README.md
└── .env
```

---

## ⚙️ Installation

### 1. Cloner le dépôt
```bash
git clone https://github.com/your-username/StockGenius.git
cd StockGenius
```

### 2. Créer et activer un environnement virtuel
```bash
python -m venv venv
source venv/bin/activate    # Linux / MacOS
venv\Scripts\activate       # Windows
```

### 3. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 4. Configurer la base de données
- Installer **XAMPP** ou **MAMP** pour un serveur local MySQL.
- Créer une base de données `stockgenius_db` dans phpMyAdmin.
- Dans le fichier `.env` ou `config.py`, définir l'URI MySQL :

```python
SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://username:password@localhost/stockgenius_db'
SQLALCHEMY_TRACK_MODIFICATIONS = False
SECRET_KEY = 'votre_cle_secrete'
```

### 5. Initialiser la base de données
```bash
flask db init
flask db migrate -m "Initial migration."
flask db upgrade
```

### 6. Lancer l'application
```bash
flask run
```

Accéder à : [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## 📚 Principaux Endpoints API

| Méthode | Route | Description |
|:---|:---|:---|
| `POST` | `/api/auth/login` | Authentification utilisateur |
| `POST` | `/api/products/` | Créer un produit |
| `GET` | `/api/products/` | Lister tous les produits |
| `GET` | `/api/products/<id>` | Obtenir un produit par ID |
| `PUT` | `/api/products/<id>` | Mettre à jour un produit |
| `DELETE` | `/api/products/<id>` | Supprimer un produit |
| `POST` | `/api/orders/` | Créer une commande |
| `GET` | `/api/orders/` | Lister toutes les commandes |

---

## 🛠️ Technologies utilisées

- **Python 3.11+**
- **Flask** (Microframework Web)
- **SQLAlchemy** (ORM pour MySQL)
- **MySQL Server** (Base de données)
- **Flask-Migrate** (Gestion de migrations)
- **Flask-JWT-Extended** (Authentification sécurisée)

---

## 🔐 Sécurité

- Authentification JWT pour sécuriser les endpoints.
- Gestion des mots de passe avec hashing (bcrypt).
- Validation d'input des utilisateurs.

---

## ✨ Exemples de requêtes API (via Postman)

### Ajouter un produit
```http
POST /api/products/
Content-Type: application/json

{
    "name": "Laptop Dell XPS",
    "price": 1500,
    "quantity": 10
}
```

### Créer une commande
```http
POST /api/orders/
Content-Type: application/json

{
    "product_id": 1,
    "quantity": 2
}
```

---

## 📜 Licence

Ce projet est sous licence **MIT** — voir le fichier [LICENSE](LICENSE) pour plus d'informations.

---

## 📬 Contact

Développé avec ❤️ par **[Rachid OUAGUID](https://github.com/CleverRachid)**

- 📧 Email : rachid.ouaguid@gmail.com


Développé avec ❤️ par **[Nouhaila BLACHE](https://github.com/nouhaila2001204)**

- 📧 Email : blachenouhaila@gmail.com

Développé avec ❤️ par **[Yassine Taleb](https://github.com/devproggithub)**

- 📧 Email : taleb.yassine95@gmail.com

---

## 📖 Références fiables

- [Documentation Flask](https://flask.palletsprojects.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/en/20/)
- [Flask-JWT-Extended Docs](https://flask-jwt-extended.readthedocs.io/en/stable/)
- [XAMPP Official Website](https://www.apachefriends.org/index.html)

---

