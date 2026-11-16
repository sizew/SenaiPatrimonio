// ============================================================
// CONFIGURAÇÃO GERAL
// ============================================================
const API = window.location.origin;

function escapeHTML(value) {
    return String(value ?? '').replace(/[&<>"']/g, char => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    })[char]);
}

let usuarioId = null;
let usuarioTipo = null;
let usuarioNome = null;

// ============================================================
// TOAST NOTIFICAÇÃO
// ============================================================
function showToast(titulo, msg, tipo = 'sucesso') {
    const icons = {
        sucesso: { icon: 'check_circle', cls: 'text-emerald-400' },
        erro:    { icon: 'error',        cls: 'text-rose-400' },
        aviso:   { icon: 'warning',      cls: 'text-amber-400' }
    };
    const t = icons[tipo] || icons.sucesso;
    const el = document.getElementById('toast');
    document.getElementById('toast-icon').className = `material-symbols-rounded ${t.cls} text-xl`;
    document.getElementById('toast-icon').innerText = t.icon;
    document.getElementById('toast-title').innerText = titulo;
    document.getElementById('toast-msg').innerText = msg;

    el.classList.remove('translate-x-full', 'opacity-0');
    el.classList.add('translate-x-0', 'opacity-100');
    setTimeout(hideToast, 4000);
}

function hideToast() {
    const el = document.getElementById('toast');
    el.classList.add('translate-x-full', 'opacity-0');
    el.classList.remove('translate-x-0', 'opacity-100');
}

// ============================================================
// AUTENTICAÇÃO
// ============================================================
function fazerLogin() {
    const email = document.getElementById('input-email').value.trim();
    const senha = document.getElementById('input-senha').value.trim();

    if (!email || !senha) {
        showToast('Campos Obrigatórios', 'Preencha o e-mail e a senha.', 'aviso');
        return;
    }

    const btn = document.getElementById('btn-login');
    btn.innerHTML = '<span class="material-symbols-rounded animate-spin text-sm mr-2">sync</span> Validando...';
    btn.disabled = true;

    fetch(`${API}/api/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, senha })
    })
    .then(r => r.json())
    .then(u => {
        if (u.erro) throw new Error(u.erro);
        usuarioId = u.id;
        usuarioTipo = u.tipo;
        usuarioNome = u.nome;
        document.getElementById('btn-alterar-senha').classList.toggle('hidden', u.tipo !== 'secretaria');

        document.getElementById('tela-login').classList.add('hidden');
        document.getElementById('tela-painel').classList.remove('hidden');
        document.getElementById('tela-painel').classList.add('flex');

        document.getElementById('header-nome').innerText = u.nome;
        document.getElementById('header-tipo').innerText = u.tipo === 'secretaria' ? 'Secretaria' : 'Docente';
        document.getElementById('avatar-img').src = `https://api.dicebear.com/7.x/notionists/svg?seed=${encodeURIComponent(u.nome)}&backgroundColor=transparent`;

        if (u.tipo === 'secretaria') {
            document.getElementById('sessao-secretaria').classList.remove('hidden');
            document.getElementById('sessao-professor').classList.add('hidden');
            carregarStats();
            carregarProfessores();
            carregarFilaCrachas();
            carregarLeiturasRecentes();
            carregarLabsSelect();
            carregarLaboratorios();
            carregarHistorico();
        } else {
            document.getElementById('sessao-professor').classList.remove('hidden');
            document.getElementById('sessao-secretaria').classList.add('hidden');
            document.getElementById('prof-saudacao').innerText = `Olá, ${u.nome.split(' ')[0]}!`;
            carregarLaboratorios();
        }
        showToast('Bem-vindo!', `Sessão iniciada como ${u.nome}.`, 'sucesso');
    })
    .catch(err => {
        showToast('Acesso Negado', err.message, 'erro');
        btn.innerHTML = 'ENTRAR NO SISTEMA';
        btn.disabled = false;
    });
}

async function fazerLogout() {
    try {
        await fetch(`${API}/api/logout`, { method: 'POST' });
    } catch (_) {}
    usuarioId = null;
    usuarioTipo = null;
    usuarioNome = null;
    document.getElementById('tela-painel').classList.add('hidden');
    document.getElementById('tela-painel').classList.remove('flex');
    document.getElementById('tela-login').classList.remove('hidden');
    document.getElementById('input-email').value = '';
    document.getElementById('input-senha').value = '';
    document.getElementById('btn-alterar-senha').classList.add('hidden');
    document.getElementById('btn-login').innerHTML = 'ENTRAR NO SISTEMA';
    document.getElementById('btn-login').disabled = false;
    showToast('Sessão Encerrada', 'Você saiu do sistema com segurança.', 'sucesso');
}

async function alterarSenha() {
    const senhaAtual = prompt('Informe sua senha atual:');
    if (senhaAtual === null) return;
    const senhaNova = prompt('Informe a nova senha (mínimo de 12 caracteres):');
    if (senhaNova === null) return;

    try {
        const resposta = await fetch(`${API}/api/secretaria/senha`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ senha_atual: senhaAtual, senha_nova: senhaNova })
        });
        const dados = await resposta.json();
        if (!resposta.ok) throw new Error(dados.erro || 'Não foi possível alterar a senha.');
        showToast('Senha atualizada', 'A senha da Secretaria foi alterada.', 'sucesso');
    } catch (erro) {
        showToast('Erro', erro.message, 'erro');
    }
}

