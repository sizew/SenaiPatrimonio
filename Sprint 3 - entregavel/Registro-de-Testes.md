# Registro de testes — Sprint 3

## Execução anterior à última mudança de interface

Ambiente: cliente de testes Flask e banco SQLite temporário; a base do usuário não foi alterada. Resultado registrado: **17 aprovados, 0 reprovados**. Os testes simularam chamadas HTTP e leitura RFID pela rota Flask; não utilizaram placa/câmera reais.

| ID | Teste | Resultado registrado | Status |
|---|---|---|---|
| T01 | Abrir a página principal | HTTP 200 | Aprovado |
| T02 | Acessar API administrativa sem sessão | HTTP 401 | Aprovado |
| T03 | Login Secretaria | HTTP 200 e sessão criada | Aprovado |
| T04 | Base limpa | Uma sala de informática | Aprovado |
| T05 | Cadastrar professor | HTTP 201 | Aprovado |
| T06 | Cadastrar PC-01 | HTTP 201 | Aprovado |
| T07 | Cadastrar PC-02 | HTTP 201 | Aprovado |
| T08 | Vincular UID RFID válido | HTTP 200 | Aprovado |
| T09 | RFID inicia turno | Ação `aberto` | Aprovado |
| T10 | Abrir URL `/uso/PC-01` | Formulário HTTP 200 | Aprovado |
| T11 | Registrar aluno no PC-01 | HTTP 200 | Aprovado |
| T12 | Segundo usuário no PC ativo | HTTP 409, bloqueado | Aprovado |
| T13 | Mesmo aluno em outro PC ativo | HTTP 409, bloqueado | Aprovado |
| T14 | Consultar estado da sala | Aluno e PC associados | Aprovado |
| T15 | RFID encerra turno | Ação `encerrado` | Aprovado |
| T16 | Consultar histórico encerrado | Registro persistido com horário final | Aprovado |
| T17 | Logout Secretaria | Sessão encerrada | Aprovado |

## Validações manuais informadas pela equipe

| ID | Funcionalidade | Teste realizado | Resultado informado | Status |
|---|---|---|---|---|
| T18 | Atualização do histórico | Conferir a tabela após encerrar o uso e verificar o horário de encerramento. | O usuário confirmou que a tela está correta e mostra o horário de encerramento. | Aprovado — confirmação do usuário |
| T19 | Integração RFID, servidor e QR | Executar o fluxo integrado no ambiente da equipe, incluindo leitura RFID, uso do QR e consulta da tela. | O usuário informou que o teste integrado foi realizado. Detalhes de aparelho, passos observados, data e evidências não foram fornecidos. | Aprovado — teste informado pelo usuário |

## Limites das evidências manuais

O usuário confirmou que o QR abriu usando o IP local do servidor e informou que o fluxo integrado foi testado. A data, o modelo do leitor/celular, os passos detalhados e capturas/logs não foram registrados. A equipe também informou que compilou/testou o firmware duas vezes, sem logs anexados. Os resultados manuais acima são registrados como relato da equipe, sem evidência técnica anexada.
