#include <SPI.h>
#include <MFRC522.h>
#include <HX711.h>
#define SS_PIN 10
#define RST_PIN 9
#define LED_G 6
#define LED_R 7

MFRC522 mfrc522(SS_PIN, RST_PIN);
MFRC522::MIFARE_Key key;
MFRC522::StatusCode status;
HX711 scale;
float calibration_factor = -375;

// Initialisation de la balance (si utilisée)
float weight_grams = 0;

void setup() {
  Serial.begin(9600);
  SPI.begin();
  mfrc522.PCD_Init();
  
  pinMode(LED_G, OUTPUT);
  pinMode(LED_R, OUTPUT);

  scale.begin(5, 4);
  scale.set_scale(calibration_factor);
  scale.tare();  // Réinitialiser la balance à 0
  
  // Préparer la clé pour authentification
  for (byte i = 0; i < 6; i++) {
    key.keyByte[i] = 0xFF;  // Clé par défaut
  }
  
  Serial.println("System ready: Waiting for RFID cards...");
}

void loop() {

   updateWeight();
  // Détection automatique des cartes
  if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {
    // Obtenir l'UID
    String uid = "";
    for (byte i = 0; i < mfrc522.uid.size; i++) {
      uid += (mfrc522.uid.uidByte[i] < 0x10 ? "0" : "");
      uid += String(mfrc522.uid.uidByte[i], HEX);
    }
    uid.toUpperCase();
    
    // Lire les données de la carte
    String data = readCardData();
    
    // Envoyer au format JSON via port série
    Serial.print("{\"uid\":\"");
    Serial.print(uid);
    Serial.print("\",\"weight\":");
    Serial.print(weight_grams);
    Serial.print(",\"data\":\"");
    Serial.print(data);
    Serial.println("\"}");
    
    // LED verte pour confirmer
    digitalWrite(LED_G, HIGH);
    delay(1000);
    digitalWrite(LED_G, LOW);
    
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
    return "AUTH_ERROR";
  }
  
  byte buffer[18];
  byte size = sizeof(buffer);
  status = mfrc522.MIFARE_Read(blockAddr, buffer, &size);
  
  if (status != MFRC522::STATUS_OK) {
    return "READ_ERROR";
  }
  
  // Convertir en chaîne
  String data = "";
  for (byte i = 0; i < 16 && buffer[i] != 0; i++) {
    data += (char)buffer[i];
  }
  
  return data;
}
