# python app.py

from flask import Flask, jsonify, request
import sqlite3
import os

# --- Configurações ---
app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'database.db')

# --- Funções Auxiliares para o Banco de Dados ---
def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# --- Endpoints ---
@app.route('/')
def index():
    return "Bem-vindo à API do RADAR PNCP!"

@app.route('/licitacoes', methods=['GET'])
def get_licitacoes():
    filtros = {
        'ufs': request.args.getlist('uf'),
        'modalidadesId': request.args.getlist('modalidadeId', type=int),
        'statusId': request.args.get('status', default=None, type=int),
        'dataPubInicio': request.args.get('dataPubInicio', default=None, type=str),
        'dataPubFim': request.args.get('dataPubFim', default=None, type=str),
        'valorMin': request.args.get('valorMin', default=None, type=float),
        'valorMax': request.args.get('valorMax', default=None, type=float),
        'municipiosNome': request.args.getlist('municipioNome'),
        'dataAtualizacaoInicio': request.args.get('dataAtualizacaoInicio', default=None, type=str),
        'dataAtualizacaoFim': request.args.get('dataAtualizacaoFim', default=None, type=str),
        'palavrasChave': request.args.getlist('palavraChave'),
        'excluirPalavras': request.args.getlist('excluirPalavra'),
        'anoCompra': request.args.get('anoCompra', type=int),
        'cnpjOrgao': request.args.get('cnpjOrgao'),
        'statusRadar': request.args.get('statusRadar', default=None, type=str)
    }

    pagina = request.args.get('pagina', default=1, type=int)
    if pagina < 1: # Adiciona validação para página
        pagina = 1
    por_pagina = request.args.get('porPagina', default=20, type=int)
    if por_pagina < 1: # Adiciona validação para por_pagina
        por_pagina = 20
    elif por_pagina > 100: # Limite opcional para por_pagina
        por_pagina = 100


    offset = (pagina - 1) * por_pagina

    orderBy_param = request.args.get('orderBy', default='dataPublicacaoPncp', type=str)
    orderDir_param = request.args.get('orderDir', default='DESC', type=str).upper()

    #Validação para evitar injeção de SQL
    campos_validos_ordenacao = [
        'dataPublicacaoPncp', 'dataAtualizacao', 'valorTotalEstimado',
        'dataAberturaProposta', 'dataEncerramentoProposta', 'modalidadeNome',
        'orgaoEntidadeRazaoSocial', 'unidadeOrgaoMunicipioNome',
        'situacaoReal'
    ]

    # >>> INÍCIO DA MODIFICAÇÃO PARA ERRO 400 <<<
    if orderBy_param not in campos_validos_ordenacao:
        return jsonify({
            "erro": "Parâmetro de ordenação inválido",
            "detalhes": f"O valor '{orderBy_param}' para 'orderBy' não é válido. Campos válidos: {', '.join(campos_validos_ordenacao)}."
        }), 400

    if orderDir_param not in ['ASC', 'DESC']:
        return jsonify({
            "erro": "Parâmetro de direção de ordenação inválido",
            "detalhes": f"O valor '{orderDir_param}' para 'orderDir' não é válido. Use 'ASC' ou 'DESC'."
        }), 400
    # >>> FIM DA MODIFICAÇÃO PARA ERRO 400 <<<

    condicoes_db = []
    parametros_db = []

    if filtros['statusRadar']:
        condicoes_db.append("situacaoReal = ?")
        parametros_db.append(filtros['statusRadar'])
    elif filtros['statusId'] is not None:
        condicoes_db.append("situacaoCompraId = ?") #LEMBRAR QUE ESTÁ POR ID
        parametros_db.append(filtros['statusId'])

    if filtros['ufs']:
        placeholders = ', '.join(['?'] * len(filtros['ufs']))
        condicoes_db.append(f"unidadeOrgaoUfSigla IN ({placeholders})")
        parametros_db.extend([uf.upper() for uf in filtros['ufs']])

    if filtros['modalidadesId']:
        placeholders = ', '.join(['?'] * len(filtros['modalidadesId']))
        condicoes_db.append(f"modalidadeId IN ({placeholders})")
        parametros_db.extend(filtros['modalidadesId'])

    if filtros['excluirPalavras']:
        campos_texto_busca = [
            "objetoCompra", "orgaoEntidadeRazaoSocial", "unidadeOrgaoNome",
            "numeroControlePNCP", "unidadeOrgaoMunicipioNome", "unidadeOrgaoUfNome",
            "CAST(unidadeOrgaoCodigoIbge AS TEXT)", "orgaoEntidadeCnpj"
        ]
        for palavra_excluir in filtros['excluirPalavras']:
            termo_excluir = f"%{palavra_excluir}%"
            condicoes_palavra_excluir_and = []
            for campo in campos_texto_busca:
                condicoes_palavra_excluir_and.append(f"COALESCE({campo}, '') NOT LIKE ?")
                parametros_db.append(termo_excluir)
            if condicoes_palavra_excluir_and:
                condicoes_db.append(f"({' AND '.join(condicoes_palavra_excluir_and)})")

    if filtros['palavrasChave']:
        campos_texto_busca = [
            "objetoCompra", "orgaoEntidadeRazaoSocial", "unidadeOrgaoNome",
            "numeroControlePNCP", "unidadeOrgaoMunicipioNome", "unidadeOrgaoUfNome",
            "CAST(unidadeOrgaoCodigoIbge AS TEXT)", "orgaoEntidadeCnpj"
        ]
        sub_condicoes_palavras_or_geral = []
        for palavra_chave in filtros['palavrasChave']:
            termo_like = f"%{palavra_chave}%"
            condicoes_campos_or_para_palavra = []
            for campo in campos_texto_busca:
                condicoes_campos_or_para_palavra.append(f"COALESCE({campo}, '') LIKE ?")
                parametros_db.append(termo_like)
            if condicoes_campos_or_para_palavra:
                sub_condicoes_palavras_or_geral.append(f"({' OR '.join(condicoes_campos_or_para_palavra)})")
        if sub_condicoes_palavras_or_geral:
            condicoes_db.append(f"({' OR '.join(sub_condicoes_palavras_or_geral)})")

    if filtros['dataPubInicio']:
        condicoes_db.append("dataPublicacaoPncp >= ?")
        parametros_db.append(filtros['dataPubInicio'])
    if filtros['dataPubFim']:
        condicoes_db.append("dataPublicacaoPncp <= ?")
        parametros_db.append(filtros['dataPubFim'])

    if filtros['valorMin'] is not None:
        condicoes_db.append("valorTotalEstimado >= ?")
        parametros_db.append(filtros['valorMin'])
    if filtros['valorMax'] is not None:
        condicoes_db.append("valorTotalEstimado <= ?")
        parametros_db.append(filtros['valorMax'])

    if filtros['dataAtualizacaoInicio']:
        condicoes_db.append("dataAtualizacao >= ?")
        parametros_db.append(filtros['dataAtualizacaoInicio'])
    if filtros['dataAtualizacaoFim']:
        condicoes_db.append("dataAtualizacao <= ?")
        parametros_db.append(filtros['dataAtualizacaoFim'])

    if filtros['anoCompra'] is not None:
        condicoes_db.append("anoCompra = ?")
        parametros_db.append(filtros['anoCompra'])

    if filtros['cnpjOrgao']:
        condicoes_db.append("orgaoEntidadeCnpj = ?")
        parametros_db.append(filtros['cnpjOrgao'])

    if filtros['municipiosNome']:
        sub_condicoes_municipio = []
        for nome_mun in filtros['municipiosNome']:
            termo_mun = f"%{nome_mun.upper()}%"
            sub_condicoes_municipio.append("UPPER(unidadeOrgaoMunicipioNome) LIKE ?")
            parametros_db.append(termo_mun)
        if sub_condicoes_municipio:
            condicoes_db.append(f"({ ' OR '.join(sub_condicoes_municipio) })")

    query_select_dados = "SELECT * FROM licitacoes"
    query_select_contagem = "SELECT COUNT(id) FROM licitacoes"
    query_where = ""
    if condicoes_db:
        query_where = " WHERE " + " AND ".join(condicoes_db)

    query_order_limit_offset_dados = f" ORDER BY {orderBy_param} {orderDir_param} LIMIT ? OFFSET ?"

    sql_query_dados_final = query_select_dados + query_where + query_order_limit_offset_dados
    parametros_dados_sql_final = parametros_db + [por_pagina, offset]

    sql_query_contagem_final = query_select_contagem + query_where

    conn = get_db_connection()
    cursor = conn.cursor()
    licitacoes_lista = []
    total_registros = 0
    try:
        cursor.execute(sql_query_dados_final, parametros_dados_sql_final)
        licitacoes_rows = cursor.fetchall()
        licitacoes_lista = [dict(row) for row in licitacoes_rows]

        cursor.execute(sql_query_contagem_final, parametros_db)
        total_registros_fetch = cursor.fetchone()
        if total_registros_fetch:
            total_registros = total_registros_fetch[0]

    except sqlite3.Error as e:
        print(f"Erro ao buscar/contar no banco local: {e}")
        if conn: conn.close()
        return jsonify({"erro": "Erro interno ao processar sua busca.", "detalhes": str(e)}), 500
    finally:
        if conn: conn.close()

    total_paginas_final = (total_registros + por_pagina - 1) // por_pagina if por_pagina > 0 and total_registros > 0 else 0
    if total_registros == 0: total_paginas_final = 0

    return jsonify({
        "pagina_atual": pagina,
        "por_pagina": por_pagina,
        "total_registros": total_registros,
        "total_paginas": total_paginas_final,
        "origem_dados": "banco_local_janela_anual",
        "licitacoes": licitacoes_lista
    })
    


