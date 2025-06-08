// static/js/main.js

document.addEventListener('DOMContentLoaded', function () {
    console.log("DOM Carregado. Iniciando main.js...");

    // Elementos do DOM
    const filtrosAtivosContainer = document.getElementById('filtrosAtivosContainer');
    const filtrosAtivosTexto = document.getElementById('filtrosAtivosTexto');
    const linkLimparFiltrosRapido = document.getElementById('linkLimparFiltrosRapido');

    const ufsContainer = document.getElementById('ufsContainerDropdown');
    const municipiosSelect = document.getElementById('municipios');
    const municipiosHelp = document.getElementById('municipiosHelp');
    const modalidadesContainer = document.getElementById('modalidadesContainerDropdown'); 
    const statusContainer = document.getElementById('statusContainer');
    const statusWarning = document.getElementById('statusWarning');
    const palavraChaveInclusaoInput = document.getElementById('palavraChaveInclusao');
    const palavraChaveExclusaoInput = document.getElementById('palavraChaveExclusao');
    const dataPubInicioInput = document.getElementById('dataPubInicio');
    const dataPubFimInput = document.getElementById('dataPubFim');
    const dataAtualizacaoInicioInput = document.getElementById('dataAtualizacaoInicio'); // Você precisará adicionar este input no HTML
    const dataAtualizacaoFimInput = document.getElementById('dataAtualizacaoFim');     // e este também
    const valorMinInput = document.getElementById('valorMin');
    const valorMaxInput = document.getElementById('valorMax');
    const btnBuscarLicitacoes = document.getElementById('btnBuscarLicitacoes');
    const btnLimparFiltros = document.getElementById('btnLimparFiltros');    
    const licitacoesTableBody = document.getElementById('licitacoesTableBody');
    const paginationControls = document.getElementById('paginationControls');
    const totalRegistrosInfo = document.getElementById('totalRegistrosInfo');
    const exibicaoInfo = document.getElementById('exibicaoInfo');
    const ordenarPorSelect = document.getElementById('ordenarPor');
    const itensPorPaginaSelect = document.getElementById('itensPorPagina');
    const palavraChaveInclusaoInputField = document.getElementById('palavraChaveInclusaoInput'); // Novo ID
    //const btnAddPalavraInclusao = document.getElementById('btnAddPalavraInclusao');
    const tagsPalavraInclusaoContainer = document.getElementById('tagsPalavraInclusaoContainer');
    const palavraChaveExclusaoInputField = document.getElementById('palavraChaveExclusaoInput'); // Novo ID
    //const btnAddPalavraExclusao = document.getElementById('btnAddPalavraExclusao');
    const tagsPalavraExclusaoContainer = document.getElementById('tagsPalavraExclusaoContainer');
    const loadingOverlay = document.getElementById('loadingOverlay');

    if(linkLimparFiltrosRapido) { // Garante que o elemento existe
        linkLimparFiltrosRapido.addEventListener('click', function(e){
            e.preventDefault(); // Previne o comportamento padrão do link (navegar para #)
            console.log("Link Limpar Filtros Rápido clicado"); // Para debug
            limparFiltros(); // Chama a função principal de limpar filtros
        });
    }
    // Arrays para armazenar as palavras-chave
    let palavrasChaveInclusao = [];
    let palavrasChaveExclusao = [];
    // Estado da Aplicação (para filtros, paginação, etc.)
    let currentPage = 1;
    
    // --- CONFIGURAÇÕES DE FILTROS ---
    const ufsLista = [ /* ... sua lista de UFs ... */ 
        { sigla: "AC", nome: "Acre" }, { sigla: "AL", nome: "Alagoas" }, { sigla: "AP", nome: "Amapá" },
        { sigla: "AM", nome: "Amazonas" }, { sigla: "BA", nome: "Bahia" }, { sigla: "CE", nome: "Ceará" },
        { sigla: "DF", nome: "Distrito Federal" }, { sigla: "ES", nome: "Espírito Santo" }, { sigla: "GO", nome: "Goiás" },
        { sigla: "MA", nome: "Maranhão" }, { sigla: "MT", nome: "Mato Grosso" }, { sigla: "MS", nome: "Mato Grosso do Sul" },
        { sigla: "MG", nome: "Minas Gerais" }, { sigla: "PA", nome: "Pará" }, { sigla: "PB", nome: "Paraíba" },
        { sigla: "PR", nome: "Paraná" }, { sigla: "PE", nome: "Pernambuco" }, { sigla: "PI", nome: "Piauí" },
        { sigla: "RJ", nome: "Rio de Janeiro" }, { sigla: "RN", nome: "Rio Grande do Norte" }, { sigla: "RS", nome: "Rio Grande do Sul" },
        { sigla: "RO", nome: "Rondônia" }, { sigla: "RR", nome: "Roraima" }, { sigla: "SC", nome: "Santa Catarina" },
        { sigla: "SP", nome: "São Paulo" }, { sigla: "SE", nome: "Sergipe" }, { sigla: "TO", nome: "Tocantins" }
    ];

    // FUNÇÃO DE TAGS NAS PALAVRAS-CHAVE
    function renderTags(palavrasArray, containerElement, tipo) { // tipo pode ser 'inclusao' ou 'exclusao'
        containerElement.innerHTML = ''; // Limpa tags existentes
        palavrasArray.forEach((palavra, index) => {
            const tag = document.createElement('span');
            tag.classList.add('tag-item');
            tag.textContent = palavra;
            
            const removeBtn = document.createElement('button');
            removeBtn.classList.add('remove-tag');
            removeBtn.innerHTML = '×'; // Caractere 'x'
            removeBtn.title = 'Remover palavra';
            removeBtn.addEventListener('click', () => {
                if (tipo === 'inclusao') {
                    palavrasChaveInclusao.splice(index, 1);
                    renderTags(palavrasChaveInclusao, tagsPalavraInclusaoContainer, 'inclusao');
                } else if (tipo === 'exclusao') {
                    palavrasChaveExclusao.splice(index, 1);
                    renderTags(palavrasChaveExclusao, tagsPalavraExclusaoContainer, 'exclusao');
                }
            });
            tag.appendChild(removeBtn);
            containerElement.appendChild(tag);
        });
    }

    function addPalavraChave(inputField, palavrasArray, containerElement, tipo) {
        const termos = inputField.value.trim();
        if (termos) {
            // Divide por vírgula ou ponto e vírgula, e limpa cada termo
            const novasPalavras = termos.split(/[,;]+/).map(p => p.trim()).filter(p => p !== "");
            
            novasPalavras.forEach(novaPalavra => {
                if (novaPalavra && !palavrasArray.includes(novaPalavra)) { // Evita duplicatas
                    palavrasArray.push(novaPalavra);
                }
            });
            inputField.value = ''; // Limpa o input
            renderTags(palavrasArray, containerElement, tipo);
        }
    }

    // Event Listeners para adicionar palavras-chave
    if (palavraChaveInclusaoInputField) {
        palavraChaveInclusaoInputField.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' || e.key === ',') {
                e.preventDefault(); 
                addPalavraChave(palavraChaveInclusaoInputField, palavrasChaveInclusao, tagsPalavraInclusaoContainer, 'inclusao');
            }
        });
    }

    if (palavraChaveExclusaoInputField) {
        palavraChaveExclusaoInputField.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' || e.key === ',') {
                e.preventDefault();
                addPalavraChave(palavraChaveExclusaoInputField, palavrasChaveExclusao, tagsPalavraExclusaoContainer, 'exclusao');
            }
        });
    }// FIM DA FUNÇÃO DE TAGS NAS PALAVRAS-CHAVE

    // FUNÇÃO DAS TAGS NO TOPO
    function atualizarExibicaoFiltrosAtivos() {
        if (!filtrosAtivosContainer || !filtrosAtivosTexto) return;

        let filtrosAplicados = [];

        // Palavras-chave de Inclusão
        if (palavrasChaveInclusao.length > 0) {
            filtrosAplicados.push(`Buscar: ${palavrasChaveInclusao.map(p => `<span class="badge bg-primary">${p}</span>`).join(' ')}`);
        }
        // Palavras-chave de Exclusão
        if (palavrasChaveExclusao.length > 0) {
            filtrosAplicados.push(`Excluir: ${palavrasChaveExclusao.map(p => `<span class="badge bg-danger">${p}</span>`).join(' ')}`);
        }
        // UFs
        const ufsSelecionadas = Array.from(document.querySelectorAll('#ufsContainerDropdown .filter-uf:checked')).map(cb => cb.value);
        if (ufsSelecionadas.length > 0) {
            filtrosAplicados.push(`UF: ${ufsSelecionadas.map(uf => `<span class="badge bg-secondary">${uf}</span>`).join(' ')}`);
        }
        // Municípios
        const municipiosSelecionados = Array.from(document.querySelectorAll('#municipiosContainerDropdown .filter-municipio:checked')).map(cb => cb.value);
        if (municipiosSelecionados.length > 0) {
            filtrosAplicados.push(`Município: ${municipiosSelecionados.map(m => `<span class="badge bg-info text-dark">${m}</span>`).join(' ')}`);
        }
        // Modalidades
        const modalidadesSelecionadas = Array.from(document.querySelectorAll('#modalidadesContainerDropdown .filter-modalidade:checked'))
                                        .map(cb => {
                                            const label = document.querySelector(`label[for="${cb.id}"]`);
                                            return label ? label.textContent : cb.value; // Pega o nome do label
                                        });
        if (modalidadesSelecionadas.length > 0) {
            filtrosAplicados.push(`Modalidade: ${modalidadesSelecionadas.map(m => `<span class="badge bg-warning text-dark">${m}</span>`).join(' ')}`);
        }
        // Status
        const statusSelecionadoRadio = document.querySelector('.filter-status:checked');
        if (statusSelecionadoRadio && statusSelecionadoRadio.value) { // Se não for "Todos"
            const labelStatus = document.querySelector(`label[for="${statusSelecionadoRadio.id}"]`);
            filtrosAplicados.push(`Status: <span class="badge bg-success">${labelStatus ? labelStatus.textContent : statusSelecionadoRadio.value}</span>`);
        } else if (statusSelecionadoRadio && statusSelecionadoRadio.value === "") {
            filtrosAplicados.push(`Status: <span class="badge bg-dark">Todos</span>`);
        }


        // Datas Publicação
        if (dataPubInicioInput.value || dataPubFimInput.value) {
            let strDataPub = "Data Pub.: ";
            if (dataPubInicioInput.value) strDataPub += `de ${new Date(dataPubInicioInput.value+'T00:00:00').toLocaleDateString('pt-BR')} `;
            if (dataPubFimInput.value) strDataPub += `até ${new Date(dataPubFimInput.value+'T00:00:00').toLocaleDateString('pt-BR')}`;
            filtrosAplicados.push(`<span class="badge bg-light text-dark border">${strDataPub.trim()}</span>`);
        }
        // Datas Atualização (SE OS INPUTS EXISTIREM)
        if (dataAtualizacaoInicioInput && dataAtualizacaoFimInput && (dataAtualizacaoInicioInput.value || dataAtualizacaoFimInput.value)) {
            let strDataAtual = "Data Atual.: ";
            if (dataAtualizacaoInicioInput.value) strDataAtual += `de ${new Date(dataAtualizacaoInicioInput.value+'T00:00:00').toLocaleDateString('pt-BR')} `;
            if (dataAtualizacaoFimInput.value) strDataAtual += `até ${new Date(dataAtualizacaoFimInput.value+'T00:00:00').toLocaleDateString('pt-BR')}`;
            filtrosAplicados.push(`<span class="badge bg-light text-dark border">${strDataAtual.trim()}</span>`);
        }
        // Valor
        if (valorMinInput.value || valorMaxInput.value) {
            let strValor = "Valor: ";
            if (valorMinInput.value) strValor += `min R$ ${valorMinInput.value} `;
            if (valorMaxInput.value) strValor += `max R$ ${valorMaxInput.value}`;
            filtrosAplicados.push(`<span class="badge bg-light text-dark border">${strValor.trim()}</span>`);
        }


        if (filtrosAplicados.length > 0) {
            filtrosAtivosTexto.innerHTML = filtrosAplicados.join(' • '); // Separador • é um ponto
            filtrosAtivosContainer.style.display = 'block';
        } else {
            filtrosAtivosTexto.innerHTML = 'Nenhum filtro aplicado.';
            // filtrosAtivosContainer.style.display = 'none'; // Ou mostrar "Nenhum filtro aplicado"
        }
    }

    //  FUNÇÃO DE FILTROS - ESTADO -UF
    function updateUFSelectedCount() {
        const count = document.querySelectorAll('#ufsContainerDropdown .filter-uf:checked').length;
        const badge = document.getElementById('ufSelectedCount');
        if (badge) {
            badge.textContent = count;
            badge.style.display = count > 0 ? '' : 'none';
        }
    }

    //  FUNÇÃO DE FILTROS - MODALIDADE
    function updateModalidadeSelectedCount() {
        // O container de modalidades no seu JS original é 'modalidadesContainer'
        const count = document.querySelectorAll('#modalidadesContainerDropdown .filter-modalidade:checked').length;
        const badge = document.getElementById('modalidadesSelectedCount');
        if (badge) {
            badge.textContent = count;
            badge.style.display = count > 0 ? 'inline-block' : 'none';
        }
    }

     //  FUNÇÃO DE FILTROS - MUNICIPIO
    function updateMunicipioSelectedCount() {
        const count = document.querySelectorAll('#municipiosContainerDropdown .filter-municipio:checked').length;
        const badge = document.getElementById('municipiosSelectedCount');
        if (badge) {
            badge.textContent = count;
            // No seu HTML o badge já tem '0', então só precisamos controlar a visibilidade se quiser.
            // Para consistência, vamos usar a mesma lógica:
            badge.style.display = count > 0 ? 'inline-block' : 'none';
            if (count === 0) badge.textContent = '0'; // Garante que o '0' volte ao limpar.
        }
    }

    // FUNÇÃO PESQUISA DENTRO DOS FILTROS
    function setupFilterSearch(inputId, containerId, itemSelector) {
        const searchInput = document.getElementById(inputId);
        const container = document.getElementById(containerId);

        if (!searchInput || !container) {
            return; // Sai da função se os elementos não existirem
        }

        searchInput.addEventListener('input', function () {
            const searchTerm = searchInput.value.toLowerCase();
            const items = container.querySelectorAll(itemSelector);

            items.forEach(item => {
                // Acessa o texto do <label> que está dentro do div do item
                const label = item.querySelector('label');
                if (label) {
                    const itemText = label.textContent.toLowerCase();
                    // Mostra ou esconde o item (o div.form-check) com base na busca
                    if (itemText.includes(searchTerm)) {
                        item.style.display = 'block'; // Ou '' para voltar ao padrão
                    } else {
                        item.style.display = 'none';
                    }
                }
            });
        });
        container.addEventListener('click', function(event) {
            // Verifica se o que foi clicado foi realmente um checkbox
            if (event.target.matches('.form-check-input')) {
                
                // 1. Limpa o campo de busca
                searchInput.value = '';

                // 2. Garante que todos os itens da lista fiquem visíveis novamente
                const items = container.querySelectorAll(itemSelector);
                items.forEach(item => {
                    item.style.display = 'block';
                });
            }
        });        
    }


    // --- FUNÇÕES DE INICIALIZAÇÃO E POPULAÇÃO DE FILTROS ---
    async function popularModalidades() { 
        if (!modalidadesContainer) return; // Se o container não for encontrado, a função para aqui
        modalidadesContainer.innerHTML = '<small class="text-muted">Carregando modalidades...</small>';
        try {
            const response = await fetch('/api/frontend/referencias/modalidades');            
            if (!response.ok) throw new Error(`Erro ${response.status} ao buscar modalidades.`);
            const modalidadesApi = await response.json();

            modalidadesContainer.innerHTML = ''; 
            if (modalidadesApi && modalidadesApi.length > 0) {
                modalidadesApi.sort((a, b) => a.modalidadeNome.localeCompare(b.modalidadeNome)); 
                modalidadesApi.forEach(mod => {
                    const div = document.createElement('div');
                    div.classList.add('form-check');
                    div.innerHTML = `
                        <input class="form-check-input filter-modalidade" type="checkbox" value="${mod.modalidadeId}" id="mod-${mod.modalidadeId}">
                        <label class="form-check-label" for="mod-${mod.modalidadeId}">${mod.modalidadeNome}</label>
                    `;
                    modalidadesContainer.appendChild(div);

                    // Adiciona o listener para atualizar o contador a cada clique
                    div.querySelector('.filter-modalidade').addEventListener('change', updateModalidadeSelectedCount);
                });
            } else {
                modalidadesContainer.innerHTML = '<small class="text-danger">Nenhuma modalidade encontrada.</small>';
            }
        } catch (error) {
            console.error("Erro ao carregar modalidades:", error);
            modalidadesContainer.innerHTML = `<small class="text-danger">Erro ao carregar modalidades: ${error.message}</small>`;
        }
        // Atualiza a contagem inicial (deve ser 0)
        updateModalidadeSelectedCount();
    }


    async function popularStatus() { 
        if (!statusContainer) return;
        statusContainer.innerHTML = '<small class="text-muted">Carregando status...</small>';
        try {
            const response = await fetch('/api/frontend/referencias/statusradar');
            if (!response.ok) throw new Error(`Erro ${response.status} ao buscar status radar.`);
            const statusRadarApi = await response.json();

            statusContainer.innerHTML = ''; 
            if (statusRadarApi && statusRadarApi.length > 0) {
                const defaultStatusValue = "A Receber/Recebendo Proposta"; 
                
                statusRadarApi.sort((a,b) => a.nome.localeCompare(b.nome)); 

                statusRadarApi.forEach(st => {
                    const div = document.createElement('div');
                    div.classList.add('form-check');
                    const isChecked = st.id === defaultStatusValue; 
                    // Gerar um ID de elemento mais seguro
                    const elementId = `status-radar-${st.id.toLowerCase().replace(/[^a-z0-9-_]/g, '') || 'unk'}`;
                    div.innerHTML = `
                        <input class="form-check-input filter-status" type="radio" name="statusLicitacao" 
                               value="${st.id}" id="${elementId}" ${isChecked ? 'checked' : ''}>
                        <label class="form-check-label" for="${elementId}">${st.nome}</label>
                    `;
                    statusContainer.appendChild(div);
                    // Não precisamos mais de currentFilters.statusRadar aqui
                });

                const divTodos = document.createElement('div');
                divTodos.classList.add('form-check');
                const idTodos = "status-radar-todos";
                divTodos.innerHTML = `
                    <input class="form-check-input filter-status" type="radio" name="statusLicitacao" value="" id="${idTodos}">
                    <label class="form-check-label" for="${idTodos}">Todos</label>
                `;
                statusContainer.appendChild(divTodos);

                document.querySelectorAll('.filter-status').forEach(radio => {
                    radio.addEventListener('change', handleStatusChange); 
                });

            } else {
                statusContainer.innerHTML = '<small class="text-danger">Nenhum status encontrado.</small>';
            }
        } catch (error) {
            console.error("Erro ao carregar status radar:", error);
            statusContainer.innerHTML = `<small class="text-danger">Erro ao carregar status: ${error.message}</small>`;
        }
    }


    function popularUFs() { 
        if (!ufsContainer) return;
        ufsContainer.innerHTML = ''; 
        ufsLista.forEach(uf => {
            const div = document.createElement('div');
            div.classList.add('form-check');
            // Gerar um ID de elemento mais seguro
            const elementId = `uf-${uf.sigla.toLowerCase().replace(/[^a-z0-9-_]/g, '')}`;
            div.innerHTML = `
                <input class="form-check-input filter-uf" type="checkbox" value="${uf.sigla}" id="${elementId}">
                <label class="form-check-label" for="${elementId}">${uf.nome} (${uf.sigla})</label>
            `;
            ufsContainer.appendChild(div);
        });
        document.querySelectorAll('.filter-uf').forEach(checkbox => {
            checkbox.addEventListener('change', handleUFChange);
        });

        updateUFSelectedCount(); 
    }


    async function handleUFChange() {       
        updateUFSelectedCount(); // Mantém a chamada para o contador de UF

        const ufsSelecionadas = Array.from(document.querySelectorAll('.filter-uf:checked')).map(cb => cb.value);
        const municipiosContainer = document.getElementById('municipiosContainerDropdown');
        const municipiosDropdownButton = document.getElementById('dropdownMunicipiosButton'); 
        const municipiosHelp = document.getElementById('municipiosHelp');

        if (!municipiosContainer || !municipiosDropdownButton) return;

        // Limpa e desabilita o botão enquanto carrega ou se não há UFs
        municipiosDropdownButton.disabled = true;
        municipiosContainer.innerHTML = '';
        
        if (ufsSelecionadas.length === 0) {
            municipiosContainer.innerHTML = '<small class="text-muted p-2">Selecione uma UF primeiro</small>';
            if (municipiosHelp) municipiosHelp.textContent = "Selecione uma ou mais UFs para listar os municípios.";
            updateMunicipioSelectedCount(); // Reseta a contagem para 0 
            return; //Sai da função
        }

        municipiosDropdownButton.disabled = false;

        municipiosContainer.innerHTML = '<div class="p-2 text-muted">Carregando municípios...</div>';
        if (municipiosHelp) municipiosHelp.textContent = `Carregando municípios para ${ufsSelecionadas.join(', ')}...`;

        let todosMunicipios = [];
        let ufsComErro = [];

        for (const uf of ufsSelecionadas) {
            try {
                const response = await fetch(`/api/ibge/municipios/${uf}`);
                const data = await response.json(); // Consome o stream uma vez e armazena
                console.log(`Resposta da API para UF ${uf}:`, data); // Usa a variável data
                if (!response.ok) {
                    ufsComErro.push(uf);
                    continue;
                }
                data.forEach(mun => {
                    todosMunicipios.push({
                        id: `${uf}-${mun.id}`,
                        nome: `${mun.nome} (${uf})`,
                        nomeOriginal: mun.nome,
                        uf: uf
                    });
                });
            } catch (error) {
                console.error(`Erro crítico ao carregar municípios para ${uf}:`, error);
                ufsComErro.push(uf);
            }
        }

        todosMunicipios.sort((a, b) => a.nome.localeCompare(b.nome));
        municipiosContainer.innerHTML = ''; // Limpa "Carregando..."

        if (todosMunicipios.length > 0) {
            todosMunicipios.forEach(mun => {
                const div = document.createElement('div');
                div.classList.add('form-check', 'ms-2');
                const munId = `mun-${mun.id.replace(/[^a-zA-Z0-9]/g, '')}`;
                div.innerHTML = `
                    <input class="form-check-input filter-municipio" type="checkbox" value="${mun.nomeOriginal}" id="${munId}">
                    <label class="form-check-label" for="${munId}">${mun.nome}</label>
                `;
                municipiosContainer.appendChild(div);
            });
            
            // Adiciona listeners aos novos checkboxes de município
            document.querySelectorAll('.filter-municipio').forEach(cb => {
                cb.addEventListener('change', updateMunicipioSelectedCount);
            });
                        
            if(municipiosHelp) municipiosHelp.textContent = `Municípios de ${ufsSelecionadas.join(', ')}. Selecione um ou mais.`;
        } else {
            municipiosContainer.innerHTML = '<small class="text-danger p-2">Nenhum município encontrado.</small>';
            if (municipiosHelp) municipiosHelp.textContent = "Nenhum município encontrado para as UFs selecionadas.";
        }

        if (ufsComErro.length > 0 && municipiosHelp) {
            municipiosHelp.textContent += ` (Erro ao carregar de: ${ufsComErro.join(', ')})`;
        }
        
        updateMunicipioSelectedCount(); // Atualiza a contagem (será 0 neste ponto)
    }

     
    function handleStatusChange(event) {
        const selectedStatus = event.target.value;
        // Regra: Se "Todos" (ID vazio) ou "Encerradas" (ID 2) for selecionado, palavra-chave é obrigatória
        if (selectedStatus === "" || selectedStatus === "Encerrada") {
            // Não vamos bloquear aqui, mas podemos avisar ou validar na hora de buscar
        }
    }
    
    // Função para exibir Data e Hora Atual  ## NA VERDADE NEM PRECISO DISSO. POSSO ATÉ REMOVER
    function displayCurrentDateTime() {
        const dateTimeElement = document.getElementById('current-datetime');
        if (dateTimeElement) {
            const now = new Date();
            const optionsDate = { year: 'numeric', month: '2-digit', day: '2-digit' };
            const optionsTime = { hour: '2-digit', minute: '2-digit', second: '2-digit' };
            const formattedDate = now.toLocaleDateString('pt-BR', optionsDate);
            const formattedTime = now.toLocaleTimeString('pt-BR', optionsTime);
            dateTimeElement.textContent = `${formattedDate} ${formattedTime}`;
        }
    }

    // --- FUNÇÕES DE BUSCA E RENDERIZAÇÃO DE LICITAÇÕES ---
    async function buscarLicitacoes(page = 1) {
        currentPage = page;
        const params = new URLSearchParams();
        
        if(loadingOverlay) loadingOverlay.classList.remove('d-none');

        // Coleta palavraChave uma vez no início da função
        if (palavrasChaveInclusao.length > 0) {
            palavrasChaveInclusao.forEach(p => params.append('palavraChave', p));
        }
        if (palavrasChaveExclusao.length > 0) {
            palavrasChaveExclusao.forEach(p => params.append('excluirPalavra', p));
        }
                
        document.querySelectorAll('.filter-uf:checked').forEach(cb => params.append('uf', cb.value));
        document.querySelectorAll('.filter-modalidade:checked').forEach(cb => params.append('modalidadeId', cb.value));
        
        const statusSelecionadoRadio = document.querySelector('.filter-status:checked');
        let statusRadarValor = '';
        if (statusSelecionadoRadio) {
            statusRadarValor = statusSelecionadoRadio.value;
        }

        if (statusRadarValor) {
            params.append('statusRadar', statusRadarValor);
        }

        // Validação de palavra-chave para statusRadar "Todos" (valor vazio) ou "Encerradas"
        statusWarning.classList.add('d-none');
        
        if ((statusRadarValor === "" || statusRadarValor === "Encerrada") && !palavraChaveInc) {
            // A API do backend agora lida com a validação de obrigatoriedade, então o frontend pode apenas avisar
            // ou o backend retornará um erro 400 que trataremos.
            // Por enquanto, vamos manter o aviso no frontend:
            statusWarning.textContent = 'Palavra-chave de busca é obrigatória para este status.';
            statusWarning.classList.remove('d-none');
            // Aliás vamos interromper a busca aqui para melhor UX, em vez de esperar o erro 400 do backend
            licitacoesTableBody.innerHTML = `<tr><td colspan="8" class="text-center text-danger">Forneça uma palavra-chave para buscar com o status selecionado.</td></tr>`;
            totalRegistrosInfo.textContent = '0';
            exibicaoInfo.textContent = '';
            paginationControls.innerHTML = '';
            return; 
        }
        
        // Coleta de Municípios
        const municipiosSelecionados = Array.from(document.querySelectorAll('#municipiosContainerDropdown .filter-municipio:checked')).map(cb => cb.value);
        if (municipiosSelecionados.length > 0) {
            municipiosSelecionados.forEach(mun => params.append('municipioNome', mun));
        }

        // Datas de Publicação
        const dataInicio = dataPubInicioInput.value;
        if (dataInicio) params.append('dataPubInicio', dataInicio);
        const dataFim = dataPubFimInput.value;
        if (dataFim) params.append('dataPubFim', dataFim);

        // >>> ADICIONAR COLETA DAS DATAS DE ATUALIZAÇÃO <<<
        if(dataAtualizacaoInicioInput && dataAtualizacaoFimInput) { // Verificar se os elementos existem
            const dataAtualInicio = dataAtualizacaoInicioInput.value;
            if (dataAtualInicio) params.append('dataAtualizacaoInicio', dataAtualInicio);
            const dataAtualFim = dataAtualizacaoFimInput.value;
            if (dataAtualFim) params.append('dataAtualizacaoFim', dataAtualFim);
        }


        const valMin = valorMinInput.value;
        if (valMin) params.append('valorMin', valMin);
        const valMax = valorMaxInput.value;
        if (valMax) params.append('valorMax', valMax);

        params.append('pagina', currentPage);
        params.append('porPagina', itensPorPaginaSelect.value);

        const [orderByField, orderDirValue] = ordenarPorSelect.value.split('_');
        params.append('orderBy', orderByField);
        params.append('orderDir', orderDirValue.toUpperCase()); 


        licitacoesTableBody.innerHTML = `<tr><td colspan="8" class="text-center">Buscando licitações... <div class="spinner-border spinner-border-sm" role="status"><span class="visually-hidden">Loading...</span></div></td></tr>`;
        totalRegistrosInfo.textContent = '-';
        exibicaoInfo.textContent = '';

        try {
            const response = await fetch(`/api/frontend/licitacoes?${params.toString()}`);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({})); 
                if (response.status === 400 && errorData.erro) {
                    throw new Error(`Erro de validação: ${errorData.erro} ${errorData.detalhes ? '('+errorData.detalhes+')' : ''}`);
                }
                throw new Error(errorData.erro_backend || errorData.erro_frontend || `Erro ${response.status}`);
            }
                        
            const data = await response.json(); 

            renderLicitacoesTable(data.licitacoes);
            renderPagination(data);
            atualizarExibicaoFiltrosAtivos();
                                
            totalRegistrosInfo.textContent = data.total_registros || '0';
            if (data.licitacoes && data.licitacoes.length > 0) {
                 const inicio = (data.pagina_atual - 1) * parseInt(data.por_pagina, 10) + 1; // Garantir que por_pagina é número
                 const fim = inicio + data.licitacoes.length - 1;
                 exibicaoInfo.textContent = `Exibindo ${inicio}-${fim} de ${data.total_registros}`;
            } else {
                 exibicaoInfo.textContent = "Nenhum resultado";
            }

        } catch (error) {
            console.error("Erro ao buscar licitações:", error);
            licitacoesTableBody.innerHTML = `<tr><td colspan="8" class="text-center text-danger">Erro ao buscar licitações: ${error.message}</td></tr>`;
            totalRegistrosInfo.textContent = '0';
            exibicaoInfo.textContent = 'Erro';
            paginationControls.innerHTML = '';
        }finally {
            // Oculta o overlay de carregamento no final, seja sucesso ou erro
            if (loadingOverlay) loadingOverlay.classList.add('d-none');
        }
    }

    function renderLicitacoesTable(licitacoes) {
        licitacoesTableBody.innerHTML = ''; 
        if (!licitacoes || licitacoes.length === 0) {
            licitacoesTableBody.innerHTML = `<tr><td colspan="8" class="text-center">Nenhuma licitação encontrada para os filtros aplicados.</td></tr>`;
            return;
        }

        licitacoes.forEach(lic => {
            const tr = document.createElement('tr');
            const statusBadgeClass = getStatusBadgeClass(lic.situacaoReal); 
            const objetoCompleto = lic.objetoCompra || 'N/I';
            const objetoCurto = objetoCompleto.substring(0, 100);
            let objetoHtml = objetoCompleto; // Por padrão, mostra completo
            if (objetoCompleto.length > 100) {
                objetoHtml = `<span class="objeto-curto">${objetoCurto}... <a href="#" class="ver-mais-objeto" data-objeto-completo="${lic.id}">Ver mais</a></span>
                            <span class="objeto-completo d-none">${objetoCompleto} <a href="#" class="ver-menos-objeto" data-objeto-completo="${lic.id}">Ver menos</a></span>`;
            }
            tr.innerHTML = `
                <td>${lic.unidadeOrgaoMunicipioNome || 'N/I'}/${lic.unidadeOrgaoUfSigla || 'N/I'}</td>
                
                <td><div class="objeto-container" data-lic-id="${lic.id}">${objetoHtml}</div></td>
                <td>${lic.orgaoEntidadeRazaoSocial || 'N/I'}</td>
                <td><span class="badge ${statusBadgeClass}">${lic.situacaoReal || lic.situacaoCompraNome || 'N/I'}</span></td>
                <td>${lic.valorTotalEstimado ? `R$ ${parseFloat(lic.valorTotalEstimado).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : 'N/I'}</td>
                <td>${lic.modalidadeNome || 'N/I'}</td>
                <td>${lic.dataAtualizacao ? new Date(lic.dataAtualizacao + 'T00:00:00Z').toLocaleDateString('pt-BR') : 'N/I'}</td> 
                <td>
                    <a href="${lic.link_portal_pncp || '#'}" class="btn btn-sm btn-outline-primary" title="Acessar PNCP" target="_blank" ${!lic.link_portal_pncp ? 'disabled' : ''}><i class="bi bi-box-arrow-up-right"></i></a>
                    <button class="btn btn-sm btn-info btn-detalhes" title="Mais Detalhes" data-pncp-id="${lic.numeroControlePNCP}"><i class="bi bi-eye-fill"></i></button>
                </td>
            `;
            licitacoesTableBody.appendChild(tr);
        });
        
        document.querySelectorAll('.ver-mais-objeto').forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                const container = this.closest('.objeto-container');
                container.querySelector('.objeto-curto').classList.add('d-none');
                container.querySelector('.objeto-completo').classList.remove('d-none');
            });
        });
        document.querySelectorAll('.ver-menos-objeto').forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                const container = this.closest('.objeto-container');
                container.querySelector('.objeto-completo').classList.add('d-none');
                container.querySelector('.objeto-curto').classList.remove('d-none');
            });
        });

        document.querySelectorAll('.btn-detalhes').forEach(button => {
            button.addEventListener('click', handleDetalhesClick);
        });
    } 

    // Função auxiliar para definir a classe do badge de status
    function getStatusBadgeClass(situacaoReal) {
        if (!situacaoReal) return 'bg-secondary';
        const statusLower = situacaoReal.toLowerCase();
        if (statusLower.includes('recebendo') || statusLower.includes('aberta') || statusLower.includes('divulgada')) {
            return 'bg-success'; // Verde para ativas
        } else if (statusLower.includes('encerrada') || statusLower.includes('homologada') || statusLower.includes('concluída')) {
            return 'bg-primary'; // Azul para encerradas/concluídas
        } else if (statusLower.includes('julgamento')) {
            return 'bg-warning text-dark'; // Amarelo para em julgamento
        } else if (statusLower.includes('suspensa')) {
            return 'bg-info text-dark'; // Ciano para suspensas
        } else if (statusLower.includes('anulada') || statusLower.includes('revogada') || statusLower.includes('cancelada')) {
            return 'bg-danger'; // Vermelho para anuladas/canceladas
        }
        return 'bg-secondary'; // Padrão
    }


    function renderPagination(data) {
        paginationControls.innerHTML = '';
        if (!data || !data.licitacoes || data.total_paginas == null || data.total_paginas <= 1) { // Adicionada checagem para data.licitacoes e data.total_paginas
            console.log("renderPagination: Dados insuficientes ou não precisa de paginação.", data);
            return;
        }

        const pagina_atual = parseInt(data.pagina_atual, 10); // Garantir que é número
        const total_paginas = parseInt(data.total_paginas, 10); // Garantir que é número

        // Validação adicional
        if (isNaN(pagina_atual) || isNaN(total_paginas)) {
            console.error("renderPagination: pagina_atual ou total_paginas não são números válidos.", data);
            return;
        }

        // Botão Anterior
        const prevLi = document.createElement('li');
        prevLi.classList.add('page-item');
        if (pagina_atual === 1) {
            prevLi.classList.add('disabled');
        }
        prevLi.innerHTML = `<a class="page-link" href="#" data-page="${pagina_atual - 1}">Anterior</a>`;
        paginationControls.appendChild(prevLi);

        // Números das Páginas (lógica simples para mostrar algumas páginas)
        let startPage = Math.max(1, pagina_atual - 2);
        let endPage = Math.min(total_paginas, pagina_atual + 2);

        // Ajustar startPage e endPage para sempre mostrar um número fixo de links se possível
        const maxPageLinks = 5; // Número de links de página que queremos mostrar (ex: 1 ... 3 4 5 ... 10)
        if (endPage - startPage + 1 < maxPageLinks) {
            if (pagina_atual < maxPageLinks / 2) { // Perto do início
                endPage = Math.min(total_paginas, startPage + maxPageLinks - 1);
            } else if (pagina_atual > total_paginas - maxPageLinks / 2) { // Perto do fim
                startPage = Math.max(1, endPage - maxPageLinks + 1);
            } else { // No meio
                const diff = Math.floor((maxPageLinks - (endPage - startPage + 1)) / 2);
                startPage = Math.max(1, startPage - diff);
                endPage = Math.min(total_paginas, endPage + (maxPageLinks - (endPage - startPage + 1) - diff) ) ; // O que sobrou
            }
            // Reajuste final se estourar os limites
            if (endPage - startPage + 1 > maxPageLinks) {
                if (startPage === 1) endPage = startPage + maxPageLinks - 1;
                else startPage = endPage - maxPageLinks + 1;
            }
        }

        if (startPage > 1) {
            const firstLi = document.createElement('li');
            firstLi.classList.add('page-item');
            firstLi.innerHTML = `<a class="page-link" href="#" data-page="1">1</a>`;
            paginationControls.appendChild(firstLi);
            if (startPage > 2) {
                const dotsLi = document.createElement('li');
                dotsLi.classList.add('page-item', 'disabled');
                dotsLi.innerHTML = `<span class="page-link">...</span>`;
                paginationControls.appendChild(dotsLi);
            }
        }

        for (let i = startPage; i <= endPage; i++) {
            const pageLi = document.createElement('li');
            pageLi.classList.add('page-item');
            if (i === pagina_atual) {
                pageLi.classList.add('active');
            }
            pageLi.innerHTML = `<a class="page-link" href="#" data-page="${i}">${i}</a>`;
            paginationControls.appendChild(pageLi);
        }
        
        if (endPage < total_paginas) {
            if (endPage < total_paginas - 1) {
                const dotsLi = document.createElement('li');
                dotsLi.classList.add('page-item', 'disabled');
                dotsLi.innerHTML = `<span class="page-link">...</span>`;
                paginationControls.appendChild(dotsLi);
            }
            const lastLi = document.createElement('li');
            lastLi.classList.add('page-item');
            lastLi.innerHTML = `<a class="page-link" href="#" data-page="${total_paginas}">${total_paginas}</a>`;
            paginationControls.appendChild(lastLi);
        }

        // Botão Próximo
        const nextLi = document.createElement('li');
        nextLi.classList.add('page-item');
        if (pagina_atual === total_paginas) {
            nextLi.classList.add('disabled');
        }
        nextLi.innerHTML = `<a class="page-link" href="#" data-page="${pagina_atual + 1}">Próxima</a>`;
        paginationControls.appendChild(nextLi);

        // Adicionar event listeners aos links de paginação
        paginationControls.querySelectorAll('.page-link').forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                // Verifica se o elemento pai (li) está desabilitado ou ativo
                const parentLi = this.closest('.page-item');
                if (parentLi && (parentLi.classList.contains('disabled') || parentLi.classList.contains('active'))) {
                    return;
                }
                const page = parseInt(this.dataset.page);
                if (page && !isNaN(page)) { // Verifica se page é um número válido
                    buscarLicitacoes(page);
                }
            });
        });
    }

    function limparFiltros() {        
        if(palavraChaveInclusaoInputField) palavraChaveInclusaoInputField.value = '';
        if(palavraChaveExclusaoInputField) palavraChaveExclusaoInputField.value = '';

        palavrasChaveInclusao = []; // Limpa o array
        palavrasChaveExclusao = []; // Limpa o array
        renderTags(palavrasChaveInclusao, tagsPalavraInclusaoContainer, 'inclusao'); // Re-renderiza (vazio)
        renderTags(palavrasChaveExclusao, tagsPalavraExclusaoContainer, 'exclusao'); // Re-renderiza (vazio)

        //document.querySelectorAll('.filter-uf:checked').forEach(cb => cb.checked = false);
        //handleUFChange(); 
        document.querySelectorAll('#ufsContainerDropdown .filter-uf:checked').forEach(cb => cb.checked = false);
        // Atualizar contagem e municípios após desmarcar UFs
        if (typeof updateUFSelectedCount === "function") updateUFSelectedCount(); // Atualiza badge de UF SE ESSE TIVER PROBLEMA, UTILIZAR O DE CIMA
        handleUFChange(); // Isso deve limpar e desabilitar os municípios e atualizar o badge de municípios
        
        //document.querySelectorAll('.filter-modalidade:checked').forEach(cb => cb.checked = false);           
        //updateModalidadeSelectedCount(); // >>> Resetar o contador de modalidades <<<
        document.querySelectorAll('#modalidadesContainerDropdown .filter-modalidade:checked').forEach(cb => cb.checked = false);
        if (typeof updateModalidadeSelectedCount === "function") updateModalidadeSelectedCount(); // Atualiza badge de modalidade (criar essa função)

        

        // Resetar status para o default
        const radiosStatus = document.querySelectorAll('.filter-status');
        let defaultStatusRadio = null;
        const defaultStatusValue = "A Receber/Recebendo Proposta"; // Mesmo default usado em popularStatus
        radiosStatus.forEach(radio => {
            if (radio.value === defaultStatusValue) {
                defaultStatusRadio = radio;
            }
            // Desmarcar todos primeiro (embora radio buttons se auto-desmarquem, é uma garantia)
            // radio.checked = false; // Não precisa, pois ao marcar um, os outros desmarcam
        });

        if (defaultStatusRadio) {
            defaultStatusRadio.checked = true;
        } else if (radiosStatus.length > 0) {
             // Se o default específico não for encontrado, marcar o primeiro que não seja "Todos"
            const primeiroValido = Array.from(radiosStatus).find(r => r.value !== "");
            if (primeiroValido) primeiroValido.checked = true;
            else if(radiosStatus.length > 0) radiosStatus[0].checked = true; // Como último recurso, marca o primeiro
        }
        statusWarning.classList.add('d-none');

        if(dataPubInicioInput) dataPubInicioInput.value = '';
        if(dataPubFimInput) dataPubFimInput.value = '';
        if(dataAtualizacaoInicioInput) dataAtualizacaoInicioInput.value = '';
        if(dataAtualizacaoFimInput) dataAtualizacaoFimInput.value = '';
        if(valorMinInput) valorMinInput.value = '';
        if(valorMaxInput) valorMaxInput.value = '';
        
        const advancedCollapse = document.getElementById('collapseAdvanced');
        if (advancedCollapse && advancedCollapse.classList.contains('show')) {
            new bootstrap.Collapse(advancedCollapse).hide();
        }
                
        console.log("Filtros limpos, buscando licitações...");        
        atualizarExibicaoFiltrosAtivos(); 

        // Event listener para o link de limpar rápido
        if(linkLimparFiltrosRapido) {
            linkLimparFiltrosRapido.addEventListener('click', function(e){
                e.preventDefault();
                limparFiltros(); // Chama a função principal de limpar filtros
            });
        }
        buscarLicitacoes(1); 
    }

    // --- HANDLERS DE EVENTOS GLOBAIS ---
    if (btnBuscarLicitacoes) {
        btnBuscarLicitacoes.addEventListener('click', () => buscarLicitacoes(1));
    }
    if (btnLimparFiltros) {
        btnLimparFiltros.addEventListener('click', limparFiltros);
    }
    if (ordenarPorSelect) {
        ordenarPorSelect.addEventListener('change', () => buscarLicitacoes(currentPage)); // Rebusca a página atual com nova ordenação
    }
    if (itensPorPaginaSelect) {
        itensPorPaginaSelect.addEventListener('change', () => buscarLicitacoes(1)); // Volta para a primeira página com nova quantidade
    }

    // Placeholder para função de detalhes
    const detailsPanelElement = document.getElementById('detailsPanel');
    const detailsPanel = detailsPanelElement ? new bootstrap.Offcanvas(detailsPanelElement) : null;
    const detailsPanelContent = document.getElementById('detailsPanelContent');
    // ... (outros elementos do painel de detalhes)

    async function handleDetalhesClick(event) {
        const button = event.currentTarget;
        const pncpId = button.dataset.pncpId;
        if (!pncpId || !detailsPanel) return;

        detailsPanelContent.innerHTML = '<p class="text-center">Carregando detalhes...</p>';
        // Limpar outras partes do painel (itens, arquivos)
        document.getElementById('detailsPanelItensTableBody').innerHTML = '';
        document.getElementById('detailsPanelItensPagination').innerHTML = '';
        document.getElementById('detailsPanelArquivosList').innerHTML = '';

        detailsPanel.show();

        try {
            const response = await fetch(`/api/frontend/licitacao/${encodeURIComponent(pncpId)}`);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({erro_frontend: "Erro desconhecido na resposta da API de detalhes."}));
                throw new Error(errorData.erro_backend || errorData.erro_frontend || `Erro ${response.status}`);
            }
            const data = await response.json();
            //(DEBUG)
            console.log("Dados DETALHES para PNCP ID:", pncpId, JSON.parse(JSON.stringify(data))); // Log profundo dos dados
            renderDetailsPanelContent(data); // Implementar esta função

        } catch (error) {
            console.error("Erro ao buscar detalhes da licitação:", error);
            detailsPanelContent.innerHTML = `<p class="text-center text-danger">Erro ao carregar detalhes: ${error.message}</p>`;
        }
    }

    //FUNÇÃO DO PAINEL DETALHES
    function renderDetailsPanelContent(data) {
        if (!data || !data.licitacao) {
            detailsPanelContent.innerHTML = '<p class="text-center text-danger">Dados da licitação não encontrados.</p>';
            return;
        }
        const lic = data.licitacao;
        //DEBUG
        console.log("Detalhes da Licitação Específica:", lic);

        // Atualizar título do Offcanvas (PAINEL DETALHES)
        const detailsPanelLabel = document.getElementById('detailsPanelLabel');
        if (detailsPanelLabel) {            
            detailsPanelLabel.textContent = lic.unidadeOrgaoNome ? `Unidade: ${lic.unidadeOrgaoNome}` : (lic.processo ? `Processo: ${lic.processo}` 
                : `Detalhes: ${lic.numeroControlePNCP || 'N/I'}`);
            //detailsPanelLabel.textContent = lic.processo ? `Processo: ${lic.processo}` : `Detalhes: ${lic.numeroControlePNCP || 'N/I'}`;
        }

         // Formatar datas helper (opcional, mas útil)
        const formatDate = (dateString) => {
            if (!dateString) return 'N/I';
            // Adiciona 'Z' para garantir que seja tratada como UTC se não tiver fuso,
            // evitando problemas de off-by-one day dependendo do fuso do cliente.
            // Se a data já vier com fuso do backend, pode não ser necessário o 'Z'.
            return new Date(dateString + 'T00:00:00Z').toLocaleDateString('pt-BR');
        };


        let htmlContent = `
            <p><strong>Número PNCP:</strong> ${lic.numeroControlePNCP || 'N/I'}</p>
            ${
                lic.processo 
                    ? `<p><strong>Número do Processo:</strong> ${lic.processo}</p>` 
                    : ''
            }
            <p><strong>Objeto:</strong></p>
            <div class="mb-2" style="white-space: pre-wrap; background-color: #f8f9fa; padding: 10px; border-radius: 5px; max-height: 150px; overflow-y: auto;">${lic.objetoCompra || 'N/I'}</div>
            <p><strong>Órgão:</strong> ${lic.orgaoEntidadeRazaoSocial || 'N/I'}</p>
            <p><strong>Unidade Compradora:</strong> ${lic.unidadeOrgaoNome || 'N/I'}</p>
            <p><strong>Município/UF:</strong> ${lic.unidadeOrgaoMunicipioNome || 'N/I'}/${lic.unidadeOrgaoUfSigla || 'N/I'}</p>
            <p><strong>Modalidade:</strong> ${lic.modalidadeNome || 'N/I'}</p>    
            <!-- DESABILITADO PARA TESTAR O DE BAIXO <p><strong>Amparo Legal:</strong> ${lic.amparoLegalNome || 'N/I'}</p> -->
            ${lic.amparoLegalNome ? `<p><strong>Amparo Legal:</strong> ${lic.amparoLegalNome}</p>` : ''}
            ${
                lic.valorTotalHomologado
                    ? `<p><strong>Valor Total Homologado:</strong> R$ ${parseFloat(lic.valorTotalHomologado).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>`
                    : ''
            }
            ${lic.modoDisputaNome ? `<p><strong>Modo de Disputa:</strong> ${lic.modoDisputaNome}</p>` : '<p class="text-muted small"><small><strong>Modo de Disputa:</strong> (Não informado)</small></p>'}
            ${lic.tipolnstrumentoConvocatorioNome ? `<p><strong>Tipo:</strong> ${lic.tipolnstrumentoConvocatorioNome}</p>` : '<p class="text-muted small"><small><strong>Tipo:</strong> (Não informado)</small></p>'}
            <!-- DESABILITADO PARA TESTAR O DE BAIXO <p><strong>Situação:</strong> <span class="badge ${getStatusBadgeClass(lic.situacaoReal)}">${lic.situacaoReal || 'N/I'}</span></p>  -->
            ${lic.situacaoReal ? `<p><small><strong>Situação Atual:</strong> ${lic.situacaoReal} </small></p>` : ''}            
            
            <!-- DESABILITADO PARA TESTAR O DE BAIXO <p><strong>Data Publicação PNCP:</strong> ${lic.dataPublicacaoPncp ? new Date(lic.dataPublicacaoPncp + 'T00:00:00').toLocaleDateString('pt-BR') : 'N/I'}</p>  -->
            <p><strong>Data Publicação PNCP:</strong> ${formatDate(lic.dataPublicacaoPncp)}</p>

            <p><strong>Início Recebimento Propostas:</strong> ${formatDate(lic.dataAberturaProposta)}</p>
            <p><strong>Fim Recebimento Propostas:</strong> ${formatDate(lic.dataEncerramentoProposta)}</p>
            <p><strong>Última Atualização:</strong> ${formatDate(lic.dataAtualizacao)}</p>
            <p><strong>Valor Total Estimado:</strong> ${lic.valorTotalEstimado ? `R$ ${parseFloat(lic.valorTotalEstimado).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : 'N/I'}</p>
            <p><strong>Informação Complementar:</strong></p>
            <div style="white-space: pre-wrap; background-color: #f8f9fa; padding: 10px; border-radius: 5px; max-height: 150px; overflow-y: auto;">
                ${lic.informacaoComplementar || 'Nenhuma'}
            </div>
            
        `;

        
        let justificativaHtml = '';
        if (lic.justificativaPresencial) {
            const textoCompleto = lic.justificativaPresencial;
            const limite = 200;
            if (textoCompleto.length > limite) {
                const textoCurto = textoCompleto.substring(0, limite);
                // Usar IDs únicos para cada instância se houver múltiplas licitações abertas (não é o caso aqui com um só painel)
                justificativaHtml = `
                    <p><strong>Justificativa Presencial:</strong></p>
                    <div class="justificativa-container">
                        <span class="justificativa-curta" style="white-space: pre-wrap;">${textoCurto}... <a href="#" class="ver-mais-justificativa">Ver mais</a></span>
                        <span class="justificativa-completa d-none" style="white-space: pre-wrap;">${textoCompleto} <a href="#" class="ver-menos-justificativa">Ver menos</a></span>
                    </div>`;
            } else {
                justificativaHtml = `<p><strong>Justificativa Presencial:</strong></p><div style="white-space: pre-wrap;">${textoCompleto}</div>`;
            }
        }
        
        htmlContent += justificativaHtml;
        // Renderizar conteúdo 
        detailsPanelContent.innerHTML = htmlContent;

        const verMaisJust = detailsPanelContent.querySelector('.ver-mais-justificativa');
        if (verMaisJust) {
            verMaisJust.addEventListener('click', function(e) {
                e.preventDefault();
                const container = this.closest('.justificativa-container');
                container.querySelector('.justificativa-curta').classList.add('d-none');
                container.querySelector('.justificativa-completa').classList.remove('d-none');
            });
        }
        const verMenosJust = detailsPanelContent.querySelector('.ver-menos-justificativa');
        if (verMenosJust) {
            verMenosJust.addEventListener('click', function(e) {
                e.preventDefault();
                const container = this.closest('.justificativa-container');
                container.querySelector('.justificativa-completa').classList.add('d-none');
                container.querySelector('.justificativa-curta').classList.remove('d-none');
            });
        }




        //DEBUG
        const btnPncp = document.getElementById('detailsPanelBtnPncp');
        if (btnPncp) {
            if (lic.link_portal_pncp && lic.link_portal_pncp.trim() !== "") {
                btnPncp.href = lic.link_portal_pncp;
                btnPncp.classList.remove('disabled'); // Estilo visual de habilitado
                btnPncp.removeAttribute('aria-disabled'); // Acessibilidade
            } else {
                btnPncp.href = '#'; // Impede navegação
                btnPncp.classList.add('disabled');   // Estilo visual de desabilitado
                btnPncp.setAttribute('aria-disabled', 'true'); // Acessibilidade
            }
        }
                
        // Botão Sistema de Origem 
        const btnSistemaOrigem = document.getElementById('detailsPanelBtnSistemaOrigem');
        if (btnSistemaOrigem) {
            if (lic.linkSistemaOrigem && lic.linkSistemaOrigem.trim() !== "") { // Assumindo que 'linkSistemaOrigem' virá da API
                btnSistemaOrigem.disabled = false; 
                btnSistemaOrigem.innerHTML = '<i class="bi bi-building"></i> Acessar Sistema de Origem';
                // Definir o que acontece ao clicar. Se for apenas um link:
                btnSistemaOrigem.onclick = () => { window.open(lic.linkSistemaOrigem, '_blank'); };
            } else {
                btnSistemaOrigem.disabled = true;
                btnSistemaOrigem.innerHTML = '<i class="bi bi-building"></i> Sistema de Origem (Não disponível)';
                btnSistemaOrigem.onclick = null; // Remove handler anterior se houver
            }
        }


        renderDetailsPanelItens(data.itens || []);
        renderDetailsPanelArquivos(data.arquivos || []);
    }

    // Placeholder para renderizar itens e arquivos no painel de detalhes (a ser implementado)
    let currentDetalhesItens = [];
    let currentDetalhesItensPage = 1;
    const ITENS_POR_PAGINA_DETALHES = 5;

    function renderDetailsPanelItens(itens) {
        currentDetalhesItens = itens;
        currentDetalhesItensPage = 1;
        displayDetalhesItensPage();
    }

    function displayDetalhesItensPage() {
        const tableBody = document.getElementById('detailsPanelItensTableBody');
        const pagination = document.getElementById('detailsPanelItensPagination');
        tableBody.innerHTML = '';
        pagination.innerHTML = '';

        
        if (!currentDetalhesItens || currentDetalhesItens.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="5" class="text-center">Nenhum item encontrado.</td></tr>';
            return;
        }

        const totalPages = Math.ceil(currentDetalhesItens.length / ITENS_POR_PAGINA_DETALHES);
        const startIndex = (currentDetalhesItensPage - 1) * ITENS_POR_PAGINA_DETALHES;
        const endIndex = startIndex + ITENS_POR_PAGINA_DETALHES;
        const pageItens = currentDetalhesItens.slice(startIndex, endIndex);

        pageItens.forEach(item => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${item.numeroItem || 'N/I'}</td>
                <td>${item.descricao || 'N/I'}</td>
                <td>${item.quantidade || 'N/I'}</td>
                <td>${item.valorUnitarioEstimado ? parseFloat(item.valorUnitarioEstimado).toLocaleString('pt-BR', {style: 'currency', currency: 'BRL'}) : 'N/I'}</td>
                <td>${item.valorTotal ? parseFloat(item.valorTotal).toLocaleString('pt-BR', {style: 'currency', currency: 'BRL'}) : 'N/I'}</td>
            `;
            tableBody.appendChild(tr);
        });

        // Paginação simples para itens
        if (totalPages > 1) {
            // Botão Anterior
            const prevLi = document.createElement('li');
            prevLi.classList.add('page-item');
            if (currentDetalhesItensPage === 1) {
                prevLi.classList.add('disabled');
            }
            prevLi.innerHTML = `<a class="page-link page-link-sm" href="#">Ant</a>`;
            prevLi.addEventListener('click', (e) => { e.preventDefault(); if(currentDetalhesItensPage > 1) { currentDetalhesItensPage--; displayDetalhesItensPage(); }});
            pagination.appendChild(prevLi);

            // Info da Página
            const pageInfo = document.createElement('li');
            pageInfo.classList.add('page-item', 'disabled');
            pageInfo.innerHTML = `<span class="page-link page-link-sm">${currentDetalhesItensPage}/${totalPages}</span>`;
            pagination.appendChild(pageInfo);

            // Botão Próximo
            const nextLi = document.createElement('li');
            nextLi.classList.add('page-item');
            if (currentDetalhesItensPage === totalPages) {
                nextLi.classList.add('disabled'); // Adiciona a classe 'disabled' apenas se necessário
            }   
            nextLi.innerHTML = `<a class="page-link page-link-sm" href="#">Próx</a>`;
            nextLi.addEventListener('click', (e) => { e.preventDefault(); if(currentDetalhesItensPage < totalPages) { currentDetalhesItensPage++; displayDetalhesItensPage(); }});
            pagination.appendChild(nextLi);
        
        } else if (totalPages === 1 && currentDetalhesItens.length > 0) { 
            const pageInfo = document.createElement('li');
            pageInfo.classList.add('page-item');
            pageInfo.classList.add('disabled');
            pageInfo.innerHTML = `<span class="page-link page-link-sm">${currentDetalhesItensPage} / ${totalPages}</span>`;
            pagination.appendChild(pageInfo);
        }
        
    }


    function renderDetailsPanelArquivos(arquivos) {
        const listElement = document.getElementById('detailsPanelArquivosList');
        listElement.innerHTML = '';
        if (!arquivos || arquivos.length === 0) {
            const li = document.createElement('li');
            li.classList.add('list-group-item');
            li.textContent = 'Nenhum arquivo encontrado.';
            listElement.appendChild(li);
            return;
        }
        arquivos.forEach(arq => {
            const li = document.createElement('li');
            li.classList.add('list-group-item');
            li.innerHTML = `<a href="${arq.link_download}" target="_blank"><i class="bi bi-file-earmark-arrow-down"></i> ${arq.titulo || 'Arquivo sem título'}</a>`;
            listElement.appendChild(li);
        });
    }

    // --- INICIALIZAÇÃO DA PÁGINA (MODIFICADA) ---
    async function inicializarPagina() {
        displayCurrentDateTime();
        setInterval(displayCurrentDateTime, 1000);
        
        popularUFs(); 
        await popularModalidades(); 
        await popularStatus();      

        const defaultStatusChecked = document.querySelector('.filter-status:checked');
        const palavraChaveInicial = palavraChaveInclusaoInput.value.trim();

        // A lógica de busca inicial pode ser simplificada para apenas buscar
        // se as condições mínimas forem atendidas.
        // A busca inicial com status default deve funcionar se não cair na validação de palavra-chave.
        if (defaultStatusChecked) {
            const statusVal = defaultStatusChecked.value;
            if (!((statusVal === "" || statusVal === "Encerrada") && !palavraChaveInicial)) {
                console.log("Inicializando busca de licitações com status default...");
                buscarLicitacoes(1);
            } else {
                // Exibe mensagem de aviso se a condição de palavra-chave não for atendida pelo default
                statusWarning.textContent = `Palavra-chave é obrigatória para o status "${defaultStatusChecked.labels[0].textContent || 'Todos'}".`;
                statusWarning.classList.remove('d-none');
                licitacoesTableBody.innerHTML = `<tr><td colspan="8" class="text-center">Forneça uma palavra-chave para buscar com o status selecionado.</td></tr>`;
            }
        } else {
            // Caso nenhum status esteja marcado por padrão (improvável com a lógica de popularStatus)
            licitacoesTableBody.innerHTML = `<tr><td colspan="8" class="text-center">Selecione os filtros e clique em "Aplicar Filtros".</td></tr>`;
        }
        setupFilterSearch('ufSearchInput', 'ufsContainerDropdown', '.form-check');
        setupFilterSearch('modalidadeSearchInput', 'modalidadesContainerDropdown', '.form-check');
        setupFilterSearch('municipioSearchInput', 'municipiosContainerDropdown', '.form-check');

    }


    // --- ATRIBUIÇÃO DE EVENT LISTENERS (colocar após a definição das funções) ---
    if (btnBuscarLicitacoes) {
        btnBuscarLicitacoes.addEventListener('click', () => buscarLicitacoes(1));
    }
    if (btnLimparFiltros) {
        btnLimparFiltros.addEventListener('click', limparFiltros);
    }
    // Corrigido para buscar a página atual, não a primeira sempre na ordenação
    if (ordenarPorSelect) {
        ordenarPorSelect.addEventListener('change', () => buscarLicitacoes(currentPage || 1)); 
    }
    if (itensPorPaginaSelect) {
        itensPorPaginaSelect.addEventListener('change', () => buscarLicitacoes(1)); 
    }
    // Adicionar o event listener para btnAtualizarTabela aqui também, se a função já existir
    const btnAtualizarTabela = document.getElementById('btnAtualizarTabela');
    if (btnAtualizarTabela) {
        btnAtualizarTabela.disabled = false; 
        btnAtualizarTabela.addEventListener('click', () => {
            console.log("Botão Atualizar Tabela clicado - Refazendo busca para página:", currentPage);
            if (currentPage < 1) currentPage = 1; 
            buscarLicitacoes(currentPage); 
        });
    }

    inicializarPagina(); 
});