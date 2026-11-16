import sqlite3
import os
import hmac
import re
from html import escape
from functools import wraps
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, session, redirect
from werkzeug.security import generate_password_hash, check_password_hash

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))
DB_FILE = os.path.join(os.path.dirname(__file__), 'database', 'patrimonio.db')

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')
app.secret_key = os.environ.get('FLASK_SECRET_KEY') or os.urandom(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax')


def secretaria_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if session.get('usuario_tipo') != 'secretaria':
            return jsonify({"erro": "Acesso restrito à Secretaria."}), 401
        return func(*args, **kwargs)
    return wrapper


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get('usuario_id'):
            return jsonify({"erro": "Faça login para continuar."}), 401
        return func(*args, **kwargs)
    return wrapper

# ============================================================
# BANCO DE DADOS
# ============================================================
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = get_db()
    cursor = conn.cursor()

    # 1. Usuários do sistema (secretaria, professores)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            tipo TEXT NOT NULL,         -- 'secretaria', 'professor'
            tag_rfid TEXT UNIQUE,       -- Pode ser NULL (aguardando ativação de crachá)
            criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. Crachás recentes lidos no leitor (persistidos no SQLite)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS crachas_recentes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag_uid TEXT UNIQUE NOT NULL,
            data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'Pendente',   -- 'Pendente', 'Vinculado', 'Ignorado'
            vinculado_a_nome TEXT
        )
    """)

    # Histórico de todas as leituras em tempo real no leitor RFID
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leituras_rfid (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag_uid TEXT NOT NULL,
            usuario_nome TEXT,
            tipo_leitura TEXT,      -- 'novo_pendente', 'turno_aberto', 'turno_encerrado', 'negado'
            detalhes TEXT,
            data_hora DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 3. Laboratórios / Ambientes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS laboratorios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            localizacao TEXT,
            status TEXT DEFAULT 'Livre',      -- 'Livre', 'Em Uso'
            responsavel_id INTEGER,           -- FK -> usuarios.id
            responsavel_nome TEXT,
            inicio_uso DATETIME,
            FOREIGN KEY (responsavel_id) REFERENCES usuarios(id)
        )
    """)

    # 4. Patrimônios / Equipamentos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patrimonios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_patrimonio TEXT UNIQUE NOT NULL,   -- Ex: PC-01, PC-02
            descricao TEXT NOT NULL,
            categoria TEXT DEFAULT 'computador',      -- 'computador', 'ferramenta', 'instrumento'
            laboratorio_id INTEGER,
            status TEXT DEFAULT 'Disponivel',         -- 'Disponivel', 'Em Uso', 'Manutencao'
            FOREIGN KEY (laboratorio_id) REFERENCES laboratorios(id)
        )
    """)

    # 5. Registros de uso dos computadores por aluno durante o turno do professor.
    # Os nomes da tabela/colunas são legados para manter compatibilidade com a base atual.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cautelas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patrimonio_id INTEGER NOT NULL,
            nome_usuario TEXT NOT NULL,               -- Aluno que registrou no PC
            responsavel_id INTEGER NOT NULL,          -- Professor com turno ativo
            laboratorio_id INTEGER NOT NULL,
            retirada_em DATETIME DEFAULT CURRENT_TIMESTAMP,
            devolucao_em DATETIME,                    -- NULL = em aberto
            status TEXT DEFAULT 'Ativa',              -- 'Ativa', 'Devolvida'
            FOREIGN KEY (patrimonio_id) REFERENCES patrimonios(id),
            FOREIGN KEY (responsavel_id) REFERENCES usuarios(id),
            FOREIGN KEY (laboratorio_id) REFERENCES laboratorios(id)
        )
    """)

    # Seed inicial: Secretaria
    cursor.execute("SELECT id FROM usuarios WHERE email='secretaria@senai.br'")
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO usuarios (nome, email, senha, tipo)
            VALUES (?, ?, ?, ?)
        """, ('Secretaria SENAI', 'secretaria@senai.br', generate_password_hash('senai123'), 'secretaria'))

    # Seed inicial do piloto: uma sala de informática.
    cursor.execute("SELECT COUNT(*) as total FROM laboratorios")
    if cursor.fetchone()['total'] == 0:
        labs = [('Sala de Informática', 'Sala de Informática')]
        cursor.executemany("INSERT INTO laboratorios (nome, localizacao) VALUES (?, ?)", labs)

    conn.commit()
    conn.close()

# ============================================================
# ROTAS ESTÁTICAS E PÁGINAS WEB
# ============================================================
@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/ativar')
def serve_ativar():
    if session.get('usuario_tipo') != 'secretaria':
        return redirect('/')
    return send_from_directory(app.static_folder, 'ativar.html')

@app.route('/qr')
@app.route('/etiquetas')
def serve_etiquetas():
    return send_from_directory(app.static_folder, 'qr_generator.html')

# ============================================================
# REGISTRO DE USO DO COMPUTADOR PELO ALUNO VIA QR CODE
# GET  /uso/<PC-XX> → Página mobile para registrar quem está usando o PC
# POST /api/retirar/<PC-XX> → Rota legada que registra o uso do PC
# ============================================================
@app.route('/uso/<numero_patrimonio>')
@app.route('/retirar/<numero_patrimonio>')
def pagina_retirada(numero_patrimonio):
    numero = numero_patrimonio.strip().upper()
    if not re.fullmatch(r"[A-Z0-9_-]{1,32}", numero):
        return "Identificador de patrimônio inválido.", 400
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT p.id, p.descricao, p.status, p.laboratorio_id,
               l.nome as lab_nome, l.status as lab_status,
               l.responsavel_nome
        FROM patrimonios p
        LEFT JOIN laboratorios l ON p.laboratorio_id = l.id
        WHERE p.numero_patrimonio = ?
    """, (numero,))
    pat = cursor.fetchone()

    em_uso_por = None
    if pat:
        cursor.execute("""
            SELECT nome_usuario FROM cautelas
            WHERE patrimonio_id = ? AND status = 'Ativa'
            LIMIT 1
        """, (pat['id'],))
        c = cursor.fetchone()
        if c:
            em_uso_por = c['nome_usuario']

    # Se o PC não existe no cadastro, exibe erro claro
    if not pat:
        estado = "nao_encontrado"
        descricao = f"Patrimônio {numero}"
        lab_nome = "Cadastro inexistente"
        responsavel = ""
    elif not pat['laboratorio_id'] or pat['lab_status'] != 'Em Uso':
        estado = "sem_turno"
        descricao = pat['descricao']
        lab_nome = pat['lab_nome'] or "Laboratório não vinculado"
        responsavel = ""
    elif em_uso_por:
        estado = "ocupado"
        descricao = pat['descricao']
        lab_nome = pat['lab_nome'] or "Laboratório"
        responsavel = pat['responsavel_nome'] or ""
    else:
        estado = "disponivel"
        descricao = pat['descricao']
        lab_nome = pat['lab_nome'] or "Laboratório"
        responsavel = pat['responsavel_nome'] or ""

    conn.close()

    numero_html = escape(numero)
    descricao_html = escape(descricao or '')
    lab_nome_html = escape(lab_nome or '')
    responsavel_html = escape(responsavel or '')
    em_uso_por_html = escape(em_uso_por or '')

    estado_html = {
        "nao_encontrado": f"""
            <div class="status-box status-erro">
                <span class="material-symbols-rounded icon-lg">sentiment_dissatisfied</span>
                <h2>PC Não Encontrado</h2>
                <p>O equipamento <strong>{numero_html}</strong> não está cadastrado no sistema.<br>Verifique a etiqueta ou contate a secretaria.</p>
            </div>""",
        "sem_turno": f"""
            <div class="status-box status-aviso">
                <span class="material-symbols-rounded icon-lg">schedule</span>
                <h2>Nenhum Turno Ativo</h2>
                <p>O professor ainda não iniciou o turno nesta sala.<br>Aguarde a abertura do turno para registrar o uso do computador.</p>
            </div>""",
        "ocupado": f"""
            <div class="status-box status-erro">
                <span class="material-symbols-rounded icon-lg">person_off</span>
                <h2>PC em Uso</h2>
                <p>Este computador já está vinculado a <strong>{em_uso_por_html}</strong>.<br>Por favor, escolha outro disponível.</p>
            </div>""",
        "disponivel": f"""
            <div class="status-box status-ok">
                <span class="material-symbols-rounded icon-lg">computer</span>
                <h2>PC Disponível</h2>
                <p>Digite seu nome completo para vincular seu uso:</p>
            </div>
            <form id="form-registro" onsubmit="registrar(event)" style="display:flex; flex-direction:column; gap:12px;">
                <input type="text" id="nome" name="nome" placeholder="Seu nome completo"
                    minlength="3" maxlength="80" autocomplete="name" autofocus required class="input-nome">
                <button type="submit" class="btn-confirmar">
                    <span class="material-symbols-rounded">assignment_turned_in</span>
                    Confirmar Uso do PC
                </button>
            </form>"""
    }

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
    <title>{numero_html} · SENAI Patrimônio</title>
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap" rel="stylesheet">
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Inter', sans-serif;
            background: #0F172A;
            color: #CBD5E1;
            min-height: 100dvh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 24px 20px;
        }}
        .card {{
            background: #1E293B;
            border: 1px solid #334155;
            border-radius: 20px;
            width: 100%;
            max-width: 400px;
            overflow: hidden;
            box-shadow: 0 20px 25px -5px rgba(0,0,0,0.5);
        }}
        .header {{
            background: #E3000F;
            padding: 18px 24px;
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .header img {{ height: 26px; filter: brightness(0) invert(1); }}
        .header-text h1 {{ font-size: 13px; font-weight: 900; color: white; letter-spacing: 0.05em; text-transform: uppercase; }}
        .header-text p {{ font-size: 11px; color: rgba(255,255,255,0.8); margin-top: 1px; }}
        .body {{ padding: 24px; display: flex; flex-direction: column; gap: 18px; }}
        .pc-badge {{
            display: flex;
            align-items: center;
            gap: 14px;
            background: #0F172A;
            border: 1px solid #334155;
            border-radius: 14px;
            padding: 14px 16px;
        }}
        .pc-badge .icon {{ font-size: 34px; color: #60A5FA; font-variation-settings: 'FILL' 1; }}
        .pc-badge .pc-num {{ font-size: 24px; font-weight: 900; color: white; line-height: 1; }}
        .pc-badge .pc-desc {{ font-size: 12px; color: #64748B; margin-top: 3px; }}
        .lab-info {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            color: #94A3B8;
            background: #0F172A/50;
            padding: 8px 12px;
            border-radius: 8px;
        }}
        .status-box {{
            border-radius: 14px;
            padding: 20px;
            text-align: center;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 8px;
        }}
        .status-box h2 {{ font-size: 16px; font-weight: 700; }}
        .status-box p {{ font-size: 13px; line-height: 1.5; color: #94A3B8; }}
        .icon-lg {{ font-size: 42px !important; font-variation-settings: 'FILL' 1; }}
        .status-ok {{ background: rgba(34,197,94,0.08); border: 1px solid rgba(34,197,94,0.25); color: #4ade80; }}
        .status-aviso {{ background: rgba(245,158,11,0.08); border: 1px solid rgba(245,158,11,0.25); color: #fbbf24; }}
        .status-erro {{ background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.25); color: #f87171; }}
        .input-nome {{
            width: 100%;
            background: #0F172A;
            border: 2px solid #334155;
            border-radius: 12px;
            padding: 14px 16px;
            font-size: 16px;
            font-family: 'Inter', sans-serif;
            color: white;
            outline: none;
            transition: border-color 0.2s;
        }}
        .input-nome:focus {{ border-color: #E3000F; }}
        .btn-confirmar {{
            width: 100%;
            background: #E3000F;
            color: white;
            border: none;
            border-radius: 12px;
            padding: 16px;
            font-size: 15px;
            font-weight: 700;
            font-family: 'Inter', sans-serif;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            transition: background 0.2s;
        }}
        .btn-confirmar:hover {{ background: #C4000C; }}
        .resp-ok {{ text-align: center; padding: 20px; display: none; flex-direction: column; align-items: center; gap: 12px; }}
        .resp-ok .check {{ font-size: 56px; color: #4ade80; font-variation-settings: 'FILL' 1; }}
        .resp-ok h2 {{ font-size: 18px; font-weight: 900; color: white; }}
        .resp-ok p {{ font-size: 13px; color: #94A3B8; line-height: 1.5; }}
        .footer {{ margin-top: 24px; font-size: 11px; color: #475569; text-align: center; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <img src="/assets/img/logo-senai.png" alt="SENAI">
            <div class="header-text">
                <h1>Controle de Patrimônio</h1>
                <p>Auto-registro de PC</p>
            </div>
        </div>
        <div class="body">
            <div class="pc-badge">
                <span class="material-symbols-rounded icon">computer</span>
                <div>
                    <div class="pc-num">{numero_html}</div>
                    <div class="pc-desc">{descricao_html}</div>
                </div>
            </div>
            {f'<div class="lab-info"><span class="material-symbols-rounded" style="font-size:16px;">meeting_room</span> {lab_nome_html} {"· Prof. " + responsavel_html if responsavel_html else ""}</div>' if lab_nome else ''}
            {estado_html.get(estado, '')}
            <div class="resp-ok" id="resp-ok">
                <span class="material-symbols-rounded check">task_alt</span>
                <h2>Uso Registrado</h2>
                <p id="resp-msg">Seu uso foi registrado com sucesso.<br>Pode fechar esta tela e utilizar o computador.</p>
            </div>
        </div>
    </div>
    <p class="footer">SENAI-SP · Controle de Patrimônio Inteligente</p>

    <script>
        async function registrar(e) {{
            e.preventDefault();
            const nome = document.getElementById('nome').value.trim();
            if (!nome) return;

            const btn = document.querySelector('.btn-confirmar');
            btn.disabled = true;
            btn.innerHTML = '<span class="material-symbols-rounded animate-spin">sync</span> Registrando...';

            try {{
                const res = await fetch('/api/retirar/{numero}', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{nome_usuario: nome}})
                }});
                const data = await res.json();

                const form = document.getElementById('form-registro');
                if (form) form.style.display = 'none';
                const statusBox = document.querySelector('.status-box');
                if (statusBox) statusBox.style.display = 'none';

                const ok = document.getElementById('resp-ok');
                ok.style.display = 'flex';

                if (data.erro) {{
                    ok.querySelector('.check').innerText = 'error';
                    ok.querySelector('.check').style.color = '#f87171';
                    ok.querySelector('h2').innerText = 'Atenção';
                    document.getElementById('resp-msg').innerText = data.erro;
                }} else {{
                    const msg = document.getElementById('resp-msg');
                    msg.textContent = 'Uso de ' + '{numero}' + ' registrado para ' + nome + '. Bom trabalho!';
                }}
            }} catch(err) {{
                alert('Erro de conexão com o servidor.');
                btn.disabled = false;
                btn.innerHTML = 'Confirmar Uso do PC';
            }}
        }}
    </script>
</body>
</html>"""
    return html

@app.route('/api/retirar/<numero_patrimonio>', methods=['POST'])
def api_retirada_aluno(numero_patrimonio):
    numero = numero_patrimonio.strip().upper()
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        return jsonify({"erro": "Envie os dados do registro de uso em formato JSON."}), 400
    nome_recebido = dados.get('nome_usuario', '')
    if not isinstance(nome_recebido, str):
        return jsonify({"erro": "Informe um nome válido."}), 400
    nome_usuario = nome_recebido.strip()

    # Validação do nome do aluno (mínimo 3 letras, máximo 80, não apenas espaços/números)
    if not nome_usuario or len(nome_usuario) < 3:
        return jsonify({"erro": "Informe seu nome completo (mínimo de 3 caracteres)."}), 400
    if len(nome_usuario) > 80:
        return jsonify({"erro": "O nome informado é muito longo (máximo de 80 caracteres)."}), 400
    if not any(c.isalpha() for c in nome_usuario):
        return jsonify({"erro": "O nome deve conter letras válidas."}), 400

    conn = get_db()
    cursor = conn.cursor()

    # 1. PC deve estar previamente cadastrado (proibida a criação automática de patrimônio)
    cursor.execute("""
        SELECT id, descricao, laboratorio_id, status
        FROM patrimonios
        WHERE numero_patrimonio = ?
    """, (numero,))
    pat = cursor.fetchone()

    if not pat:
        conn.close()
        return jsonify({"erro": f"O patrimônio '{numero}' não foi encontrado no sistema. Contate a secretaria."}), 404

    pat_id = pat['id']
    lab_id = pat['laboratorio_id']

    # 2. Corrigir atribuição de laboratório: usar estritamente o laboratório ao qual o PC pertence
    if not lab_id:
        conn.close()
        return jsonify({"erro": f"O patrimônio '{numero}' não está vinculado a nenhuma sala/laboratório."}), 400

    cursor.execute("""
        SELECT id, nome, status, responsavel_id, responsavel_nome
        FROM laboratorios
        WHERE id = ?
    """, (lab_id,))
    lab = cursor.fetchone()

    if not lab or lab['status'] != 'Em Uso' or not lab['responsavel_id']:
        conn.close()
        nome_lab = lab['nome'] if lab else "neste laboratório"
        return jsonify({"erro": f"Nenhum turno ativo em '{nome_lab}'. Aguarde o professor abrir a aula."}), 403

    responsavel_id = lab['responsavel_id']

    # 3. Impedir que o mesmo PC seja vinculado a dois alunos ao mesmo tempo
    cursor.execute("""
        SELECT nome_usuario FROM cautelas
        WHERE patrimonio_id = ? AND status = 'Ativa'
    """, (pat_id,))
    existente = cursor.fetchone()
    if existente:
        conn.close()
        return jsonify({"erro": f"Este PC já está em uso por {existente['nome_usuario']}."}), 409

    # 4. Impedir que o mesmo aluno esteja em dois computadores ativos ao mesmo tempo
    cursor.execute("""
        SELECT p.numero_patrimonio
        FROM cautelas c
        JOIN patrimonios p ON c.patrimonio_id = p.id
        WHERE LOWER(c.nome_usuario) = ? AND c.status = 'Ativa'
        LIMIT 1
    """, (nome_usuario.lower(),))
    duplicado = cursor.fetchone()
    if duplicado:
        conn.close()
        return jsonify({
            "erro": f"Você ({nome_usuario}) já possui o computador {duplicado['numero_patrimonio']} em uso ativo no momento."
        }), 409

    # 5. Registra quem está usando o computador e atualiza seu status para 'Em Uso'.
    cursor.execute("""
        INSERT INTO cautelas (patrimonio_id, nome_usuario, responsavel_id, laboratorio_id)
        VALUES (?, ?, ?, ?)
    """, (pat_id, nome_usuario, responsavel_id, lab_id))
    cursor.execute("UPDATE patrimonios SET status='Em Uso' WHERE id=?", (pat_id,))

    conn.commit()
    conn.close()

    return jsonify({"status": "ok", "mensagem": f"{nome_usuario} registrado no {numero} com sucesso!"}), 200

# ============================================================
# AUTHENTICATION
# ============================================================
@app.route('/api/login', methods=['POST'])
def login():
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        dados = {}
    email_recebido = dados.get('email', '')
    senha = dados.get('senha', '')
    if not isinstance(email_recebido, str) or not isinstance(senha, str):
        return jsonify({"erro": "E-mail ou senha incorretos."}), 401
    email = email_recebido.strip().lower()

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, tipo, senha FROM usuarios WHERE LOWER(email)=?", (email,))
    u = cursor.fetchone()
    if u:
        stored_password = u['senha'] or ''
        try:
            valid_password = check_password_hash(stored_password, senha)
        except (ValueError, TypeError):
            valid_password = False
        if not valid_password and hmac.compare_digest(stored_password, senha):
            valid_password = True
            cursor.execute("UPDATE usuarios SET senha=? WHERE id=?", (generate_password_hash(senha), u['id']))
            conn.commit()
    else:
        valid_password = False
    conn.close()

    if not u or not valid_password:
        return jsonify({"erro": "E-mail ou senha incorretos."}), 401

    session.clear()
    session['usuario_id'] = u['id']
    session['usuario_tipo'] = u['tipo']
    session['usuario_nome'] = u['nome']
    return jsonify({"id": u['id'], "nome": u['nome'], "tipo": u['tipo']}), 200


@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"status": "ok"}), 200


@app.route('/api/secretaria/senha', methods=['POST'])
@secretaria_required
def alterar_senha_secretaria():
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        dados = {}
    senha_atual = dados.get('senha_atual', '')
    senha_nova = dados.get('senha_nova', '')
    if not isinstance(senha_atual, str) or not isinstance(senha_nova, str) or len(senha_nova) < 12:
        return jsonify({"erro": "A nova senha deve ter pelo menos 12 caracteres."}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT senha FROM usuarios WHERE id=? AND tipo='secretaria'", (session['usuario_id'],))
    usuario = cursor.fetchone()
    if not usuario:
        conn.close()
        return jsonify({"erro": "Conta da Secretaria não encontrada."}), 404

    senha_armazenada = usuario['senha'] or ''
    try:
        senha_valida = check_password_hash(senha_armazenada, senha_atual)
    except (ValueError, TypeError):
        senha_valida = False
    if not senha_valida:
        senha_valida = hmac.compare_digest(senha_armazenada, senha_atual)
    if not senha_valida:
        conn.close()
        return jsonify({"erro": "A senha atual está incorreta."}), 401

    cursor.execute("UPDATE usuarios SET senha=? WHERE id=?", (generate_password_hash(senha_nova), session['usuario_id']))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "mensagem": "Senha atualizada."}), 200

# ============================================================
# STATS & DASHBOARD
# ============================================================
@app.route('/api/stats', methods=['GET'])
@secretaria_required
def stats():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as t FROM laboratorios WHERE status='Em Uso'")
    labs_em_uso = cursor.fetchone()['t']

    cursor.execute("SELECT COUNT(*) as t FROM cautelas WHERE status='Ativa'")
    cautelas_ativas = cursor.fetchone()['t']

    cursor.execute("SELECT COUNT(*) as t FROM patrimonios")
    total_patrimonios = cursor.fetchone()['t']

    cursor.execute("SELECT COUNT(*) as t FROM usuarios WHERE tipo='professor'")
    total_professores = cursor.fetchone()['t']

    cursor.execute("SELECT COUNT(*) as t FROM usuarios WHERE tipo='professor' AND tag_rfid IS NOT NULL")
    professores_ativos = cursor.fetchone()['t']

    cursor.execute("SELECT COUNT(*) as t FROM crachas_recentes WHERE status='Pendente'")
    crachas_pendentes = cursor.fetchone()['t']

    conn.close()
    return jsonify({
        "labs_em_uso": labs_em_uso,
        "cautelas_ativas": cautelas_ativas,
        "total_patrimonios": total_patrimonios,
        "total_professores": total_professores,
        "professores_ativos": professores_ativos,
        "crachas_pendentes": crachas_pendentes
    })

# ============================================================
# RFID LEITURA (ESP8266)
# ============================================================
@app.route('/api/rfid/leitura', methods=['POST'])
def leitura_rfid():
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        return jsonify({"status": "erro", "mensagem": "Envie uma leitura válida em JSON."}), 400
    uid_recebido = dados.get('tag_uid', '')
    if not isinstance(uid_recebido, str):
        return jsonify({"status": "erro", "mensagem": "UID inválido."}), 400
    tag_uid = uid_recebido.strip().upper()
    try:
        lab_id = int(dados.get('lab_id', 1))
    except (TypeError, ValueError):
        return jsonify({"status": "erro", "mensagem": "Laboratório inválido."}), 400
    if lab_id < 1:
        return jsonify({"status": "erro", "mensagem": "Laboratório inválido."}), 400

    if not re.fullmatch(r"[A-F0-9]{4,32}", tag_uid):
        return jsonify({"status": "erro", "mensagem": "UID inválido."}), 400

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, nome, tipo, email FROM usuarios WHERE tag_rfid=?", (tag_uid,))
    usuario = cursor.fetchone()

    # 1. Se o crachá NÃO pertence a ninguém:
    if not usuario:
        # Salva ou atualiza na tabela persistente de crachás recentes
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("SELECT id FROM crachas_recentes WHERE tag_uid=?", (tag_uid,))
        rec = cursor.fetchone()
        if rec:
            cursor.execute("UPDATE crachas_recentes SET data_hora=?, status='Pendente' WHERE tag_uid=?", (agora, tag_uid))
        else:
            cursor.execute("INSERT INTO crachas_recentes (tag_uid, data_hora, status) VALUES (?, ?, 'Pendente')", (tag_uid, agora))

        # Registra no log de leituras
        cursor.execute("""
            INSERT INTO leituras_rfid (tag_uid, usuario_nome, tipo_leitura, detalhes, data_hora)
            VALUES (?, NULL, 'novo_pendente', 'Crachá novo aguardando vinculação', ?)
        """, (tag_uid, agora))

        conn.commit()
        conn.close()
        return jsonify({
            "status": "pendente",
            "mensagem": "Cracha aguardando ativacao.",
            "uid": tag_uid
        }), 200

    # 2. Se o crachá pertence a um usuário:
    if usuario['tipo'] != 'professor':
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO leituras_rfid (tag_uid, usuario_nome, tipo_leitura, detalhes, data_hora)
            VALUES (?, ?, 'negado', 'Acesso negado - Não é docente', ?)
        """, (tag_uid, usuario['nome'], agora))
        conn.commit()
        conn.close()
        return jsonify({"status": "negado", "mensagem": "Apenas professores iniciam turno de patrimônio."}), 200

    prof_id = usuario['id']
    prof_nome = usuario['nome']

    cursor.execute("SELECT id, nome, status, responsavel_id FROM laboratorios WHERE id=?", (lab_id,))
    lab = cursor.fetchone()
    if not lab:
        conn.close()
        return jsonify({"status": "erro", "mensagem": "Laboratório não encontrado."}), 404

    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Toggle de Turno:
    if lab['status'] == 'Em Uso' and lab['responsavel_id'] == prof_id:
        # Encerra o turno e finaliza os registros de uso do laboratório.
        cursor.execute("""
            UPDATE cautelas SET status='Devolvida', devolucao_em=?
            WHERE laboratorio_id=? AND status='Ativa'
        """, (agora, lab_id))
        cursor.execute("""
            UPDATE patrimonios SET status='Disponivel'
            WHERE laboratorio_id=? AND status='Em Uso'
        """, (lab_id,))
        cursor.execute("""
            UPDATE laboratorios SET status='Livre', responsavel_id=NULL, responsavel_nome=NULL, inicio_uso=NULL
            WHERE id=?
        """, (lab_id,))

        cursor.execute("""
            INSERT INTO leituras_rfid (tag_uid, usuario_nome, tipo_leitura, detalhes, data_hora)
            VALUES (?, ?, 'turno_encerrado', ?, ?)
        """, (tag_uid, prof_nome, f"Turno encerrado no {lab['nome']}", agora))

        conn.commit()
        conn.close()
        return jsonify({
            "status": "sucesso",
            "acao": "encerrado",
            "mensagem": f"Turno de {prof_nome} encerrado.",
            "professor": prof_nome,
            "lab": lab['nome']
        }), 200
    else:
        # Inicia turno novo
        cursor.execute("""
            UPDATE laboratorios SET status='Em Uso', responsavel_id=?, responsavel_nome=?, inicio_uso=?
            WHERE id=?
        """, (prof_id, prof_nome, agora, lab_id))

        cursor.execute("""
            INSERT INTO leituras_rfid (tag_uid, usuario_nome, tipo_leitura, detalhes, data_hora)
            VALUES (?, ?, 'turno_aberto', ?, ?)
        """, (tag_uid, prof_nome, f"Turno aberto no {lab['nome']}", agora))

        conn.commit()
        conn.close()
        return jsonify({
            "status": "sucesso",
            "acao": "aberto",
            "mensagem": f"Turno iniciado por {prof_nome}.",
            "professor": prof_nome,
            "lab": lab['nome']
        }), 200

# ============================================================
# CRACHÁS RECENTES & FILA DE ATIVAÇÃO
# ============================================================
@app.route('/api/crachas/fila', methods=['GET'])
@secretaria_required
def fila_crachas():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, tag_uid, data_hora, status
        FROM crachas_recentes
        WHERE status = 'Pendente'
        ORDER BY data_hora DESC
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify(rows)

@app.route('/api/crachas/leituras', methods=['GET'])
@secretaria_required
def leituras_recentes():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, tag_uid, usuario_nome, tipo_leitura, detalhes, data_hora
        FROM leituras_rfid
        ORDER BY id DESC
        LIMIT 12
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify(rows)

@app.route('/api/crachas/recentes', methods=['GET'])
@secretaria_required
def crachas_recentes():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT tag_uid, data_hora, status, vinculado_a_nome
        FROM crachas_recentes
        ORDER BY data_hora DESC
        LIMIT 10
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify(rows)

@app.route('/api/crachas/recentes/<tag_uid>', methods=['DELETE'])
@secretaria_required
def ignorar_cracha(tag_uid):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE crachas_recentes SET status='Ignorado' WHERE tag_uid=?", (tag_uid,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True}), 200

# ============================================================
# PROFESSORES (Pré-Cadastro & Ativação de Crachá)
# ============================================================
@app.route('/api/professores', methods=['GET'])
@secretaria_required
def listar_professores():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, nome, email, tipo, tag_rfid,
               CASE WHEN tag_rfid IS NOT NULL AND tag_rfid != '' THEN 'Ativo' ELSE 'Aguardando' END as status_cracha
        FROM usuarios
        WHERE tipo='professor'
        ORDER BY nome
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify(rows)

@app.route('/api/professores', methods=['POST'])
@secretaria_required
def cadastrar_professor():
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        return jsonify({"erro": "Envie os dados do professor em formato JSON."}), 400
    nome = dados.get('nome', '')
    email = dados.get('email', '')
    senha = dados.get('senha', 'senai123')
    tag_rfid = dados.get('tag_rfid', '')
    if not all(isinstance(v, str) for v in (nome, email, senha, tag_rfid)):
        return jsonify({"erro": "Os dados do professor são inválidos."}), 400
    nome = nome.strip()
    email = email.strip().lower()
    tag_rfid = tag_rfid.strip().upper() or None

    if not nome or not email:
        return jsonify({"erro": "Nome e e-mail são obrigatórios."}), 400
    if tag_rfid and not re.fullmatch(r"[A-F0-9]{4,32}", tag_rfid):
        return jsonify({"erro": "UID do crachá inválido."}), 400

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO usuarios (nome, email, senha, tipo, tag_rfid)
            VALUES (?, ?, ?, 'professor', ?)
        """, (nome, email, generate_password_hash(senha), tag_rfid))
        prof_id = cursor.lastrowid

        if tag_rfid:
            cursor.execute("UPDATE crachas_recentes SET status='Vinculado', vinculado_a_nome=? WHERE tag_uid=?", (nome, tag_rfid))

        conn.commit()
        conn.close()
        return jsonify({"status": "ok", "id": prof_id, "mensagem": f"Professor {nome} pré-cadastrado com sucesso!"}), 201
    except sqlite3.IntegrityError as e:
        conn.close()
        return jsonify({"erro": "Este e-mail ou crachá já está cadastrado no sistema."}), 400

@app.route('/api/professores/<int:prof_id>/vincular-cracha', methods=['POST'])
@secretaria_required
def vincular_cracha(prof_id):
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict) or not isinstance(dados.get('tag_uid', ''), str):
        return jsonify({"erro": "UID do crachá inválido."}), 400
    tag_uid = dados.get('tag_uid', '').strip().upper()

    if not re.fullmatch(r"[A-F0-9]{4,32}", tag_uid):
        return jsonify({"erro": "UID do crachá inválido."}), 400

    conn = get_db()
    cursor = conn.cursor()

    # Verifica se já está em outro professor
    cursor.execute("SELECT id, nome FROM usuarios WHERE tag_rfid=? AND id != ?", (tag_uid, prof_id))
    outro = cursor.fetchone()
    if outro:
        conn.close()
        return jsonify({"erro": f"Este crachá já pertence ao professor {outro['nome']}."}), 400

    cursor.execute("SELECT nome FROM usuarios WHERE id=? AND tipo='professor'", (prof_id,))
    prof = cursor.fetchone()
    if not prof:
        conn.close()
        return jsonify({"erro": "Professor não encontrado."}), 404

    cursor.execute("UPDATE usuarios SET tag_rfid=? WHERE id=?", (tag_uid, prof_id))
    cursor.execute("UPDATE crachas_recentes SET status='Vinculado', vinculado_a_nome=? WHERE tag_uid=?", (prof['nome'], tag_uid))
    conn.commit()
    conn.close()

    return jsonify({"status": "ok", "mensagem": f"Crachá {tag_uid} vinculado ao professor {prof['nome']} com sucesso!"}), 200

@app.route('/api/professores/<int:prof_id>/desvincular-cracha', methods=['POST'])
@secretaria_required
def desvincular_cracha(prof_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET tag_rfid=NULL WHERE id=? AND tipo='professor'", (prof_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "mensagem": "Crachá desvinculado."}), 200

# ============================================================
# LABORATÓRIOS
# ============================================================
@app.route('/api/laboratorios', methods=['GET'])
@login_required
def listar_laboratorios():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM laboratorios ORDER BY nome")
    labs = []
    for lab in cursor.fetchall():
        cursor.execute("""
            SELECT c.id, c.nome_usuario, p.numero_patrimonio, p.descricao, c.retirada_em
            FROM cautelas c
            JOIN patrimonios p ON c.patrimonio_id = p.id
            WHERE c.laboratorio_id=? AND c.status='Ativa'
            ORDER BY c.retirada_em
        """, (lab['id'],))
        cautelas = [dict(r) for r in cursor.fetchall()]
        labs.append({
            "id": lab['id'],
            "nome": lab['nome'],
            "localizacao": lab['localizacao'],
            "status": lab['status'],
            "responsavel_id": lab['responsavel_id'],
            "responsavel_nome": lab['responsavel_nome'],
            "inicio_uso": lab['inicio_uso'],
            "cautelas_ativas": cautelas
        })
    conn.close()
    return jsonify(labs)

@app.route('/api/laboratorios/<int:lab_id>/encerrar', methods=['POST'])
@login_required
def encerrar_turno(lab_id):
    if session.get('usuario_tipo') != 'secretaria':
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT responsavel_id FROM laboratorios WHERE id=?", (lab_id,))
        lab = cursor.fetchone()
        conn.close()
        if not lab or lab['responsavel_id'] != session.get('usuario_id'):
            return jsonify({"erro": "Você só pode encerrar seu próprio turno."}), 403
    conn = get_db()
    cursor = conn.cursor()
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        UPDATE cautelas SET status='Devolvida', devolucao_em=?
        WHERE laboratorio_id=? AND status='Ativa'
    """, (agora, lab_id))
    cursor.execute("""
        UPDATE patrimonios SET status='Disponivel'
        WHERE laboratorio_id=? AND status='Em Uso'
    """, (lab_id,))
    cursor.execute("""
        UPDATE laboratorios SET status='Livre', responsavel_id=NULL, responsavel_nome=NULL, inicio_uso=NULL
        WHERE id=?
    """, (lab_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "mensagem": "Turno encerrado e registros de uso finalizados."}), 200

# ============================================================
# PATRIMÔNIOS (Cadastro e Listagem)
# ============================================================
@app.route('/api/patrimonios', methods=['GET'])
@secretaria_required
def listar_patrimonios():
    lab_id = request.args.get('lab_id')
    conn = get_db()
    cursor = conn.cursor()
    if lab_id:
        cursor.execute("SELECT * FROM patrimonios WHERE laboratorio_id=? ORDER BY numero_patrimonio", (lab_id,))
    else:
        cursor.execute("SELECT * FROM patrimonios ORDER BY numero_patrimonio")
    items = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify(items)

@app.route('/api/patrimonios', methods=['POST'])
@secretaria_required
def cadastrar_patrimonio():
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        return jsonify({"erro": "Envie os dados do patrimônio em formato JSON."}), 400
    numero = dados.get('numero_patrimonio', '')
    descricao = dados.get('descricao', '')
    if not isinstance(numero, str) or not isinstance(descricao, str):
        return jsonify({"erro": "Os dados do patrimônio são inválidos."}), 400
    numero = numero.strip().upper()
    descricao = descricao.strip()
    categoria = dados.get('categoria', 'computador')
    lab_id = dados.get('laboratorio_id')

    if not numero or not descricao:
        return jsonify({"erro": "Número de patrimônio e descrição são obrigatórios."}), 400
    if not re.fullmatch(r"[A-Z0-9_-]{1,32}", numero):
        return jsonify({"erro": "Use até 32 letras, números, hífen ou sublinhado no identificador."}), 400

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO patrimonios (numero_patrimonio, descricao, categoria, laboratorio_id)
            VALUES (?, ?, ?, ?)
        """, (numero, descricao, categoria, lab_id or None))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return jsonify({"status": "ok", "id": new_id, "numero_patrimonio": numero}), 201
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"erro": f"O patrimônio '{numero}' já está cadastrado."}), 400

# ============================================================
# CAUTELAS & HISTÓRICO
# ============================================================
@app.route('/api/cautelas/<int:cautela_id>/devolver', methods=['POST'])
@login_required
def devolver_cautela(cautela_id):
    conn = get_db()
    cursor = conn.cursor()
    if session.get('usuario_tipo') != 'secretaria':
        cursor.execute("SELECT responsavel_id FROM cautelas WHERE id=?", (cautela_id,))
        cautela = cursor.fetchone()
        if not cautela or cautela['responsavel_id'] != session.get('usuario_id'):
            conn.close()
            return jsonify({"erro": "Você só pode finalizar registros de uso do seu laboratório."}), 403
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        UPDATE cautelas SET status='Devolvida', devolucao_em=? WHERE id=?
    """, (agora, cautela_id))
    cursor.execute("""
        UPDATE patrimonios SET status='Disponivel'
        WHERE id = (SELECT patrimonio_id FROM cautelas WHERE id=?)
    """, (cautela_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "mensagem": "Registro de uso finalizado; computador disponível."}), 200

@app.route('/api/historico', methods=['GET'])
@secretaria_required
def historico():
    try:
        limit = max(1, min(int(request.args.get('limit', 50)), 500))
    except ValueError:
        return jsonify({"erro": "O limite do histórico deve ser um número inteiro."}), 400
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.id, c.nome_usuario, c.status, c.retirada_em, c.devolucao_em,
               p.numero_patrimonio, p.descricao, u.nome as responsavel,
               l.nome as laboratorio
        FROM cautelas c
        JOIN patrimonios p ON c.patrimonio_id = p.id
        JOIN usuarios u ON c.responsavel_id = u.id
        JOIN laboratorios l ON c.laboratorio_id = l.id
        ORDER BY c.retirada_em DESC
        LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify(rows)

# ============================================================
# INICIALIZAÇÃO DO SERVIDOR (PORTA 5000)
# ============================================================
if __name__ == '__main__':
    init_db()
    # Ativa o modo debug apenas se a variável de ambiente FLASK_DEBUG=true estiver definida
    # Em ambiente de uso, não deixar debug=True (expõe o console interativo do Flask).
    modo_debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    print("\n=========================================")
    print("  SENAI PATRIMONIO >> SERVIDOR ATIVO :5000")
    if modo_debug:
        print("  [ATENCAO] Modo DEBUG ativo")
    print("=========================================\n")
    app.run(host='0.0.0.0', port=5000, debug=modo_debug)