// ============================================================
// SECRETARIA: INDICADORES (KPIs)
// ============================================================
function carregarStats() {
    fetch(`${API}/api/stats`)
        .then(r => r.json())
        .then(s => {
            document.getElementById('stat-labs').innerText = s.labs_em_uso;
            document.getElementById('stat-cautelas').innerText = s.cautelas_ativas;
            document.getElementById('stat-profs').innerText = s.total_professores;
            document.getElementById('stat-ativos').innerText = s.professores_ativos;
        })
        .catch(() => {});
}

// ============================================================
// SECRETARIA: GESTÃO DE PROFESSORES (Pré-Cadastro & Crachás)
// ============================================================
function carregarProfessores() {
    fetch(`${API}/api/professores`)
        .then(r => r.json())
        .then(profs => {
            const tbody = document.getElementById('tabela-professores');
            if (!profs || profs.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" class="text-center text-slate-500 py-8 text-xs">Nenhum professor pré-cadastrado ainda.</td></tr>';
                return;
            }

            tbody.innerHTML = profs.map(p => {
                const ativo = p.tag_rfid && p.tag_rfid.trim() !== '';
                return `
                <tr class="hover:bg-slate-700/20 transition-colors">
                    <td class="px-6 py-4 font-bold text-white flex items-center gap-2.5">
                        <div class="h-7 w-7 rounded-full bg-slate-700 flex items-center justify-center text-xs font-bold text-slate-300">
                            ${escapeHTML(p.nome.charAt(0).toUpperCase())}
                        </div>
                        ${escapeHTML(p.nome)}
                    </td>
                    <td class="px-6 py-4 text-xs text-slate-400 font-mono">${escapeHTML(p.email)}</td>
                    <td class="px-6 py-4">
                        ${ativo ? `
                            <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-emerald-950/60 text-emerald-400 border border-emerald-800/40 font-mono">
                                <span class="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
                                ${escapeHTML(p.tag_rfid)} (Ativo)
                            </span>
                        ` : `
                            <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-amber-950/60 text-amber-400 border border-amber-800/40">
                                <span class="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse"></span>
                                Aguardando Crachá
                            </span>
                        `}
                    </td>
                    <td class="px-6 py-4 text-right">
                        ${ativo ? `
                            <button onclick="desvincularCracha(${p.id})" class="text-xs text-slate-400 hover:text-rose-400 transition-colors font-medium">
                                Desvincular
                            </button>
                        ` : `
                            <button data-vincular-prof="${Number(p.id)}" data-prof-nome="${escapeHTML(p.nome)}" class="text-xs bg-senai/90 hover:bg-senai text-white font-bold px-3 py-1.5 rounded-lg transition-colors">
                                Vincular Crachá
                            </button>
                        `}
                    </td>
                </tr>`;
            }).join('');
            tbody.querySelectorAll('[data-vincular-prof]').forEach(button => {
                button.addEventListener('click', () => abrirModalVincular(button.dataset.vincularProf, button.dataset.profNome));
            });
        })
        .catch(() => {});
}

