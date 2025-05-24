#include <SPI.h>
#include <MFRC522.h>
#include <HX711.h>
#include <ArduinoJson.h>  // Ajouté pour faciliter la création de JSON

#define SS_PIN 10
#define RST_PIN 9
#define LED_G 6    // LED verte pour indiquer un succès
#define LED_R 7    // LED rouge pour indiquer une erreur
#define LED_Y 3    // LED jaune pour indiquer attente/processus en cours (optionnel)
#define ZONE_ID 2  // ID de la zone actuelle - MODIFIER selon votre zone

MFRC522 mfrc522(SS_PIN, RST_PIN);
MFRC522::MIFARE_Key key;
MFRC522::StatusCode status;
HX711 scale;
float calibration_factor = 215.0;

// Initialisation de la balance
float weight_grams = 0;

// Pour éviter la lecture répétée de la même carte
String lastReadUID = "";
unsigned long lastReadTime = 0;
const unsigned long READ_TIMEOUT = 3000; // 3 secondes entre les lectures

void setup() {
  Serial.begin(9600);
  SPI.begin();
  mfrc522.PCD_Init();
  
  pinMode(LED_G, OUTPUT);
  pinMode(LED_R, OUTPUT);
  pinMode(LED_Y, OUTPUT); // LED jaune pour les états intermédiaires
  
  // Allumer brièvement toutes les LEDs pour tester
  digitalWrite(LED_G, HIGH);
  digitalWrite(LED_R, HIGH);
  digitalWrite(LED_Y, HIGH);
  delay(500);
  digitalWrite(LED_G, LOW);
  digitalWrite(LED_R, LOW);
  digitalWrite(LED_Y, LOW);

  scale.begin(5, 4);
  scale.set_scale(calibration_factor);
  scale.tare();  // Réinitialiser la balance à 0
  
  // Préparer la clé pour authentification
  for (byte i = 0; i < 6; i++) {
    key.keyByte[i] = 0xFF;  // Clé par défaut
  }
  
}

void loop() {
  // Mettre à jour le poids
  updateWeight();
  
  // Faire clignoter la LED jaune pour indiquer que le système est en attente
  if (millis() % 1000 < 500) {
    digitalWrite(LED_Y, HIGH);
  } else {
    digitalWrite(LED_Y, LOW);
  }
  
  // Détection automatique des cartes
  if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {
    // Allumer la LED jaune fixe pour indiquer une lecture en cours
    digitalWrite(LED_Y, HIGH);
    
    // Obtenir l'UID
    String uid = "";
    for (byte i = 0; i < mfrc522.uid.size; i++) {
      uid += (mfrc522.uid.uidByte[i] < 0x10 ? "0" : "");
      uid += String(mfrc522.uid.uidByte[i], HEX);
    }
    uid.toUpperCase();
    
    // Vérifier si c'est la même carte récemment lue
    if (uid != lastReadUID || (millis() - lastReadTime > READ_TIMEOUT)) {
      lastReadUID = uid;
      lastReadTime = millis();
      
      // Lire les données de la carte
      String data = readCardData();
      
      // Créer et envoyer le JSON
      StaticJsonDocument<256> doc;
      doc["uid"] = uid;
      doc["weight"] = weight_grams;
      doc["zone_id"] = ZONE_ID;  // Important: Identifie la zone dans laquelle le produit est placé
      doc["data"] = data;
      doc["timestamp"] = millis();
      doc["reader_type"] = "zone";  // Pour identifier que c'est le lecteur de zone
      
      // Sérialiser le JSON et envoyer
      String jsonOutput;
      serializeJson(doc, jsonOutput);
      Serial.println(jsonOutput);
      
      // LED verte pour confirmer
      digitalWrite(LED_G, HIGH);
      digitalWrite(LED_Y, LOW);
      delay(500);
      digitalWrite(LED_G, LOW);
    } else {
      // Même carte, ignorée
      digitalWrite(LED_R, HIGH);
      digitalWrite(LED_Y, LOW);
      delay(200);
      digitalWrite(LED_R, LOW);
    }
    
    // Terminer l'opération PICC
    mfrc522.PICC_HaltA();
    mfrc522.PCD_StopCrypto1();
  }
  
  delay(100); // Petite pause pour économiser les ressources
}

void updateWeight() {
  weight_grams = scale.get_units(5);  // Moyenne sur 5 lectures pour plus de stabilité
  if (weight_grams < 0) {
    weight_grams = 0.00;
  }
}

String readCardData() {
  byte blockAddr = 4;
  status = mfrc522.PCD_Authenticate(MFRC522::PICC_CMD_MF_AUTH_KEY_A, blockAddr, &key, &(mfrc522.uid));
  
  if (status != MFRC522::STATUS_OK) {
    digitalWrite(LED_R, HIGH);
    delay(500);
    digitalWrite(LED_R, LOW);
    return "AUTH_ERROR";
  }
  
  byte buffer[18];
  byte size = sizeof(buffer);
  status = mfrc522.MIFARE_Read(blockAddr, buffer, &size);
  
  if (status != MFRC522::STATUS_OK) {
    digitalWrite(LED_R, HIGH);
    delay(500);
    digitalWrite(LED_R, LOW);
    return "READ_ERROR";
  }
  
  // Convertir en chaîne
  String data = "";
  for (byte i = 0; i < 16 && buffer[i] != 0; i++) {
    data += (char)buffer[i];
  }
  
  return data;
}

// Fonction pour lire les données structurées de la carte
// Utilisée si vous stockez des données au format JSON ou autre format structuré
String readStructuredData() {
  String result = "";
  byte buffer[18];
  byte size = sizeof(buffer);
  
  // Lecture du bloc 4 (informations de base)
  byte blockAddr = 4;
  status = mfrc522.PCD_Authenticate(MFRC522::PICC_CMD_MF_AUTH_KEY_A, blockAddr, &key, &(mfrc522.uid));
  
  if (status != MFRC522::STATUS_OK) {
    return "AUTH_ERROR";
  }
  
  status = mfrc522.MIFARE_Read(blockAddr, buffer, &size);
  
  if (status != MFRC522::STATUS_OK) {
    return "READ_ERROR";
  }
  
  // Lire les données de base (bloc 4)
  String basicInfo = "";
  for (byte i = 0; i < 16 && buffer[i] != 0; i++) {
    basicInfo += (char)buffer[i];
  }
  
  // Construire un JSON si nécessaire
  StaticJsonDocument<128> doc;
  doc["product_info"] = basicInfo;
  
  // Si besoin, lire d'autres blocs pour plus d'informations
  
  // Sérialiser le résultat
  serializeJson(doc, result);
  return result;
}