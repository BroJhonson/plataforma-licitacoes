# sync_api.py

import requests # (Para fazer requisições HTTP)
import sqlite3 # (Para interagir com o banco de dados SQLite)
import json # (Para lidar com dados JSON da API, embora 'requests' já faça muito disso)
import os # (Para caminhos de arquivo)
import time
from datetime import datetime, date, timedelta # (Para trabalhar com datas)

# --- Configurações ---
# Define o caminho para a pasta backend
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Define o caminho completo para o arquivo do banco de dados
DATABASE_PATH = os.path.join(BASE_DIR, 'database.db')
# Data atual para o parâmetro dataFinal (formato YYYYMMDD)
hoje = date.today()
data_futura = hoje + timedelta(days=6*30) # Aproximação de 6 meses (180 dias)
DATA_ATUAL_PARAM = data_futura.strftime('%Y%m%d')
#print(f"INFO: Usando dataFinal calculada como: {DATA_ATUAL_PARAM}")
TAMANHO_PAGINA = 10 # OBRIGATORIO
LIMITE_PAGINAS_TESTE = 1 # OBRIGATORIO. Mudar para None para buscar todas.
CODIGOS_MODALIDADE = [6] # (OBRIGATORIO. 5 = Concorrencia; 6 = Pregão Eletrônico)
API_BASE_URL = "https://pncp.gov.br/api/consulta" # (URL base da API do PNCP)      
API_BASE_URL_PNCP_API = "https://pncp.gov.br/pncp-api"   # Para itens e arquivos    ## PARA TODOS OS LINKS DE ARQUIVOS E ITENS USAR PAGINAÇÃO SE NECESSARIO ##
ENDPOINT_PROPOSTAS_ABERTAS = "/v1/contratacoes/proposta" # (Endpoint específico)


    ##CONFIGURAÇÃO DA API PARA ENCONTRAR OS ITENS/ARQUIVOS DAS LICITAÇÕES ##
def fetch_itens_from_api(cnpj_orgao, ano_compra, sequencial_compra, pagina=1, tamanho_pagina=50):
    """Busca uma página de itens de uma licitação."""
    url = f"{API_BASE_URL_PNCP_API}/v1/orgaos/{cnpj_orgao}/compras/{ano_compra}/{sequencial_compra}/itens"
    params = {'pagina': pagina, 'tamanhoPagina': tamanho_pagina}
    headers = {'Accept': 'application/json'}
    print(f"ITENS: Buscando em {url} com params {params}")
    try:
        response = requests.get(url, params=params, headers=headers, timeout=60)
        response.raise_for_status()
        if response.status_code == 204: return [] # Retorna lista vazia
        return response.json() 
    except Exception as e:
        print(f"ITENS: Erro ao buscar itens para {cnpj_orgao}/{ano_compra}/{sequencial_compra}: {e}")
        if hasattr(e, 'response') and e.response is not None:
             print(f"ITENS: Status: {e.response.status_code}, Texto: {e.response.text[:200]}")
        return None # Indica erro
    
def fetch_arquivos_from_api(cnpj_orgao, ano_compra, sequencial_compra, pagina=1, tamanho_pagina=50):
    url = f"{API_BASE_URL_PNCP_API}/v1/orgaos/{cnpj_orgao}/compras/{ano_compra}/{sequencial_compra}/arquivos"

    params = {'pagina': pagina, 'tamanhoPagina': tamanho_pagina}
    headers = {'Accept': 'application/json'}
    print(f"ARQUIVOS: Buscando em {url} com params {params}")
    try:
        response = requests.get(url, params=params, headers=headers, timeout=60)
        response.raise_for_status()
        if response.status_code == 204: return [] # Retorna lista vazia        
        return response.json() 
    except Exception as e:
        print(f"ARQUIVOS: Erro ao buscar arquivoS para {cnpj_orgao}/{ano_compra}/{sequencial_compra}: {e}")
        if hasattr(e, 'response') and e.response is not None:
             print(f"ARQUIVOS: Status: {e.response.status_code}, Texto: {e.response.text[:200]}")
        return None 