function abrirModalPreCadastro() {
    document.getElementById('modal-prof-nome').value = '';
    document.getElementById('modal-prof-email').value = '';
    document.getElementById('modal-precadastro').classList.remove('hidden');
    document.getElementById('modal-prof-nome').focus();
}

function fecharModalPreCadastro() {
    document.getElementById('modal-precadastro').classList.add('hidden');
}

function salvarPreCadastro() {
    const nome = document.getElementById('modal-prof-nome').value.trim();
    const email = document.getElementById('modal-prof-email').value.trim();

    if (!nome || !email) {
        showToast('Atenção', 'Informe o nome e o e-mail do docente.', 'aviso');
        return;
    }

    fetch(`${API}/api/professores`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nome, email })
    })
    .then(r => r.json())
    .then(data => {
        if (data.erro) {
            showToast('Erro', data.erro, 'erro');
            return;
        }
        showToast('Professor Cadastrado!', data.mensagem, 'sucesso');
        fecharModalPreCadastro();
        carregarProfessores();
        carregarStats();
    })
    .catch(() => showToast('Erro', 'Falha ao salvar professor.', 'erro'));
}

// ============================================================
// SECRETARIA: VINCULAR CRACHÁ (Ativação)
// ============================================================
function abrirModalVincular(profId, profNome) {
    document.getElementById('modal-vincular-prof-id').value = profId;
    document.getElementById('modal-vincular-sub').innerText = `Docente: ${profNome}`;
    document.getElementById('modal-vincular-uid-manual').value = '';
    document.getElementById('modal-vincular').classList.remove('hidden');

    carregarListaCrachasModal(profId);
}

function fecharModalVincular() {
    document.getElementById('modal-vincular').classList.add('hidden');
}

function carregarListaCrachasModal(profId) {
    const container = document.getElementById('lista-crachas-selecao');
    container.innerHTML = '<p class="text-xs text-slate-500 py-3 text-center">Buscando crachás detectados...</p>';

    fetch(`${API}/api/crachas/recentes`)
        .then(r => r.json())
        .then(crachas => {
            const pendentes = crachas.filter(c => c.status === 'Pendente');
            if (pendentes.length === 0) {
                container.innerHTML = `
                    <div class="bg-slate-900/50 border border-slate-700/60 rounded-xl p-3 text-center">
                        <p class="text-xs text-slate-400">Nenhum crachá pendente no momento.</p>
                        <p class="text-[11px] text-slate-500 mt-1">Passe o crachá no leitor RFID agora ou digite o código abaixo.</p>
                    </div>`;
                return;
            }

            container.innerHTML = pendentes.map(c => `
                <div class="flex items-center justify-between bg-slate-900/80 border border-slate-700 rounded-xl p-3 hover:border-slate-500 transition-colors">
                    <div class="flex items-center gap-3">
                        <span class="material-symbols-rounded text-senai text-lg">contactless</span>
                        <div>
                            <p class="text-sm font-black text-white font-mono">${escapeHTML(c.tag_uid)}</p>
                            <p class="text-[10px] text-slate-500">Lido às ${c.data_hora ? c.data_hora.substring(11,16) : '--'}</p>
                        </div>
                    </div>
                    <button onclick="vincularCrachaConfirmado(${Number(profId)}, '${escapeHTML(c.tag_uid)}')" class="bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1">
                        <span class="material-symbols-rounded text-sm">link</span> Vincular
                    </button>
                </div>
            `).join('');
        })
        .catch(() => {
            container.innerHTML = '<p class="text-xs text-rose-400 py-3 text-center">Erro ao carregar leituras.</p>';
        });
}

