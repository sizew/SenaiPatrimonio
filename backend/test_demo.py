import sys
import os

# Adiciona diretório do backend ao sys.path
sys.path.insert(0, os.path.dirname(__file__))

from app import app
from seed_demo import reset_demo

def run_tests():
    print("\n==================================================")
    print("  EXECUTANDO BATERIA DE TESTES AUTOMATIZADOS")
    print("==================================================")

    # 1. Reseta o banco para o estado padrão limpo
    reset_demo()

    client = app.test_client()
    erros = 0
    sucessos = 0

    def assert_test(nome, condicao, detalhe=""):
        nonlocal erros, sucessos
        if condicao:
            print(f" [PASS] {nome}")
            sucessos += 1
        else:
            print(f" [FAIL] {nome} -> {detalhe}")
            erros += 1

    print("\n--- 1. TESTES DE RFID ---")

    # 1.1 Tag desconhecida -> Deve salvar como pendente
    res = client.post('/api/rfid/leitura', json={'tag_uid': 'AA11BB22', 'lab_id': 1})
    data = res.get_json()
    assert_test("Tag desconhecida retorna 'pendente'", res.status_code == 200 and data.get('status') == 'pendente', f"status={res.status_code}, data={data}")

    # 1.2 Tag não-docente (ex: cadastrada como secretaria)
    # Cadastra tag para a secretaria e passa no leitor
    with app.app_context():
        import sqlite3
        conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), 'database', 'patrimonio.db'))
        conn.execute("UPDATE usuarios SET tag_rfid='SEC9999' WHERE email='secretaria@senai.br'")
        conn.commit()
        conn.close()

    res = client.post('/api/rfid/leitura', json={'tag_uid': 'SEC9999', 'lab_id': 1})
    data = res.get_json()
    assert_test("Tag não-docente retorna 'negado'", res.status_code == 200 and data.get('status') == 'negado', f"status={res.status_code}, data={data}")

    print("\n--- 2. TESTES DE RETIRADA ANTES DO TURNO ---")

    # 2.1 PC inexistente -> 404
    res = client.post('/api/retirar/PC-999', json={'nome_usuario': 'Carlos Aluno'})
    data = res.get_json()
    assert_test("PC inexistente retorna 404", res.status_code == 404, f"status={res.status_code}, data={data}")

    # 2.2 Nome inválido (< 3 caracteres ou sem letras) -> 400
    res = client.post('/api/retirar/PC-01', json={'nome_usuario': '  '})
    assert_test("Nome vazio retorna 400", res.status_code == 400)
    res = client.post('/api/retirar/PC-01', json={'nome_usuario': 'Al'})
    assert_test("Nome curto (<3 letras) retorna 400", res.status_code == 400)

    # 2.3 PC cadastrado mas sem turno aberto -> 403
    res = client.post('/api/retirar/PC-01', json={'nome_usuario': 'Carlos Aluno'})
    data = res.get_json()
    assert_test("Retirada sem turno aberto retorna 403", res.status_code == 403, f"status={res.status_code}, data={data}")

    print("\n--- 3. TESTE DE ABERTURA DE TURNO ---")

    # 3.1 Professor Gabriel passa crachá cadastrado (1758E500) -> abre turno
    res = client.post('/api/rfid/leitura', json={'tag_uid': '1758E500', 'lab_id': 1})
    data = res.get_json()
    assert_test("Professor passa crachá -> turno aberto", res.status_code == 200 and data.get('acao') == 'aberto', f"status={res.status_code}, data={data}")

    print("\n--- 4. TESTES DE CAUTELA DO PC COM TURNO ABERTO ---")

    # 4.1 Aluno 1 retira PC-01 -> Sucesso (200)
    res = client.post('/api/retirar/PC-01', json={'nome_usuario': 'Lucas Mendes'})
    data = res.get_json()
    assert_test("Aluno retira PC-01 com sucesso", res.status_code == 200 and data.get('status') == 'ok', f"status={res.status_code}, data={data}")

    # 4.2 Outro aluno tenta retirar o mesmo PC-01 -> 409 (Já em uso)
    res = client.post('/api/retirar/PC-01', json={'nome_usuario': 'Mariana Souza'})
    data = res.get_json()
    assert_test("Tentativa de retirar PC já ocupado retorna 409", res.status_code == 409, f"status={res.status_code}, data={data}")

    # 4.3 Mesmo aluno tenta retirar um segundo computador (PC-02) -> 409 (Aluno em 2 PCs)
    res = client.post('/api/retirar/PC-02', json={'nome_usuario': 'Lucas Mendes'})
    data = res.get_json()
    assert_test("Mesmo aluno em dois PCs ativos retorna 409", res.status_code == 409, f"status={res.status_code}, data={data}")

    # 4.4 Outra aluna (Mariana) retira PC-02 -> Sucesso (200)
    res = client.post('/api/retirar/PC-02', json={'nome_usuario': 'Mariana Souza'})
    data = res.get_json()
    assert_test("Mariana retira PC-02 com sucesso", res.status_code == 200 and data.get('status') == 'ok', f"status={res.status_code}, data={data}")

    print("\n--- 5. TESTE DE ENCERRAMENTO DE TURNO ---")

    # 5.1 Professor Gabriel passa crachá novamente -> Encerra turno e devolve PCs
    res = client.post('/api/rfid/leitura', json={'tag_uid': '1758E500', 'lab_id': 1})
    data = res.get_json()
    assert_test("Professor passa crachá de novo -> turno encerrado", res.status_code == 200 and data.get('acao') == 'encerrado', f"status={res.status_code}, data={data}")

    # 5.2 Tentativa de retirar PC após encerramento do turno -> 403
    res = client.post('/api/retirar/PC-01', json={'nome_usuario': 'Beatriz Lima'})
    data = res.get_json()
    assert_test("Tentativa de retirada após turno fechado retorna 403", res.status_code == 403, f"status={res.status_code}, data={data}")

    print("\n==================================================")
    print(f"  RESULTADO DOS TESTES: {sucessos} Passaram | {erros} Falharam")
    print("==================================================\n")

    return erros == 0

if __name__ == '__main__':
    ok = run_tests()
    sys.exit(0 if ok else 1)
