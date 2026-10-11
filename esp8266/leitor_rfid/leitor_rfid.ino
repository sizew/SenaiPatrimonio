#include <SPI.h>
#include <MFRC522.h>
#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include "config.h"

// ============================================================
// PINOS - WeMos D1 R1 (ESP8266 no formato Arduino Uno)
// Leitor RFID (MFRC522):
// RST = D9  (GPIO 2)
// SDA = D10 (GPIO 15)
// MOSI= D11 (GPIO 13)
// MISO= D12 (GPIO 12)
// SCK = D13 (GPIO 14)
// VCC = 3.3V  |  GND = GND
// ============================================================
#define RST_PIN  2   // D9
#define SS_PIN   15  // D10

MFRC522 rfid(SS_PIN, RST_PIN);

// Variável para controle de reconexão Wi-Fi não-bloqueante
unsigned long ultimaTentativaWifi = 0;

void conectarWiFi() {
    Serial.print(F("Conectando na rede Wi-Fi: "));
    Serial.println(WIFI_SSID);

    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    int tentativas = 0;
    while (WiFi.status() != WL_CONNECTED && tentativas < 25) {
        delay(400);
        Serial.print(F("."));
        tentativas++;
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println(F("\n[OK] Wi-Fi Conectado com Sucesso!"));
        Serial.print(F("IP do Leitor: "));
        Serial.println(WiFi.localIP());
        Serial.print(F("Servidor Alvo: "));
        Serial.println(SERVER_URL);
        Serial.print(F("ID Laboratorio: "));
        Serial.println(LAB_ID);
    } else {
        Serial.println(F("\n[AVISO] Nao conectou de imediato. Tentando novamente no loop..."));
    }
}

void setup() {
    Serial.begin(115200);
    while (!Serial);

    SPI.begin();
    rfid.PCD_Init();

    Serial.println(F("\n\n========================================="));
    Serial.println(F("   SENAI PATRIMONIO - LEITOR RFID        "));
    Serial.println(F("========================================="));

    conectarWiFi();

    Serial.println(F("========================================="));
    Serial.println(F("Pronto! Aproxime um cracha do leitor...\n"));
}

void loop() {
    // Reconexão Wi-Fi robusta e não-bloqueante (tenta a cada 5s se oscilar)
    if (WiFi.status() != WL_CONNECTED) {
        unsigned long agora = millis();
        if (agora - ultimaTentativaWifi > 5000) {
            ultimaTentativaWifi = agora;
            Serial.println(F("[!] Sinal Wi-Fi desconectado. Tentando reconectar..."));
            WiFi.reconnect();
        }
        delay(100);
        return;
    }

    // Aguarda aproximação física do crachá
    if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) {
        delay(50);
        return;
    }

    // Extrai o código UID em hexadecimal maiúsculo
    String uid = "";
    for (byte i = 0; i < rfid.uid.size; i++) {
        uid += String(rfid.uid.uidByte[i] < 0x10 ? "0" : "");
        uid += String(rfid.uid.uidByte[i], HEX);
    }
    uid.toUpperCase();

    Serial.println(F("-----------------------------------------"));
    Serial.print(F("[+] Cracha Detectado! UID: "));
    Serial.println(uid);
    Serial.println(F("Enviando leitura para o servidor SENAI..."));

    WiFiClient client;
    HTTPClient http;

    http.begin(client, SERVER_URL);
    http.setTimeout(HTTP_TIMEOUT_MS);
    http.addHeader("Content-Type", "application/json");

    String jsonPayload = "{\"tag_uid\":\"" + uid + "\",\"lab_id\":" + String(LAB_ID) + "}";
    int httpCode = http.POST(jsonPayload);

    if (httpCode > 0) {
        String resposta = http.getString();
        Serial.print(F("Resposta do Servidor (HTTP "));
        Serial.print(httpCode);
        Serial.print(F("): "));
        Serial.println(resposta);

        if (resposta.indexOf("\"aberto\"") >= 0) {
            Serial.println(F(">>> SUCESSO: TURNO DE AULA INICIADO!"));
        } else if (resposta.indexOf("\"encerrado\"") >= 0) {
            Serial.println(F(">>> SUCESSO: TURNO ENCERRADO / PATRIMONIOS LIBERADOS!"));
        } else if (resposta.indexOf("\"pendente\"") >= 0) {
            Serial.println(F(">>> CRACHA DETECTADO! Aguardando ativacao pela secretaria."));
        } else if (resposta.indexOf("\"negado\"") >= 0) {
            Serial.println(F(">>> ACESSO RECUSADO: Apenas professores iniciam turno."));
        }
    } else {
        Serial.print(F("[ERRO] Falha de conexao com o servidor. Codigo HTTP: "));
        Serial.println(httpCode);
        Serial.print(F("Verifique se o servidor Python esta ativo em: "));
        Serial.println(SERVER_URL);
    }

    http.end();
    rfid.PICC_HaltA();
    rfid.PCD_StopCrypto1();

    delay(1500); // Pausa de estabilização
    Serial.println(F("\nAguardando proximo cracha...\n"));
}