@app.route('/licitacao/<path:numero_controle_pncp>', methods=['GET'])
def get_detalhe_licitacao(numero_controle_pncp):
    conn = get_db_connection()
    cursor = conn.cursor()
    query_licitacao_principal = "SELECT * FROM licitacoes WHERE numeroControlePNCP = ?" # situacaoReal está aqui
    cursor.execute(query_licitacao_principal, (numero_controle_pncp,))
    licitacao_principal_row = cursor.fetchone()

    if not licitacao_principal_row:
        conn.close()
        return jsonify({"erro": "Licitação não encontrada", "numeroControlePNCP": numero_controle_pncp}), 404

    licitacao_principal_dict = dict(licitacao_principal_row)
    licitacao_id_local = licitacao_principal_dict['id']

    query_itens = "SELECT * FROM itens_licitacao WHERE licitacao_id = ?"
    cursor.execute(query_itens, (licitacao_id_local,))
    itens_rows = cursor.fetchall()
    itens_lista = [dict(row) for row in itens_rows]

    query_arquivos = "SELECT * FROM arquivos_licitacao WHERE licitacao_id = ?"
    cursor.execute(query_arquivos, (licitacao_id_local,))
    arquivos_rows = cursor.fetchall()
    arquivos_lista = [dict(row) for row in arquivos_rows]

    conn.close()

    # 'situacaoReal' já está em licitacao_principal_dict
    resposta_final = {
        "licitacao": licitacao_principal_dict,
        "itens": itens_lista,
        "arquivos": arquivos_lista
    }
    return jsonify(resposta_final)

