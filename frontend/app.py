from flask import Flask, render_template, request, jsonify # jsonify adicionado
import requests # Para chamar a API do backend RADAR PNCP e IBGE

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_muito_segura_aqui' # Mude isso!

# URL base da API do Backend RADAR PNCP
API_BACKEND_URL = "http://127.0.0.1:5000" # URL do seu backend original

# Rota principal que renderiza o index.html
@app.route('/')
def index():
    return render_template('index.html')
                                          
# --- API ROUTES FOR FRONTEND JAVASCRIPT ---
@app.route('/api/frontend/licitacoes', methods=['GET'])
def api_get_licitacoes():
    # Coleta todos os query parameters enviados pelo JavaScript
    # Estes parâmetros devem corresponder aos que a API do backend RADAR PNCP espera
    params_from_js = request.args.to_dict(flat=False) # flat=False para lidar com params repetidos (ex: uf)
    
    # Pequena transformação para o parâmetro 'uf' se ele vier como uma lista do JS
    # A biblioteca 'requests' lida bem com listas para parâmetros repetidos.
    # Ex: se params_from_js['uf'] for ['SP', 'RJ'], requests fará ?uf=SP&uf=RJ
    
    print(f"Frontend API: Chamando backend /licitacoes com params: {params_from_js}")

    try:
        response = requests.get(f"{API_BACKEND_URL}/licitacoes", params=params_from_js)
        response.raise_for_status() # Levanta um erro para respostas HTTP ruins (4xx ou 5xx)
        return jsonify(response.json()) # Retorna o JSON da API do backend para o JS
    except requests.exceptions.HTTPError as http_err:
        # Tenta retornar a mensagem de erro do backend, se disponível
        error_json = None
        try:
            error_json = http_err.response.json()
        except ValueError: #Se a resposta de erro não for JSON
            pass # error_json permanece None
        
        if error_json and 'erro' in error_json:
             return jsonify({"erro_backend": error_json.get('erro'), "detalhes_backend": error_json.get('detalhes'), "status_code": http_err.response.status_code}), http_err.response.status_code
        else:
            return jsonify({"erro_frontend": f"Erro HTTP ao chamar backend: {http_err}", "status_code": http_err.response.status_code if http_err.response is not None else 503}), (http_err.response.status_code if http_err.response is not None else 503)
    except requests.exceptions.RequestException as e:
        # Erro de conexão, timeout, etc.
        return jsonify({"erro_frontend": f"Erro de conexão com o backend: {e}", "status_code": 503}), 503
    except ValueError: # Erro ao decodificar JSON da API do backend (improvável se raise_for_status passou)
        return jsonify({"erro_frontend": "Resposta inválida (JSON) da API do backend.", "status_code": 500}), 500


@app.route('/api/frontend/licitacao/<path:pncp_id>', methods=['GET'])
def api_get_licitacao_detalhes(pncp_id):
    print(f"Frontend API: Chamando backend /licitacao/{pncp_id}")
    try:
        response = requests.get(f"{API_BACKEND_URL}/licitacao/{pncp_id}")
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.HTTPError as http_err:
        error_json = None
        try:
            error_json = http_err.response.json()
        except ValueError:
            pass
        
        if error_json and 'erro' in error_json:
             return jsonify({"erro_backend": error_json.get('erro'), "detalhes_backend": error_json.get('detalhes'), "status_code": http_err.response.status_code}), http_err.response.status_code
        else:
            return jsonify({"erro_frontend": f"Erro HTTP ao chamar backend para detalhes: {http_err}", "status_code": http_err.response.status_code if http_err.response is not None else 503}), (http_err.response.status_code if http_err.response is not None else 503)
    except requests.exceptions.RequestException as e:
        return jsonify({"erro_frontend": f"Erro de conexão com o backend para detalhes: {e}", "status_code": 503}), 503
    except ValueError:
        return jsonify({"erro_frontend": "Resposta inválida (JSON) da API do backend para detalhes.", "status_code": 500}), 500


@app.route('/api/ibge/municipios/<uf_sigla>', methods=['GET'])
def api_get_municipios_ibge(uf_sigla):
    # Validação simples da UF (poderia ser mais robusta)
    if not uf_sigla or len(uf_sigla) != 2 or not uf_sigla.isalpha():
        return jsonify({"erro": "Sigla da UF inválida."}), 400
    
    ibge_api_url = f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf_sigla.upper()}/municipios"
    print(f"Frontend API: Chamando IBGE API: {ibge_api_url}")
    try:
        response = requests.get(ibge_api_url)
        response.raise_for_status()
        # A API do IBGE retorna uma lista de objetos, cada um com 'id' e 'nome'
        municipios = [{"id": m["id"], "nome": m["nome"]} for m in response.json()]
        return jsonify(municipios)
    except requests.exceptions.HTTPError as http_err:
        return jsonify({"erro": f"Erro ao buscar municípios no IBGE: {http_err}", "status_code": http_err.response.status_code}), http_err.response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"erro": f"Erro de conexão com API do IBGE: {e}", "status_code": 503}), 503
    except ValueError:
        return jsonify({"erro": "Resposta inválida (JSON) da API do IBGE.", "status_code": 500}), 500

@app.route('/api/frontend/referencias/modalidades', methods=['GET'])
def api_get_referencia_modalidades():
    print("Frontend API: Chamando backend /referencias/modalidades")
    try:
        response = requests.get(f"{API_BACKEND_URL}/referencias/modalidades")
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar modalidades do backend: {e}")
        return jsonify({"erro_frontend": f"Erro ao buscar modalidades: {e}", "status_code": 503}), 503
    except ValueError:
        return jsonify({"erro_frontend": "Resposta inválida (JSON) da API de modalidades.", "status_code": 500}), 500

@app.route('/api/frontend/referencias/statusradar', methods=['GET'])
def api_get_referencia_statusradar():
    print("Frontend API: Chamando backend /referencias/statusradar")
    try:
        response = requests.get(f"{API_BACKEND_URL}/referencias/statusradar")
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar status radar do backend: {e}")
        return jsonify({"erro_frontend": f"Erro ao buscar status radar: {e}", "status_code": 503}), 503
    except ValueError:
        return jsonify({"erro_frontend": "Resposta inválida (JSON) da API de status radar.", "status_code": 500}), 500

# (Opcional) Se você também quiser usar /referencias/statuscompra
@app.route('/api/frontend/referencias/statuscompra', methods=['GET'])
def api_get_referencia_statuscompra():
    print("Frontend API: Chamando backend /referencias/statuscompra")
    try:
        response = requests.get(f"{API_BACKEND_URL}/referencias/statuscompra")
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar status compra do backend: {e}")
        return jsonify({"erro_frontend": f"Erro ao buscar status compra: {e}", "status_code": 503}), 503
    except ValueError:
        return jsonify({"erro_frontend": "Resposta inválida (JSON) da API de status compra.", "status_code": 500}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5001)