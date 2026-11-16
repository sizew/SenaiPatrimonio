# SENAI Patrimônio

Sistema web integrado a RFID para registrar o uso dos computadores da sala de informática. O professor inicia ou encerra o turno com o crachá; o aluno lê o QR Code do computador e informa seu nome. O painel associa aluno, computador, sala, professor e horário para acompanhamento e histórico.

## Escopo desta versão

- Piloto direcionado a uma sala de informática.
- Registro do professor responsável pelo turno via RFID.
- Registro de quem está usando cada computador via QR Code.
- Acompanhamento do uso atual e consulta ao histórico pela Secretaria.
- O QR pede o nome digitado pelo aluno; essa versão não autentica a identidade do aluno.
- Não controla fechaduras nem registra automaticamente todas as pessoas que entram na sala.
- Empréstimo de equipamento para fora da sala, chamados de manutenção, limpeza e app com login individual ficam fora do escopo desta versão.

## Requisitos

- Python 3.9 ou superior
- Flask (`python -m pip install Flask`)
- Arduino IDE e biblioteca MFRC522 para gravar o ESP8266, se for demonstrar o RFID físico
- Computador servidor, ESP8266 e celular conectados à mesma rede local

## Preparação e início

1. Abra PowerShell na pasta do projeto e instale o Flask, se necessário:

   ```powershell
   python -m pip install Flask
   ```

2. Para iniciar uma base limpa, execute:

   ```powershell
   python backend/inicializar_banco.py
   ```

   **Atenção:** esse comando apaga os usuários, crachás, equipamentos e históricos existentes e recria a conta da Secretaria e a sala de informática. Não execute se quiser preservar dados cadastrados.

3. Inicie o servidor:

   ```powershell
   python backend/app.py
   ```

4. No computador servidor, abra `http://localhost:5000`. Para celulares na rede, use `http://<IP_DO_SERVIDOR>:5000`.

## Conta inicial da Secretaria

- E-mail: `secretaria@senai.br`
- Senha inicial: `senai123`

Altere a senha inicial antes de inserir dados reais.

## Preparação do ESP8266

Crie localmente `esp8266/leitor_rfid/config.h` com os dados da rede e o endereço do servidor. O arquivo é ignorado pelo Git; não compartilhe credenciais.

```cpp
const char* WIFI_SSID     = "NOME_DO_SEU_WIFI";
const char* WIFI_PASSWORD = "SENHA_DO_SEU_WIFI";
const char* SERVER_URL    = "http://<IP_DO_SERVIDOR>:5000/api/rfid/leitura";
const int LAB_ID          = 1;
```

No Arduino IDE, selecione **LOLIN(WEMOS) D1 R1**. Ligue o MFRC522 em 3.3V (nunca 5V): RST→D9, SDA/SS→D10, MOSI→D11, MISO→D12, SCK→D13, VCC→3.3V e GND→GND.

## Roteiro do fluxo principal

1. Entre no painel como Secretaria.
2. Cadastre o professor e o computador (por exemplo, `PC-01`) na sala de informática.
3. Vincule o crachá do professor.
4. Grave e conecte o ESP8266 ao servidor. A leitura do crachá inicia o turno.
5. Abra **QR dos PCs** e gere/imprima as etiquetas dos computadores cadastrados. Se abrir o gerador por `localhost`, informe o IP do servidor para os celulares.
6. No celular conectado à mesma rede, leia o QR do computador em uso e informe o nome do aluno.
7. Confira no painel o aluno, computador, sala, professor responsável e início do uso.
8. Leia novamente o crachá para encerrar o turno; os registros ativos são finalizados e passam ao histórico.

Para encerrar o servidor, use `Ctrl+C` no terminal.

## Regras do sistema

- Só computador cadastrado e associado à sala pode receber registro de uso.
- O turno da sala deve estar ativo para registrar um computador em uso.
- Cada computador só pode ter um usuário registrado ao mesmo tempo.
- Cada nome de aluno só pode estar associado a um computador em uso ao mesmo tempo.
- O encerramento do turno finaliza os registros ativos daquela sala.
- O histórico exibe o início e o encerramento de cada registro; a tela da Secretaria atualiza automaticamente durante a sessão.
- Operações administrativas exigem sessão da Secretaria; senhas são armazenadas com hash.

## Privacidade e rede

O nome do aluno é digitado no formulário e não é autenticado nesta versão. Use apenas dados de teste durante demonstrações públicas. A unidade deve definir aviso de privacidade, base legal, controle de acesso e prazo de retenção antes de usar dados pessoais reais. O serviço foi preparado para rede local; não exponha o servidor diretamente à internet.

## Estrutura

```text
backend/app.py                     API Flask e interface servida pelo backend
backend/inicializar_banco.py       Reinicializa a base de demonstração
frontend/                          Painel, fluxo de uso e gerador de QR
esp8266/leitor_rfid/leitor_rfid.ino Firmware do leitor RFID
```

## Repositório

Código-fonte: [github.com/sizew/SenaiPatrimonio](https://github.com/sizew/SenaiPatrimonio)
