# Sprint 3 - Entrega

Pacote do SENAI Patrimônio para o piloto de uma sala de informática.

## Documentos DOCX prontos para abrir ou importar no Google Docs

- `Documentacao-Final.docx`
- `Registro-de-Testes.docx`
- `Pendencias-da-Entrega.docx`
- `Instrucoes-de-Execucao.docx`
- `LEIA-ME.docx`

Os arquivos Markdown equivalentes são mantidos como fontes editáveis. O `README.md` dentro de `Codigo-Fonte/` também permanece para orientar a execução junto ao código.

## Código-fonte

A pasta `Codigo-Fonte/` contém servidor Flask, interface web, inicializador SQLite, firmware ESP8266 e instruções de execução. A cópia local pode conter `backend/database/patrimonio.db` e `esp8266/leitor_rfid/config.h`, que são dados de execução/configuração local; não os inclua em arquivos enviados ou compartilhados. O `.gitignore` os exclui do Git, mas não de uma cópia manual da pasta.

O inicializador limpa cadastros e históricos e recria a Secretaria e uma sala de informática. Execute somente quando quiser reiniciar a base.

Repositório: https://github.com/sizew/SenaiPatrimonio. As alterações locais desta entrega ainda precisam ser publicadas no GitHub.
