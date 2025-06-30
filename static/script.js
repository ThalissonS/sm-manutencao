document.addEventListener('DOMContentLoaded', () => {
    const formManutencao = document.getElementById('form-manutencao');
    const tabelaCorpo = document.getElementById('tabela-corpo');
    const formTitle = document.getElementById('form-title');
    const editIdInput = document.getElementById('edit-id');
    const btnSalvar = document.getElementById('btn-salvar');
    const btnCancelar = document.getElementById('btn-cancelar');
    const btnFiltrar = document.getElementById('btn-filtrar');
    const filtroTermo = document.getElementById('filtro-termo');
    const filtroDataInicio = document.getElementById('filtro-data-inicio');
    const filtroDataFim = document.getElementById('filtro-data-fim');
    const btnExportar = document.getElementById('btn-exportar');
    const formImportar = document.getElementById('form-importar');
    const inputArquivo = document.getElementById('arquivo-excel');

    const entrarModoEdicao = () => {
        formTitle.innerText = 'Editar Manutenção';
        btnSalvar.innerText = 'Salvar Alterações';
        btnCancelar.style.display = 'inline-block';
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    const sairModoEdicao = () => {
        formTitle.innerText = 'Registrar Nova Manutenção';
        btnSalvar.innerText = 'Salvar Manutenção';
        btnCancelar.style.display = 'none';
        editIdInput.value = '';
        formManutencao.reset();
    };

    const getFiltros = () => {
        const params = new URLSearchParams();
        if (filtroTermo.value) {
            params.append('termo', filtroTermo.value);
        }
        if (filtroDataInicio.value) {
            params.append('data_inicio', filtroDataInicio.value);
        }
        if (filtroDataFim.value) {
            params.append('data_fim', filtroDataFim.value);
        }
        return params;
    };

    const carregarManutencoes = async () => {
        const params = getFiltros();
        const url = `/api/manutencoes?${params.toString()}`;
        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error(`Erro HTTP: ${response.status}`);
            const manutencoes = await response.json();
            tabelaCorpo.innerHTML = '';
            if (manutencoes.length === 0) {
                tabelaCorpo.innerHTML = '<tr><td colspan="8" style="text-align: center;">Nenhum registro encontrado.</td></tr>';
                return;
            }
            manutencoes.forEach(m => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${m.serie_empacotadeira}</td>
                    <td>${m.data}</td>
                    <td>${m.num_equipamento || '-'}</td>
                    <td>${m.descricao}</td>
                    <td>${m.solicitante}</td>
                    <td>${m.responsavel}</td>
                    <td>${m.valor.replace('.', ',')}</td>
                    <td>
                        <div class="grid">
                            <button class="btn-editar" data-id="${m.id}">Editar</button>
                            <button class="btn-excluir secondary" data-id="${m.id}">Excluir</button>
                        </div>
                    </td>
                `;
                tabelaCorpo.appendChild(tr);
            });
        } catch (error) {
            console.error("Falha ao carregar manutenções:", error);
            tabelaCorpo.innerHTML = '<tr><td colspan="8" style="text-align: center;">Erro ao carregar os dados.</td></tr>';
        }
    };

    formManutencao.addEventListener('submit', async (event) => {
        event.preventDefault();
        const formData = new FormData(formManutencao);
        const dados = Object.fromEntries(formData.entries());
        dados.valor = parseFloat(dados.valor);
        const id = editIdInput.value;
        const isEditMode = id !== '';
        const url = isEditMode ? `/api/manutencao/${id}` : '/api/manutencoes';
        const method = isEditMode ? 'PUT' : 'POST';
        try {
            const response = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(dados)
            });
            if (!response.ok) {
                const erro = await response.json();
                throw new Error(erro.erro || `Erro HTTP: ${response.status}`);
            }
            sairModoEdicao();
            carregarManutencoes();
        } catch (error) {
            console.error("Falha ao salvar:", error);
            alert(`Não foi possível salvar: ${error.message}`);
        }
    });

    tabelaCorpo.addEventListener('click', async (event) => {
        const target = event.target;
        if (target.classList.contains('btn-excluir')) {
            const id = target.dataset.id;
            if (confirm('Tem certeza que deseja excluir este registro? Esta ação não pode ser desfeita.')) {
                try {
                    const response = await fetch(`/api/manutencao/${id}`, { method: 'DELETE' });
                    if (!response.ok) throw new Error('Falha ao excluir.');
                    carregarManutencoes();
                } catch (error) {
                    alert(error.message);
                }
            }
        }
        if (target.classList.contains('btn-editar')) {
            const id = target.dataset.id;
            try {
                const response = await fetch(`/api/manutencao/${id}`);
                if (!response.ok) throw new Error('Não foi possível carregar os dados para edição.');
                const dados = await response.json();
                document.getElementById('edit-id').value = dados.id;
                document.getElementById('serie_empacotadeira').value = dados.serie_empacotadeira;
                document.getElementById('data').value = dados.data_iso;
                document.getElementById('num_equipamento').value = dados.num_equipamento || '';
                document.getElementById('descricao').value = dados.descricao;
                document.getElementById('solicitante').value = dados.solicitante;
                document.getElementById('responsavel').value = dados.responsavel;
                document.getElementById('valor').value = dados.valor;
                entrarModoEdicao();
            } catch (error) {
                alert(error.message);
            }
        }
    });
    
    btnCancelar.addEventListener('click', sairModoEdicao);
    btnFiltrar.addEventListener('click', carregarManutencoes);
    btnExportar.addEventListener('click', () => {
        const params = getFiltros();
        const url = `/api/exportar?${params.toString()}`;
        window.location.href = url;
    });

    formImportar.addEventListener('submit', async (event) => {
        event.preventDefault();
        if (!inputArquivo.files || inputArquivo.files.length === 0) {
            alert('Por favor, selecione um arquivo para importar.');
            return;
        }
        const arquivo = inputArquivo.files[0];
        const formData = new FormData();
        formData.append('arquivo', arquivo);
        const submitButton = formImportar.querySelector('button[type="submit"]');
        const originalButtonText = submitButton.innerText;
        submitButton.disabled = true;
        submitButton.innerText = 'Importando...';
        try {
            const response = await fetch('/api/importar', {
                method: 'POST',
                body: formData,
            });
            const resultado = await response.json();
            if (!response.ok) {
                throw new Error(resultado.erro || 'Ocorreu um erro desconhecido.');
            }
            alert(resultado.mensagem);
            carregarManutencoes();
        } catch (error) {
            console.error('Erro na importação:', error);
            alert(`Falha na importação: ${error.message}`);
        } finally {
            formImportar.reset();
            submitButton.disabled = false;
            submitButton.innerText = originalButtonText;
        }
    });

    carregarManutencoes();
});