@app.route('/referencias/modalidades', methods=['GET'])
def get_modalidades_referencia():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT modalidadeId, modalidadeNome FROM licitacoes ORDER BY modalidadeNome")
    modalidades = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(modalidades)

@app.route('/referencias/statuscompra', methods=['GET'])
def get_statuscompra_referencia():
    # Retorna os status originais da API PNCP
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT situacaoCompraId, situacaoCompraNome FROM licitacoes ORDER BY situacaoCompraNome")
    status_compra = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(status_compra)

@app.route('/referencias/statusradar', methods=['GET'])
def get_statusradar_referencia():
    # Retorna os nossos status calculados (situacaoReal)
    conn = get_db_connection()
    cursor = conn.cursor()
    # Busca os valores distintos de situacaoReal que existem no banco
    cursor.execute("SELECT DISTINCT situacaoReal FROM licitacoes WHERE situacaoReal IS NOT NULL ORDER BY situacaoReal")
    status_radar_rows = cursor.fetchall()
    # Formata para uma lista de dicionários para consistência, ou apenas uma lista de strings se preferir.
    # O frontend pode precisar de um "id" e "nome" para o select.
    # Vamos criar um formato { "id": "Status Nome", "nome": "Status Nome" }
    status_radar = [{"id": row['situacaoReal'], "nome": row['situacaoReal']} for row in status_radar_rows]
    conn.close()
    return jsonify(status_radar)


if __name__ == '__main__':
    # É uma boa prática garantir que a pasta 'backend' exista se o DB estiver dentro dela
    # No entanto, DATABASE_PATH já é construído a partir de BASE_DIR,
    # e o SQLite cria o arquivo de banco de dados se ele não existir no caminho especificado.
    # A criação da tabela é feita pelo database_setup.py
    app.run(debug=True)