function vincularCrachaConfirmado(profId, tagUid) {
    fetch(`${API}/api/professores/${profId}/vincular-cracha`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tag_uid: tagUid })
    })
    .then(r => r.json())
    .then(data => {
        if (data.erro) {
            showToast('Erro', data.erro, 'erro');
            return;
        }
        showToast('Crachá Vinculado!', data.mensagem, 'sucesso');
        fecharModalVincular();
        carregarProfessores();
        carregarStats();
        carregarCrachasRecentes();
    })
    .catch(() => showToast('Erro', 'Falha ao vincular crachá.', 'erro'));
}

function confirmarVinculacaoManual() {
    const profId = document.getElementById('modal-vincular-prof-id').value;
    const uid = document.getElementById('modal-vincular-uid-manual').value.trim().toUpperCase();

    if (!uid) {
        showToast('Aviso', 'Digite o código UID do crachá.', 'aviso');
        return;
    }
    vincularCrachaConfirmado(profId, uid);
}

function desvincularCracha(profId) {
    if (!confirm('Deseja realmente desvincular este crachá do professor?')) return;

    fetch(`${API}/api/professores/${profId}/desvincular-cracha`, { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            showToast('Desvinculado', data.mensagem, 'sucesso');
            carregarProfessores();
            carregarStats();
        })
        .catch(() => showToast('Erro', 'Falha ao desvincular.', 'erro'));
}

// ============================================================
// SECRETARIA: FILA DE CRACHÁS PENDENTES & MONITOR RFID
// ============================================================
function carregarFilaCrachas() {
    fetch(`${API}/api/crachas/fila`)
        .then(r => r.json())
        .then(fila => {
            const container = document.getElementById('lista-fila-crachas');
            if (!container) return;

            if (!fila || fila.length === 0) {
                container.innerHTML = `
                    <div class="flex flex-col items-center justify-center py-8 text-center text-slate-500">
                        <span class="material-symbols-rounded text-3xl mb-1 text-slate-600">contactless</span>
                        <p class="text-xs">Nenhum crachá pendente na fila.</p>
                        <p class="text-[10px] text-slate-600 mt-0.5">Aproxime um crachá no leitor para ele aparecer aqui.</p>
                    </div>`;
                return;
            }

            container.innerHTML = fila.map(c => `
                <div class="flex items-center justify-between bg-slate-900/80 border border-amber-800/50 hover:border-amber-600 rounded-xl p-3 transition-colors shadow-sm">
                    <div class="flex items-center gap-3">
                        <div class="h-9 w-9 rounded-xl bg-amber-950/60 border border-amber-800/40 flex items-center justify-center text-amber-400">
                            <span class="material-symbols-rounded text-lg">contactless</span>
                        </div>
                        <div>
                            <p class="text-sm font-black text-white font-mono tracking-wider">${escapeHTML(c.tag_uid)}</p>
                            <p class="text-[10px] text-amber-400/80 font-medium">Lido às ${c.data_hora ? c.data_hora.substring(11, 19) : '--'}</p>
                        </div>
                    </div>
                    <div class="flex items-center gap-2">
                        <button onclick="ignorarCrachaFila('${escapeHTML(c.tag_uid)}')" class="p-1.5 text-slate-500 hover:text-rose-400 rounded-lg hover:bg-slate-800 transition-colors" title="Ignorar este crachá">
                            <span class="material-symbols-rounded text-base">close</span>
                        </button>
                        <button onclick="abrirModalVincularParaUid('${escapeHTML(c.tag_uid)}')" class="bg-senai hover:bg-senai-hover text-white text-xs font-bold px-3 py-1.5 rounded-lg flex items-center gap-1 transition-colors shadow">
                            <span class="material-symbols-rounded text-sm">link</span> Vincular
                        </button>
                    </div>
                </div>
            `).join('');
        })
        .catch(() => {});
}

function ignorarCrachaFila(tagUid) {
    fetch(`${API}/api/crachas/recentes/${tagUid}`, { method: 'DELETE' })
        .then(() => {
            carregarFilaCrachas();
            showToast('Ignorado', `Crachá ${tagUid} removido da fila.`, 'aviso');
        })
        .catch(() => {});
}

