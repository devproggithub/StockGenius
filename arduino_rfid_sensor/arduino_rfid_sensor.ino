#include <SPI.h>
#include <MFRC522.h>
#include <MFRC522Extended.h>
#include <Wire.h>

#define SS_PIN 10
#define RST_PIN 9
#define LED_G 6
#define LED_R 7

MFRC522 mfrc522(SS_PIN, RST_PIN);
MFRC522::MIFARE_Key key;
MFRC522::StatusCode status;

// Structure pour les informations du produit
struct ProductInfo {
  char productId[10];
  char productName[20];
  int quantity;
  float price;
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
  
  Serial.println(F("Scanner une carte RFID pour lire/écrire des données"));
  Serial.println(F("Commandes disponibles:"));
  Serial.println(F("r - Lire les données de la carte"));
  Serial.println(F("w - Écrire des données sur la carte"));
  Serial.println(F("WRITE:json - Écrire des données JSON sur la carte"));
}
void loop() 
{
  // Code existant pour la vérification des commandes...
  
  // Détection automatique des cartes
  if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {
    // Afficher l'UID de la carte
    String content = "";
    for (byte i = 0; i < mfrc522.uid.size; i++) 
    {
      content.concat(String(mfrc522.uid.uidByte[i] < 0x10 ? " 0" : " "));
      content.concat(String(mfrc522.uid.uidByte[i], HEX));
    }
    content.toUpperCase();
    Serial.print("UID de la carte: ");
    Serial.println(content.substring(1));
    
    // Vérifier les accès selon l'UID
    if (content.substring(1) == "F3 A7 9B AA") 
    {
      digitalWrite(LED_G, HIGH);
      delay(2000);
      digitalWrite(LED_G, LOW);
    }
    else if (content.substring(1) == "83 C4 5A 9A") 
    {
      digitalWrite(LED_G, HIGH);
      delay(2000);
      digitalWrite(LED_G, LOW);
    }
    else {
      digitalWrite(LED_R, HIGH);
      delay(2000);
      digitalWrite(LED_R, LOW);
    }
    
    // Lire et envoyer les données au format JSON
    readCardData();
    
    // Terminer l'opération PICC
    mfrc522.PICC_HaltA();
    mfrc522.PCD_StopCrypto1();
    
    delay(1000); // Éviter les lectures multiples
  }
}

