# backend/sync_api.py

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

API_BASE_URL = "https://pncp.gov.br/api/consulta" # (URL base da API do PNCP)
ENDPOINT_PROPOSTAS_ABERTAS = "/v1/contratacoes/proposta" # (Endpoint específico)

# Data atual para o parâmetro dataFinal (formato YYYYMMDD)
hoje = date.today()
data_futura = hoje + timedelta(days=6*30) # Aproximação de 6 meses (180 dias)
DATA_ATUAL_PARAM = data_futura.strftime('%Y%m%d')
#print(f"INFO: Usando dataFinal calculada como: {DATA_ATUAL_PARAM}")

TAMANHO_PAGINA = 50 # (Tamanho da página, conforme definido)
LIMITE_PAGINAS_TESTE = 2 # (Limite para testes iniciais, conforme sua sugestão). Mude para None para buscar todas.

# Códigos de modalidade de contratação que queremos buscar (exemplo: Pregão Eletrônico = 6)
# Você pode adicionar outros códigos aqui se precisar de mais modalidades.
# Por enquanto, vamos focar em uma para simplificar.
# Se quiser todas as modalidades ativas, a API não exige 'codigoModalidadeContratacao'
# se 'dataFinal' estiver presente e 'situacaoCompraId=1' for implícito pelo endpoint.
# Vamos deixar flexível para adicionar, mas começar buscando sem especificar modalidade,
# para pegar todas as ativas. Se a API exigir, adaptamos.
# A documentação diz que codigoModalidadeContratacao é obrigatório.
# Vamos usar Pregão (6) e Concorrência (5) como exemplo para começar.
# Se quiser todas, teria que fazer uma chamada por modalidade ou verificar se a API aceita sem.
# De acordo com a documentação do serviço 6.4, `codigoModalidadeContratacao` é obrigatório.
# Vamos focar no Pregão Eletrônico (código 6) por agora.
CODIGOS_MODALIDADE = [6] # (Ex: 6 para Pregão Eletrônico)


# --- Funções Auxiliares ---
def format_date_to_iso(date_str):
    """Converte data do formato YYYYMMDD para YYYY-MM-DD ISO."""
    if not date_str or len(date_str) != 8:
        return None # (Retorna None se a string de data for inválida ou vazia)
    try:
        # (Cria um objeto datetime a partir da string e depois formata para ISO)
        return datetime.strptime(date_str, '%Y%m%d').strftime('%Y-%m-%d')
    except ValueError:
        return None # (Retorna None se a conversão falhar)

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

