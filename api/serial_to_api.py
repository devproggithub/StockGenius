import serial
import requests
import json
import time

# Configurez le port série (adapté à votre configuration)
PORT = 'COM13'  # Changez selon votre port Arduino
BAUD_RATE = 9600

# URL de votre API Flask
API_URL = "http://localhost:5000/api/rfid/data"

def main():
    print(f"Démarrage de la passerelle série vers API...")
    print(f"Port: {PORT}, Baud rate: {BAUD_RATE}")
    print(f"API URL: {API_URL}")
    
    try:
        # Ouvrir la connexion série
        ser = serial.Serial(PORT, BAUD_RATE, timeout=1)
        print("Connexion série établie. En attente de données...")
        
        while True:
            # Lire une ligne du port série
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').strip()
                
                # Vérifier si c'est un JSON
                if line.startswith('{') and line.endswith('}'):
                    try:
                        # Analyser le JSON
                        data = json.loads(line)
                        print(f"Données reçues: {data}")
                        
                        # Envoyer à l'API
                        response = requests.post(API_URL, json=data)
                        
                        # Afficher la réponse
                        if response.status_code == 200 or response.status_code == 201:
                            print(f"✅ Données envoyées avec succès! Code: {response.status_code}")
                        else:
                            print(f"❌ Erreur API: {response.status_code}")
                            print(response.text)
                            
                    except json.JSONDecodeError:
                        print(f"❌ Erreur JSON invalide: {line}")
                    except requests.RequestException as e:
                        print(f"❌ Erreur de connexion à l'API: {e}")
                else:
                    print(f"Message: {line}")
            
            # Petite pause
            time.sleep(0.1)
            
    except serial.SerialException as e:
        print(f"❌ Erreur de connexion série: {e}")
    except KeyboardInterrupt:
        print("Programme arrêté par l'utilisateur")
    finally:
        # Fermer la connexion série si elle est ouverte
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("Connexion série fermée")

if __name__== "_main_":
    main()