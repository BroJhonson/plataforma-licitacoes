# python sync_api.py

import requests # (Para fazer requisições HTTP)
import sqlite3 # (Para interagir com o banco de dados SQLite)
import json # (Para lidar com dados JSON da API, embora 'requests' já faça muito disso)
import os # (Para caminhos de arquivo)
import time
from datetime import datetime, date, timedelta # (Para trabalhar com datas)
# -- CONFIGURAÇÃO DE PROXY PARA PYTHONANYWHERE --
# Necessário para contas gratuitas acessarem APIs fora da whitelist
proxy_url = "http://proxy.server:3128"
proxies = {
   "http": proxy_url,
   "https": proxy_url,
}
# -- FIM DA CONFIGURAÇÃO DE PROXY --


# --- Configurações ---
# Define o caminho para a pasta backend
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Define o caminho completo para o arquivo do banco de dados
DATABASE_PATH = os.path.join(BASE_DIR, 'database.db')
TAMANHO_PAGINA_SYNC  = 50 # OBRIGATORIO
LIMITE_PAGINAS_TESTE_SYNC = 1 # OBRIGATORIO. Mudar para None para buscar todas.
CODIGOS_MODALIDADE = [5, 6, 1, 2, 3, 4, 7, 8, 9, 10, 11, 12, 13 ] # (OBRIGATORIO)
DIAS_JANELA_SINCRONIZACAO = 365 #Periodo da busca
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
        response = requests.get(url, params=params, headers=headers, timeout=60, proxies=proxies)
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
        response = requests.get(url, params=params, headers=headers, timeout=60, proxies=proxies)
        response.raise_for_status()
        if response.status_code == 204: return [] # Retorna lista vazia        
        return response.json() 
    except Exception as e:
        print(f"ARQUIVOS: Erro ao buscar arquivoS para {cnpj_orgao}/{ano_compra}/{sequencial_compra} (Pag: {pagina}): {e}")
        if hasattr(e, 'response') and e.response is not None:
             print(f"ARQUIVOS: Status: {e.response.status_code}, Texto: {e.response.text[:200]}")
        return None 



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
        response = requests.get(url_api_pncp, params=params_api, timeout=120, proxies=proxies)
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
      
    # Mapeamento de licitacao_db 
    licitacao_db_parcial = {
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
        'dataAberturaProposta': licitacao_api_item.get('dataAberturaProposta'),
        'dataEncerramentoProposta': licitacao_api_item.get('dataEncerramentoProposta'),
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
        'justificativaPresencial': licitacao_api_item.get('justificativaPresencial'),
        #'link_portal_pncp': link_pncp_val
    }
    
    if not licitacao_db_parcial['numeroControlePNCP']:
        print(f"AVISO (save_db): Licitação da lista sem 'numeroControlePNCP'. Dados: {licitacao_api_item}")
        return None
    
     # Gerar link_portal_pncp
    cnpj_l = licitacao_db_parcial['orgaoEntidadeCnpj']
    ano_l = licitacao_db_parcial['anoCompra']
    seq_l = licitacao_db_parcial['sequencialCompra']
    link_pncp_val = None
    if cnpj_l and ano_l and seq_l is not None:
        try:
            seq_sem_zeros = str(int(str(seq_l)))
            link_pncp_val = f"https://pncp.gov.br/app/editais/{cnpj_l}/{ano_l}/{seq_sem_zeros}"
        except ValueError: link_pncp_val = None
    licitacao_db_parcial['link_portal_pncp'] = link_pncp_val

    # --- Determinar flag_houve_mudanca_real e obter licitacao_id_local_existente ---
    # Esta flag e o ID são importantes para decidir se buscamos itens/arquivos e para o UPSERT.
    licitacao_id_local_final = None
    flag_houve_mudanca_real = False
    
    cursor.execute("SELECT id, dataAtualizacao FROM licitacoes WHERE numeroControlePNCP = ?", (licitacao_db_parcial['numeroControlePNCP'],))
    row_existente = cursor.fetchone()
    api_data_att_str = licitacao_db_parcial.get('dataAtualizacao')
    api_data_att_dt = datetime.strptime(api_data_att_str, '%Y-%m-%d').date() if api_data_att_str else None

    if row_existente:
        licitacao_id_local_final = row_existente['id']
        db_data_att_str = row_existente['dataAtualizacao']
        db_data_att_dt = datetime.strptime(db_data_att_str, '%Y-%m-%d').date() if db_data_att_str else None
        if api_data_att_dt and (not db_data_att_dt or api_data_att_dt > db_data_att_dt):
            flag_houve_mudanca_real = True
    else:
        flag_houve_mudanca_real = True # Nova licitação, considera como mudança

    # --- Buscar Itens (SEMPRE que houver mudança ou for nova, OU se não tiver itens e quisermos popular) ---
    # Para determinar 'situacaoReal' com base nos itens, precisamos deles AGORA.
    # A lógica de 'buscar_sub_detalhes' precisa ser adaptada.
    # Vamos buscar itens se for nova ou atualizada, ou se o banco não tem itens para ela.
    
    itens_da_licitacao_api = [] # Lista de itens buscados da API
    necessita_buscar_itens = False
    if flag_houve_mudanca_real:
        necessita_buscar_itens = True
    elif licitacao_id_local_final: # Se já existe no DB mas não houve mudança na dataAtualizacao
        cursor.execute("SELECT COUNT(id) FROM itens_licitacao WHERE licitacao_id = ?", (licitacao_id_local_final,))
        if cursor.fetchone()[0] == 0:
            necessita_buscar_itens = True
            print(f"INFO (save_db): Licitação {licitacao_db_parcial['numeroControlePNCP']} sem itens no banco. Buscando...")


    if necessita_buscar_itens and licitacao_db_parcial['orgaoEntidadeCnpj'] and licitacao_db_parcial['anoCompra'] and licitacao_db_parcial['sequencialCompra'] is not None:
        print(f"INFO (save_db): Iniciando busca de ITENS para {licitacao_db_parcial['numeroControlePNCP']} (para definir situacaoReal e salvar)")
        # fetch_all_itens_for_licitacao agora SÓ BUSCA e retorna a lista de itens da API
        # O salvamento dos itens será feito DEPOIS de salvar a licitação principal.
        itens_brutos_api = fetch_all_itens_for_licitacao_APENAS_BUSCA(
            licitacao_db_parcial['orgaoEntidadeCnpj'], 
            licitacao_db_parcial['anoCompra'], 
            licitacao_db_parcial['sequencialCompra']
        )
        if itens_brutos_api:
            itens_da_licitacao_api = itens_brutos_api 
            # Guardamos para usar na lógica de situacaoReal e para salvar depois
    
    # --- LÓGICA PARA DEFINIR licitacao_db_parcial['situacaoReal'] ---
    hoje_date = date.today()
    data_encerramento_str = licitacao_db_parcial.get('dataEncerramentoProposta')
    status_compra_api = licitacao_db_parcial.get('situacaoCompraId')
    
    situacao_real_calculada = "Desconhecida" # Default

    status_api_encerram_definitivo = [2, 3] #  Anulada,  Deserta

    if status_compra_api in status_api_encerram_definitivo:
        situacao_real_calculada = "Encerrada"
    elif status_compra_api == 4: # TRATAMENTO EXPLÍCITO PARA SUSPENSA
        situacao_real_calculada = "Suspensa"
    elif licitacao_db_parcial.get('dataAberturaProposta') is None and data_encerramento_str is None:
        # Se NÃO HÁ datas de abertura E encerramento, você considera encerrada.
        # Isso pode ser um problema se a API nem sempre fornecer essas datas para licitações ativas.
        situacao_real_calculada = "Encerrada" # (Considerada encerrada por falta de datas)
    elif status_compra_api == 1: # Apenas se for "Divulgada no PNCP" pela API
        encerra_por_item_ou_julgamento = False
       
        if itens_da_licitacao_api: # VERIFICA SE HÁ ITENS
            status_itens_que_encerram = ["Homologado", "Fracassado", "Deserto", "Anulado/Revogado/Cancelado" ] 
            # ERRO POTENCIAL 1: Acessa [0] sem checar se itens_da_licitacao_api tem elementos. (Corrigido no código acima com 'if itens_da_licitacao_api:')
            # Mas ainda pode ter problemas se a lista for vazia após o 'if'
            
            # Assumindo que 'itens_da_licitacao_api' não é None, mas PODE SER UMA LISTA VAZIA
            if len(itens_da_licitacao_api) > 0:
                primeiro_item_status = itens_da_licitacao_api[0].get('situacaoCompraItemNome')
                if primeiro_item_status: # Verifica se o status do item não é None
                    primeiro_item_status_lower = primeiro_item_status.lower()
                
                    # ERRO POTENCIAL 2: Se 'situacaoCompraItemNome' for qualquer coisa que NÃO esteja em status_itens_que_encerram E NÃO seja 'Em Andamento', cai em "Em Julgamento"
                    if primeiro_item_status_lower in [s.lower() for s in status_itens_que_encerram]: # Comparação case-insensitive
                        situacao_real_calculada = "Encerrada"
                        encerra_por_item_ou_julgamento = True
                    # >>> ESTE É UM PONTO CRÍTICO <<<
                    elif primeiro_item_status_lower and primeiro_item_status_lower != "em andamento": 
                        # Se o status do primeiro item NÃO for "em andamento" e NÃO for um dos que encerram,
                        # ele se torna "Em Julgamento/Propostas Encerradas"
                        situacao_real_calculada = "Em Julgamento/Propostas Encerradas"
                        # status_item_para_julgamento = itens_da_licitacao_api[0].get('situacaoCompraItemNome') # Não usado, pode remover
                        encerra_por_item_ou_julgamento = True
                else: # Se o primeiro item não tem 'situacaoCompraItemNome'
                    # O que fazer aqui? Por enquanto, não define encerra_por_item_ou_julgamento, então a lógica abaixo baseada em datas será usada.
                    pass 
            # else: # Se itens_da_licitacao_api for uma lista vazia
                # Nenhuma lógica de item será aplicada. A lógica de datas abaixo será usada.

        # Se não foi encerrada/julgamento por item (encerra_por_item_ou_julgamento é False)
        if not encerra_por_item_ou_julgamento: 
            if data_encerramento_str:
                try:
                    data_encerramento_datetime_obj = datetime.fromisoformat(data_encerramento_str.replace('Z', '+00:00')) # Lida com 'Z' se presente
                    data_encerramento_date_obj = data_encerramento_datetime_obj.date() 
                    if hoje_date > data_encerramento_date_obj:                    
                        # Se a data de encerramento já passou, vira "Em Julgamento/Propostas Encerradas"
                        situacao_real_calculada = "Em Julgamento/Propostas Encerradas"
                    else:
                        situacao_real_calculada = "A Receber/Recebendo Proposta"
                except ValueError:
                     # Data de encerramento em formato inválido, o que fazer?
                     # Talvez tratar como "A Receber/Recebendo Proposta" ou "Desconhecida" e logar um aviso
                     print(f"AVISO: Formato inválido para dataEncerramentoProposta: {data_encerramento_str} para {licitacao_db_parcial['numeroControlePNCP']}")
                     situacao_real_calculada = "A Receber/Recebendo Proposta" # Ou outra default segura
            else: # Sem data de encerramento, mas ativa pela API e não definida por status de item
                  # E aqui se status_compra_api == 1, será "A Receber/Recebendo Proposta"
                situacao_real_calculada = "A Receber/Recebendo Proposta"
    # else:
        # Se status_compra_api não for 1, 2, 3 ou 4, e tiver datas de abertura/encerramento,
        # vai usar o 'situacao_real_calculada = "Desconhecida"' inicial.
        # Se você espera mais casos, precisa tratar outros status_compra_api.

    licitacao_db_parcial['situacaoReal'] = situacao_real_calculada
    # --- FIM DA LÓGICA situacaoReal ---


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
        link_portal_pncp, justificativaPresencial, situacaoReal 
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
        :link_portal_pncp, :justificativaPresencial, :situacaoReal 
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
        link_portal_pncp = excluded.link_portal_pncp,             
        justificativaPresencial = excluded.justificativaPresencial,
        situacaoReal = excluded.situacaoReal
    WHERE licitacoes.dataAtualizacao < excluded.dataAtualizacao OR licitacoes.dataAtualizacao IS NULL;"""
    
    
    try:
        if flag_houve_mudanca_real: # Só executa UPSERT se for nova ou API tem dados mais novos
            cursor.execute(sql_upsert_licitacao, licitacao_db_parcial)
            if cursor.rowcount > 0:
                if not row_existente: 
                    licitacao_id_local_final = cursor.lastrowid
                # (licitacao_id_local_final já tem valor se row_existente)
                print(f"INFO (SAVE_DB): Licitação {licitacao_db_parcial['numeroControlePNCP']} UPSERTED. ID: {licitacao_id_local_final}. SituacaoReal: {situacao_real_calculada}")
            elif row_existente:
                 print(f"INFO (SAVE_DB): Licitação {licitacao_db_parcial['numeroControlePNCP']} não precisou de update. ID: {licitacao_id_local_final}. SituacaoReal: {situacao_real_calculada}")
        elif row_existente:
             licitacao_id_local_final = row_existente['id'] # Garante que temos o ID
             print(f"INFO (SAVE_DB): Licitação {licitacao_db_parcial['numeroControlePNCP']} já atualizada. ID: {licitacao_id_local_final}. SituacaoReal (do DB): {row_existente['situacaoReal'] if 'situacaoReal' in row_existente.keys() else 'N/A'}") # Mostra o do DB
        
        if not licitacao_id_local_final and flag_houve_mudanca_real:
            cursor.execute("SELECT id FROM licitacoes WHERE numeroControlePNCP = ?", (licitacao_db_parcial['numeroControlePNCP'],))
            id_row = cursor.fetchone()
            if id_row: licitacao_id_local_final = id_row['id']
            
    except sqlite3.Error as e:
        print(f"ERRO (SAVE_DB): Ao salvar principal {licitacao_db_parcial.get('numeroControlePNCP')}: {e}")
        return None
        
    if not licitacao_id_local_final:
        print(f"AVISO CRÍTICO (SAVE_DB): Falha ao obter ID local para {licitacao_db_parcial.get('numeroControlePNCP')}")
        return None 

    # --- SALVAR ITENS E ARQUIVOS (usando licitacao_id_local_final e os itens_da_licitacao_api) ---
    # Somente se houve mudança real ou se os itens não existiam antes (essa lógica de "não existiam antes" foi feita para buscar_sub_detalhes)
    # A flag_houve_mudanca_real já cobre o caso de ser novo ou atualizado.
    # Se não houve mudança e os itens já existem, podemos pular o re-salvamento deles se não mudaram.
    # Mas para garantir consistência com 'situacaoReal', talvez seja bom sempre processar itens se 'flag_houve_mudanca_real'
    # ou se 'necessita_buscar_itens' era true.
    
    if necessita_buscar_itens and itens_da_licitacao_api: # Se buscamos e obtivemos itens
        salvar_itens_no_banco(conn, licitacao_id_local_final, itens_da_licitacao_api) # Nova função para apenas salvar

    # Lógica para arquivos (similar: buscar se necessário e depois salvar)
    # ... fetch_all_arquivos_for_licitacao_APENAS_BUSCA e salvar_arquivos_no_banco ...
    # Por agora, vamos manter a chamada original, mas idealmente ela também seria dividida.
    if flag_houve_mudanca_real or necessita_buscar_itens: # Condição simplificada para buscar arquivos
        if licitacao_db_parcial['orgaoEntidadeCnpj'] and licitacao_db_parcial['anoCompra'] and licitacao_db_parcial['sequencialCompra'] is not None:
            fetch_all_arquivos_for_licitacao(conn, licitacao_id_local_final, 
                                             licitacao_db_parcial['orgaoEntidadeCnpj'], 
                                             licitacao_db_parcial['anoCompra'], 
                                             licitacao_db_parcial['sequencialCompra'])
    
    return licitacao_id_local_final

# Nova função para buscar itens sem salvar (para desacoplar)
def fetch_all_itens_for_licitacao_APENAS_BUSCA(cnpj_orgao, ano_compra, sequencial_compra):
    todos_itens_api = []
    pagina_atual_itens = 1
    # ... (lógica de loop e chamada a fetch_itens_from_api como em fetch_all_itens_for_licitacao) ...
    # MAS SEM A PARTE DE SALVAR NO BANCO AQUI DENTRO
    while True:
        itens_pagina = fetch_itens_from_api(cnpj_orgao, ano_compra, sequencial_compra, pagina_atual_itens, TAMANHO_PAGINA_SYNC)
        if itens_pagina is None: return None 
        if not itens_pagina: break
        todos_itens_api.extend(itens_pagina)
        if len(itens_pagina) < TAMANHO_PAGINA_SYNC: break
        pagina_atual_itens += 1
        time.sleep(0.2)
    print(f"ITENS (Busca): Total de {len(todos_itens_api)} itens encontrados para {cnpj_orgao}/{ano_compra}/{sequencial_compra}.")
    return todos_itens_api

# Nova função para salvar itens no banco (separada da busca)
def salvar_itens_no_banco(conn, licitacao_id_local, lista_itens_api):
    if not lista_itens_api:
        print(f"INFO (ITENS_SAVE): Sem itens para salvar para licitação ID {licitacao_id_local}.")
        return
    
    cursor = conn.cursor()
    try:
        # Deletar itens antigos ANTES do loop, uma única vez
        print(f"DEBUG (ITENS_SAVE): Deletando itens antigos para licitação ID {licitacao_id_local}")
        cursor.execute("DELETE FROM itens_licitacao WHERE licitacao_id = ?", (licitacao_id_local,))
    except sqlite3.Error as e:
        print(f"ERRO (ITENS_SAVE): Ao deletar itens antigos (lic_id {licitacao_id_local}): {e}")
        # Você pode querer retornar ou levantar o erro aqui, dependendo da sua estratégia
        return 

    # Defina a string SQL uma vez, antes do loop
    sql_insert_item = """
    INSERT INTO itens_licitacao (
        licitacao_id, numeroItem, descricao, materialOuServicoNome, quantidade,
        unidadeMedida, valorUnitarioEstimado, valorTotal, orcamentoSigiloso,
        itemCategoriaNome, categoriaItemCatalogo, criterioJulgamentoNome, 
        situacaoCompraItemNome, tipoBeneficioNome, incentivoProdutivoBasico, dataInclusao,
        dataAtualizacao, temResultado, informacaoComplementar
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""" # 19 placeholders
    
    itens_salvos_count = 0
    itens_com_erro_count = 0

    for item_api in lista_itens_api: 
        item_db_tuple = (      
            licitacao_id_local,
            item_api.get('numeroItem'),
            item_api.get('descricao'),
            item_api.get('materialOuServicoNome'),
            item_api.get('quantidade'),
            item_api.get('unidadeMedida'),
            item_api.get('valorUnitarioEstimado'),
            item_api.get('valorTotal'),
            bool(item_api.get('orcamentoSigiloso')), 
            item_api.get('itemCategoriaNome'),
            item_api.get('categoriaItemCatalogo'),
            item_api.get('criterioJulgamentoNome'),
            item_api.get('situacaoCompraItemNome'),
            item_api.get('tipoBeneficioNome'),
            bool(item_api.get('incentivoProdutivoBasico')), 
            item_api.get('dataInclusao', '').split('T')[0] if item_api.get('dataInclusao') else None,
            item_api.get('dataAtualizacao', '').split('T')[0] if item_api.get('dataAtualizacao') else None,
            bool(item_api.get('temResultado')), 
            item_api.get('informacaoComplementar')
        )
        try:
            # Se precisar do debug da tupla, coloque-o AQUI:
            # print(f"DEBUG ITENS_SAVE: Tentando inserir tupla: {item_db_tuple}")
            
            cursor.execute(sql_insert_item, item_db_tuple)
            
            if cursor.rowcount > 0: 
                itens_salvos_count += 1
            else:
                print(f"AVISO (ITENS_SAVE): Insert do item {item_api.get('numeroItem')} (lic_id {licitacao_id_local}) não afetou linhas. Dados: {item_db_tuple}")
        except sqlite3.Error as e:
            itens_com_erro_count += 1
            print(f"ERRO (ITENS_SAVE): Ao salvar item {item_api.get('numeroItem')} da licitação ID {licitacao_id_local}: {e} - Dados: {item_db_tuple}")

    print(f"INFO (ITENS_SAVE): Para licitação ID {licitacao_id_local}: {itens_salvos_count} itens salvos, {itens_com_erro_count} itens com erro.")

# (Similarmente, você pode querer dividir fetch_all_arquivos_for_licitacao em busca e salvamento)




    
def sync_licitacoes_ultima_janela_anual():
    conn = get_db_connection()
    if not conn: return

    agora = datetime.now()
    data_fim_periodo_dt = agora
    data_inicio_periodo_dt = agora - timedelta(days=DIAS_JANELA_SINCRONIZACAO) # Últimos 12 meses

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
    print("Iniciando script de sincronização (janela de {DIAS_JANELA_SINCRONIZACAO} dias de atualizações)...")
    sync_licitacoes_ultima_janela_anual()
    print("Script de sincronização finalizado.")