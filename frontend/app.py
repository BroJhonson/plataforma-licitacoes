from flask import Flask, render_template, request, jsonify # jsonify adicionado
import requests # Para chamar a API do backend RADAR PNCP e IBGE
from markupsafe import Markup, escape 

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_muito_segura_aqui' # Mude isso!
API_BACKEND_URL = "http://127.0.0.1:5000" # URL do seu backend original

                   
# Rotas principais que renderiza as Paginas
@app.route('/') 
def inicio():
    return render_template('index.html', page_title="Bem-vindo ao RADAR PNCP", body_class="page-home")

@app.route('/radarPNCP')
def buscador_licitacoes():
    return render_template('radar.html', page_title="Buscar Licitações - RADAR PNCP", body_class="page-busca-licitacoes")

# app.py (no topo ou antes das rotas do blog)
posts_blog_exemplo = [
    {
        "id": 1, 
        "slug": "como-encontrar-licitacoes-por-palavra-chave", # Usar letras minúsculas, sem espaços (hífens são bons)
        "titulo": "Como Encontrar Licitações por Palavra-chave",
        "data": "06/06/2024", # Mantenha o formato que desejar
        "resumo": "Aprenda a usar filtros estratégicos para encontrar licitações perfeitas para o seu negócio.",
        "imagem_destaque": "artigo1.jpg", # Nome do arquivo da imagem
        "conteudo_completo": """<h2>Entendendo a Busca por Palavra-Chave</h2>
            <p>A busca por palavra-chave é uma das ferramentas mais poderosas ao procurar licitações. 
            No entanto, para ser eficaz, é preciso estratégia...</p>
            <p>Imagine que você vende 'equipamentos de informática'. Digitar apenas 'informática' pode trazer
            milhares de resultados, incluindo serviços de manutenção que não são seu foco.</p>
            <h3>Dicas para Otimizar sua Busca:</h3>
            <ul>
                <li><strong>Seja Específico:</strong> Em vez de "material", tente "material de escritório" ou "material de construção".</li>
                <li><strong>Use Múltiplas Palavras (com vírgula no Radar PNCP):</strong> "consultoria ambiental, licenciamento" para encontrar ambos.</li>
                <li><strong>Pense em Sinônimos:</strong> Se você oferece "treinamento", tente também "capacitação", "curso".</li>
                <li><strong>Utilize Palavras de Exclusão:</strong> Se você vende produtos novos, pode querer excluir termos como "usado" ou "reparo".</li>
            </ul>
            <p>No nosso sistema Radar PNCP, a interface de tags para palavras-chave (que estamos desenvolvendo!) 
            facilitará ainda mais esse processo, permitindo adicionar e remover termos de forma visual e intuitiva.</p>
            <p>Lembre-se também de combinar o filtro de palavras-chave com outros filtros como UF, modalidade e status 
            para refinar ainda mais seus resultados e encontrar as oportunidades que realmente importam para o seu negócio.</p>
        """
    },
    {
        "id": 2, 
        "slug": "nova-lei-de-licitacoes-o-que-voce-precisa-saber",
        "titulo": "Nova Lei de Licitações: O Que Você Precisa Saber",
        "data": "07/06/2024",
        "resumo": "Entenda o impacto da nova legislação e como se adaptar a tempo para aproveitar as mudanças.",
        "imagem_destaque": "artigo2.jpg",
        "conteudo_completo": """<h2>Principais Mudanças da Lei 14.133/2021</h2>
            <p>A Nova Lei de Licitações e Contratos Administrativos (Lei nº 14.133/2021) trouxe modernização e 
            novos paradigmas para as compras públicas no Brasil...</p>
            <p>Alguns pontos de destaque incluem:</p>
            <ul>
                <li><strong>Novas Modalidades:</strong> Como o diálogo competitivo.</li>
                <li><strong>Portal Nacional de Contratações Públicas (PNCP):</strong> Centralização das informações.</li>
                <li><strong>Foco no Planejamento:</strong> Ênfase na fase preparatória das licitações.</li>
                <li><strong>Critérios de Julgamento:</strong> Além do menor preço, o maior desconto, melhor técnica ou conteúdo artístico, etc.</li>
            </ul>
            <p>Adaptar-se a essa nova realidade é fundamental. Isso inclui revisar processos internos, capacitar equipes
            e entender os novos instrumentos como o Estudo Técnico Preliminar (ETP) e o Termo de Referência.</p>
        """
    },
    {
        "id": 3, 
        "slug": "erros-comuns-em-propostas-de-licitacao",
        "titulo": "Erros Comuns em Propostas de Licitação e Como Evitá-los",
        "data": "08/06/2024",
        "resumo": "Evite armadilhas que podem desclassificar sua empresa nas licitações públicas.",
        "imagem_destaque": "artigo3.jpg",
        "conteudo_completo": """<h2>Não Deixe que Pequenos Erros Custem Grandes Oportunidades</h2>
            <p>Participar de licitações pode ser um processo complexo, e pequenos descuidos na elaboração da proposta
            podem levar à desclassificação. Conhecer os erros mais comuns é o primeiro passo para evitá-los.</p>
            <h3>Principais Armadilhas:</h3>
            <ol>
                <li><strong>Documentação Incompleta ou Vencida:</strong> Certidões negativas, balanços, atestados de capacidade técnica. Tudo deve estar rigorosamente em dia e conforme solicitado no edital.</li>
                <li><strong>Não Atender às Especificações Técnicas:</strong> O produto ou serviço ofertado deve corresponder exatamente ao que foi descrito no Termo de Referência ou Projeto Básico. Qualquer desvio pode ser motivo para desclassificação.</li>
                <li><strong>Erros na Planilha de Preços:</strong> Cálculos incorretos, omissão de custos, ou preços inexequíveis (muito baixos) ou excessivos.</li>
                <li><strong>Perda de Prazos:</strong> Tanto para envio de propostas quanto para recursos ou envio de documentação complementar.</li>
                <li><strong>Assinaturas Ausentes ou Inválidas:</strong> Propostas e declarações devem ser devidamente assinadas por quem tem poderes para tal.</li>
            </ol>
            <p>A atenção aos detalhes, uma leitura minuciosa do edital e um bom planejamento são seus maiores aliados para evitar esses erros e aumentar suas chances de sucesso.</p>
        """
    }
]

