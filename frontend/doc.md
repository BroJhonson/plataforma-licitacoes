## Documentação da API RADAR PNCP (Backend) para Frontend

### Endpoint Principal de Listagem de Licitações

**GET /licitacoes**

Retorna uma lista paginada de licitações com base nos filtros fornecidos.

**Parâmetros de Query (Query Parameters):**

*   **Paginação:**
    *   `pagina` (integer, opcional, default: 1): Número da página desejada.
    *   `porPagina` (integer, opcional, default: 20): Quantidade de registros por página.
*   **Ordenação:**
    *   `orderBy` (string, opcional, default: 'dataPublicacaoPncp'): Campo pelo qual ordenar.
        Campos válidos:
        *   `dataPublicacaoPncp` (Data de Publicação no PNCP)
        *   `dataAtualizacao` (Data da Última Atualização da Licitação)
        *   `valorTotalEstimado`
        *   `dataAberturaProposta`
        *   `dataEncerramentoProposta`
        *   `modalidadeNome`
        *   `orgaoEntidadeRazaoSocial`
        *   `unidadeOrgaoMunicipioNome`
        *   `situacaoReal` (Status calculado pelo Radar PNCP)
    *   `orderDir` (string, opcional, default: 'DESC'): Direção da ordenação.
        Valores válidos: `ASC` (ascendente), `DESC` (descendente).
*   **Filtros Gerais:**
    *   `uf` (string, pode ser repetido para múltiplos UFs, ex: `uf=SP&uf=RJ`): Sigla da UF (ex: SP, RJ, MG).
    *   `modalidadeId` (integer, pode ser repetido, ex: `modalidadeId=5&modalidadeId=6`): ID da modalidade. Usar `/referencias/modalidades` para obter a lista.
    *   `status` (integer, opcional): Filtra pelo `situacaoCompraId` original da API PNCP (usado se `statusRadar` não for fornecido). Usar `/referencias/statuscompra` para obter a lista.
    *   `statusRadar` (string, opcional): Filtra pela `situacaoReal` calculada pelo Radar PNCP (ex: "A Receber/Recebendo Proposta", "Encerrada"). Usar `/referencias/statusradar` para obter a lista. **Este filtro tem prioridade sobre `status` se ambos forem fornecidos.**
    *   `dataPubInicio` (string, opcional, formato: YYYY-MM-DD): Data de publicação PNCP inicial.
    *   `dataPubFim` (string, opcional, formato: YYYY-MM-DD): Data de publicação PNCP final.
    *   `dataAtualizacaoInicio` (string, opcional, formato: YYYY-MM-DD): Data de atualização inicial.
    *   `dataAtualizacaoFim` (string, opcional, formato: YYYY-MM-DD): Data de atualização final.
    *   `valorMin` (float, opcional): Valor total estimado mínimo.
    *   `valorMax` (float, opcional): Valor total estimado máximo.
    *   `municipioNome` (string, pode ser repetido, ex: `municipioNome=Campinas&municipioNome=Santos`): Nome do município (busca parcial, case-insensitive).
    *   `anoCompra` (integer, opcional): Ano da compra (ex: 2023).
    *   `cnpjOrgao` (string, opcional): CNPJ do órgão/entidade.
    *   `palavraChave` (string, pode ser repetido, ex: `palavraChave=consultoria&palavraChave=software`): Busca por termos em campos de texto. Se múltiplos `palavraChave` são fornecidos, a lógica é OR (qualquer uma das palavras).
    *   `excluirPalavra` (string, pode ser repetido, ex: `excluirPalavra=teste&excluirPalavra=demo`): Exclui licitações que contenham qualquer um destes termos nos campos de texto.

**Resposta (JSON):**

```json
{
    "pagina_atual": 1,
    "por_pagina": 20,
    "total_registros": 150,
    "total_paginas": 8,
    "origem_dados": "banco_local_janela_anual",
    "licitacoes": [
        {
            "id": 1,
            "numeroControlePNCP": "123-4-567/2023",
            "anoCompra": 2023,
            "modalidadeNome": "PREGÃO ELETRÔNICO",
            "objetoCompra": "Aquisição de material de escritório...",
            "dataPublicacaoPncp": "2023-10-01",
            "dataAtualizacao": "2023-10-05",
            "valorTotalEstimado": 50000.00,
            "orgaoEntidadeRazaoSocial": "PREFEITURA MUNICIPAL DE EXEMPLO",
            "unidadeOrgaoMunicipioNome": "EXEMPLO",
            "unidadeOrgaoUfSigla": "EX",
            "situacaoCompraId": 1,
            "situacaoCompraNome": "Divulgada no PNCP",
            "situacaoReal": "A Receber/Recebendo Proposta", // Campo calculado
            // ...outros campos da licitação...
            "link_portal_pncp": "https://pncp.gov.br/app/editais/..."
        }
        // ...mais licitações...
    ]
}

//Resposta (JSON)
{
    "licitacao": {
        "id": 1,
        "numeroControlePNCP": "123-4-567/2023",
        "anoCompra": 2023,
        // ...todos os campos da licitação, incluindo "situacaoReal"...
        "situacaoReal": "A Receber/Recebendo Proposta"
    },
    "itens": [
        {
            "id": 10,
            "licitacao_id": 1,
            "numeroItem": 1,
            "descricao": "Caneta esferográfica azul",
            // ...outros campos do item...
        }
        // ...mais itens...
    ],
    "arquivos": [
        {
            "id": 20,
            "licitacao_id": 1,
            "titulo": "Edital Completo.pdf",
            "link_download": "https://pncp.gov.br/pncp-api/v1/orgaos/...",
            // ...outros campos do arquivo...
        }
        // ...mais arquivos...
    ]
}

//Possível Erro:
//404 Não encontrado: Se a licitação com o fornecido não for encontrada.numeroControlePNCP
{
    "erro": "Licitação não encontrada",
    "numeroControlePNCP": "ID_NAO_ENCONTRADO"
}

//Notas Importantes para o Frontend
//Campo :situacaoReal Este é o status da licitação calculado pelo nosso backend e é o mais recomendado para exibição e filtro primário do status da licitação.
//Ordenação por :dataAtualizacao Para ordenar pela data de atualização, use . para mais antigo primeiro, para mais recente primeiro. orderBy=dataAtualizacao orderDir=ASC orderDir=DESC
//Múltiplos Valores para Filtros: Filtros como , , , , podem ser repetidos na URL para aplicar múltiplos valores (ex: ).uf modalidadeId municipioNome palavraChave excluirPalavra uf=SP&uf=RJ
//Consistência dos Dados: O backend sincroniza dados da API PNCP periodicamente. Pode haver um pequeno delay entre a atualização no PNCP e a disponibilidade no Radar PNCP. O campo sem resposta de indica uma fonte. origem_dados /licitacoes
//Paginação: Utilize os campos , e da resposta de para construir a interface de paginção.pagina_atual total_registros total_paginas /licitacoes