### ITENS DA LICITAÇÃO ###
def fetch_all_itens_for_licitacao(conn, licitacao_id_local, cnpj_orgao, ano_compra, sequencial_compra):
    """Busca todos os itens de uma licitação, lidando com paginação."""
    todos_itens_api = []
    pagina_atual_itens = 1
    tamanho_pagina_itens = 100 # API do PNCP costuma ter limites altos para sub-recursos
    
    while True:
        itens_pagina = fetch_itens_from_api(cnpj_orgao, ano_compra, sequencial_compra, pagina_atual_itens, tamanho_pagina_itens)
        if itens_pagina is None: # Erro na chamada
            print(f"ITENS: Falha ao buscar página {pagina_atual_itens} de itens. Abortando busca de itens para esta licitação.")
            return None # Ou retorna o que conseguiu até agora: todos_itens_api
        
        if not itens_pagina: # Lista vazia, fim da paginação
            break
        
        todos_itens_api.extend(itens_pagina)
        
        # A API de itens parece não retornar 'paginasRestantes'.
        # Se o número de itens retornados for menor que tamanho_pagina_itens, assumimos que é a última página.
        if len(itens_pagina) < tamanho_pagina_itens:
            break
        pagina_atual_itens += 1
        time.sleep(0.2) # Delay entre páginas de itens
    
    print(f"ITENS: Total de {len(todos_itens_api)} itens encontrados para {cnpj_orgao}/{ano_compra}/{sequencial_compra}.")
    
    # Salvar no banco
    if todos_itens_api:
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM itens_licitacao WHERE licitacao_id = ?", (licitacao_id_local,))
        except sqlite3.Error as e:
            print(f"ERRO (save_db): Ao deletar itens antigos da licitação ID {licitacao_id_local}: {e}")

        sql_insert_item = """
        INSERT INTO itens_licitacao (
            licitacao_id, numeroItem, descricao, materialOuServicoNome, quantidade,
            unidadeMedida, valorUnitarioEstimado, valorTotal, orcamentoSigiloso,
            itemCategoriaNome, categoriaItemCatalogo, criterioJulgamentoNome, 
            situacaoCompraItemNome, tipoBeneficioNome, incentivoProdutivoBasico, dataInclusao,
            dataAtualizacao, temResultado, informacaoComplementar
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""" # 19 placeholders
        
        itens_salvos_count = 0
        for item_api in todos_itens_api:
            item_db_tuple = (       # Renomeado para não confundir com licitacao_db
                licitacao_id_local,
                item_api.get('numeroItem'),
                item_api.get('descricao'),
                item_api.get('materialOuServicoNome'),
                item_api.get('quantidade'),
                item_api.get('unidadeMedida'),
                item_api.get('valorUnitarioEstimado'),
                item_api.get('valorTotal'),
                item_api.get('orcamentoSigiloso'), # API envia boolean
                item_api.get('itemCategoriaNome'),
                item_api.get('categoriaItemCatalogo'),
                item_api.get('criterioJulgamentoNome'),
                item_api.get('situacaoCompraItemNome'),
                item_api.get('tipoBeneficioNome'),
                item_api.get('incentivoProdutivoBasico'), # API envia boolean
                item_api.get('dataInclusao', '').split('T')[0] if item_api.get('dataInclusao') else None,
                item_api.get('dataAtualizacao', '').split('T')[0] if item_api.get('dataAtualizacao') else None,
                item_api.get('temResultado'), # API envia boolean
                item_api.get('informacaoComplementar')
            )
            try: # ... (try-except para executar o insert)
                cursor.execute(sql_insert_item, item_db_tuple)
                itens_salvos_count += 1
            except sqlite3.Error as e:
                print(f"ERRO (save_db): Ao salvar item {item_api.get('numeroItem')} da licitação ID {licitacao_id_local}: {e} - Dados: {item_db_tuple}")
        if itens_salvos_count > 0:
            print(f"INFO (save_db): {itens_salvos_count} itens da licitação {licitacao_id_local} salvos.")
    return todos_itens_api