@app.route('/blog')
def pagina_blog():
    return render_template('pagina_blog.html', posts=posts_blog_exemplo, page_title="Nosso Blog", body_class="page-blog")

@app.route('/blog/<string:post_slug>')
def pagina_post_blog(post_slug):
    print(f"Recebido slug da URL: '{post_slug}'") # DEBUG
    
    post_encontrado = None # Inicializa como None

    for p_exemplo in posts_blog_exemplo:
        print(f"Comparando '{post_slug}' com slug do post da lista: '{p_exemplo.get('slug')}'") # DEBUG
        if p_exemplo.get("slug") == post_slug:
            post_encontrado = p_exemplo
            print(f"Match! Post encontrado: {p_exemplo['titulo']}") # DEBUG
            break # IMPORTANTE: Sai do loop assim que encontrar o post correto
    
    if post_encontrado:
        return render_template('pagina_post_individual.html', 
                               post=post_encontrado, 
                               page_title=post_encontrado["titulo"], 
                               body_class="page-post-individual")
    else:
        print(f"Post com slug '{post_slug}' NÃO encontrado na lista!") # DEBUG

        return render_template('404.html', page_title="Post não encontrado", body_class="page-error"), 404
        #return "Post não encontrado", 404 # Simples por enquanto, Ou redirecione para a lista do blog


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

# Filtro personalizado nl2br PARA QUEBRA DE LINHA DOS PARAGRAFOS
def nl2br_filter(value):
    if value is None:
        return ''
    # Escapa o HTML para segurança, substitui \n por <br>\n, e marca como Markup seguro
    return Markup(str(escape(value)).replace('\n', '<br>\n'))

app.jinja_env.filters['nl2br'] = nl2br_filter # Registra o filtro

if __name__ == '__main__':
    app.run(debug=True, port=5001)