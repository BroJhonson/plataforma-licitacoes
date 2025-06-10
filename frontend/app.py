from flask import Flask, render_template, request, jsonify # jsonify adicionado
import requests # Para chamar a API do backend RADAR PNCP e IBGE

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_muito_segura_aqui' # Mude isso!
API_BACKEND_URL = "http://127.0.0.1:5000" # URL do seu backend original

                  
# Rotas principais que renderiza as Paginas
@app.route('/')
def index():
    return render_template('index.html', page_title="Buscar Licitações", body_class="page-busca-licitacoes")

@app.route('/home') 
def pagina_home():
    return render_template('pagina_home.html', page_title="Bem-vindo", body_class="page-home")

@app.route('/blog') #Depois modifico isso, ou deixo inativo
def pagina_blog():
    # Para um blog real, você buscaria posts de um banco de dados ou CMS.
    # Por agora, vamos usar dados de exemplo.
    posts_exemplo = [
        {
            "id": 1, "slug": "importancia-de-acompanhar-licitacoes",
            "titulo": "A Importância de Acompanhar Licitações Públicas",
            "data": "05/06/2024",
            "resumo": "Descubra por que monitorar o PNCP pode abrir novas oportunidades para seu negócio e como nossa ferramenta pode ajudar.",
            "conteudo_completo": "Conteúdo completo do post sobre a importância..." # Para uma página de post individual
        },
        {
            "id": 2, "slug": "dicas-para-vencer-licitacoes",
            "titulo": "5 Dicas Essenciais para Preparar Propostas Vencedoras",
            "data": "28/05/2024",
            "resumo": "Aprenda estratégias chave para aumentar suas chances de sucesso em processos licitatórios.",
            "conteudo_completo": "Conteúdo completo do post sobre dicas para vencer..."
        },
        # Adicione mais posts de exemplo se desejar
    ]
    return render_template('pagina_blog.html', posts=posts_exemplo, page_title="Nosso Blog", body_class="page-blog")

# (Opcional) Rota para um post individual do blog
@app.route('/blog/<string:post_slug>')
def pagina_post_blog(post_slug):
    # Lógica para encontrar o post pelo slug (você precisaria implementar isso)
    # Por agora, apenas um exemplo.
    posts_exemplo = [
        {"id": 1, "slug": "importancia-de-acompanhar-licitacoes", "titulo": "A Importância de Acompanhar Licitações Públicas", "data": "05/06/2024", "conteudo_completo": "Este é o conteúdo completo sobre a importância de acompanhar licitações..."},
        {"id": 2, "slug": "dicas-para-vencer-licitacoes", "titulo": "5 Dicas Essenciais para Preparar Propostas Vencedoras", "data": "28/05/2024", "conteudo_completo": "Aqui detalhamos as 5 dicas essenciais..."}
    ]
    post_encontrado = next((post for post in posts_exemplo if post["slug"] == post_slug), None)
    
    if post_encontrado:
        return render_template('pagina_post_individual.html', post=post_encontrado, page_title=post_encontrado["titulo"])
    else:
        return render_template('404.html', page_title="Post não encontrado", body_class="page-error"), 404 # Um template 404 genérico


@app.route('/contato')
def pagina_contato():
    return render_template('pagina_contato.html', page_title="Fale Conosco", body_class="page-contato")

@app.route('/politica-de-privacidade')
def pagina_politica_privacidade():
    return render_template('pagina_politica_privacidade.html', page_title="Política de Privacidade", body_class="page-legal")

@app.route('/politica-de-cookies')
def pagina_politica_cookies():
    return render_template('pagina_politica_cookies.html', page_title="Política de Cookies", body_class="page-legal")



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