### ARQUIVOS ###
def fetch_all_arquivos_for_licitacao(conn, licitacao_id_local, cnpj_orgao, ano_compra, sequencial_compra):
    todos_arquivos_api_metadados = [] # Lista para guardar os metadados de todos os arquivos
    pagina_atual_arquivos = 1
    tamanho_pagina_arquivos = 100 # API do PNCP costuma ter limites altos para sub-recursos

    while True:
        # 1. Busca uma página de METADADOS de arquivos para verificar a quantidade de arquivos
        arquivos_pagina_metadados = fetch_arquivos_from_api( # Função que chama o endpoint de lista
            cnpj_orgao, ano_compra, sequencial_compra, 
            pagina_atual_arquivos, tamanho_pagina_arquivos
        )
        
        if arquivos_pagina_metadados is None: # Erro na chamada
            print(f"ARQUIVOS: Falha ao buscar página {pagina_atual_arquivos} de arquivos. Abortando.")
            return # Ou lida com o erro de outra forma
                
        if not arquivos_pagina_metadados: # Lista vazia, fim da paginação
            break
            
        todos_arquivos_api_metadados.extend(arquivos_pagina_metadados)
        
        if len(arquivos_pagina_metadados) < tamanho_pagina_arquivos:
            break
        pagina_atual_arquivos += 1
        time.sleep(0.2)
        
    print(f"ARQUIVOS: Total de {len(todos_arquivos_api_metadados)} metadados de arquivos encontrados para {cnpj_orgao}/{ano_compra}/{sequencial_compra}.")
    
    if todos_arquivos_api_metadados:
        cursor = conn.cursor()
        # Opcional: Deletar arquivos antigos desta licitação antes de (re)inserir
        try:
            cursor.execute("DELETE FROM arquivos_licitacao WHERE licitacao_id = ?", (licitacao_id_local,))
        except sqlite3.Error as e:
            print(f"ERRO (save_db): Ao deletar arquivos antigos da licitação ID {licitacao_id_local}: {e}")

        sql_insert_arquivo = """
            INSERT INTO arquivos_licitacao (
                licitacao_id, titulo, link_download, dataPublicacaoPncp, anoCompra, statusAtivo
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(link_download) DO NOTHING;""" 
                    
        arquivos_salvos_count = 0
        for arquivo_metadata_api in todos_arquivos_api_metadados: # Itera sobre os metadados de cada arquivo
            nome_do_arquivo = arquivo_metadata_api.get('titulo')
            id_do_documento_api = arquivo_metadata_api.get('sequencialDocumento') 

            if nome_do_arquivo and id_do_documento_api is not None: # id pode ser 0
                # 2. Monta o link de download para ESTE arquivo específico
                link_de_download_individual = f"{API_BASE_URL_PNCP_API}/v1/orgaos/{cnpj_orgao}/compras/{ano_compra}/{sequencial_compra}/arquivos/{id_do_documento_api}"
                
                arquivo_db_tuple =(
                    licitacao_id_local,
                    arquivo_metadata_api.get('titulo'),
                    link_de_download_individual,
                    arquivo_metadata_api.get('dataPublicacaoPncp', '').split('T')[0] if arquivo_metadata_api.get('dataPublicacaoPncp') else None,
                    arquivo_metadata_api.get('anoCompra'),
                    arquivo_metadata_api.get('statusAtivo')
                )
                try:
                    cursor.execute(sql_insert_arquivo, arquivo_db_tuple)
                    if cursor.rowcount > 0:
                        arquivos_salvos_count += 1
                except sqlite3.Error as e:
                    print(f"ERRO (save_db): Ao salvar arquivo {nome_do_arquivo} (lic_id {licitacao_id_local}): {e} - Dados: {arquivo_db_tuple}")
            else:
                print(f"AVISO (arquivos): Metadados do arquivo incompletos, pulando. Nome: {nome_do_arquivo}, ID Doc: {id_do_documento_api}")

        if arquivos_salvos_count > 0:
            print(f"INFO (save_db): {arquivos_salvos_count} arquivos da licitação {licitacao_id_local} salvos.")
           


    
