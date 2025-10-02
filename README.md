# RADAR PNCP - Um Buscador Avançado para Licitações Públicas
"Projeto Completo Junto. E com SQLite"

![RADAR PNCP Screenshot](caminho/para/sua/screenshot.png) 
<!-- TODO: Substitua pelo caminho de uma boa screenshot da sua aplicação -->

O **RADAR PNCP** é uma aplicação web completa, desenvolvida com Flask (Python) e JavaScript moderno, que funciona como uma interface amigável e poderosa para o Portal Nacional de Contratações Públicas (PNCP) do Brasil. O objetivo principal é simplificar e agilizar a busca, filtragem e acompanhamento de licitações públicas, oferecendo uma experiência de usuário superior à do portal oficial.

A aplicação utiliza um banco de dados local (SQLite) que é populado e sincronizado periodicamente através de um script que consome a API do PNCP, garantindo buscas rápidas e performáticas sem depender de chamadas diretas à API oficial em tempo real.

---

## ✨ Funcionalidades Principais

*   **Busca Avançada por Palavras-Chave:** Filtre licitações usando múltiplos termos de inclusão (requer que **todos** os termos estejam presentes) e exclusão.
*   **Filtros Abrangentes:** Refine sua busca por Status, Modalidade, Estado (UF), Município, Faixa de Valor e Período de Publicação/Atualização.
*   **Interface Reativa:** Tabela de resultados com paginação, ordenação e atualização dinâmica sem a necessidade de recarregar a página.
*   **Painel de Detalhes Integrado:** Visualize todos os detalhes de uma licitação, incluindo seus itens e arquivos para download, em um painel lateral (Offcanvas) sem sair da tela de busca.
*   **Sistema de Favoritos:** Salve licitações de interesse para fácil acesso posterior (utilizando o `localStorage` do navegador).
*   **Exportação para CSV:** Exporte os resultados da sua busca atual para uma planilha com um único clique.
*   **Sincronização de Dados:** Um script de backend robusto (`sync_api.py`) mantém o banco de dados local atualizado com as últimas licitações do PNCP.
*   **Páginas de Conteúdo:** Seções de Blog e um formulário de Contato funcional para feedback dos usuários.
*   **Design Responsivo:** Interface otimizada para desktop, tablets e dispositivos móveis.

---

## 🛠️ Tecnologias Utilizadas

**Backend:**
*   **Python 3**
*   **Flask:** Microframework para a aplicação web e API.
*   **SQLite 3:** Banco de dados relacional embarcado.
*   **Requests:** Para consumir a API do PNCP.
*   **Tenacity:** Para retentativas robustas em chamadas de API.
*   **python-dotenv:** Para gerenciamento de variáveis de ambiente.

**Frontend:**
*   **HTML5** e **SCSS (Sass)**
*   **JavaScript (ES6+ Modules):** Lógica da interface do usuário.
*   **Bootstrap 5:** Framework para componentes e layout responsivo.
*   **Node.js / npm:** Para gerenciamento de pacotes e scripts de build.
*   **esbuild:** Bundler JavaScript para compilar o código do frontend.

**Ambiente de Desenvolvimento:**
*   **concurrently:** Para executar os processos de backend e frontend simultaneamente.
*   **nodemon:** Para recarregar o servidor Flask automaticamente durante o desenvolvimento.

---

## 🚀 Como Executar o Projeto Localmente

Siga os passos abaixo para configurar e executar o RADAR PNCP em sua máquina.

### Pré-requisitos
*   [Git](https://git-scm.com/)
*   [Python 3.8+](https://www.python.org/) e `pip`
*   [Node.js e npm](https://nodejs.org/)

### 1. Clonar o Repositório
```bash
git clone https://github.com/BroJhonson/plataforma-licitacoes.git
cd plataforma-licitacoes
