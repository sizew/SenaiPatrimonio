# SENAI Patrimônio

Sistema web para controle de patrimônio e uso de equipamentos em laboratórios. Integra painel da Secretaria, abertura de turno por crachá RFID e retirada de equipamentos pelo QR Code.

## Apresentação ao vivo

### Antes da reunião

1. No computador servidor, conecte o leitor ESP8266 e os celulares à mesma rede Wi-Fi. Para o QR funcionar no celular, use o IP de rede do computador, não `localhost`.
2. Confira o IP do computador com `ipconfig`. Atualize `SERVER_URL` em `esp8266/leitor_rfid/config.h` para `http://<IP_DO_COMPUTADOR>:5000/api/rfid/leitura` e confira o `LAB_ID`.
3. Prepare a base inicial:

   ```powershell
   python backend/inicializar_banco.py
   ```

   **Este comando apaga os dados atuais** e recria a conta da Secretaria e sete laboratórios padrão. Professores, crachás, patrimônios e histórico começam vazios.

4. Instale as dependências do servidor, se necessário:

   ```powershell
   python -m pip install Flask
   ```

5. Inicie o servidor:

   ```powershell
   python backend/app.py
   ```

6. Se o Firewall do Windows perguntar, permita conexões na rede privada para que os celulares e o ESP8266 acessem a porta 5000.

### Entrar no painel

No computador, abra `http://localhost:5000`. Na Secretaria, entre com:

- **E-mail:** `secretaria@senai.br`
- **Senha inicial:** `senai123`

Use **Alterar senha** no cabeçalho antes de cadastrar informações reais.

### Roteiro sugerido

1. **Cadastre um professor:** em *Professores Cadastrados*, clique em **Pré-cadastrar** e informe nome e e-mail.
2. **Cadastre um equipamento:** em *Cadastrar Patrimônio*, informe identificador, categoria, descrição e laboratório. Para seguir este roteiro, use `PC-01`.
3. **Vincule um crachá:** aproxime um crachá ainda não cadastrado do leitor. Quando aparecer na fila, use **Vincular** na linha do professor.
4. **Abra o turno:** aproxime novamente o crachá vinculado. O laboratório ficará em uso.
5. **Gere o QR:** no painel, abra **QR dos PCs**. O gerador aproveita o endereço usado para abrir a página. Se estiver usando `localhost`, informe no campo o IP de rede do computador servidor. Imprima a etiqueta de `PC-01`.
6. **Registre um aluno:** leia o QR com um celular conectado à mesma rede, informe o nome e confirme. A cautela aparecerá no painel.
7. **Mostre os bloqueios:** tente registrar outra pessoa no mesmo PC e o mesmo nome em outro computador; as duas tentativas devem ser recusadas.
8. **Encerre o turno:** aproxime novamente o crachá. As cautelas ativas serão devolvidas e aparecerão no histórico.

Para encerrar o servidor, volte ao terminal e pressione `Ctrl+C`.

## Requisitos e execução

- Python 3.9 ou superior
- Flask (`python -m pip install Flask`)
- Arduino IDE e biblioteca MFRC522, para gravar o firmware no ESP8266

O servidor atende em `http://localhost:5000` e escuta também na rede local. Para abrir o painel em outro computador, use `http://<IP_DO_SERVIDOR>:5000`.

## Configuração do ESP8266

Crie `esp8266/leitor_rfid/config.h` localmente com os dados da rede:

```cpp
const char* WIFI_SSID     = "NOME_DO_SEU_WIFI";
const char* WIFI_PASSWORD = "SENHA_DO_SEU_WIFI";
const char* SERVER_URL    = "http://<IP_DO_COMPUTADOR>:5000/api/rfid/leitura";
const int LAB_ID          = 1;
```

Esse arquivo contém credenciais e é ignorado pelo Git. Conecte o MFRC522 ao WeMos D1 R1:

| MFRC522 | WeMos D1 R1 |
|---|---|
| RST | D9 (GPIO 2) |
| SDA / SS | D10 (GPIO 15) |
| MOSI | D11 (GPIO 13) |
| MISO | D12 (GPIO 12) |
| SCK | D13 (GPIO 14) |
| VCC | 3.3V — nunca use 5V |
| GND | GND |

Selecione **LOLIN(WEMOS) D1 R1** na Arduino IDE e grave `leitor_rfid.ino`.

## O que o sistema faz

- Só permite retirada de equipamento previamente cadastrado.
- Só permite retirada durante um turno aberto no laboratório associado ao equipamento.
- Impede que um computador ou aluno tenha mais de uma cautela ativa.
- Encerra as cautelas do laboratório quando o professor fecha o turno.
- Exige sessão autenticada da Secretaria para as operações administrativas. As senhas são armazenadas com hash.

O registro por QR e a rota de leitura do ESP8266 são acessíveis na rede local para atender aos fluxos de aluno e hardware. Não exponha o servidor diretamente à internet. A organização deve definir aviso de privacidade, base legal e prazo de retenção dos dados antes de usar informações pessoais reais.

## Estrutura

```text
backend/app.py                     API Flask e interface servida pelo backend
backend/inicializar_banco.py       Reinicia a base com Secretaria e laboratórios padrão
backend/database/patrimonio.db     Banco local SQLite, ignorado pelo Git
frontend/                          Painel, ativação de crachás e gerador de QR
esp8266/leitor_rfid/leitor_rfid.ino Firmware do leitor RFID
```

## Licença

Projeto educacional e institucional do SENAI-SP.