def get_db_connection():
    """Retorna uma conexão com o banco de dados."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row # (Permite acessar colunas pelo nome)
    return conn



# --- Lógica Principal de Sincronização ---
def fetch_licitacoes_from_api(codigo_modalidade, pagina=1):
    """Busca licitações de uma página específica da API para uma dada modalidade."""
    params = {
        'dataFinal': DATA_ATUAL_PARAM,
        'codigoModalidadeContratacao': codigo_modalidade,
        'pagina': pagina,
        'tamanhoPagina': TAMANHO_PAGINA,
        # 'ufSigla': 'SP', # Exemplo se quisesse filtrar por UF
        # 'codigoMunicipioIbge': '3550308', # Exemplo para São Paulo capital
        # Outros parâmetros opcionais podem ser adicionados aqui
    }
    headers = {
        'Accept': 'application/json' # (Define o tipo de conteúdo esperado na resposta)
    }
    
    url = f"{API_BASE_URL}{ENDPOINT_PROPOSTAS_ABERTAS}"
    print(f"Buscando dados da API: {url} com params: {params}")
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30) # (Timeout de 30s)
        response.raise_for_status() # (Levanta um erro HTTP para respostas 4xx ou 5xx)

        if response.status_code == 204: # (No Content)
            print("API retornou 204 No Content (sem dados para os parâmetros).")
            return None, 0 # (Retorna None para dados e 0 para páginas restantes)
        
        data = response.json() # (Converte a resposta JSON em um dicionário Python)
        return data.get('data'), data.get('paginasRestantes', 0) # (Retorna a lista de licitações e o número de páginas restantes)

    except requests.exceptions.HTTPError as http_err:
        print(f"Erro HTTP ao chamar a API: {http_err}")
        print(f"Conteúdo da resposta: {response.text if response else 'Nenhuma resposta'}")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Erro de Conexão com a API: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"Timeout ao chamar a API: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"Erro genérico de requisição à API: {req_err}")
    except json.JSONDecodeError as json_err:
        print(f"Erro ao decodificar JSON da API: {json_err.msg}. Resposta: {response.text}")

    return None, 0 # (Em caso de erro, retorna None e 0 páginas restantes)


def save_licitacao_to_db(conn, licitacao_api_lista, pncp_ids_from_current_sync_set):
    cursor = conn.cursor()
    
    # Criação do link_portal_pncp (COMO VOCÊ FEZ, ESTÁ ÓTIMO)
    cnpj_orgao_link = licitacao_api_lista.get('orgaoEntidade', {}).get('cnpj')
    ano_compra_link = licitacao_api_lista.get('anoCompra')
    sequencial_compra_link = licitacao_api_lista.get('sequencialCompra')
    link_pncp_val = None
    if cnpj_orgao_link and ano_compra_link and sequencial_compra_link is not None:
        try:
            seq_sem_zeros = str(int(str(sequencial_compra_link)))
            link_pncp_val = f"https://pncp.gov.br/app/editais/{cnpj_orgao_link}/{ano_compra_link}/{seq_sem_zeros}"
        except ValueError:
            link_pncp_val = None

    # Mapeamento de licitacao_db (COMO VOCÊ FEZ, SÓ ADICIONANDO link_portal_pncp AO FINAL)
    licitacao_db = {
        'numeroControlePNCP': licitacao_api_lista.get('numeroControlePNCP'),
        'numeroCompra': licitacao_api_lista.get('numeroCompra'),
        'anoCompra': licitacao_api_lista.get('anoCompra'),
        'processo': licitacao_api_lista.get('processo'),
        'tipolnstrumentoConvocatorioId': licitacao_api_lista.get('tipoInstrumentoConvocatorioCodigo'),
        'tipolnstrumentoConvocatorioNome': licitacao_api_lista.get('tipoInstrumentoConvocatorioNome'),
        'modalidadeId': licitacao_api_lista.get('modalidadeId'),
        'modalidadeNome': licitacao_api_lista.get('modalidadeNome'),
        'modoDisputaId': licitacao_api_lista.get('modoDisputaId'),
        'modoDisputaNome': licitacao_api_lista.get('modoDisputaNome'),
        'situacaoCompraId': licitacao_api_lista.get('situacaoCompraId'),
        'situacaoCompraNome': licitacao_api_lista.get('situacaoCompraNome'),
        'objetoCompra': licitacao_api_lista.get('objetoCompra'),
        'informacaoComplementar': licitacao_api_lista.get('informacaoComplementar'),
        'srp': licitacao_api_lista.get('srp'),
        'amparoLegalCodigo': licitacao_api_lista.get('amparoLegal', {}).get('codigo'),
        'amparoLegalNome': licitacao_api_lista.get('amparoLegal', {}).get('nome'),
        'amparoLegalDescricao': licitacao_api_lista.get('amparoLegal', {}).get('descricao'),
        'valorTotalEstimado': licitacao_api_lista.get('valorTotalEstimado'),
        'valorTotalHomologado': licitacao_api_lista.get('valorTotalHomologado'),
        'dataAberturaProposta': licitacao_api_lista.get('dataAberturaProposta', '').split('T')[0] if licitacao_api_lista.get('dataAberturaProposta') else None,
        'dataEncerramentoProposta': licitacao_api_lista.get('dataEncerramentoProposta', '').split('T')[0] if licitacao_api_lista.get('dataEncerramentoProposta') else None,
        'dataPublicacaoPncp': licitacao_api_lista.get('dataPublicacaoPncp', '').split('T')[0] if licitacao_api_lista.get('dataPublicacaoPncp') else None,
        'dataInclusao': licitacao_api_lista.get('dataInclusao', '').split('T')[0] if licitacao_api_lista.get('dataInclusao') else None,
        'dataAtualizacao': licitacao_api_lista.get('dataAtualizacao', '').split('T')[0] if licitacao_api_lista.get('dataAtualizacao') else None,
        'sequencialCompra': licitacao_api_lista.get('sequencialCompra'),
        'orgaoEntidadeCnpj': licitacao_api_lista.get('orgaoEntidade', {}).get('cnpj'),
        'orgaoEntidadeRazaoSocial': licitacao_api_lista.get('orgaoEntidade', {}).get('razaoSocial'),
        'orgaoEntidadePoderId': licitacao_api_lista.get('orgaoEntidade', {}).get('poderId'),
        'orgaoEntidadeEsferaId': licitacao_api_lista.get('orgaoEntidade', {}).get('esferaId'),
        'unidadeOrgaoCodigo': licitacao_api_lista.get('unidadeOrgao', {}).get('codigoUnidade'),
        'unidadeOrgaoNome': licitacao_api_lista.get('unidadeOrgao', {}).get('nomeUnidade'),
        'unidadeOrgaoCodigoIbge': licitacao_api_lista.get('unidadeOrgao', {}).get('codigoIbge'),
        'unidadeOrgaoMunicipioNome': licitacao_api_lista.get('unidadeOrgao', {}).get('municipioNome'),
        'unidadeOrgaoUfSigla': licitacao_api_lista.get('unidadeOrgao', {}).get('ufSigla'),
        'unidadeOrgaoUfNome': licitacao_api_lista.get('unidadeOrgao', {}).get('ufNome'),
        'usuarioNome': licitacao_api_lista.get('usuarioNome'),
        'linkSistemaOrigem': licitacao_api_lista.get('linkSistemaOrigem'),
        'link_portal_pncp': link_pncp_val, # Adicionado
        'justificativaPresencial': licitacao_api_lista.get('justificativaPresencial')
    }
    
    if not licitacao_db['numeroControlePNCP']:
        print(f"AVISO (save_db): Licitação da lista sem 'numeroControlePNCP'. Dados: {licitacao_api_lista}")
        return None

    if licitacao_db['situacaoCompraId'] == 1:
        pncp_ids_from_current_sync_set.add(licitacao_db['numeroControlePNCP'])
    else:
        print(f"INFO (save_db): Licitação {licitacao_db['numeroControlePNCP']} da lista não é ativa (situação: {licitacao_db['situacaoCompraId']}). Pulando.")
        return None

    # SQL UPSERT ATUALIZADO
    sql_upsert_licitacao = """
    INSERT INTO licitacoes (
        numeroControlePNCP, numeroCompra, anoCompra, processo,
        tipolnstrumentoConvocatorioId, tipolnstrumentoConvocatorioNome,
        modalidadeId, modalidadeNome, modoDisputaId, modoDisputaNome,
        situacaoCompraId, situacaoCompraNome, objetoCompra, informacaoComplementar, srp,
        amparoLegalCodigo, amparoLegalNome, amparoLegalDescricao,
        valorTotalEstimado, valorTotalHomologado, dataAberturaProposta,
        dataEncerramentoProposta, dataPublicacaoPncp, dataInclusao, dataAtualizacao,
        sequencialCompra, orgaoEntidadeCnpj, orgaoEntidadeRazaoSocial,
        orgaoEntidadePoderId, orgaoEntidadeEsferaId, unidadeOrgaoCodigo, unidadeOrgaoNome,
        unidadeOrgaoCodigoIbge, unidadeOrgaoMunicipioNome, unidadeOrgaoUfSigla,
        unidadeOrgaoUfNome, usuarioNome, linkSistemaOrigem, 
        link_portal_pncp, justificativaPresencial                  -- Adicionado link_portal_pncp
    ) VALUES (
        :numeroControlePNCP, :numeroCompra, :anoCompra, :processo,
        :tipolnstrumentoConvocatorioId, :tipolnstrumentoConvocatorioNome,
        :modalidadeId, :modalidadeNome, :modoDisputaId, :modoDisputaNome,
        :situacaoCompraId, :situacaoCompraNome, :objetoCompra, :informacaoComplementar, :srp,
        :amparoLegalCodigo, :amparoLegalNome, :amparoLegalDescricao,
        :valorTotalEstimado, :valorTotalHomologado, :dataAberturaProposta,
        :dataEncerramentoProposta, :dataPublicacaoPncp, :dataInclusao, :dataAtualizacao,
        :sequencialCompra, :orgaoEntidadeCnpj, :orgaoEntidadeRazaoSocial,
        :orgaoEntidadePoderId, :orgaoEntidadeEsferaId, :unidadeOrgaoCodigo, :unidadeOrgaoNome,
        :unidadeOrgaoCodigoIbge, :unidadeOrgaoMunicipioNome, :unidadeOrgaoUfSigla,
        :unidadeOrgaoUfNome, :usuarioNome, :linkSistemaOrigem,
        :link_portal_pncp, :justificativaPresencial              -- Adicionado :link_portal_pncp
    )
    ON CONFLICT(numeroControlePNCP) DO UPDATE SET
        numeroCompra = excluded.numeroCompra,
        anoCompra = excluded.anoCompra,
        processo = excluded.processo,
        tipolnstrumentoConvocatorioId = excluded.tipolnstrumentoConvocatorioId,
        tipolnstrumentoConvocatorioNome = excluded.tipolnstrumentoConvocatorioNome,
        modalidadeId = excluded.modalidadeId,
        modalidadeNome = excluded.modalidadeNome,
        modoDisputaId = excluded.modoDisputaId,
        modoDisputaNome = excluded.modoDisputaNome,
        situacaoCompraId = excluded.situacaoCompraId,
        situacaoCompraNome = excluded.situacaoCompraNome,
        objetoCompra = excluded.objetoCompra,
        informacaoComplementar = excluded.informacaoComplementar,
        srp = excluded.srp,
        amparoLegalCodigo = excluded.amparoLegalCodigo,
        amparoLegalNome = excluded.amparoLegalNome,
        amparoLegalDescricao = excluded.amparoLegalDescricao,
        valorTotalEstimado = excluded.valorTotalEstimado,
        valorTotalHomologado = excluded.valorTotalHomologado,
        dataAberturaProposta = excluded.dataAberturaProposta,
        dataEncerramentoProposta = excluded.dataEncerramentoProposta,
        dataPublicacaoPncp = excluded.dataPublicacaoPncp,
        dataInclusao = excluded.dataInclusao,
        dataAtualizacao = excluded.dataAtualizacao,
        sequencialCompra = excluded.sequencialCompra,
        orgaoEntidadeCnpj = excluded.orgaoEntidadeCnpj,
        orgaoEntidadeRazaoSocial = excluded.orgaoEntidadeRazaoSocial,
        orgaoEntidadePoderId = excluded.orgaoEntidadePoderId,
        orgaoEntidadeEsferaId = excluded.orgaoEntidadeEsferaId,
        unidadeOrgaoCodigo = excluded.unidadeOrgaoCodigo,
        unidadeOrgaoNome = excluded.unidadeOrgaoNome,
        unidadeOrgaoCodigoIbge = excluded.unidadeOrgaoCodigoIbge,
        unidadeOrgaoMunicipioNome = excluded.unidadeOrgaoMunicipioNome,
        unidadeOrgaoUfSigla = excluded.unidadeOrgaoUfSigla,
        unidadeOrgaoUfNome = excluded.unidadeOrgaoUfNome,
        usuarioNome = excluded.usuarioNome,
        linkSistemaOrigem = excluded.linkSistemaOrigem,
        link_portal_pncp = excluded.link_portal_pncp,             -- Adicionado link_portal_pncp
        justificativaPresencial = excluded.justificativaPresencial
    WHERE licitacoes.dataAtualizacao < excluded.dataAtualizacao OR licitacoes.dataAtualizacao IS NULL;"""
    
    licitacao_id_local_final = None
    flag_houve_mudanca_real = False 

    try:
        cursor.execute("SELECT id, dataAtualizacao FROM licitacoes WHERE numeroControlePNCP = ?", (licitacao_db['numeroControlePNCP'],))
        row = cursor.fetchone()
        data_atualizacao_api_dt = datetime.strptime(licitacao_db['dataAtualizacao'], '%Y-%m-%d') if licitacao_db['dataAtualizacao'] else None

        if row: 
            id_existente, data_atualizacao_db_str = row
            licitacao_id_local_final = id_existente
            if data_atualizacao_db_str: # Apenas tenta converter se não for None
                data_atualizacao_db_dt = datetime.strptime(data_atualizacao_db_str, '%Y-%m-%d')
                if data_atualizacao_api_dt and (data_atualizacao_api_dt > data_atualizacao_db_dt):
                    flag_houve_mudanca_real = True
            elif data_atualizacao_api_dt: # DB não tem data, API tem -> é uma atualização
                flag_houve_mudanca_real = True
        else: 
            flag_houve_mudanca_real = True 

        if flag_houve_mudanca_real: 
            cursor.execute(sql_upsert_licitacao, licitacao_db) 
            if cursor.rowcount > 0:
                if not row: 
                    licitacao_id_local_final = cursor.lastrowid
                # (Já temos licitacao_id_local_final se row existia)
                print(f"INFO (save_db): Licitação {licitacao_db['numeroControlePNCP']} INSERIDA/ATUALIZADA com ID local {licitacao_id_local_final}.")
            elif row: # UPSERT não afetou (WHERE não passou), mas ID já existe
                 licitacao_id_local_final = row[0] # Garante que temos o ID
                 print(f"INFO (save_db): Licitação {licitacao_db['numeroControlePNCP']} (ID {licitacao_id_local_final}) já existe, UPSERT não alterou (data não mais nova).")
            # else: # Não existia e não inseriu? Erro ou condição inesperada
        elif row : 
            licitacao_id_local_final = row[0]
            print(f"INFO (save_db): Licitação {licitacao_db['numeroControlePNCP']} (ID {licitacao_id_local_final}) já existe e está atualizada. Nenhuma alteração na principal.")
        
        # Se ainda não temos o ID local (caso de UPSERT ter falhado ou WHERE não satisfeito e não era nova)
        if not licitacao_id_local_final and row: # Se existia mas algo deu errado no UPSERT
            licitacao_id_local_final = row[0]
        elif not licitacao_id_local_final and not row and not flag_houve_mudanca_real: # Não existia e não era pra mudar, mas não pegou ID?
            # Tenta pegar o ID recém-inserido se for o caso, ou se UPSERT falhou em retornar lastrowid
             cursor.execute("SELECT id FROM licitacoes WHERE numeroControlePNCP = ?", (licitacao_db['numeroControlePNCP'],))
             id_row_check = cursor.fetchone()
             if id_row_check: licitacao_id_local_final = id_row_check[0]


    except sqlite3.Error as e:
        print(f"ERRO (save_db): Ao salvar licitação principal {licitacao_db.get('numeroControlePNCP', 'N/A')}: {e}")
        return None 
    
    if not licitacao_id_local_final:
        print(f"AVISO CRÍTICO (save_db): Não foi possível obter/confirmar ID local para {licitacao_db['numeroControlePNCP']}. Pulando sub-detalhes.")
        return None

    # --- BUSCAR E SALVAR ITENS (e futuramente ARQUIVOS) ---
    buscar_sub_detalhes = False
    if flag_houve_mudanca_real:
        buscar_sub_detalhes = True
    else: 
        cursor.execute("SELECT COUNT(id) FROM itens_licitacao WHERE licitacao_id = ?", (licitacao_id_local_final,))
        count_itens = cursor.fetchone()[0]
        if count_itens == 0:
            buscar_sub_detalhes = True
            print(f"INFO (save_db): Licitação {licitacao_db['numeroControlePNCP']} (ID {licitacao_id_local_final}) sem mudança principal, mas não possui itens. Buscando itens.")
    
    if buscar_sub_detalhes:
        cnpj_param = licitacao_db.get('orgaoEntidadeCnpj')
        ano_param = licitacao_db.get('anoCompra')
        sequencial_param = licitacao_db.get('sequencialCompra')

        if cnpj_param and ano_param and sequencial_param is not None:
            print(f"INFO (save_db): Iniciando busca de ITENS para {licitacao_db['numeroControlePNCP']} (ID Local: {licitacao_id_local_final})")
            fetch_all_itens_for_licitacao(conn, licitacao_id_local_final, cnpj_param, ano_param, sequencial_param)
            
            print(f"INFO (save_db): Iniciando busca de ARQUIVOS para {licitacao_db['numeroControlePNCP']} (ID Local: {licitacao_id_local_final})")
            fetch_all_arquivos_for_licitacao(conn, licitacao_id_local_final, cnpj_param, ano_param, sequencial_param) # Descomentar e implementar
        else:
            print(f"AVISO (save_db): Não foi possível buscar sub-detalhes para {licitacao_db['numeroControlePNCP']} por falta de CNPJ, Ano ou Sequencial.")
    else:
        print(f"INFO (save_db): Licitação {licitacao_db['numeroControlePNCP']} (ID {licitacao_id_local_final}) não necessita busca de sub-detalhes no momento.")

    return licitacao_id_local_final


def sync_all_active_licitacoes():
    conn = get_db_connection()
    if not conn:
        return

    total_licitacoes_com_subdetalhes_processados = 0 # Renomeado para clareza
    total_erros_api_lista = 0 # Para erros ao buscar a lista principal

    pncp_ids_from_current_sync = set() 

    for codigo_modalidade in CODIGOS_MODALIDADE:
        print(f"\n--- Iniciando sincronização para modalidade: {codigo_modalidade} ---")
        pagina_atual = 1
        paginas_processadas_modalidade = 0

        while True:
            if LIMITE_PAGINAS_TESTE is not None and paginas_processadas_modalidade >= LIMITE_PAGINAS_TESTE:
                print(f"Limite de {LIMITE_PAGINAS_TESTE} páginas de teste atingido para modalidade {codigo_modalidade}. Parando.")
                break
            
            print(f"Buscando página {pagina_atual} para modalidade {codigo_modalidade}...")
            licitacoes_data, paginas_restantes = fetch_licitacoes_from_api(codigo_modalidade, pagina_atual)

            if licitacoes_data is None: # Erro na chamada da API de lista
				# Se fetch_licitacoes_from_api retorna None para os dados, pode ser um erro de API ou 204 No Content.
                # Se for 204, paginas_restantes também será 0, o loop vai parar.
                # Se for erro de API, paginas_restantes será 0 e o loop também para.
                total_erros_api_lista += 1
                if total_erros_api_lista > 5:
                    print("Muitos erros de API ao buscar listas. Abortando sincronização.")
                    conn.close() # Fechar conexão antes de sair
                    return # Sair da função sync_all_active_licitacoes
                print(f"Não foi possível obter dados da página {pagina_atual} para modalidade {codigo_modalidade}. Tentando próxima ou parando.")
                # Decide se continua para a próxima página ou para a modalidade (paginas_restantes=0 pararia)
                # Se o erro for crítico, o break abaixo é apropriado para a modalidade.
                # Se quiséssemos tentar a próxima página mesmo com erro nesta, a lógica seria diferente.
                break # Para esta modalidade se houve erro na busca da página atual

            if not licitacoes_data: # Lista explicitamente vazia (não None)
                print(f"Nenhuma licitação encontrada na página {pagina_atual} para modalidade {codigo_modalidade}.")
            else: 
                print(f"Processando {len(licitacoes_data)} licitações da página {pagina_atual}...")
                for licitacao_api_item_da_lista in licitacoes_data:
                    # Passa o item da lista e o set para a função
                    # save_licitacao_to_db irá:
                    # 1. Salvar/atualizar licitacao principal se for ativa.
                    # 2. Adicionar ao pncp_ids_from_current_sync se ativa.
                    # 3. Chamar fetch_all_itens_for_licitacao (e futuramente arquivos).
                    id_local_salvo = save_licitacao_to_db(conn, licitacao_api_item_da_lista, pncp_ids_from_current_sync)
                    
                    if id_local_salvo: # Se save_licitacao_to_db processou e retornou um ID
                        total_licitacoes_com_subdetalhes_processados += 1
            
            conn.commit() # Commit após processar todos os itens de uma página da lista
            print(f"Página {pagina_atual} processada. {paginas_restantes} páginas restantes para esta modalidade.")
            paginas_processadas_modalidade += 1
            
            if paginas_restantes == 0:
                print(f"Todas as páginas processadas para a modalidade {codigo_modalidade}.")
                break 
            
            pagina_atual += 1
            time.sleep(0.5) 
        
        if total_erros_api_lista > 5: break # Sai do loop de modalidades também

    # Aqui viria a lógica de limpeza de licitações que não estão mais ativas (usando pncp_ids_from_current_sync)
    # Mas vamos deixar isso para depois, conforme o plano.

    conn.close()
    print(f"\n--- Sincronização concluída ---")
    print(f"Total de licitações da lista para as quais tentamos salvar/atualizar dados principais e sub-detalhes: {total_licitacoes_com_subdetalhes_processados}")

# ... (if __name__ == '__main__': ...)

save_licitacao_to_db
# --- Ponto de Entrada do Script ---
if __name__ == '__main__':
    print("Iniciando script de sincronização com a API do PNCP...")
    sync_all_active_licitacoes()
    print("Script de sincronização finalizado.") 