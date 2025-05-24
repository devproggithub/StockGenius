#include <SPI.h>
#include <MFRC522.h>
#include <MFRC522Extended.h>
#include <Wire.h>

#define SS_PIN 10
#define RST_PIN 9
#define LED_G 6   // LED verte pour indiquer succès
#define LED_R 7   // LED rouge pour indiquer échec

MFRC522 mfrc522(SS_PIN, RST_PIN);
MFRC522::MIFARE_Key key;
MFRC522::StatusCode status;

// Structure pour les informations de la carte RFID
struct RFIDData {
  char uid[20];        // UID de la carte
  char productId[10];  // ID du produit
  char productName[20]; // Nom du produit
};

void setup() 
{
  Serial.begin(9600);   // Initialiser la communication série
  SPI.begin();          // Initialiser le bus SPI
  mfrc522.PCD_Init();   // Initialiser MFRC522
  
  pinMode(LED_G, OUTPUT);
  pinMode(LED_R, OUTPUT);
  
  // Préparer la clé pour authentification
  for (byte i = 0; i < 6; i++) {
    key.keyByte[i] = 0xFF;  // Clé par défaut
  }
  
  Serial.println(F("Système de gestion de badges RFID pour produits"));
  Serial.println(F("Commandes disponibles:"));
  Serial.println(F("r - Lire les données du badge"));
  Serial.println(F("w - Écrire des données sur le badge"));
  Serial.println(F("WRITE:json - Écrire des données JSON sur le badge"));
  Serial.println(F("Placez un badge ou envoyez une commande"));
  
  // Afficher le format attendu pour faciliter la compatibilité
  Serial.println(F("Format JSON attendu: {\"uid\":\"ID\",\"raw_data\":\"ProductID:ProductName:0\"}"));
}

void loop() 
{
  // Vérifier si des commandes sont disponibles via le port série
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
    if (command == "r") {
      Serial.println(F("Placez le badge à lire..."));
      while (!mfrc522.PICC_IsNewCardPresent() || !mfrc522.PICC_ReadCardSerial()) {
        delay(100);
      }
      readCardData();
      mfrc522.PICC_HaltA();
      mfrc522.PCD_StopCrypto1();
    }
    else if (command == "w") {
      Serial.println(F("Placez le badge à programmer..."));
      while (!mfrc522.PICC_IsNewCardPresent() || !mfrc522.PICC_ReadCardSerial()) {
        delay(100);
      }
      writeCardData();
      mfrc522.PICC_HaltA();
      mfrc522.PCD_StopCrypto1();
    }
    else if (command.startsWith("WRITE:")) {
      processJsonCommand(command);
    }
  }
  
  // Détection automatique des badges
  if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {
    // Afficher l'UID du badge
    String content = "";
    for (byte i = 0; i < mfrc522.uid.size; i++) 
    {
      content.concat(String(mfrc522.uid.uidByte[i] < 0x10 ? " 0" : " "));
      content.concat(String(mfrc522.uid.uidByte[i], HEX));
    }
    content.toUpperCase();
    Serial.print("UID du badge: ");
    Serial.println(content.substring(1));
    
    // Lire et envoyer les données au format JSON
    readCardData();
    
    // Terminer l'opération PICC
    mfrc522.PICC_HaltA();
    mfrc522.PCD_StopCrypto1();
    
    delay(1000); // Éviter les lectures multiples
  }
}

