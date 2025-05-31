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
TAMANHO_PAGINA_SYNC  = 50 # OBRIGATORIO
LIMITE_PAGINAS_TESTE_SYNC = 1 # OBRIGATORIO. Mudar para None para buscar todas.
CODIGOS_MODALIDADE = [5, 6] # (OBRIGATORIO. 5 = Concorrencia; 6 = Pregão Eletrônico)
API_BASE_URL = "https://pncp.gov.br/api/consulta" # (URL base da API do PNCP)      
API_BASE_URL_PNCP_API = "https://pncp.gov.br/pncp-api"   # Para itens e arquivos    ## PARA TODOS OS LINKS DE ARQUIVOS E ITENS USAR PAGINAÇÃO SE NECESSARIO ##
ENDPOINT_PROPOSTAS_ABERTAS = "/v1/contratacoes/proposta" # (Endpoint específico)


    ##CONFIGURAÇÃO DA API PARA ENCONTRAR OS ITENS/ARQUIVOS DAS LICITAÇÕES ##
def fetch_itens_from_api(cnpj_orgao, ano_compra, sequencial_compra, pagina=1, tamanho_pagina=TAMANHO_PAGINA_SYNC):
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
        print(f"ITENS: Erro ao buscar itens para {cnpj_orgao}/{ano_compra}/{sequencial_compra} (Pag: {pagina}): {e}")
        if hasattr(e, 'response') and e.response is not None:
             print(f"ITENS: Status: {e.response.status_code}, Texto: {e.response.text[:200]}")
        return None # Indica erro
    