function carregarLeiturasRecentes() {
    fetch(`${API}/api/crachas/leituras`)
        .then(r => r.json())
        .then(leituras => {
            const container = document.getElementById('lista-leituras-recentes');
            if (!container) return;

            if (!leituras || leituras.length === 0) {
                container.innerHTML = `
                    <div class="flex flex-col items-center justify-center py-8 text-center text-slate-500 font-sans">
                        <span class="material-symbols-rounded text-3xl mb-1 text-slate-600">sensors</span>
                        <p class="text-xs">Aguardando leituras do leitor RFID...</p>
                    </div>`;
                return;
            }

            container.innerHTML = leituras.map(l => {
                let badgeClass = "bg-slate-800 text-slate-300 border-slate-700";
                let icon = "contactless";
                let statusTxt = "Leitura";

                if (l.tipo_leitura === 'turno_aberto') {
                    badgeClass = "bg-emerald-950/60 text-emerald-400 border-emerald-800/40";
                    icon = "login";
                    statusTxt = "Turno Aberto";
                } else if (l.tipo_leitura === 'turno_encerrado') {
                    badgeClass = "bg-rose-950/60 text-rose-400 border-rose-800/40";
                    icon = "logout";
                    statusTxt = "Turno Encerrado";
                } else if (l.tipo_leitura === 'novo_pendente') {
                    badgeClass = "bg-amber-950/60 text-amber-400 border-amber-800/40";
                    icon = "fiber_new";
                    statusTxt = "Novo Crachá";
                } else if (l.tipo_leitura === 'negado') {
                    badgeClass = "bg-rose-950/60 text-rose-400 border-rose-800/40";
                    icon = "block";
                    statusTxt = "Negado";
                }

                return `
                <div class="flex items-center justify-between bg-slate-900/60 border border-slate-700/60 rounded-xl px-3 py-2 text-xs">
                    <div class="flex items-center gap-2">
                        <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold border ${badgeClass}">
                            <span class="material-symbols-rounded text-xs">${icon}</span>
                            ${statusTxt}
                        </span>
                        <span class="font-bold text-white font-mono">${l.tag_uid}</span>
                        ${l.usuario_nome ? `<span class="text-slate-300 font-sans text-xs ml-1">· ${escapeHTML(l.usuario_nome)}</span>` : ''}
                    </div>
                    <span class="text-[10px] text-slate-500 font-mono">${l.data_hora ? l.data_hora.substring(11, 19) : ''}</span>
                </div>`;
            }).join('');
        })
        .catch(() => {});
}

function abrirModalVincularParaUid(tagUid) {
    document.getElementById('modal-vincular-uid-manual').value = tagUid;
    document.getElementById('modal-vincular-sub').innerText = `Crachá Selecionado: ${tagUid}`;
    document.getElementById('modal-vincular').classList.remove('hidden');

    const container = document.getElementById('lista-crachas-selecao');
    container.innerHTML = '<p class="text-xs text-slate-400 py-3 text-center">Buscando professores para vincular...</p>';

    fetch(`${API}/api/professores`)
        .then(r => r.json())
        .then(profs => {
            const aguardando = profs.filter(p => !p.tag_rfid || p.tag_rfid.trim() === '');
            if (aguardando.length === 0) {
                container.innerHTML = `
                    <div class="bg-slate-900/60 border border-slate-700 rounded-xl p-4 text-center">
                        <p class="text-xs text-amber-400 font-bold">Nenhum professor aguardando crachá!</p>
                        <p class="text-[11px] text-slate-400 mt-1">Clique em "Pré-cadastrar" primeiro para cadastrar o docente.</p>
                    </div>`;
                return;
            }

            container.innerHTML = `
                <div class="space-y-2">
                    <p class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Escolha qual docente receberá o crachá <span class="font-mono text-white">${tagUid}</span>:</p>
                    ${aguardando.map(p => `
                        <div class="flex items-center justify-between bg-slate-900 border border-slate-700 hover:border-senai rounded-xl p-3 transition-colors">
                            <div>
                                <p class="text-xs font-bold text-white">${escapeHTML(p.nome)}</p>
                                <p class="text-[10px] text-slate-400 font-mono">${escapeHTML(p.email)}</p>
                            </div>
                            <button onclick="vincularCrachaConfirmado(${p.id}, '${tagUid}')" class="bg-senai hover:bg-senai-hover text-white text-xs font-bold px-3 py-1.5 rounded-lg flex items-center gap-1 transition-colors">
                                <span class="material-symbols-rounded text-sm">link</span> Atribuir
                            </button>
                        </div>
                    `).join('')}
                </div>`;
        })
        .catch(() => {
            container.innerHTML = '<p class="text-xs text-rose-400 py-3 text-center">Erro ao carregar lista de professores.</p>';
        });
}