void writeCardData() {
  // Construire une chaîne au format "ID:Nom:0"
  String dataToWrite = "";
  
  // Vider le buffer série
  while(Serial.available()) { Serial.read(); }
  
  // ID du produit
  Serial.println(F("Entrez l'ID du produit:"));
  while (!Serial.available()) { delay(100); }
  delay(500);
  String productId = "";
  while(Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') continue;
    productId += c;
  }
  dataToWrite += productId + ":";
  
  // Nom du produit
  Serial.println(F("Entrez le nom du produit:"));
  while (!Serial.available()) { delay(100); }
  delay(500);
  String productName = "";
  while(Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') continue;
    productName += c;
  }
  dataToWrite += productName + ":0";  // Ajout de ":0" à la fin
  
  Serial.print(F("Données à écrire: "));
  Serial.println(dataToWrite);
  
  // Convertir en tableau d'octets
  byte buffer[16];
  memset(buffer, 0, sizeof(buffer));
  
  byte dataLength = min(dataToWrite.length(), (unsigned int)15);
  for (byte i = 0; i < dataLength; i++) {
    buffer[i] = dataToWrite.charAt(i);
  }
  buffer[dataLength] = 0; // Terminateur nul
  
  // Écrire sur le badge
  byte blockAddr = 4; // Bloc de données
  status = mfrc522.PCD_Authenticate(MFRC522::PICC_CMD_MF_AUTH_KEY_A, blockAddr, &key, &(mfrc522.uid));
  if (status != MFRC522::STATUS_OK) {
    Serial.print(F("Échec d'authentification. Code: "));
    Serial.println(mfrc522.GetStatusCodeName(status));
    digitalWrite(LED_R, HIGH);
    delay(1000);
    digitalWrite(LED_R, LOW);
    return;
  }
  
  status = mfrc522.MIFARE_Write(blockAddr, buffer, 16);
  if (status != MFRC522::STATUS_OK) {
    Serial.print(F("Échec d'écriture. Code: "));
    Serial.println(mfrc522.GetStatusCodeName(status));
    digitalWrite(LED_R, HIGH);
    delay(1000);
    digitalWrite(LED_R, LOW);
    return;
  }
  
  Serial.println(F("Données écrites avec succès!"));
  digitalWrite(LED_G, HIGH);
  delay(1000);
  digitalWrite(LED_G, LOW);
}

void readCardData() {
  Serial.println(F("Lecture des données..."));
  
  // Obtenir l'UID
  String uid = "";
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    uid += (mfrc522.uid.uidByte[i] < 0x10 ? "0" : "");
    uid += String(mfrc522.uid.uidByte[i], HEX);
  }
  uid.toUpperCase();
  
  byte blockAddr = 4;
  status = mfrc522.PCD_Authenticate(MFRC522::PICC_CMD_MF_AUTH_KEY_A, blockAddr, &key, &(mfrc522.uid));
  if (status != MFRC522::STATUS_OK) {
    // En cas d'erreur, envoyer uniquement l'UID en JSON
    Serial.print("{\"uid\":\"");
    Serial.print(uid);
    Serial.println("\",\"error\":\"Échec d'authentification\"}");
    digitalWrite(LED_R, HIGH);
    delay(1000);
    digitalWrite(LED_R, LOW);
    return;
  }
  
  byte buffer[18];
  byte size = sizeof(buffer);
  status = mfrc522.MIFARE_Read(blockAddr, buffer, &size);
  if (status != MFRC522::STATUS_OK) {
    // En cas d'erreur, envoyer uniquement l'UID en JSON
    Serial.print("{\"uid\":\"");
    Serial.print(uid);
    Serial.println("\",\"error\":\"Échec de lecture\"}");
    digitalWrite(LED_R, HIGH);
    delay(1000);
    digitalWrite(LED_R, LOW);
    return;
  }
  
  // Convertir en chaîne
  String data = "";
  for (byte i = 0; i < 16 && buffer[i] != 0; i++) {
    data += (char)buffer[i];
  }
  
  // Format JSON avec raw_data au lieu de data
  Serial.print("{\"uid\":\"");
  Serial.print(uid);
  Serial.print("\",\"raw_data\":\"");
  Serial.print(data); // "ProductID:ProductName:0" dans raw_data
  Serial.print("\",\"timestamp\":");
  Serial.print(millis());
  Serial.println("}");
  
  // Indiquer succès de lecture
  digitalWrite(LED_G, HIGH);
  delay(500);
  digitalWrite(LED_G, LOW);
}

