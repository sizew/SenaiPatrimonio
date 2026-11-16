# Documentação final — Sprint 3

## Identificação

**Projeto:** SENAI Patrimônio — Registro de Uso dos Computadores  
**Escopo:** piloto de uma sala de informática.  
**Demonstração prevista:** 01/12/2026.  
**Integrantes:** Felipe Santos Silva; Otávio Silva Garbin; Gabriel Viana dos Reis; Eduardo Gandra.  
**Repositório:** https://github.com/sizew/SenaiPatrimonio

## TAP consolidado

### Contexto e problema

A equipe precisa saber quem está usando cada computador da sala de informática e relacionar esse uso à sala e ao turno da aula. Sem um registro central, o acompanhamento e a consulta ao histórico dependem de conferência manual.

### Justificativa e objetivos

O sistema combina RFID, QR Code e painel web para acompanhar o uso dos computadores. O objetivo geral é registrar quem está usando cada computador durante o turno. Os objetivos específicos são identificar o professor responsável pelo turno, permitir que o aluno registre o computador por QR, vincular o registro à sala e aos horários de início e encerramento e disponibilizar o acompanhamento e histórico à Secretaria.

### Usuários e stakeholders

- **Secretaria:** prepara cadastros e consulta uso e histórico.
- **Professor:** inicia e encerra o turno usando crachá RFID.
- **Aluno:** lê o QR do computador e informa o nome.
- **Coordenação/gestão:** acompanha a operação do piloto.
- **Equipe de projeto:** desenvolve e demonstra o sistema.

### Escopo

**Incluído:** uma sala de informática; cadastro de professor, crachá e computadores; abertura/encerramento do turno por RFID; registro de uso do computador por QR; bloqueio de duplicidades; painel e histórico com horários.

**Fora do escopo:** fechadura eletrônica; identificação automática de todos que entram na sala; login individual do aluno; uso piloto em várias salas; chamados de manutenção; limpeza; exportação de relatórios.

### Premissas, restrições e riscos

- Servidor, leitor ESP8266 e celular alcançam o servidor na rede local.
- Cada computador está cadastrado e associado à sala; o professor tem crachá vinculado.
- O nome digitado pelo aluno não é autenticado; o sistema não comprova a identidade.
- Falha de rede, leitor ou IP incorreto pode interromper o fluxo; conferir conectividade antes da aula.
- O inicializador apaga cadastros e histórico. Não executá-lo quando os dados precisarem ser preservados.
- Antes de inserir dados reais, a unidade deve definir aviso de privacidade, finalidade, acesso e prazo de retenção. Esta documentação não afirma conformidade legal completa.

## Requisitos e critérios de aceite

| ID | Requisito | Critério de aceite |
|---|---|---|
| RF01 | Abrir/encerrar o turno por RFID | Crachá do professor inicia o turno; nova leitura encerra o turno e finaliza registros ativos. |
| RF02 | Preparar professor, crachá e computadores | Secretaria autenticada cadastra os dados e associa o crachá ao professor. |
| RF03 | Registrar uso por QR | Com turno ativo, o QR do computador abre o formulário; aluno informa o nome e o sistema associa PC, sala, professor e horário. |
| RF04 | Evitar uso simultâneo duplicado | Um PC não aceita dois usuários ativos e um nome não fica ativo em dois PCs. |
| RF05 | Acompanhar situação e histórico | Painel atualiza o uso atual; histórico apresenta início, fim e situação do registro. |
| RNF01 | Acesso administrativo | Operações administrativas exigem login da Secretaria; senha é armazenada com hash. |
| RNF02 | Acesso em rede local | QR funciona no celular usando o IP local do servidor, não `localhost`. |

## Histórias de usuário e backlog

1. **Secretaria:** quero cadastrar professor, crachá e computadores para preparar a sala. **Aceite:** cadastros aparecem no sistema.
2. **Professor:** quero iniciar e encerrar o turno com RFID para registrar a aula. **Aceite:** leituras válidas alternam o turno e registram os eventos.
3. **Aluno:** quero escanear o QR do computador em uso para associá-lo ao meu nome. **Aceite:** uso ativo aparece no computador correto e duplicidades são bloqueadas.
4. **Secretaria/gestão:** quero ver os computadores em uso e consultar quando o uso terminou. **Aceite:** painel e histórico mostram início, fim e situação atualizados.

**Prioridade alta:** autenticação da Secretaria, cadastros, ciclo RFID, registro QR, prevenção de duplicidade e histórico.  
**Melhorias futuras:** login institucional do aluno; check-in de todas as pessoas na sala; expansão para outras salas; chamados, limpeza e exportação de relatórios.

## MVP e funcionalidades

Fluxo do MVP: Secretaria cadastra professor e computadores → professor abre turno por RFID → aluno escaneia o QR do computador e informa o nome → painel mostra a associação → professor encerra turno → sistema grava o horário de encerramento e exibe o evento no histórico.

O painel da Secretaria contém cadastros, estado do turno, computadores em uso e histórico. O gerador imprime QR para os computadores. A interface mostra horário de início e encerramento; o histórico é recarregado durante a sessão e após finalização manual/turno.

## Arquitetura e tecnologias

- **ESP8266 + MFRC522:** lê UID do crachá e envia `tag_uid`/`lab_id` por HTTP.
- **Flask/Python:** serve telas, API e regras de negócio.
- **SQLite:** armazena cadastros, eventos RFID, sala, equipamentos e registros de uso.
- **HTML/CSS/JavaScript:** painel web e formulário QR no celular.

Integração: RFID → API Flask → SQLite; navegador/celular → QR → API Flask → SQLite → atualização do painel/histórico. O piloto usa uma sala e rede local.

## Problemas e correções

- `HTTP_TIMEOUT_MS` ausente no firmware foi definido; a equipe relatou duas compilações/testes da correção, sem logs anexados.
- QR com `localhost` não abre em outro dispositivo; usar IP do servidor na rede local. A equipe confirmou que o QR abriu após essa configuração.
- A interface usava linguagem de retirada/devolução; foi alinhada a registro de uso, preservando nomes internos antigos do banco/API para evitar migração.
- O histórico não era carregado novamente após o fim do uso; agora tem atualização periódica e imediata após encerramento, com horários de início e fim.

## Protótipo e evidência visual

A interface HTML implementada é o protótipo funcional. O arquivo Figma recebido estava sem link acessível; anexar URL ou capturas da tela caso seja exigido como artefato separado.

## Referências e limites

Materiais iniciais da Sprint 1 descrevem Forves/SalaOS e um escopo amplo com portas, limpeza e manutenção. Essas funções não são apresentadas como implementadas no SENAI Patrimônio; ficam como possibilidades futuras. O código está em `Codigo-Fonte/`; alterações locais ainda não foram publicadas no remoto.
