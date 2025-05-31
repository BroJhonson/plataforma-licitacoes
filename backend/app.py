# backend/app.py

from flask import Flask, jsonify, request
import sqlite3
import os
from datetime import datetime # Não precisamos de date, timedelta aqui por enquanto

# --- Configurações ---
app = Flask(__name__) 

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'database.db')
API_BASE_URL_CONSULTA_PNCP = "https://pncp.gov.br/api/consulta" # Renomeado para clareza

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
    # Usar um único dicionário para todos os filtros coletados
    filtros = {
        'ufs': request.args.getlist('uf'), # Sempre retorna lista
        'modalidadesId': request.args.getlist('modalidadeId', type=int), # Sempre retorna lista
        'palavraChave': request.args.get('palavraChave', default=None, type=str),
        'excluirPalavras': request.args.getlist('excluirPalavra'), # Sempre retorna lista
        'statusId': request.args.get('status', default=None, type=int), # status é único
        'dataPubInicio': request.args.get('dataPubInicio', default=None, type=str),
        'dataPubFim': request.args.get('dataPubFim', default=None, type=str),
        'valorMin': request.args.get('valorMin', default=None, type=float),
        'valorMax': request.args.get('valorMax', default=None, type=float)
    }
    
    pagina = request.args.get('pagina', default=1, type=int)
    por_pagina = request.args.get('porPagina', default=20, type=int)
    offset = (pagina - 1) * por_pagina
    # --- Construção da Query SQL 
    condicoes_db = []
    parametros_db = []
    

    licitacoes_lista = []
    total_registros = 0
    origem_dados = "banco_local" # Default


    if filtros['statusId'] is not None:
        condicoes_db.append("situacaoCompraId = ?")
        parametros_db.append(filtros['statusId'])
         # Se não for fornecido, não filtra por status (busca todos os status do seu banco)

    if filtros['ufs']:
        placeholders = ', '.join(['?'] * len(filtros['ufs']))
        condicoes_db.append(f"unidadeOrgaoUfSigla IN ({placeholders})")
        parametros_db.extend([uf.upper() for uf in filtros['ufs']])
        
    if filtros['modalidadesId']:
        placeholders = ', '.join(['?'] * len(filtros['modalidadesId']))
        condicoes_db.append(f"modalidadeId IN ({placeholders})")
        parametros_db.extend(filtros['modalidadesId'])

    if filtros['palavraChave']:     #ADICIONAR DEPOIS MAIS LOCAIS DE PROCURA
        termo = f"%{filtros['palavraChave']}%"
        condicoes_db.append("(objetoCompra LIKE ? OR orgaoEntidadeRazaoSocial LIKE ? OR unidadeOrgaoNome LIKE ? OR numeroControlePNCP LIKE ?)")
        parametros_db.extend([termo] * 4)

    if filtros['excluirPalavras']:      #MESMA FITA DA OUTRA SITUAÇÃO
        for palavra in filtros['excluirPalavras']:
            termo_excluir = f"%{palavra}%"
            condicoes_db.append("(COALESCE(objetoCompra, '') NOT LIKE ? AND COALESCE(orgaoEntidadeRazaoSocial, '') NOT LIKE ? AND COALESCE(unidadeOrgaoNome, '') NOT LIKE ? AND COALESCE(numeroControlePNCP, '') NOT LIKE ?)")
            parametros_db.extend([termo_excluir] * 4)
        
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
        
    
    query_select_dados = "SELECT * FROM licitacoes"
    query_select_contagem = "SELECT COUNT(id) FROM licitacoes"
    query_where = ""
    if condicoes_db: 
        query_where = " WHERE " + " AND ".join(condicoes_db) 
    
    query_order_limit_offset_dados = " ORDER BY dataPublicacaoPncp DESC LIMIT ? OFFSET ?" # Ou outra ordenação
    
    sql_query_dados_final = query_select_dados + query_where + query_order_limit_offset_dados
    parametros_dados_sql_final = parametros_db + [por_pagina, offset] # Renomeado de parametros_sql para parametros_db
    
    sql_query_contagem_final = query_select_contagem + query_where
    
    # (Resto da execução e retorno do JSON)
    conn = get_db_connection()
    cursor = conn.cursor()
    licitacoes_lista = []
    total_registros = 0
    try:
        print(f"DB Query Dados: {sql_query_dados_final}")
        print(f"DB Params Dados: {parametros_dados_sql_final}")
        cursor.execute(sql_query_dados_final, parametros_dados_sql_final)
        licitacoes_rows = cursor.fetchall()
        licitacoes_lista = [dict(row) for row in licitacoes_rows]

        print(f"DB Query Contagem: {sql_query_contagem_final}")
        print(f"DB Params Contagem: {parametros_db}") # Usa parametros_db
        cursor.execute(sql_query_contagem_final, parametros_db) # Usa parametros_db
        total_registros = cursor.fetchone()[0]
    except sqlite3.Error as e:
        print(f"Erro ao buscar/contar no banco local: {e}")
        # Não precisa de fallback, então pode retornar erro 500 ou lista vazia.
        if conn: conn.close()
        return jsonify({"erro": "Erro interno ao processar sua busca.", "detalhes": str(e)}), 500
    finally:
        if conn: conn.close()

    total_paginas_final = (total_registros + por_pagina - 1) // por_pagina if por_pagina > 0 and total_registros > 0 else 0
    if total_registros == 0 : total_paginas_final = 0

    return jsonify({
        "pagina_atual": pagina,
        "por_pagina": por_pagina,
        "total_registros": total_registros,
        "total_paginas": total_paginas_final,
        "origem_dados": "banco_local_janela_anual", # Nova origem
        "licitacoes": licitacoes_lista
    })
    


@app.route('/licitacao/<path:numero_controle_pncp>', methods=['GET'])
def get_detalhe_licitacao(numero_controle_pncp):
    # ... (seu código de detalhes, que está bom) ...
    conn = get_db_connection()
    cursor = conn.cursor()
    query_licitacao_principal = "SELECT * FROM licitacoes WHERE numeroControlePNCP = ?"
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
    resposta_final = {
        "licitacao": licitacao_principal_dict,
        "itens": itens_lista,
        "arquivos": arquivos_lista
    }
    return jsonify(resposta_final)

if __name__ == '__main__':
    app.run(debug=True)