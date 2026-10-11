# 🏢 SENAI Patrimônio

> **Sistema Inteligente de Controle de Patrimônio e Rastreabilidade de Laboratórios**  
> Integração de Hardware IoT (ESP8266 + RFID) com Aplicação Web em Tempo Real e Auto-registro via QR Code Mobile.

---

## 📌 Visão Geral

O **SENAI Patrimônio** foi desenvolvido para solucionar a rastreabilidade e a gestão do uso de computadores e equipamentos em laboratórios educacionais. Ele substitui pranchetas e registros manuais por um fluxo automatizado em três etapas:

1. **Abertura do Turno pelo Docente:** O professor aproxima seu crachá RFID no leitor instalado na sala, abrindo o turno de aula e liberando os computadores para uso.
2. **Auto-registro do Aluno via QR Code:** O aluno aponta a câmera do celular para o QR Code fixado no monitor do computador e informa seu nome para vincular o uso da máquina.
3. **Encerramento Automático:** Ao final da aula, o professor aproxima novamente o crachá no leitor. O turno é finalizado e todos os computadores da sala são devolvidos automaticamente, gerando um histórico auditável.

---

## 🛠️ Tecnologias Utilizadas

| Camada | Tecnologia | Detalhes |
|---|---|---|
| **Backend** | Python 3 + Flask | API REST, SQLite3, CORS habilitado |
| **Frontend** | HTML5, Tailwind CSS, JS (ES6+) | Painel responsivo, polling em tempo real a cada 2.5s |
| **Hardware** | ESP8266 (WeMos D1 R1) | Conexão Wi-Fi, HTTPClient com timeout de 3.5s |
| **RFID** | Leitor MFRC522 (13.56 MHz) | Comunicação SPI com a placa microcontroladora |
| **Etiquetas / QR** | QRCode.js | Gerador de etiquetas de bancada com URL de auto-registro |

---

## 📁 Estrutura do Projeto

```text
senai-patrimonio/
├── iniciar_servidor.bat          # Script de inicialização rápida no Windows
├── README.md                     # Documentação geral do projeto
├── README_DEMO.md                # Roteiro passo a passo para demonstração à gestão
├── .gitignore                    # Arquivos e diretórios ignorados pelo Git
│
├── backend/                      # Camada de Serviços e Banco de Dados
│   ├── app.py                    # API Flask, rotas REST e servidor HTTP (:5000)
│   ├── seed_demo.py              # Script para reset e carga inicial de demonstração
│   ├── test_demo.py              # Bateria com 13 testes automatizados
│   └── database/
│       └── patrimonio.db         # Banco de dados local SQLite3 (ignorado no Git)
│
├── esp8266/                      # Código do Dispositivo IoT
│   └── leitor_rfid/
│       ├── leitor_rfid.ino       # Firmware Arduino para o WeMos D1 R1 + MFRC522
│       ├── config.example.h      # Modelo limpo de configuração de rede/servidor
│       └── config.h              # Credenciais locais (Wi-Fi/IP - ignorado no Git)
│
└── frontend/                     # Interface do Usuário (Single-Page / Web App)
    ├── index.html                # Painel de Controle (Secretaria e Docente)
    ├── ativar.html               # Tela de auto-ativação de crachás
    ├── qr_generator.html         # Gerador e impressor de etiquetas QR Code (A4)
    ├── css/
    │   └── styles.css            # Estilos complementares
    ├── js/
    │   └── main.js               # Lógica do painel, modais e sincronização periódica
    └── assets/
        └── img/                  # Logotipos SENAI e imagens de fundo
```

---

## 🚀 Como Executar o Projeto

### 1. Pré-requisitos
* **Python 3.9+** instalado no computador.
* Dependências Python instaladas:
  ```bash
  pip install flask flask-cors
  ```
* **Arduino IDE** (caso vá gravar o firmware no microcontrolador ESP8266) com a biblioteca `MFRC522`.

---

### 2. Inicializando o Backend e Banco de Dados

1. **Popular o banco de dados com dados de teste:**
   ```bash
   python backend/seed_demo.py
   ```
   *Cria a Secretaria padrão, dois professores (um com crachá e um para vincular ao vivo) e 6 computadores no Lab. Informática 1.*

2. **Iniciar o Servidor:**
   Dê duplo clique em `iniciar_servidor.bat` ou execute no terminal:
   ```bash
   python backend/app.py
   ```
   O servidor estará ativo em:
   * **Localmente:** `http://localhost:5000`
   * **Na rede local:** `http://<SEU_IP_LOCAL>:5000`

---

### 3. Acessando a Aplicação Web

Abra o navegador em `http://localhost:5000` e utilize as credenciais padrão:

* **Secretaria (Gestão):** `secretaria@senai.br` / senha: `senai123`
* **Professor (Gabriel Viana):** `gabriel.viana@docente.senai.br` / senha: `senai123`

---

### 4. Configurando o Hardware (ESP8266 WeMos D1 R1)

1. Entre na pasta `esp8266/leitor_rfid/`.
2. Se ainda não tiver o arquivo `config.h`, copie o modelo:
   ```bash
   cp config.example.h config.h
   ```
3. Edite o `config.h` com os dados da sua rede e o IP da sua máquina:
   ```cpp
   const char* WIFI_SSID     = "NOME_DO_SEU_WIFI";
   const char* WIFI_PASSWORD = "SENHA_DO_SEU_WIFI";
   const char* SERVER_URL    = "http://<IP_DO_COMPUTADOR>:5000/api/rfid/leitura";
   const int LAB_ID          = 1;
   ```
4. Conecte o Leitor RFID MFRC522 aos pinos do WeMos D1 R1:
   * `RST` ➜ **D9** (GPIO 2)
   * `SDA / SS` ➜ **D10** (GPIO 15)
   * `MOSI` ➜ **D11** (GPIO 13)
   * `MISO` ➜ **D12** (GPIO 12)
   * `SCK` ➜ **D13** (GPIO 14)
   * `3.3V` ➜ **3.3V** *(Atenção: Nunca ligar em 5V)*
   * `GND` ➜ **GND**
5. Faça o upload pelo Arduino IDE selecionando a placa **LOLIN(WEMOS) D1 R1**.

---

## 🛡️ Regras de Negócio e Segurança

* **Bloqueio de Máquinas Inexistentes:** O sistema não cria patrimônios desconhecidos via QR Code; apenas máquinas previamente cadastradas são aceitas.
* **Validação de Entrada:** O nome do aluno deve conter no mínimo 3 caracteres válidos e letras reais.
* **Prevenção de Uso Concomitante:**
  * O mesmo computador não pode ser retirado por dois alunos ao mesmo tempo.
  * O mesmo aluno não pode registrar mais de um computador simultaneamente.
* **Controle Estrito de Turno:** O QR Code só permite retiradas se o laboratório ao qual a máquina pertence estiver com turno ativo (`Em Uso`).

---

## 🧪 Testes Automatizados

O projeto conta com uma suíte de testes integrada cobrindo leitura RFID, tentativas de fraude, regras de QR e ciclo de turnos:

```bash
python backend/test_demo.py
```
*Executa 13 cenários de teste automatizados com validação de status HTTP e regras de negócio.*

---

## 📄 Licença

Projeto desenvolvido para fins educacionais e de demonstração institucional — SENAI-SP.
