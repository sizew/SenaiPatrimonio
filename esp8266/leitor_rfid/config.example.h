#ifndef CONFIG_EXAMPLE_H
#define CONFIG_EXAMPLE_H

// ============================================================
// SENAI PATRIMÔNIO - MODELO DE CONFIGURAÇÃO DO LEITOR RFID
// Copie este arquivo como "config.h" e preencha com seus dados
// ============================================================

// Credenciais da rede Wi-Fi
const char* WIFI_SSID     = "NOME_DA_SUA_REDE";
const char* WIFI_PASSWORD = "SENHA_DA_SUA_REDE";

// Endereço do Servidor Flask (substitua pelo IP do computador na rede local)
// Exemplo: "http://192.168.1.100:5000/api/rfid/leitura"
const char* SERVER_URL    = "http://192.168.0.10:5000/api/rfid/leitura";

// ID do laboratório onde este leitor físico está fixado (1 = Lab. Informática 1)
const int LAB_ID          = 1;

// Timeout da requisição HTTP (em milissegundos) para evitar que o leitor trave
const int HTTP_TIMEOUT_MS = 3500;

// Pinos de feedback visual e sonoro (WeMos D1 R1)
#define PIN_BUZZER      D2   // GPIO 16 (Buzzer Ativo Low Level Trigger: LOW = Toca, HIGH = Desliga)
#define PIN_LED_VERDE   D3   // GPIO 5  (LED Verde: HIGH = Aceso)
#define PIN_LED_VERM    D4   // GPIO 4  (LED Vermelho: HIGH = Aceso)

#endif