def fetch_arquivos_from_api(cnpj_orgao, ano_compra, sequencial_compra, pagina=1, tamanho_pagina=TAMANHO_PAGINA_SYNC ):
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
        print(f"ARQUIVOS: Erro ao buscar arquivoS para {cnpj_orgao}/{ano_compra}/{sequencial_compra} (Pag: {pagina}): {e}")
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
        itens_pagina = fetch_itens_from_api(cnpj_orgao, ano_compra, sequencial_compra, pagina_atual_itens, TAMANHO_PAGINA_SYNC)
        if itens_pagina is None: 
            print(f"ITENS: Falha ao buscar página {pagina_atual_itens} de itens. Abortando busca de itens para esta licitação.")
            return None # Ou retorna o que conseguiu até agora: todos_itens_api
        if not itens_pagina: # Lista vazia, fim da paginação
            break
        todos_itens_api.extend(itens_pagina)
        # Se o número de itens retornados for menor que tamanho_pagina_itens, assumimos que é a última página.
        if len(itens_pagina) < TAMANHO_PAGINA_SYNC:
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
            item_db_tuple = (      
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

    while True:
        # 1. Busca uma página de METADADOS de arquivos para verificar a quantidade de arquivos
        arquivos_pagina_metadados = fetch_arquivos_from_api(
            cnpj_orgao, ano_compra, sequencial_compra, 
            pagina_atual_arquivos, TAMANHO_PAGINA_SYNC
        )
        
        if arquivos_pagina_metadados is None: # Erro na chamada
            print(f"ARQUIVOS: Falha ao buscar página {pagina_atual_arquivos} de arquivos. Abortando.")
            return # Ou lida com o erro de outra forma
                
        if not arquivos_pagina_metadados: # Lista vazia, fim da paginação
            break
            
        todos_arquivos_api_metadados.extend(arquivos_pagina_metadados)
        
        if len(arquivos_pagina_metadados) < TAMANHO_PAGINA_SYNC:
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
            print(f"ERRO (ARQUIVOS): Ao deletar arquivos antigos da licitação ID {licitacao_id_local}: {e}")

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
#def fetch_licitacoes_from_api(codigo_modalidade, pagina=1):
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

def format_datetime_for_api(dt_obj): 
    """Formata um objeto datetime para YYYYMMDD."""
    return dt_obj.strftime('%Y%m%d')

def fetch_licitacoes_por_atualizacao(data_inicio_str, data_fim_str, codigo_modalidade_api, pagina=1, tamanho_pagina=TAMANHO_PAGINA_SYNC):
    """Busca licitações da API /v1/contratacoes/atualizacao."""
    params_api = {
        'dataInicial': data_inicio_str,
        'dataFinal': data_fim_str,
        'pagina': pagina,
        'tamanhoPagina': tamanho_pagina,
        'codigoModalidadeContratacao': codigo_modalidade_api
    }
    url_api_pncp = f"{API_BASE_URL}/v1/contratacoes/atualizacao" 
    print(f"SYNC ATUALIZACAO: Buscando em {url_api_pncp} com params {params_api}")
    
    try:
        response = requests.get(url_api_pncp, params=params_api, timeout=120)
        response.raise_for_status()
        if response.status_code == 204:
            return None, 0
        data_api = response.json()
        return data_api.get('data'), data_api.get('paginasRestantes', 0)
    except Exception as e:
        print(f"SYNC ATUALIZACAO: Erro geral ao buscar (modalidade {codigo_modalidade_api}, pag {pagina}): {e}")
        return None, 0


def  save_licitacao_to_db(conn, licitacao_api_item): 
    cursor = conn.cursor()
      
    # Criação do link_portal_pncp 
    cnpj_orgao_link = licitacao_api_item.get('orgaoEntidade', {}).get('cnpj')
    ano_compra_link = licitacao_api_item.get('anoCompra')
    sequencial_compra_link = licitacao_api_item.get('sequencialCompra')
    link_pncp_val = None
    if cnpj_orgao_link and ano_compra_link and sequencial_compra_link is not None:
        try:
            seq_sem_zeros = str(int(str(sequencial_compra_link)))
            link_pncp_val = f"https://pncp.gov.br/app/editais/{cnpj_orgao_link}/{ano_compra_link}/{seq_sem_zeros}"
        except ValueError:
            link_pncp_val = None

    # Mapeamento de licitacao_db 
    licitacao_db = {
        'numeroControlePNCP': licitacao_api_item.get('numeroControlePNCP'),
        'numeroCompra': licitacao_api_item.get('numeroCompra'),
        'anoCompra': licitacao_api_item.get('anoCompra'),
        'processo': licitacao_api_item.get('processo'),
        'tipolnstrumentoConvocatorioId': licitacao_api_item.get('tipoInstrumentoConvocatorioCodigo'),
        'tipolnstrumentoConvocatorioNome': licitacao_api_item.get('tipoInstrumentoConvocatorioNome'),
        'modalidadeId': licitacao_api_item.get('modalidadeId'),
        'modalidadeNome': licitacao_api_item.get('modalidadeNome'),
        'modoDisputaId': licitacao_api_item.get('modoDisputaId'),
        'modoDisputaNome': licitacao_api_item.get('modoDisputaNome'),
        'situacaoCompraId': licitacao_api_item.get('situacaoCompraId'),
        'situacaoCompraNome': licitacao_api_item.get('situacaoCompraNome'),
        'objetoCompra': licitacao_api_item.get('objetoCompra'),
        'informacaoComplementar': licitacao_api_item.get('informacaoComplementar'),
        'srp': licitacao_api_item.get('srp'),
        'amparoLegalCodigo': licitacao_api_item.get('amparoLegal', {}).get('codigo'),
        'amparoLegalNome': licitacao_api_item.get('amparoLegal', {}).get('nome'),
        'amparoLegalDescricao': licitacao_api_item.get('amparoLegal', {}).get('descricao'),
        'valorTotalEstimado': licitacao_api_item.get('valorTotalEstimado'),
        'valorTotalHomologado': licitacao_api_item.get('valorTotalHomologado'),
        'dataAberturaProposta': licitacao_api_item.get('dataAberturaProposta', '').split('T')[0] if licitacao_api_item.get('dataAberturaProposta') else None,
        'dataEncerramentoProposta': licitacao_api_item.get('dataEncerramentoProposta', '').split('T')[0] if licitacao_api_item.get('dataEncerramentoProposta') else None,
        'dataPublicacaoPncp': licitacao_api_item.get('dataPublicacaoPncp', '').split('T')[0] if licitacao_api_item.get('dataPublicacaoPncp') else None,
        'dataInclusao': licitacao_api_item.get('dataInclusao', '').split('T')[0] if licitacao_api_item.get('dataInclusao') else None,
        'dataAtualizacao': licitacao_api_item.get('dataAtualizacao', '').split('T')[0] if licitacao_api_item.get('dataAtualizacao') else None,
        'sequencialCompra': licitacao_api_item.get('sequencialCompra'),
        'orgaoEntidadeCnpj': licitacao_api_item.get('orgaoEntidade', {}).get('cnpj'),
        'orgaoEntidadeRazaoSocial': licitacao_api_item.get('orgaoEntidade', {}).get('razaoSocial'),
        'orgaoEntidadePoderId': licitacao_api_item.get('orgaoEntidade', {}).get('poderId'),
        'orgaoEntidadeEsferaId': licitacao_api_item.get('orgaoEntidade', {}).get('esferaId'),
        'unidadeOrgaoCodigo': licitacao_api_item.get('unidadeOrgao', {}).get('codigoUnidade'),
        'unidadeOrgaoNome': licitacao_api_item.get('unidadeOrgao', {}).get('nomeUnidade'),
        'unidadeOrgaoCodigoIbge': licitacao_api_item.get('unidadeOrgao', {}).get('codigoIbge'),
        'unidadeOrgaoMunicipioNome': licitacao_api_item.get('unidadeOrgao', {}).get('municipioNome'),
        'unidadeOrgaoUfSigla': licitacao_api_item.get('unidadeOrgao', {}).get('ufSigla'),
        'unidadeOrgaoUfNome': licitacao_api_item.get('unidadeOrgao', {}).get('ufNome'),
        'usuarioNome': licitacao_api_item.get('usuarioNome'),
        'linkSistemaOrigem': licitacao_api_item.get('linkSistemaOrigem'),
        'link_portal_pncp': link_pncp_val, 
        'justificativaPresencial': licitacao_api_item.get('justificativaPresencial')
    }
    
    if not licitacao_db['numeroControlePNCP']:
        print(f"AVISO (save_db): Licitação da lista sem 'numeroControlePNCP'. Dados: {licitacao_api_item}")
        return None

    """ --if licitacao_db['situacaoCompraId'] == 1:
        --pncp_ids_from_current_sync_set.add(licitacao_db['numeroControlePNCP'])
    --else:
        --print(f"INFO (save_db): Licitação {licitacao_db['numeroControlePNCP']} da lista não é ativa (situação: {licitacao_db['situacaoCompraId']}). Pulando.")
        --return None
    """

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
        api_data_att_str = licitacao_db.get('dataAtualizacao')
        api_data_att_dt = datetime.strptime(api_data_att_str, '%Y-%m-%d').date() if api_data_att_str else None

        if row:
            licitacao_id_local_final = row['id']
            db_data_att_str = row['dataAtualizacao']
            db_data_att_dt = datetime.strptime(db_data_att_str, '%Y-%m-%d').date() if db_data_att_str else None
            if api_data_att_dt and (not db_data_att_dt or api_data_att_dt > db_data_att_dt):
                flag_houve_mudanca_real = True
        else:
            flag_houve_mudanca_real = True

        if flag_houve_mudanca_real:
            cursor.execute(sql_upsert_licitacao, licitacao_db)
            if cursor.rowcount > 0:
                if not row: licitacao_id_local_final = cursor.lastrowid
                print(f"INFO (SAVE_DB): Licitação {licitacao_db['numeroControlePNCP']} UPSERTED. ID: {licitacao_id_local_final}")
            elif row: # Não atualizou (WHERE falhou), mas já existia
                 print(f"INFO (SAVE_DB): Licitação {licitacao_db['numeroControlePNCP']} não precisou de update (data não mais nova). ID: {licitacao_id_local_final}")
        elif row:
             print(f"INFO (SAVE_DB): Licitação {licitacao_db['numeroControlePNCP']} já atualizada. ID: {licitacao_id_local_final}")
        
        if not licitacao_id_local_final and flag_houve_mudanca_real: # Se era nova e UPSERT não deu lastrowid
            cursor.execute("SELECT id FROM licitacoes WHERE numeroControlePNCP = ?", (licitacao_db['numeroControlePNCP'],))
            id_row = cursor.fetchone()
            if id_row: licitacao_id_local_final = id_row['id']
            
    except sqlite3.Error as e:
        print(f"ERRO (save_db): Ao salvar licitação principal {licitacao_db.get('numeroControlePNCP', 'N/A')}: {e}")
        return None 
    
    if not licitacao_id_local_final:
        print(f"AVISO CRÍTICO (save_db): Não foi possível obter/confirmar ID local para {licitacao_db['numeroControlePNCP']}. Pulando sub-detalhes.")
        return None

    # --- BUSCAR E SALVAR ITENS
    buscar_sub_detalhes = False
    if flag_houve_mudanca_real: buscar_sub_detalhes = True
    else:
        cursor.execute("SELECT COUNT(id) FROM itens_licitacao WHERE licitacao_id = ?", (licitacao_id_local_final,))
        if cursor.fetchone()[0] == 0: buscar_sub_detalhes = True
            
    if buscar_sub_detalhes:        
        # Pegar cnpj, ano, sequencial de licitacao_db para passar para as funções
        cnpj_p = licitacao_db.get('orgaoEntidadeCnpj')
        ano_p = licitacao_db.get('anoCompra')
        seq_p = licitacao_db.get('sequencialCompra')
        if cnpj_p and ano_p and seq_p is not None:
            print(f"INFO (SAVE_DB): Iniciando busca de ITENS para {licitacao_db['numeroControlePNCP']}")
            fetch_all_itens_for_licitacao(conn, licitacao_id_local_final, cnpj_p, ano_p, seq_p)
            print(f"INFO (SAVE_DB): Iniciando busca de ARQUIVOS para {licitacao_db['numeroControlePNCP']}")
            fetch_all_arquivos_for_licitacao(conn, licitacao_id_local_final, cnpj_p, ano_p, seq_p)
        else:
             print(f"AVISO (SAVE_DB): Faltam CNPJ/Ano/Seq para buscar sub-detalhes de {licitacao_db['numeroControlePNCP']}")
    else:
        print(f"INFO (SAVE_DB): Licitação {licitacao_db['numeroControlePNCP']} não necessita busca de sub-detalhes.")
        
    return licitacao_id_local_final


def sync_licitacoes_ultima_janela_anual():
    conn = get_db_connection()
    if not conn: return

    agora = datetime.now()
    data_fim_periodo_dt = agora
    data_inicio_periodo_dt = agora - timedelta(days=365) # Últimos 12 meses

    data_inicio_api_str = format_datetime_for_api(data_inicio_periodo_dt)
    data_fim_api_str = format_datetime_for_api(data_fim_periodo_dt)

    print(f"SYNC ANUAL: Iniciando sincronização para licitações atualizadas entre {data_inicio_api_str} e {data_fim_api_str}")

    licitacoes_processadas_total = 0
    
    for modalidade_id_sync in CODIGOS_MODALIDADE:
        print(f"\n--- SYNC JANELA: Processando Modalidade {modalidade_id_sync} ---")
        pagina_atual = 1
        paginas_processadas_modalidade = 0
        erros_api_modalidade = 0

        while True:
            if LIMITE_PAGINAS_TESTE_SYNC is not None and paginas_processadas_modalidade >= LIMITE_PAGINAS_TESTE_SYNC:
                print(f"SYNC JANELA: Limite de {LIMITE_PAGINAS_TESTE_SYNC} páginas atingido para modalidade {modalidade_id_sync}.")
                break

            licitacoes_data, paginas_restantes = fetch_licitacoes_por_atualizacao(
                data_inicio_api_str, data_fim_api_str, modalidade_id_sync, pagina_atual
            )

            if licitacoes_data is None: # Erro
                erros_api_modalidade += 1
                if erros_api_modalidade > 3:
                    print(f"SYNC JANELA: Muitos erros de API para modalidade {modalidade_id_sync}. Abortando esta modalidade.")
                    break 
                if paginas_restantes == 0 : # Se API indicou erro e fim
                    break
    
            if not licitacoes_data: # Fim dos dados
                print(f"SYNC JANELA: Nenhuma licitação na API para modalidade {modalidade_id_sync}, página {pagina_atual}.")
                # Verifique se paginas_restantes é 0 para confirmar o fim
                if paginas_restantes == 0:
                    break
                else: # Pode ser uma página vazia no meio, mas API indica mais páginas (raro)
                    print(f"SYNC ANUAL: Página {pagina_atual} vazia, mas {paginas_restantes} páginas restantes. Tentando próxima.")
                    pagina_atual += 1
                    time.sleep(0.5)
                    continue

            print(f"SYNC JANELA: Modalidade {modalidade_id_sync}, Página {pagina_atual}: Processando {len(licitacoes_data)} licitações.")
            for lic_api in licitacoes_data:
                save_licitacao_to_db(conn, lic_api) # Removido o set
                licitacoes_processadas_total += 1
            
            conn.commit()
            print(f"SYNC JANELA: Modalidade {modalidade_id_sync}, Página {pagina_atual} processada. {paginas_restantes} páginas restantes.")
            paginas_processadas_modalidade += 1
            
            if paginas_restantes == 0: break
            pagina_atual += 1
            time.sleep(0.5)

    # Limpeza de licitações MUITO antigas (fora da janela de ~13 meses, por exemplo)
    agora = datetime.now() # Recalcula 'agora' para a limpeza
    data_limite_permanencia_dt = agora - timedelta(days=395) 
    data_limite_permanencia_db_str = data_limite_permanencia_dt.strftime('%Y-%m-%d')
    try:
        cursor = conn.cursor()
        print(f"SYNC JANELA: Limpando licitações com dataAtualizacao < {data_limite_permanencia_db_str}")
        cursor.execute("DELETE FROM licitacoes WHERE dataAtualizacao < ?", (data_limite_permanencia_db_str,))
        deleted_count = cursor.rowcount
        conn.commit()
        print(f"SYNC JANELA: Limpeza de {deleted_count} licitações antigas concluída.")
    except sqlite3.Error as e:
        print(f"SYNC JANELA: Erro na limpeza: {e}")

    conn.close()
    print(f"\n--- Sincronização da Janela Anual Concluída ---")
    print(f"Total de licitações da API (na janela de atualização) processadas: {licitacoes_processadas_total}")


if __name__ == '__main__':
    print("Iniciando script de sincronização (janela anual de atualizações)...")
    sync_licitacoes_ultima_janela_anual()
    print("Script de sincronização finalizado.")