// ============================================================
// SECRETARIA: PATRIMÔNIOS
// ============================================================
function carregarLabsSelect() {
    fetch(`${API}/api/laboratorios`)
        .then(r => r.json())
        .then(labs => {
            const sel = document.getElementById('pat-lab');
            sel.innerHTML = '<option value="">Automático pelo Turno</option>' +
                labs.map(l => `<option value="${Number(l.id)}">${escapeHTML(l.nome)}</option>`).join('');
        })
        .catch(() => {});
}

function cadastrarPatrimonio() {
    const numero = document.getElementById('pat-numero').value.trim().toUpperCase();
    const descricao = document.getElementById('pat-descricao').value.trim();
    const categoria = document.getElementById('pat-categoria').value;
    const lab_id = document.getElementById('pat-lab').value;

    if (!numero || !descricao) {
        showToast('Campos Obrigatórios', 'Preencha o identificador e a descrição.', 'aviso');
        return;
    }

    fetch(`${API}/api/patrimonios`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            numero_patrimonio: numero,
            descricao,
            categoria,
            laboratorio_id: lab_id || null
        })
    })
    .then(r => r.json())
    .then(data => {
        if (data.erro) {
            showToast('Erro', data.erro, 'erro');
            return;
        }
        showToast('Patrimônio Salvo!', `Equipamento ${numero} registrado com sucesso.`, 'sucesso');
        document.getElementById('pat-numero').value = '';
        document.getElementById('pat-descricao').value = '';
        carregarStats();
    })
    .catch(() => showToast('Erro', 'Falha ao salvar patrimônio.', 'erro'));
}

// ============================================================
// SECRETARIA: HISTÓRICO DE AUDITORIA
// ============================================================
let carregandoHistorico = false;

function formatarDataHora(valor) {
    if (!valor) return '--';
    const partes = String(valor).match(/^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})/);
    if (!partes) return escapeHTML(valor);
    return `${partes[3]}/${partes[2]}/${partes[1]} ${partes[4]}:${partes[5]}`;
}

function carregarHistorico() {
    if (carregandoHistorico) return;
    carregandoHistorico = true;

    fetch(`${API}/api/historico?limit=50`)
        .then(r => r.json())
        .then(rows => {
            const tbody = document.getElementById('tabela-historico');
            if (!rows || rows.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" class="text-center text-slate-500 py-8 text-xs">Nenhum uso registrado no histórico.</td></tr>';
                return;
            }

            tbody.innerHTML = rows.map(r => `
                <tr class="hover:bg-slate-700/20 transition-colors">
                    <td class="px-6 py-4">
                        <span class="font-mono text-xs font-bold text-white bg-slate-800 border border-slate-700 px-2.5 py-1 rounded-lg">${escapeHTML(r.numero_patrimonio)}</span>
                        <span class="text-xs text-slate-400 ml-2">${escapeHTML(r.descricao)}</span>
                    </td>
                    <td class="px-6 py-4 text-xs font-bold text-slate-200">${escapeHTML(r.nome_usuario)}</td>
                    <td class="px-6 py-4 text-xs text-slate-400">${escapeHTML(r.responsavel)}</td>
                    <td class="px-6 py-4 text-xs text-slate-400">${escapeHTML(r.laboratorio)}</td>
                    <td class="px-6 py-4 text-xs text-slate-500 font-mono">${formatarDataHora(r.retirada_em)}</td>
                    <td class="px-6 py-4 text-xs text-slate-500 font-mono">${r.devolucao_em ? formatarDataHora(r.devolucao_em) : (r.status === 'Ativa' ? 'Em uso' : 'Não registrado')}</td>
                    <td class="px-6 py-4">
                        ${r.status === 'Ativa' ? `
                            <span class="text-[11px] px-2.5 py-0.5 rounded-full font-bold bg-rose-950/60 text-rose-400 border border-rose-800/40">Em Uso</span>
                        ` : `
                            <span class="text-[11px] px-2.5 py-0.5 rounded-full font-bold bg-emerald-950/60 text-emerald-400 border border-emerald-800/40">Uso Encerrado</span>
                        `}
                    </td>
                </tr>
            `).join('');
        })
        .catch(() => {})
        .finally(() => { carregandoHistorico = false; });
}

