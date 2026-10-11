import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(__file__), 'database', 'patrimonio.db')

def reset_demo():
    print("==================================================")
    print("  SENAI PATRIMÔNIO - RESET DO BANCO PARA DEMO")
    print("==================================================")

    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    
    # Se existir, podemos limpar as tabelas mantendo a estrutura
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Recria / Garante a existência de todas as tabelas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            tipo TEXT NOT NULL,
            tag_rfid TEXT UNIQUE,
            criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS crachas_recentes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag_uid TEXT UNIQUE NOT NULL,
            data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'Pendente',
            vinculado_a_nome TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leituras_rfid (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag_uid TEXT NOT NULL,
            usuario_nome TEXT,
            tipo_leitura TEXT,
            detalhes TEXT,
            data_hora DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS laboratorios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            localizacao TEXT,
            status TEXT DEFAULT 'Livre',
            responsavel_id INTEGER,
            responsavel_nome TEXT,
            inicio_uso DATETIME,
            FOREIGN KEY (responsavel_id) REFERENCES usuarios(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patrimonios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_patrimonio TEXT UNIQUE NOT NULL,
            descricao TEXT NOT NULL,
            categoria TEXT DEFAULT 'computador',
            laboratorio_id INTEGER,
            status TEXT DEFAULT 'Disponivel',
            FOREIGN KEY (laboratorio_id) REFERENCES laboratorios(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cautelas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patrimonio_id INTEGER NOT NULL,
            nome_usuario TEXT NOT NULL,
            responsavel_id INTEGER NOT NULL,
            laboratorio_id INTEGER NOT NULL,
            retirada_em DATETIME DEFAULT CURRENT_TIMESTAMP,
            devolucao_em DATETIME,
            status TEXT DEFAULT 'Ativa',
            FOREIGN KEY (patrimonio_id) REFERENCES patrimonios(id),
            FOREIGN KEY (responsavel_id) REFERENCES usuarios(id),
            FOREIGN KEY (laboratorio_id) REFERENCES laboratorios(id)
        )
    """)

    # Limpa todos os dados existentes para garantir estado limpo
    cursor.execute("DELETE FROM cautelas")
    cursor.execute("DELETE FROM leituras_rfid")
    cursor.execute("DELETE FROM crachas_recentes")
    cursor.execute("DELETE FROM patrimonios")
    cursor.execute("DELETE FROM laboratorios")
    cursor.execute("DELETE FROM usuarios")
    cursor.execute("DELETE FROM sqlite_sequence")

    print("[*] Tabelas limpas com sucesso.")

    # 1. Usuários da Demonstração
    # - 1 Secretaria
    # - 1 Professor COM crachá cadastrado (Gabriel Viana - UID: 1758E500)
    # - 1 Professor SEM crachá (Felipe Fiot - para demonstrar vínculo ao vivo)
    usuarios = [
        ('Secretaria SENAI', 'secretaria@senai.br', 'senai123', 'secretaria', None),
        ('Gabriel Viana', 'gabriel.viana@docente.senai.br', 'senai123', 'professor', '1758E500'),
        ('Felipe Fiot', 'felipe@docente.senai.br', 'senai123', 'professor', None)
    ]
    cursor.executemany("""
        INSERT INTO usuarios (nome, email, senha, tipo, tag_rfid)
        VALUES (?, ?, ?, ?, ?)
    """, usuarios)
    print(f"[+] {len(usuarios)} Usuários criados (1 Secretaria, 2 Professores).")

    # Registra o crachá do Gabriel como já vinculado no histórico
    cursor.execute("""
        INSERT INTO crachas_recentes (tag_uid, status, vinculado_a_nome)
        VALUES ('1758E500', 'Vinculado', 'Gabriel Viana')
    """)

    # 2. Laboratórios
    labs = [
        ('Lab. Informática 1', 'Bloco A - Sala 101'),
        ('Lab. Informática 2', 'Bloco A - Sala 102'),
        ('Lab. Redes',         'Bloco B - Sala 201'),
        ('Lab. Hardware',      'Bloco B - Sala 202'),
        ('Lab. Automação',     'Bloco C - Sala 301'),
        ('Lab. Eletrônica',    'Bloco C - Sala 302'),
        ('Lab. Maker / 3D',    'Bloco D - Sala 401'),
    ]
    cursor.executemany("INSERT INTO laboratorios (nome, localizacao, status) VALUES (?, ?, 'Livre')", labs)
    print(f"[+] {len(labs)} Laboratórios criados (todos com status 'Livre').")

    # 3. 6 Patrimônios cadastrados no Lab. Informática 1 (ID 1)
    pcs = [
        ('PC-01', 'Computador Dell OptiPlex - PC-01', 'computador', 1, 'Disponivel'),
        ('PC-02', 'Computador Dell OptiPlex - PC-02', 'computador', 1, 'Disponivel'),
        ('PC-03', 'Computador Dell OptiPlex - PC-03', 'computador', 1, 'Disponivel'),
        ('PC-04', 'Computador Dell OptiPlex - PC-04', 'computador', 1, 'Disponivel'),
        ('PC-05', 'Computador Dell OptiPlex - PC-05', 'computador', 1, 'Disponivel'),
        ('PC-06', 'Computador Dell OptiPlex - PC-06', 'computador', 1, 'Disponivel'),
    ]
    cursor.executemany("""
        INSERT INTO patrimonios (numero_patrimonio, descricao, categoria, laboratorio_id, status)
        VALUES (?, ?, ?, ?, ?)
    """, pcs)
    print(f"[+] {len(pcs)} PCs cadastrados no Lab. Informática 1 (PC-01 a PC-06).")

    conn.commit()
    conn.close()

    print("\n[OK] BANCO DE DADOS PREPARADO COM SUCESSO PARA A DEMO!")
    print("--------------------------------------------------")
    print("Credenciais de Teste:")
    print("  - Secretaria: secretaria@senai.br / senai123")
    print("  - Prof. Gabriel (com crachá 1758E500): gabriel.viana@docente.senai.br / senai123")
    print("  - Prof. Felipe (sem crachá - para vincular ao vivo): felipe@docente.senai.br / senai123")
    print("==================================================")

if __name__ == '__main__':
    reset_demo()