void processJsonCommand(String jsonCmd) {
  // Détecter si c'est une commande d'écriture
  if (jsonCmd.startsWith("WRITE:")) {
    String jsonData = jsonCmd.substring(6); // Retirer "WRITE:"
    
    // Attendez qu'un badge soit présent
    Serial.println(F("Placez un badge RFID..."));
    
    while (!mfrc522.PICC_IsNewCardPresent() || !mfrc522.PICC_ReadCardSerial()) {
      delay(100);
    }
    
    // Format attendu: {"raw_data":"ProductID:ProductName:0"}
    
    // Obtenir l'UID actuel du badge
    String currentUid = "";
    for (byte i = 0; i < mfrc522.uid.size; i++) {
      currentUid += (mfrc522.uid.uidByte[i] < 0x10 ? "0" : "");
      currentUid += String(mfrc522.uid.uidByte[i], HEX);
    }
    currentUid.toUpperCase();
    
    // Extraction des données du JSON
    int dataStart = jsonData.indexOf("\"raw_data\":\"") + 12;
    if (dataStart <= 12) {
      dataStart = jsonData.indexOf("\"data\":\"") + 8; // Compatibilité avec ancien format
    }
    int dataEnd = jsonData.indexOf("\"", dataStart);
    
    if (dataStart > 8) {
      String dataToWrite = jsonData.substring(dataStart, dataEnd);
      
      // Vérifier si le format se termine par ":0", sinon l'ajouter
      if (!dataToWrite.endsWith(":0")) {
        // Vérifier s'il y a au moins un ":" (séparateur ID:Nom)
        if (dataToWrite.indexOf(':') > 0) {
          dataToWrite += ":0";
        } else {
          // Si pas de séparateur, considérer que c'est juste l'ID
          dataToWrite += ":Produit:0";
        }
      }
      
      // Écrire sur le badge
      byte buffer[16];
      memset(buffer, 0, sizeof(buffer));
      
      byte dataLength = min(dataToWrite.length(), (unsigned int)15);
      for (byte i = 0; i < dataLength; i++) {
        buffer[i] = dataToWrite.charAt(i);
      }
      buffer[dataLength] = 0; // Terminateur nul
      
      // Écrire sur le badge
      byte blockAddr = 4;
      status = mfrc522.PCD_Authenticate(MFRC522::PICC_CMD_MF_AUTH_KEY_A, blockAddr, &key, &(mfrc522.uid));
      if (status != MFRC522::STATUS_OK) {
        Serial.println(F("ERROR: Échec d'authentification"));
        digitalWrite(LED_R, HIGH);
        delay(1000);
        digitalWrite(LED_R, LOW);
        return;
      }
      
      status = mfrc522.MIFARE_Write(blockAddr, buffer, 16);
      if (status != MFRC522::STATUS_OK) {
        Serial.println(F("ERROR: Échec d'écriture"));
        digitalWrite(LED_R, HIGH);
        delay(1000);
        digitalWrite(LED_R, LOW);
        return;
      }
      
      // Générer la confirmation au format JSON attendu
      Serial.print("{\"uid\":\"");
      Serial.print(currentUid);
      Serial.print("\",\"raw_data\":\"");
      Serial.print(dataToWrite);
      Serial.print("\",\"timestamp\":");
      Serial.print(millis());
      Serial.println("}");
      
      digitalWrite(LED_G, HIGH);
      delay(1000);
      digitalWrite(LED_G, LOW);
      
      // Terminer l'opération PICC
      mfrc522.PICC_HaltA();
      mfrc522.PCD_StopCrypto1();
    } else {
      Serial.println(F("ERROR: Format JSON invalide"));
      Serial.println(F("Format attendu: {\"raw_data\":\"ProductID:ProductName:0\"}"));
      digitalWrite(LED_R, HIGH);
      delay(1000);
      digitalWrite(LED_R, LOW);
    }
  }

  if (jsonCmd.startsWith("WRITE:")) {
    String jsonData = jsonCmd.substring(6); // Retirer "WRITE:"
    
    // Attendez qu'une carte soit présente
    Serial.println(F("Placez un badge RFID..."));
    
    while (!mfrc522.PICC_IsNewCardPresent() || !mfrc522.PICC_ReadCardSerial()) {
      delay(100);
    }
    
    // Préparer les données à écrire
    // Format attendu: {"uid":"83C45A9A","weight":0,"zone_id":2,"data":"0"}
    
    // Extraction des données du JSON (méthode simplifiée)
    int uidStart = jsonData.indexOf("\"uid\":\"") + 7;
    int uidEnd = jsonData.indexOf("\"", uidStart);
    
    int weightStart = jsonData.indexOf("\"weight\":") + 9;
    int weightEnd = jsonData.indexOf(",", weightStart);
    if (weightEnd < 0) weightEnd = jsonData.indexOf("}", weightStart);
    
    int zoneStart = jsonData.indexOf("\"zone_id\":") + 10;
    int zoneEnd = jsonData.indexOf(",", zoneStart);
    if (zoneEnd < 0) zoneEnd = jsonData.indexOf("}", zoneStart);
    
    int dataStart = jsonData.indexOf("\"data\":\"") + 8;
    int dataEnd = jsonData.indexOf("\"", dataStart);
    
    if (uidStart > 7 && weightStart > 9 && zoneStart > 10) {
      // Obtenir l'UID actuel du badge
      String currentUid = "";
      for (byte i = 0; i < mfrc522.uid.size; i++) {
        currentUid += (mfrc522.uid.uidByte[i] < 0x10 ? "0" : "");
        currentUid += String(mfrc522.uid.uidByte[i], HEX);
      }
      currentUid.toUpperCase();
      
      // Extraire les valeurs du JSON
      String uid = jsonData.substring(uidStart, uidEnd);
      String weight = jsonData.substring(weightStart, weightEnd);
      String zone = jsonData.substring(zoneStart, zoneEnd);
      String data = "";
      
      if (dataStart > 8) {
        data = jsonData.substring(dataStart, dataEnd);
      }
      
      // Vérification (facultative) si l'UID correspond
      if (uid != currentUid) {
        Serial.println(F("ATTENTION: L'UID défini dans le JSON ne correspond pas à l'UID de la carte"));
        Serial.print(F("UID dans JSON: "));
        Serial.println(uid);
        Serial.print(F("UID réel: "));
        Serial.println(currentUid);
        // Optionnel: Utiliser l'UID réel à la place
        uid = currentUid;
      }
      
      // Formater au format attendu pour le stockage
      String dataToWrite = uid + ":" + weight + ":" + zone + ":" + data;
      
      // Écrire sur le badge
      byte buffer[16];
      memset(buffer, 0, sizeof(buffer));
      
      byte dataLength = min(dataToWrite.length(), (unsigned int)15);
      for (byte i = 0; i < dataLength; i++) {
        buffer[i] = dataToWrite.charAt(i);
      }
      buffer[dataLength] = 0; // Terminateur nul
      
      // Écrire sur le badge
      byte blockAddr = 4;
      status = mfrc522.PCD_Authenticate(MFRC522::PICC_CMD_MF_AUTH_KEY_A, blockAddr, &key, &(mfrc522.uid));
      if (status != MFRC522::STATUS_OK) {
        Serial.println(F("ERROR: Échec d'authentification"));
        digitalWrite(LED_R, HIGH);
        delay(1000);
        digitalWrite(LED_R, LOW);
        return;
      }
      
      status = mfrc522.MIFARE_Write(blockAddr, buffer, 16);
      if (status != MFRC522::STATUS_OK) {
        Serial.println(F("ERROR: Échec d'écriture"));
        digitalWrite(LED_R, HIGH);
        delay(1000);
        digitalWrite(LED_R, LOW);
        return;
      }
      
      // Générer la confirmation au format JSON attendu
      Serial.print("{\"uid\":\"");
      Serial.print(uid);
      Serial.print("\",\"weight\":");
      Serial.print(weight);
      Serial.print(",\"zone_id\":");
      Serial.print(zone);
      Serial.print(",\"data\":\"");
      Serial.print(data);
      Serial.print("\",\"timestamp\":");
      Serial.print(millis());
      Serial.print(",\"reader_type\":\"zone\",\"status\":\"");
      Serial.print("success");
      Serial.println("\"}");
      
      digitalWrite(LED_G, HIGH);
      delay(1000);
      digitalWrite(LED_G, LOW);
      
      // Terminer l'opération PICC
      mfrc522.PICC_HaltA();
      mfrc522.PCD_StopCrypto1();
    } else {
      Serial.println(F("ERROR: Format JSON invalide"));
      Serial.println(F("Format attendu: {\"uid\":\"ID\",\"weight\":N,\"zone_id\":N,\"data\":\"X\"}"));
      digitalWrite(LED_R, HIGH);
      delay(1000);
      digitalWrite(LED_R, LOW);
    }
  }
}