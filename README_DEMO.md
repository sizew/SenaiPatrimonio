# 🎯 ROTEIRO DE DEMONSTRAÇÃO — SENAI PATRIMÔNIO

Guia prático para a apresentação da Prova de Conceito (PoC) para a gestão do SENAI.

---

## 📋 Checklist Pré-Demonstração

Antes de chamar a equipe da gestão, confira todos os itens abaixo:

- [ ] **Rede Wi-Fi:** O computador do servidor e o ESP8266 devem estar conectados na **mesma rede** (ex: Hotspot do celular `iPhone_G` ou rede local).
- [ ] **IP do Servidor:** Verifique o IP do seu computador abrindo o terminal e digitando `ipconfig`. Certifique-se de que o arquivo `esp8266/leitor_rfid/config.h` possui o IP correto na constante `SERVER_URL`.
- [ ] **Banco de Dados Limpo:** Execute o comando de reset para garantir que o ambiente comece perfeito:
  ```powershell
  python backend/seed_demo.py
  ```
- [ ] **Servidor Flask Rodando:** Dê duplo clique no arquivo `iniciar_servidor.bat` (ou execute `python backend/app.py`). O servidor estará ativo em `http://localhost:5000` (e acessível pelo IP na rede).
- [ ] **Hardware Conectado:** O WeMos D1 R1 deve estar alimentado via USB. Abra o Monitor Serial da Arduino IDE (115200 baud) para confirmar a mensagem `[OK] Wi-Fi Conectado com Sucesso!`.
- [ ] **Crachás em Mãos:**
  - Crachá 1: **Professor Gabriel Viana** (UID: `1758E500` — já cadastrado).
  - Crachá 2: **Crachá Novo / Desconhecido** (qualquer outro cartão ou chaveiro para demonstrar a vinculação ao vivo).
- [ ] **Etiquetas QR Code:** Abra a página `http://localhost:5000/qr_generator.html` no navegador do computador ou imprima as etiquetas dos computadores `PC-01` a `PC-06`.

---

## 🎭 Passo a Passo da Apresentação (Roteiro)

### 1. Abertura e Painel da Secretaria
1. Abra no navegador: `http://localhost:5000`
2. Faça login com a conta da Secretaria:
   - **E-mail:** `secretaria@senai.br`
   - **Senha:** `senai123`
3. Destaque para a gestão:
   - O painel possui atualização em tempo real (sem precisar apertar F5).
   - Mostre os KPIs no topo: laboratórios livres, 0 computadores em uso, e 6 PCs cadastrados prontos.
   - Mostre o bloco **"Salas & Laboratórios em Tempo Real"** indicando que o *Lab. Informática 1* está livre.

---

### 2. Demonstração: Detecção de Crachá Novo e Vínculo com 1 Clique
> *Objetivo: Demonstrar como novos professores recebem crachás sem complicação técnica.*

1. Aproxime o **Crachá 2** (desconhecido) da antena do leitor RFID.
2. Observe a tela da Secretaria:
   - Em menos de 2 segundos, o crachá surge automaticamente no card **"Fila de Crachás para Ativação"**.
   - No **"Monitor de Leituras em Tempo Real"**, aparece o registro do toque físico.
3. Clique no botão de vincular do professor **Felipe Fiot** (que está com status *Aguardando Crachá*).
4. O sistema vincula o crachá instantaneamente ao professor.

---

### 3. Início da Aula: Professor Abre o Turno
> *Objetivo: Demonstrar a liberação da sala e dos patrimônios pelo crachá docente.*

1. O professor **Gabriel Viana** aproxima seu crachá (`1758E500`) do leitor RFID.
2. Na tela da Secretaria (e no painel do próprio docente):
   - O card do *Lab. Informática 1* muda imediatamente para **"Em Aula"** (borda vermelha destacada).
   - Exibe: **"Resp: Gabriel Viana"** e o horário de início da aula.
   - Os computadores da sala ficam prontos para receber o registro dos alunos.

---

### 4. Aluno Vincula seu Computador pelo QR Code
> *Objetivo: Mostrar a experiência rápida e mobile do aluno na bancada.*

1. No celular (ou em uma aba anônima), aponte a câmera para o QR Code do **PC-01** (ou acesse diretamente `http://<IP_DO_PC>:5000/retirar/PC-01`).
2. A tela mobile do SENAI abre com o título **"Computador PC-01 · Lab. Informática 1 · Prof. Gabriel Viana"**.
3. O aluno digita seu nome completo (ex: `Lucas Mendes`) e toca em **"Confirmar Uso do PC"**.
4. A tela do celular exibe confirmação verde: *PC Vinculado com Sucesso!*
5. Olhe para o painel da Secretaria no projetor/computador:
   - No card do laboratório, em **"PCs em Uso (1)"**, aparece instantaneamente: **Lucas Mendes (PC-01)** com o horário da retirada.

---

### 5. Demonstração de Segurança e Regras do Sistema
> *Objetivo: Mostrar que o sistema é robusto contra fraudes ou confusões.*

1. **Tentativa de pegar o mesmo PC:** Outro aluno tenta escanear o QR do `PC-01`.
   - O sistema bloqueia informando: *"Este PC já está em uso por Lucas Mendes"*.
2. **Tentativa do mesmo aluno pegar dois PCs:** O aluno `Lucas Mendes` tenta registrar o `PC-02`.
   - O sistema bloqueia informando: *"Você já possui o computador PC-01 em uso ativo"*.
3. **Registro correto do segundo PC:** Registre outro aluno (ex: `Mariana Souza`) no `PC-02`.
   - O painel exibe imediatamente ambos os alunos ativos.

---

### 6. Fim da Aula: Encerramento do Turno e Devolução Automática
> *Objetivo: Mostrar que o professor encerra tudo com um único toque físico.*

1. Ao final da aula, o professor **Gabriel Viana** aproxima o crachá novamente no leitor RFID.
2. O sistema reconhece a ação de toggle:
   - O status do laboratório volta para **"Livre"**.
   - Todas as cautelas ativas dos computadores (`PC-01`, `PC-02`) são encerradas automaticamente com a data e hora da devolução.
   - Todos os patrimônios voltam para o status **"Disponível"**.
3. Se um aluno tentar ler o QR agora, a tela informa: *"Nenhum Turno Ativo. Aguarde o professor abrir a aula."*

---

### 7. Rastreabilidade e Auditoria para a Gestão
> *Objetivo: Apresentar o histórico auditável do patrimônio.*

1. No painel da Secretaria, role até a seção **"Rastreabilidade & Histórico de Uso"**.
2. Mostre para a gestão o registro completo:
   - Nome do aluno que utilizou a máquina.
   - Número de patrimônio do PC.
   - Professor responsável que estava em sala.
   - Horário exato de início e horário exato de devolução.
   - Status: *Devolvida*.

---

## 🧪 Testes Automatizados

Caso queira validar todo o funcionamento dos endpoints via código antes da apresentação:

```powershell
python backend/test_demo.py
```

Esse script testa 13 cenários críticos (leitura de tag nova, tag não docente, bloqueio sem turno, bloqueio de nome curto, bloqueio de aluno duplo, encerramento de turno, etc.) e garante que 100% dos testes passem.