// ============================================================
// PROFESSOR: PAINEL & CONTROLE DE SALAS
// ============================================================
function carregarLaboratorios() {
    fetch(`${API}/api/laboratorios`)
        .then(r => r.json())
        .then(labs => {
            const renderCard = lab => {
                const emUso = lab.status === 'Em Uso';
                const cautelas = lab.cautelas_ativas || [];

                return `
                <div class="bg-slate-800 border ${emUso ? 'border-senai shadow-lg shadow-red-950/30' : 'border-slate-700'} rounded-2xl p-6 flex flex-col gap-4 transition-all">
                    <div class="flex items-start justify-between">
                        <div>
                            <h3 class="font-bold text-white text-base">${escapeHTML(lab.nome)}</h3>
                            <p class="text-xs text-slate-500 mt-0.5">${escapeHTML(lab.localizacao || '')}</p>
                        </div>
                        <span class="text-xs px-3 py-1 rounded-full font-black uppercase tracking-wider ${emUso ? 'bg-red-950/80 text-rose-400 border border-red-800/50' : 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/50'}">
                            ${emUso ? 'Em Aula' : 'Livre'}
                        </span>
                    </div>

                    ${emUso ? `
                        <div class="bg-red-950/30 border border-red-800/30 rounded-xl px-4 py-3 flex items-center gap-3">
                            <span class="material-symbols-rounded text-senai text-xl">person</span>
                            <div>
                                <p class="text-xs font-bold text-white">Resp: ${escapeHTML(lab.responsavel_nome)}</p>
                                <p class="text-[10px] text-slate-400">Turno iniciado às ${lab.inicio_uso ? lab.inicio_uso.substring(11,16) : '--'}</p>
                            </div>
                        </div>

                        <!-- Lista de Alunos conectados nos PCs -->
                        <div class="space-y-2 mt-1">
                            <div class="flex items-center justify-between">
                                <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400">PCs em Uso (${cautelas.length})</span>
                            </div>

                            ${cautelas.length > 0 ? `
                                <div class="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                                    ${cautelas.map(c => `
                                        <div class="bg-slate-900/60 border border-slate-700/60 rounded-xl px-3 py-2 flex items-center justify-between">
                                            <div>
                                                <p class="text-xs font-bold text-white">${escapeHTML(c.nome_usuario)}</p>
                                                <p class="text-[10px] text-slate-400">${escapeHTML(c.numero_patrimonio)} · ${c.retirada_em ? c.retirada_em.substring(11,16) : ''}</p>
                                            </div>
                                            <button onclick="devolverCautelaManual(${c.id})" class="text-[10px] text-slate-400 hover:text-rose-400 transition-colors p-1" title="Finalizar uso deste PC">
                                                <span class="material-symbols-rounded text-base">close</span>
                                            </button>
                                        </div>
                                    `).join('')}
                                </div>
                            ` : `
                                <p class="text-xs text-slate-500 py-3 text-center bg-slate-900/30 rounded-xl">Nenhum aluno registrou PC ainda.<br>Os alunos devem escanear a etiqueta do monitor.</p>
                            `}
                        </div>

                        <div class="pt-2 mt-auto">
                            <button onclick="encerrarTurnoManual(${lab.id})" class="w-full py-2.5 bg-rose-950/40 hover:bg-rose-950/70 border border-rose-800/40 text-rose-300 font-bold rounded-xl text-xs flex items-center justify-center gap-1.5 transition-colors">
                                <span class="material-symbols-rounded text-base">stop_circle</span> Encerrar Aula & Liberar PCs
                            </button>
                        </div>
                    ` : `
                        <div class="bg-slate-900/40 border border-slate-700/40 rounded-xl p-4 text-center my-auto">
                            <span class="material-symbols-rounded text-slate-500 text-3xl">meeting_room</span>
                            <p class="text-xs text-slate-400 mt-2 font-medium">Laboratório livre no momento</p>
                        </div>
                    `}
                </div>`;
            };

            const html = labs.map(renderCard).join('');
            const gridProf = document.getElementById('grid-laboratorios');
            if (gridProf) gridProf.innerHTML = html;

            const gridSec = document.getElementById('grid-laboratorios-secretaria');
            if (gridSec) gridSec.innerHTML = html;
        })
        .catch(() => {});
}

