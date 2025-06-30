document.addEventListener('DOMContentLoaded', () => {
    // --- Seletores Globais ---
    const tabelaCorpo = document.getElementById('tabela-corpo');
    
    // --- Formulário de Manutenção ---
    const formManutencao = document.getElementById('form-manutencao');
    const formTitle = document.getElementById('form-title');
    const editIdInput = document.getElementById('edit-id');
    const btnSalvar = document.getElementById('btn-salvar');
    const btnCancelar = document.getElementById('btn-cancelar');
    const dropdownMaquinas = document.getElementById('maquina-select');
    const dropdownSolicitantes = document.getElementById('solicitante-select');
    const dropdownResponsaveis = document.getElementById('responsavel-select');
    const pecasContainer = document.getElementById('pecas-container');
    const btnAdicionarPeca = document.getElementById('btn-adicionar-peca');

    // --- Modais ---
    const modals = {
        maquinas: { dialog: document.getElementById('modal-maquinas'), form: document.getElementById('form-maquina'), tableBody: document.getElementById('tabela-maquinas'), openBtn: document.getElementById('btn-gerenciar-maquinas'), closeBtn: document.getElementById('btn-fechar-modal-maquinas'), editIdInput: document.getElementById('maquina-edit-id'), saveBtn: document.getElementById('btn-salvar-maquina'), cancelBtn: document.getElementById('btn-cancelar-maquina'), inputs: { nome: document.getElementById('maquina-nome'), serie: document.getElementById('maquina-serie') }, onUpdate: () => carregarMaquinas() },
        pecas: { dialog: document.getElementById('modal-pecas'), form: document.getElementById('form-peca'), tableBody: document.getElementById('tabela-pecas'), openBtn: document.getElementById('btn-gerenciar-pecas'), closeBtn: document.getElementById('btn-fechar-modal-pecas'), editIdInput: document.getElementById('peca-edit-id'), saveBtn: document.getElementById('btn-salvar-peca'), cancelBtn: document.getElementById('btn-cancelar-peca'), inputs: { nome: document.getElementById('peca-nome') }, onUpdate: () => carregarPecas() },
        solicitantes: { dialog: document.getElementById('modal-solicitantes'), form: document.getElementById('form-solicitante'), tableBody: document.getElementById('tabela-solicitantes'), openBtn: document.getElementById('btn-gerenciar-solicitantes'), closeBtn: document.getElementById('btn-fechar-modal-solicitantes'), editIdInput: document.getElementById('solicitante-edit-id'), saveBtn: document.getElementById('btn-salvar-solicitante'), cancelBtn: document.getElementById('btn-cancelar-solicitante'), inputs: { nome: document.getElementById('solicitante-nome') }, onUpdate: () => carregarSolicitantes() },
        responsaveis: { dialog: document.getElementById('modal-responsaveis'), form: document.getElementById('form-responsavel'), tableBody: document.getElementById('tabela-responsaveis'), openBtn: document.getElementById('btn-gerenciar-responsaveis'), closeBtn: document.getElementById('btn-fechar-modal-responsaveis'), editIdInput: document.getElementById('responsavel-edit-id'), saveBtn: document.getElementById('btn-salvar-responsavel'), cancelBtn: document.getElementById('btn-cancelar-responsavel'), inputs: { nome: document.getElementById('responsavel-nome') }, onUpdate: () => carregarResponsaveis() }
    };
    
    // --- Filtros e Ações ---
    const btnFiltrar = document.getElementById('btn-filtrar');
    const filtroTermo = document.getElementById('filtro-termo');
    const filtroDataInicio = document.getElementById('filtro-data-inicio');
    const filtroDataFim = document.getElementById('filtro-data-fim');
    const btnExportar = document.getElementById('btn-exportar');

    // --- Variáveis de Estado ---
    let catalogoPecas = [], catalogoMaquinas = [], catalogoSolicitantes = [], catalogoResponsaveis = [];
    const currencyFormatter = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });

    // --- Funções de Estado da UI ---
    const entrarModoEdicaoManutencao = () => { formTitle.innerText = 'Editar Manutenção'; btnSalvar.innerText = 'Salvar Alterações'; btnCancelar.style.display = 'inline-block'; window.scrollTo({ top: 0, behavior: 'smooth' }); };
    const sairModoEdicaoManutencao = () => { formTitle.innerText = 'Registrar Nova Manutenção'; btnSalvar.innerText = 'Salvar Manutenção'; btnCancelar.style.display = 'none'; editIdInput.value = ''; formManutencao.reset(); pecasContainer.innerHTML = ''; adicionarLinhaPeca(); };

    // --- Lógica de Peças (Formulário Principal) ---
    const adicionarLinhaPeca = (pecaUtilizada = { peca_id: '', quantidade: 1 }) => {
        const div = document.createElement('div');
        div.className = 'grid peca-linha';
        let optionsHtml = '<option value="" disabled selected>Selecione uma peça</option>';
        catalogoPecas.forEach(p => {
            const isSelected = p.id == pecaUtilizada.peca_id ? 'selected' : '';
            optionsHtml += `<option value="${p.id}" ${isSelected}>${p.nome}</option>`;
        });
        div.innerHTML = `<select name="peca_id" required>${optionsHtml}</select><input type="number" name="quantidade" placeholder="Qtd" value="${pecaUtilizada.quantidade}" min="1" required><button type="button" class="btn-remover-peca secondary outline" aria-label="Remover Peça">×</button>`;
        pecasContainer.appendChild(div);
    };

    // --- Lógica de Carregamento de Dados ---
    const fetchData = async (url) => { const response = await fetch(url); if (response.redirected) { window.location.href = response.url; throw new Error("Redirected"); } if (!response.ok) throw new Error('Falha na rede'); return response.json(); };
    const getFiltros = () => { const params = new URLSearchParams(); if (filtroTermo.value) { params.append('termo', filtroTermo.value); } if (filtroDataInicio.value) { params.append('data_inicio', filtroDataInicio.value); } if (filtroDataFim.value) { params.append('data_fim', filtroDataFim.value); } return params; };

    const carregarTudo = () => { Promise.all([carregarMaquinas(), carregarPecas(), carregarSolicitantes(), carregarResponsaveis()]).then(() => carregarManutencoes()); };
    const carregarMaquinas = async () => { catalogoMaquinas = await fetchData('/api/maquinas'); popularDropdown(dropdownMaquinas, catalogoMaquinas, 'Selecione a máquina', item => `${item.nome} (${item.serie})`); popularTabelaModal('maquinas'); };
    const carregarPecas = async () => { catalogoPecas = await fetchData('/api/pecas'); atualizarDropdownsDePecas(); popularTabelaModal('pecas'); };
    const carregarSolicitantes = async () => { catalogoSolicitantes = await fetchData('/api/solicitantes'); popularDropdown(dropdownSolicitantes, catalogoSolicitantes, 'Selecione o solicitante'); popularTabelaModal('solicitantes'); };
    const carregarResponsaveis = async () => { catalogoResponsaveis = await fetchData('/api/responsaveis'); popularDropdown(dropdownResponsaveis, catalogoResponsaveis, 'Selecione o responsável'); popularTabelaModal('responsaveis'); };
    
    const popularDropdown = (dropdown, items, placeholder, formatter = item => item.nome) => {
        const valorAtual = dropdown.value;
        dropdown.innerHTML = `<option value="" disabled selected>${placeholder}</option>`;
        items.forEach(item => { const option = document.createElement('option'); option.value = item.id; option.textContent = formatter(item); dropdown.appendChild(option); });
        dropdown.value = valorAtual;
    };
    const atualizarDropdownsDePecas = () => document.querySelectorAll('.peca-linha select[name="peca_id"]').forEach(dropdown => popularDropdown(dropdown, catalogoPecas, 'Selecione uma peça'));

    const popularTabelaModal = (tipo) => {
        const modal = modals[tipo];
        const items = tipo === 'maquinas' ? catalogoMaquinas : (tipo === 'pecas' ? catalogoPecas : (tipo === 'solicitantes' ? catalogoSolicitantes : catalogoResponsaveis));
        modal.tableBody.innerHTML = '';
        if (items.length === 0) { modal.tableBody.innerHTML = `<tr><td colspan="3" style="text-align: center;">Nenhum item cadastrado.</td></tr>`; return; }
        items.forEach(item => {
            const tr = document.createElement('tr');
            const dataAttrs = Object.keys(item).map(key => `data-${key}="${item[key]}"`).join(' ');
            const nomeTd = `<td>${item.nome}</td>`;
            const extraTd = tipo === 'maquinas' ? `<td>${item.serie}</td>` : '';
            tr.innerHTML = `${nomeTd}${extraTd}<td><div class="acoes-grid"><button class="btn-editar btn-acao" ${dataAttrs} title="Editar"><i class="fas fa-pencil-alt"></i></button><button class="btn-excluir btn-acao secondary" data-id="${item.id}" title="Excluir"><i class="fas fa-trash-alt"></i></button></div></td>`;
            modal.tableBody.appendChild(tr);
        });
    };

    const carregarManutencoes = async () => {
        const params = getFiltros();
        const url = `/api/manutencoes?${params.toString()}`;
        try {
            const manutencoes = await fetchData(url);
            tabelaCorpo.innerHTML = '';
            if (manutencoes.length === 0) { tabelaCorpo.innerHTML = '<tr><td colspan="8" style="text-align: center;">Nenhuma manutenção encontrada.</td></tr>'; return; }
            manutencoes.forEach(m => {
                const tr = document.createElement('tr');
                const pecasHtml = m.pecas_utilizadas.length > 0 ? `<ul>${m.pecas_utilizadas.map(p => `<li>${p.quantidade}x ${p.nome_peca}</li>`).join('')}</ul>` : '-';
                tr.innerHTML = `<td>${m.maquina_nome} (${m.maquina_serie})</td><td>${m.data}</td><td>${m.descricao}</td><td>${pecasHtml}</td><td>${m.solicitante_nome}</td><td>${m.responsavel_nome}</td><td>${currencyFormatter.format(m.valor)}</td><td><div class="acoes-grid"><button class="btn-editar-manutencao btn-acao" data-id="${m.id}" title="Editar"><i class="fas fa-pencil-alt"></i></button><button class="btn-excluir-manutencao btn-acao secondary" data-id="${m.id}" title="Excluir"><i class="fas fa-trash-alt"></i></button></div></td>`;
                tabelaCorpo.appendChild(tr);
            });
        } catch (error) { if (error.message !== "Redirected") { console.error("Falha:", error); tabelaCorpo.innerHTML = '<tr><td colspan="8" style="text-align: center;">Erro ao carregar dados.</td></tr>';} }
    };

    // --- Lógica de Modais Genérica ---
    const sendData = async (url, method, data) => { const response = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); const result = await response.json(); if (!response.ok) throw new Error(result.erro || 'Erro desconhecido'); return result; };
    const setupModalEventListeners = (tipo) => {
        const modal = modals[tipo];
        const endpoint = `/api/${tipo.slice(0, -1)}`;
        modal.openBtn.addEventListener('click', () => modal.dialog.showModal());
        modal.closeBtn.addEventListener('click', () => modal.dialog.close());
        modal.cancelBtn.addEventListener('click', () => sairModal(tipo));
        modal.form.addEventListener('submit', async (event) => {
            event.preventDefault();
            const id = modal.editIdInput.value;
            const data = {};
            for (const key in modal.inputs) { data[key] = modal.inputs[key].value; }
            try {
                await sendData(id ? `${endpoint}/${id}` : `/api/${tipo}`, id ? 'PUT' : 'POST', data);
                sairModal(tipo);
                modal.onUpdate();
            } catch (error) { alert(`Erro: ${error.message}`); }
        });
        modal.tableBody.addEventListener('click', async (event) => {
            const target = event.target.closest('.btn-acao');
            if (!target) return;
            const id = target.dataset.id;
            if (target.classList.contains('btn-excluir')) {
                const confirmMsg = tipo === 'maquinas' ? 'Tem certeza? Todas as manutenções associadas serão excluídas.' : 'Tem certeza?';
                if (confirm(confirmMsg)) {
                    try {
                        await sendData(`${endpoint}/${id}`, 'DELETE');
                        modal.onUpdate();
                    } catch (error) { alert(`Erro: ${error.message}`); }
                }
            } else if (target.classList.contains('btn-editar')) {
                modal.editIdInput.value = id;
                for (const key in modal.inputs) { modal.inputs[key].value = target.dataset[key]; }
                modal.saveBtn.innerText = 'Salvar Alterações';
                modal.cancelBtn.style.display = 'inline-block';
                modal.inputs.nome.focus();
            }
        });
    };
    const sairModal = (tipo) => { modals[tipo].editIdInput.value = ''; modals[tipo].form.reset(); modals[tipo].saveBtn.innerText = `Adicionar ${tipo.charAt(0).toUpperCase() + tipo.slice(1, -1)}`; modals[tipo].cancelBtn.style.display = 'none'; };
    ['maquinas', 'pecas', 'solicitantes', 'responsaveis'].forEach(setupModalEventListeners);

    // --- Listeners da Página Principal ---
    formManutencao.addEventListener('submit', async (event) => {
        event.preventDefault();
        const dadosManutencao = { maquina_id: dropdownMaquinas.value, data: document.getElementById('data').value, descricao: document.getElementById('descricao').value, solicitante_id: dropdownSolicitantes.value, responsavel_id: dropdownResponsaveis.value, valor: parseFloat(document.getElementById('valor').value), pecas: [] };
        document.querySelectorAll('.peca-linha').forEach(linha => {
            const pecaId = linha.querySelector('select[name="peca_id"]').value;
            const quantidade = linha.querySelector('input[name="quantidade"]').value;
            if (pecaId && quantidade) { dadosManutencao.pecas.push({ peca_id: pecaId, quantidade: parseInt(quantidade) }); }
        });
        const id = editIdInput.value;
        const url = id ? `/api/manutencao/${id}` : '/api/manutencoes';
        const method = id ? 'PUT' : 'POST';
        try {
            const response = await fetch(url, { method: method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(dadosManutencao) });
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                const resultado = await response.json();
                if (!response.ok) { throw new Error(resultado.erro || `Erro HTTP: ${response.status}`); }
                alert(resultado.mensagem);
                sairModoEdicaoManutencao();
                carregarManutencoes();
            } else { throw new Error('A sua sessão expirou. A página será recarregada.'); }
        } catch (error) {
            console.error("Falha ao salvar:", error);
            alert(`Não foi possível salvar: ${error.message}`);
            if (error.message.includes('sessão expirou')) { window.location.reload(); }
        }
    });

    tabelaCorpo.addEventListener('click', async (event) => {
        const target = event.target.closest('.btn-acao');
        if (!target) return;
        const id = target.dataset.id;
        if (target.classList.contains('btn-excluir-manutencao')) {
            if (confirm('Tem certeza que deseja excluir este registro?')) {
                try {
                    const response = await fetch(`/api/manutencao/${id}`, { method: 'DELETE' });
                    if (!response.ok) throw new Error('Falha ao excluir.');
                    carregarManutencoes();
                } catch (error) { alert(error.message); }
            }
        }
        if (target.classList.contains('btn-editar-manutencao')) {
            try {
                const response = await fetch(`/api/manutencao/${id}`);
                if (!response.ok) throw new Error('Não foi possível carregar dados.');
                const dados = await response.json();
                editIdInput.value = dados.id;
                dropdownMaquinas.value = dados.maquina_id;
                dropdownSolicitantes.value = dados.solicitante_id;
                dropdownResponsaveis.value = dados.responsavel_id;
                document.getElementById('data').value = dados.data_iso;
                document.getElementById('descricao').value = dados.descricao;
                document.getElementById('valor').value = dados.valor;
                pecasContainer.innerHTML = '';
                if(dados.pecas_utilizadas.length > 0) { dados.pecas_utilizadas.forEach(p => adicionarLinhaPeca(p)); } 
                else { adicionarLinhaPeca(); }
                entrarModoEdicaoManutencao();
            } catch (error) { alert(error.message); }
        }
    });
    
    btnAdicionarPeca.addEventListener('click', adicionarLinhaPeca);
    pecasContainer.addEventListener('click', (event) => { if (event.target.classList.contains('btn-remover-peca')) { event.target.closest('.peca-linha').remove(); } });
    btnCancelar.addEventListener('click', sairModoEdicaoManutencao);
    btnFiltrar.addEventListener('click', carregarManutencoes);
    btnExportar.addEventListener('click', () => { const params = getFiltros(); window.location.href = `/api/exportar?${params.toString()}`; });
    
    // --- Inicialização da Página ---
    carregarTudo();
    adicionarLinhaPeca();
});