def save_licitacao_to_db(conn, licitacao_api):
    """Salva ou atualiza uma licitação e seus itens no banco de dados."""
    cursor = conn.cursor()
    situacao_id_recebido = licitacao_api.get('situacaoCompraId') # Acesso direto.debug
    #print(f"DEBUG save_licitacao_to_db: numeroControlePNCP: {licitacao_api.get('numeroControlePNCP')}, situacaoCompraId recebido: {situacao_id_recebido}, Tipo: {type(situacao_id_recebido)}") ##Debug 
    
    # Mapeamento e transformação dos dados da API para os campos do banco
    # Adicionando verificações para campos que podem não existir ou serem nulos
    licitacao_db = {
        'numeroControlePNCP': licitacao_api.get('numeroControlePNCP'),
        'numeroCompra': licitacao_api.get('numeroCompra'),
        'anoCompra': licitacao_api.get('anoCompra'),
        'processo': licitacao_api.get('processo'), #ate aqui ok!
        'tipolnstrumentoConvocatorioId': licitacao_api.get('tipoInstrumentoConvocatorioCodigo'), # Campo é tipoInstrumentoConvocatorioCodigo
        'tipolnstrumentoConvocatorioNome': licitacao_api.get('tipoInstrumentoConvocatorioNome'),
        'modalidadeId': licitacao_api.get('modalidadeId'),
        'modalidadeNome': licitacao_api.get('modalidadeNome'),
        'modoDisputaId': licitacao_api.get('modoDisputaId'),
        'modoDisputaNome': licitacao_api.get('modoDisputaNome'),
        'situacaoCompraId': licitacao_api.get('situacaoCompraId'),  # Acesso direto
        'situacaoCompraNome': licitacao_api.get('situacaoCompraNome'), 
        'objetoCompra': licitacao_api.get('objetoCompra'),
        'informacaoComplementar': licitacao_api.get('informacaoComplementar'),
        'srp': licitacao_api.get('srp'),
        'amparoLegalCodigo': licitacao_api.get('amparoLegal', {}).get('codigo'),
        'amparoLegalNome': licitacao_api.get('amparoLegal', {}).get('nome'),
        'amparoLegalDescricao': licitacao_api.get('amparoLegal', {}).get('descricao'),
        'valorTotalEstimado': licitacao_api.get('valorTotalEstimado'),
        'valorTotalHomologado': licitacao_api.get('valorTotalHomologado'), # (Pode ser nulo para licitações não homologadas)
        'dataAberturaProposta': licitacao_api.get('dataAberturaProposta', '').split('T')[0] if licitacao_api.get('dataAberturaProposta') else None, #Modifiquei para pegar a parte ate o "T"
        'dataEncerramentoProposta': licitacao_api.get('dataEncerramentoProposta', '').split('T')[0] if licitacao_api.get('dataEncerramentoProposta') else None,
        'dataPublicacaoPncp': licitacao_api.get('dataPublicacaoPncp', '').split('T')[0] if licitacao_api.get('dataPublicacaoPncp') else None,
        'dataInclusao': licitacao_api.get('dataInclusao', '').split('T')[0] if licitacao_api.get('dataInclusao') else None,
        'dataAtualizacao': licitacao_api.get('dataAtualizacao', '').split('T')[0] if licitacao_api.get('dataAtualizacao') else None,
        'sequencialCompra': licitacao_api.get('sequencialCompra'),
            #Daqui em diante são todos objetos aninhados
        'orgaoEntidadeCnpj': licitacao_api.get('orgaoEntidade', {}).get('cnpj'),
        'orgaoEntidadeRazaoSocial': licitacao_api.get('orgaoEntidade', {}).get('razaoSocial'),
        'orgaoEntidadePoderId': licitacao_api.get('orgaoEntidade', {}).get('poderId'),
        'orgaoEntidadeEsferaId': licitacao_api.get('orgaoEntidade', {}).get('esferaId'),
        'unidadeOrgaoCodigo': licitacao_api.get('unidadeOrgao', {}).get('codigoUnidade'),
        'unidadeOrgaoNome': licitacao_api.get('unidadeOrgao', {}).get('nomeUnidade'), 
        'unidadeOrgaoCodigoIbge': licitacao_api.get('unidadeOrgao', {}).get('codigoIbge'),
        'unidadeOrgaoMunicipioNome': licitacao_api.get('unidadeOrgao', {}).get('municipioNome'),
        'unidadeOrgaoUfSigla': licitacao_api.get('unidadeOrgao', {}).get('ufSigla'),
        'unidadeOrgaoUfNome': licitacao_api.get('unidadeOrgao', {}).get('ufNome'),

        'usuarioNome': licitacao_api.get('usuarioNome'),
        'linkSistemaOrigem': licitacao_api.get('linkSistemaOrigem'),
        'justificativaPresencial': licitacao_api.get('justificativaPresencial')
    }

    # Validação básica: numeroControlePNCP é obrigatório
    if not licitacao_db['numeroControlePNCP']:
        print(f"AVISO: Licitação sem 'numeroControlePNCP'. Dados: {licitacao_api}")
        return None # (Não podemos processar sem a chave única)

    # Filtrar para salvar apenas licitações ativas (situacaoCompraId = 1)
    # O endpoint já deve trazer apenas essas, mas é uma boa dupla checagem.
    if licitacao_db['situacaoCompraId'] != 1:
        print(f"INFO (dentro de save_licitacao_to_db): Licitação {licitacao_db['numeroControlePNCP']} não está ativa (situação: {licitacao_db['situacaoCompraId']}). Pulando.")
        return None


    # Lógica UPSERT para a tabela 'licitacoes'
    # Tenta inserir. Se houver conflito na 'numeroControlePNCP', atualiza SE a dataAtualizacao da API for mais nova.
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
        unidadeOrgaoUfNome, usuarioNome, linkSistemaOrigem, justificativaPresencial
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
        :unidadeOrgaoUfNome, :usuarioNome, :linkSistemaOrigem, :justificativaPresencial
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
        dataAtualizacao = excluded.dataAtualizacao, -- (Atualiza a data de atualização)
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
        justificativaPresencial = excluded.justificativaPresencial
    WHERE licitacoes.dataAtualizacao < excluded.dataAtualizacao OR licitacoes.dataAtualizacao IS NULL; 
    -- (A cláusula WHERE na atualização é crucial: só atualiza se a nova data for mais recente
    --  ou se a data no banco for NULL. SQLite < 3.24 não suporta WHERE em DO UPDATE.
    --  Para SQLite >= 3.24, isso funciona. Para versões mais antigas, uma lógica de SELECT e depois INSERT/UPDATE seria necessária.
    --  Vamos assumir uma versão recente do SQLite. Se der erro, teremos que ajustar.)
    --  Se o SQLite for < 3.33.0, o `excluded.dataAtualizacao` não pode ser usado na cláusula WHERE.
    --  Uma alternativa é buscar o registro, comparar as datas no Python, e então decidir se faz UPDATE.
    --  Para simplificar e usar o UPSERT mais moderno, vamos com a sintaxe acima.
    --  Se for um problema, precisaremos checar a data de atualização ANTES de tentar o UPSERT.
    """
    
    licitacao_id = None
    try:
        # Antes do UPSERT, vamos verificar a data de atualização se o registro já existe
        # Esta é uma forma de contornar a limitação do WHERE em ON CONFLICT UPDATE para versões mais antigas do SQLite
        # ou para garantir a lógica de atualização.
        cursor.execute("SELECT id, dataAtualizacao FROM licitacoes WHERE numeroControlePNCP = ?", (licitacao_db['numeroControlePNCP'],))
        row = cursor.fetchone()

        if row: # Se a licitação já existe no banco
            id_existente, data_atualizacao_db_str = row
            data_atualizacao_db = datetime.strptime(data_atualizacao_db_str, '%Y-%m-%d') if data_atualizacao_db_str else None
            data_atualizacao_api = datetime.strptime(licitacao_db['dataAtualizacao'], '%Y-%m-%d') if licitacao_db['dataAtualizacao'] else None

            if data_atualizacao_api and (not data_atualizacao_db or data_atualizacao_api > data_atualizacao_db):
                # API tem dados mais recentes, então prossegue com o UPDATE (parte do UPSERT)
                pass # Deixa o UPSERT fazer o trabalho
            else:
                # Dados da API não são mais recentes, ou não há data de atualização na API. Não atualiza.
                print(f"Licitação {licitacao_db['numeroControlePNCP']} já existe e está atualizada ou API não tem data de atualização mais nova. Pulando atualização.")
                # Se não vamos atualizar, precisamos do ID para os itens.
                licitacao_id = id_existente
                # E talvez não precisemos deletar os itens antigos, a menos que a lógica de itens mude.
                # Por ora, vamos assumir que se a licitação principal não muda, os itens também não.                                ######VER ISSO DEPOIS######
                # Para uma atualização completa, deletaríamos itens antigos e inseriríamos os novos mesmo assim.    
                # Vamos optar por deletar e recriar itens para garantir consistência se a licitação for atualizada.
                # Se a licitação NÃO for atualizada, não mexemos nos itens.
                return id_existente # Retorna o ID existente sem atualizar os itens

        # Executa o UPSERT
        cursor.execute(sql_upsert_licitacao, licitacao_db)
        
        # Se uma nova linha foi inserida ou uma existente foi atualizada, o lastrowid pode ser útil.
        # Se foi INSERT, lastrowid é o novo ID. Se foi UPDATE, pode ser 0 ou o ID da linha atualizada, dependendo da versão do SQLite e da query.
        # É mais seguro pegar o ID com um SELECT após o UPSERT se o UPSERT pode ter atualizado.
        if cursor.rowcount > 0: # Verifica se alguma linha foi afetada (inserida OU atualizada)
            # Se foi inserção, lastrowid é o ID. Se atualização, precisamos buscar.
            # Como numeroControlePNCP é UNIQUE, podemos buscar por ele.
            cursor.execute("SELECT id FROM licitacoes WHERE numeroControlePNCP = ?", (licitacao_db['numeroControlePNCP'],))
            licitacao_id_row = cursor.fetchone()
            if licitacao_id_row:
                licitacao_id = licitacao_id_row[0]
            print(f"Licitação {licitacao_db['numeroControlePNCP']} salva/atualizada com ID {licitacao_id}.")
        else:
            # Isso pode acontecer se o WHERE do ON CONFLICT...DO UPDATE não foi satisfeito (dados não eram mais novos)
            # E a licitação já existia. Neste caso, o ID já foi pego pelo `row` acima.
            if row: # se existia e não atualizou
                licitacao_id = row[0]
                print(f"Licitação {licitacao_db['numeroControlePNCP']} não precisou de atualização. ID existente: {licitacao_id}")
            else: # não existia e não inseriu? Estranho.
                print(f"AVISO: Licitação {licitacao_db['numeroControlePNCP']} não foi inserida nem atualizada, e não existia. Verificar lógica.")
                return None


    except sqlite3.Error as e:
        print(f"Erro ao salvar licitação {licitacao_db.get('numeroControlePNCP', 'N/A')} no banco: {e}")
        print(f"Dados da licitação: {licitacao_db}")
        return None # (Retorna None em caso de erro no DB)

    # Salvar itens da licitação (se houver licitacao_id e itens)
    if licitacao_id and 'itens' in licitacao_api and licitacao_api['itens']:
        # Primeiro, remove itens antigos para esta licitação para evitar duplicatas ou itens desatualizados
        # Isso é importante se a lista de itens puder mudar em uma atualização
        try:
            cursor.execute("DELETE FROM itens_licitacao WHERE licitacao_id = ?", (licitacao_id,))
        except sqlite3.Error as e:
            print(f"Erro ao deletar itens antigos da licitação ID {licitacao_id}: {e}")
            # Decide se continua ou para. Por ora, vamos tentar inserir os novos.
        
        sql_insert_item = """
        INSERT INTO itens_licitacao (
            licitacao_id, numeroItem, categoriaItemNome, classificacaoCatalogoId,
            nomeClassificacaoCatalogo, quantidadeEstimada, valorUnitario, valorTotal
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        for item_api in licitacao_api['itens']:
            item_db = (
                licitacao_id,
                item_api.get('numeroItem'),
                item_api.get('categoriaItem', {}).get('nome'), # (Exemplo, ajustar se a estrutura for diferente)
                item_api.get('classificacaoCatalogo', {}).get('id'),
                item_api.get('classificacaoCatalogo', {}).get('nome'),
                item_api.get('quantidadeEstimada'),
                item_api.get('valorUnitarioEstimado'), # (Campo da API é 'valorUnitarioEstimado')
                item_api.get('valorTotal')
            )
            try:
                cursor.execute(sql_insert_item, item_db)
            except sqlite3.Error as e:
                print(f"Erro ao salvar item {item_api.get('numeroItem')} da licitação ID {licitacao_id}: {e}")
                print(f"Dados do item: {item_db}")
        print(f"Itens da licitação {licitacao_db['numeroControlePNCP']} salvos.")

    return licitacao_id # (Retorna o ID da licitação salva/atualizada)


def sync_all_active_licitacoes():
    """Busca todas as licitações ativas de todas as modalidades configuradas e de todas as páginas."""
    conn = get_db_connection()
    if not conn:
        return

    total_licitacoes_processadas = 0
    total_erros_api = 0

    for codigo_modalidade in CODIGOS_MODALIDADE:
        print(f"\n--- Iniciando sincronização para modalidade: {codigo_modalidade} ---")
        pagina_atual = 1
        paginas_processadas_modalidade = 0

        while True:
            # Aplicar o limite de páginas para teste
            if LIMITE_PAGINAS_TESTE is not None and paginas_processadas_modalidade >= LIMITE_PAGINAS_TESTE:
                print(f"Limite de {LIMITE_PAGINAS_TESTE} páginas de teste atingido para modalidade {codigo_modalidade}. Parando.")
                break
            
            print(f"Buscando página {pagina_atual} para modalidade {codigo_modalidade}...")
            licitacoes_data, paginas_restantes = fetch_licitacoes_from_api(codigo_modalidade, pagina_atual)

            if licitacoes_data is None:
                # Se fetch_licitacoes_from_api retorna None para os dados, pode ser um erro de API ou 204 No Content.
                # Se for 204, paginas_restantes também será 0, o loop vai parar.
                # Se for erro de API, paginas_restantes será 0 e o loop também para.
                total_erros_api += 1
                if total_erros_api > 5 : # (Para não floodar com erros, se a API estiver fora)
                    print("Muitos erros de API. Abortando sincronização.")
                    break 
                # Se for um erro, podemos tentar a próxima página ou parar. Por ora, o loop parará se paginas_restantes for 0.
                # Se fetch_licitacoes_from_api já tratou o erro e imprimiu, podemos só continuar para a próxima iteração do while ou break.
                # Dado que fetch_licitacoes_from_api retorna 0 paginas_restantes em erro, o loop vai parar.
                # Se quiséssemos re-tentar ou pular para a próxima página, a lógica aqui seria diferente.
                # Por hora, se há erro, paramos para essa modalidade.
                print(f"Não foi possível obter dados da página {pagina_atual} para modalidade {codigo_modalidade}.")
                break # Sai do loop while para esta modalidade

            if not licitacoes_data: # Lista vazia, mas não necessariamente um erro
                print(f"Nenhuma licitação encontrada na página {pagina_atual} para modalidade {codigo_modalidade}.")
                # Isso pode acontecer se a página estiver vazia mas ainda houver páginas restantes (improvável com esta API)
                # Ou se for a última página e ela veio vazia.
                # Se paginas_restantes for 0, o loop externo cuidará disso.
            else:
                for licitacao_api in licitacoes_data:
                    situacao_id_api = licitacao_api.get('situacaoCompraId') # Pega o valor, acesso direto
                    #print(f"DEBUG: Licitação {licitacao_api.get('numeroControlePNCP')}, situacaoCompraId da API: {situacao_id_api}, Tipo: {type(situacao_id_api)}") # DEBUG para entender o erro da chamada

                    if situacao_id_api == 1: # A condição original
                        save_licitacao_to_db(conn, licitacao_api)
                        total_licitacoes_processadas += 1
                    else:
                        print(f"INFO: Licitação {licitacao_api.get('numeroControlePNCP')} da API não é 'Divulgada' (ID 1) porque situacaoCompraId é '{situacao_id_api}'. Pulando.") # Mensagem de INFO mais detalhada
            
            conn.commit() # (Salva as alterações no banco após processar cada página)
            print(f"Página {pagina_atual} processada. {paginas_restantes} páginas restantes para esta modalidade.")
            paginas_processadas_modalidade += 1
            
            if paginas_restantes == 0:
                print(f"Todas as páginas processadas para a modalidade {codigo_modalidade}.")
                break # (Sai do loop while se não houver mais páginas)
            
            pagina_atual += 1
            # Adicionar um pequeno delay para não sobrecarregar a API
            time.sleep(0.5) # (Espera 0.5 segundos)
        
        if total_erros_api > 5 : break # Sai do loop de modalidades também

    conn.close()
    print(f"\n--- Sincronização concluída ---")
    print(f"Total de licitações (tentativas de salvar/atualizar): {total_licitacoes_processadas}")

# --- Ponto de Entrada do Script ---
if __name__ == '__main__':
    print("Iniciando script de sincronização com a API do PNCP...")
    sync_all_active_licitacoes()
    print("Script de sincronização finalizado.")