function encerrarTurnoManual(labId) {
    if (!confirm('Deseja encerrar este turno? Os registros de uso ativos da sala serão finalizados.')) return;

    fetch(`${API}/api/laboratorios/${labId}/encerrar`, { method: 'POST' })
        .then(r => r.json())
        .then(d => {
            showToast('Turno Encerrado', d.mensagem, 'sucesso');
            carregarLaboratorios();
            carregarHistorico();
            if (usuarioTipo === 'secretaria') carregarStats();
        })
        .catch(() => showToast('Erro', 'Falha ao encerrar turno.', 'erro'));
}

function devolverCautelaManual(cautelaId) {
    fetch(`${API}/api/cautelas/${cautelaId}/devolver`, { method: 'POST' })
        .then(r => r.json())
        .then(d => {
            showToast('Uso Finalizado', d.mensagem, 'sucesso');
            carregarLaboratorios();
            carregarHistorico();
            if (usuarioTipo === 'secretaria') carregarStats();
        })
        .catch(() => showToast('Erro', 'Falha ao finalizar o uso do PC.', 'erro'));
}

// ============================================================
// CICLO DE ATUALIZAÇÃO EM TEMPO REAL (POLLING A CADA 2.5s)
// ============================================================
setInterval(() => {
    if (usuarioTipo === 'professor') {
        carregarLaboratorios();
    } else if (usuarioTipo === 'secretaria') {
        carregarFilaCrachas();
        carregarLeiturasRecentes();
        carregarLaboratorios();
        carregarProfessores();
        carregarStats();
        carregarHistorico();
    }
}, 2500);

// Enter no login
document.getElementById('input-email').addEventListener('keypress', e => {
    if (e.key === 'Enter') document.getElementById('input-senha').focus();
});
document.getElementById('input-senha').addEventListener('keypress', e => {
    if (e.key === 'Enter') fazerLogin();
});

// Partículas
particlesJS('particles-js', {
    "particles": {
        "number": { "value": 55, "density": { "enable": true, "value_area": 800 } },
        "color": { "value": "#E3000F" },
        "shape": { "type": "circle" },
        "opacity": { "value": 0.35, "random": false },
        "size": { "value": 2.5, "random": true },
        "line_linked": { "enable": true, "distance": 150, "color": "#E3000F", "opacity": 0.2, "width": 1 },
        "move": { "enable": true, "speed": 2.5, "direction": "none", "random": false, "straight": false, "out_mode": "out", "bounce": false }
    },
    "interactivity": {
        "detect_on": "canvas",
        "events": { "onhover": { "enable": true, "mode": "grab" }, "onclick": { "enable": true, "mode": "push" }, "resize": true },
        "modes": { "grab": { "distance": 140, "line_linked": { "opacity": 0.6 } }, "push": { "particles_nb": 3 } }
    },
    "retina_detect": true
});