void writeCardData() {
  // Construire une chaîne simple au format "ID:Nom:Quantité:Prix"
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
  dataToWrite += productName + ":";
  
  // Quantité
  /*Serial.println(F("Entrez la quantité:"));
  while (!Serial.available()) { delay(100); }
  delay(500);
  String quantity = "";
  while(Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') continue;
    quantity += c;
  }
  dataToWrite += quantity + ":";
  
  // Prix
  Serial.println(F("Entrez le prix:"));
  while (!Serial.available()) { delay(100); }
  delay(500);
  String price = "";
  while(Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') continue;
    price += c;
  }
  dataToWrite += price;
  */
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
  
  // Écrire sur la carte
  byte blockAddr = 4;
  status = mfrc522.PCD_Authenticate(MFRC522::PICC_CMD_MF_AUTH_KEY_A, blockAddr, &key, &(mfrc522.uid));
  if (status != MFRC522::STATUS_OK) {
    Serial.print(F("Échec d'authentification. Code: "));
    Serial.println(mfrc522.GetStatusCodeName(status));
    return;
  }
  
  status = mfrc522.MIFARE_Write(blockAddr, buffer, 16);
  if (status != MFRC522::STATUS_OK) {
    Serial.print(F("Échec d'écriture. Code: "));
    Serial.println(mfrc522.GetStatusCodeName(status));
    return;
  }
  
  Serial.println(F("Données écrites avec succès!"));
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
    return;
  }
  
  // Convertir en chaîne
  String data = "";
  for (byte i = 0; i < 16 && buffer[i] != 0; i++) {
    data += (char)buffer[i];
  }
  
  // Analyser la chaîne au format "ID:Nom:Quantité:Prix"
  int separatorPos1 = data.indexOf(':');
  int separatorPos2 = data.indexOf(':', separatorPos1 + 1);
  
  // Format JSON avec les données complètes
  Serial.print("{\"uid\":\"");
  Serial.print(uid);
  Serial.print("\",\"data\":{");
  
  if (separatorPos1 > 0) {
    String id = data.substring(0, separatorPos1);
    String name = data.substring(separatorPos1 + 1, data.length());
    
    // Ajouter les champs au JSON
    Serial.print("\"id\":\"");
    Serial.print(id);
    Serial.print("\",\"name\":\"");
    Serial.print(name);
    Serial.print("\"");
    
    // Si on a des données de quantité et prix (commentées dans votre code)
    if (separatorPos2 > 0) {
      int separatorPos3 = data.indexOf(':', separatorPos2 + 1);
      if (separatorPos3 > 0) {
        String quantity = data.substring(separatorPos2 + 1, separatorPos3);
        String price = data.substring(separatorPos3 + 1);
        
        Serial.print(",\"quantity\":");
        Serial.print(quantity);
        Serial.print(",\"price\":");
        Serial.print(price);
      }
    }
  } else {
    // Données non formatées, les envoyer telles quelles
    Serial.print("\"raw\":\"");
    Serial.print(data);
    Serial.print("\"");
  }
  
  // Fermer le JSON
  Serial.println("}}");
}
void processJsonCommand(String jsonCmd) {
  // Détecter si c'est une commande d'écriture
  if (jsonCmd.startsWith("WRITE:")) {
    String jsonData = jsonCmd.substring(6); // Retirer "WRITE:"
    
    // Attendez qu'une carte soit présente
    Serial.println(F("Placez une carte RFID..."));
    
    while (!mfrc522.PICC_IsNewCardPresent() || !mfrc522.PICC_ReadCardSerial()) {
      delay(100);
    }
    
    // Préparer les données à écrire
    // Supposons que les données sont au format {"id":"123","name":"Produit"}
    // Convertir en format "123:Produit"
    
    // Ici vous auriez besoin d'une bibliothèque JSON pour parser, mais on improvise
    int idStart = jsonData.indexOf("\"id\":\"") + 6;
    int idEnd = jsonData.indexOf("\"", idStart);
    int nameStart = jsonData.indexOf("\"name\":\"") + 8;
    int nameEnd = jsonData.indexOf("\"", nameStart);
    
    if (idStart > 6 && nameStart > 8) {
      String id = jsonData.substring(idStart, idEnd);
      String name = jsonData.substring(nameStart, nameEnd);
      
      // Formater au format attendu par votre fonction writeCardData
      String dataToWrite = id + ":" + name;
      
      // Écrire sur la carte
      byte buffer[16];
      memset(buffer, 0, sizeof(buffer));
      
      byte dataLength = min(dataToWrite.length(), (unsigned int)15);
      for (byte i = 0; i < dataLength; i++) {
        buffer[i] = dataToWrite.charAt(i);
      }
      buffer[dataLength] = 0; // Terminateur nul
      
      // Écrire sur la carte
      byte blockAddr = 4;
      status = mfrc522.PCD_Authenticate(MFRC522::PICC_CMD_MF_AUTH_KEY_A, blockAddr, &key, &(mfrc522.uid));
      if (status != MFRC522::STATUS_OK) {
        Serial.println(F("ERROR: Échec d'authentification"));
        return;
      }
      
      status = mfrc522.MIFARE_Write(blockAddr, buffer, 16);
      if (status != MFRC522::STATUS_OK) {
        Serial.println(F("ERROR: Échec d'écriture"));
        return;
      }
      
      Serial.println(F("OK: Données écrites avec succès"));
      
      // Terminer l'opération PICC
      mfrc522.PICC_HaltA();
      mfrc522.PCD_StopCrypto1();
    } else {
      Serial.println(F("ERROR: Format JSON invalide"));
    }
  }
}