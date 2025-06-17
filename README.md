# Sistema de Orquestração de Múltiplos Agentes com LangChain

Este projeto demonstra uma arquitetura de orquestração de múltiplos agentes (Multi-Agent Orchestration) usando LangChain. Diferentes agentes especializados são selecionados dinamicamente para lidar com diferentes tipos de entrada do usuário, com persistência de contexto e histórico entre os agentes e o usuário.

## Arquitetura
*   **Lead Agent**: Coordena a interação com o usuário e delega tarefas.
*   **Router**: Um mecanismo (LLMRouterChain) que decide qual agente especializado é mais adequado para a consulta do usuário.
*   **Agentes Especializados (Tools)**:
    *   **AgentA**: Agora um `AgentExecutor` mais robusto, focado no domínio X. Ele utiliza suas próprias ferramentas internas para processar consultas:
        *   `BuscaInformacaoDominioX`: Para responder perguntas sobre as características, origem ou componentes de X.
        *   `CalculadoraTrivial`: Para realizar cálculos de adição simples.
    *   **AgentB**: Especialista em Y (função simples).
    *   **AgentC**: Especialista em Z (função simples).
*   **Memória**:
    *   `user_lead_memory`: Armazena o histórico da conversa entre o usuário e o Lead Agent.
    *   `lead_team_memory`: Armazena o histórico das interações do Lead Agent com os agentes especializados.
*   **API Flask**: Um servidor web simples para expor a funcionalidade do agente.
*   **LangSmith**: (Opcional) Para rastreamento, avaliação e debugging.
*   **n8n Webhook**: (Opcional) Para enviar dados da conversa para fluxos de trabalho externos no n8n.

## Estrutura de Diretórios
```
.
├── app/
│   ├── agents/             # Módulos dos agentes especializados (agent_a.py, etc.)
│   │   ├── __init__.py
│   │   ├── agent_a.py
│   │   ├── agent_a_tools.py  # Ferramentas específicas do Agente A
│   │   ├── agent_b.py
│   │   └── agent_c.py
│   ├── __init__.py
│   ├── main.py             # Lógica principal dos agentes, chains e memórias
│   ├── server.py           # Servidor Flask API
│   └── tools.py            # Definição das LangChain Tools para os agentes (usadas pelo Lead Agent)
├── .env                    # Arquivo para variáveis de ambiente (NÃO versionar chaves reais)
├── .gitignore
├── README.md               # Este arquivo
└── requirements.txt        # Dependências Python
```

## Pré-requisitos
*   Python 3.8+
*   pip (gerenciador de pacotes Python)

## Configuração
1.  **Clone o repositório (se aplicável):**
    ```bash
    # git clone <url_do_repositorio>
    # cd <nome_do_repositorio>
    ```

2.  **Crie e ative um ambiente virtual:**
    ```bash
    python -m venv venv
    # No Windows
    # venv\Scripts\activate
    # No macOS/Linux
    # source venv/bin/activate
    ```

3.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure as variáveis de ambiente:**
    Crie um arquivo chamado `.env` na raiz do projeto copiando o exemplo abaixo e preenchendo com suas chaves:
    ```env
    # OpenAI API Key (Obrigatório)
    OPENAI_API_KEY="SUA_CHAVE_API_OPENAI_AQUI"

    # LangSmith Configuration (Opcional, para rastreamento)
    LANGCHAIN_TRACING_V2="true"
    LANGCHAIN_ENDPOINT="https://api.smith.langchain.com"
    LANGCHAIN_API_KEY="SUA_CHAVE_API_LANGSMITH_AQUI"
    LANGCHAIN_PROJECT="Multi-Agent Orchestration" # Ou o nome do seu projeto no LangSmith

    # n8n Integration (Opcional)
    # URL do seu webhook no n8n para receber notificações das conversas
    N8N_WEBHOOK_URL="SUA_URL_WEBHOOK_N8N_AQUI"
    ```
    **Importante**: Substitua `"SUA_CHAVE_API_OPENAI_AQUI"`, `"SUA_CHAVE_API_LANGSMITH_AQUI"` e `"SUA_URL_WEBHOOK_N8N_AQUI"` pelas suas chaves/URLs reais.

## Executando a Aplicação
Após configurar o `.env`, você pode iniciar o servidor Flask:
```bash
python -m app.server
```
Ou, se preferir usar o Flask CLI (certifique-se de que `FLASK_APP` está configurado ou use `flask --app app.server run`):
```bash
flask run --host=0.0.0.0 --port=8000
```
O servidor estará disponível em `http://localhost:8000`.

## Como Interagir com a API

### Endpoint `/chat` (POST)
Este é o principal endpoint para interagir com o sistema de agentes.

**Exemplo de Requisição (usando curl):**
```bash
curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{"user_input": "Olá, preciso de ajuda com o tópico X"}'
```

**Exemplo de Payload de Entrada (JSON):**
```json
{
    "user_input": "Qual sua especialidade, Agente B?",
    "user_id": "usuario123" // Opcional
}
```

**Exemplo de Payload de Saída (JSON):**
```json
{
    "response": "[Agent B] Resposta especializada para: Qual sua especialidade, Agente B?"
}
```

### Endpoint `/health` (GET)
Verifica o status do servidor e do agente.
```bash
curl http://localhost:8000/health
```

### Endpoints de Memória (GET - para Debugging)
*   `/memory/user_lead`: Mostra o histórico da conversa entre usuário e Lead Agent.
*   `/memory/lead_team`: Mostra o histórico das interações do Lead Agent com os agentes especializados.
```bash
curl http://localhost:8000/memory/user_lead
curl http://localhost:8000/memory/lead_team
```

## Rastreamento com LangSmith
Se as variáveis de ambiente do LangSmith (`LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT`) estiverem configuradas corretamente no arquivo `.env`, as interações com os agentes serão automaticamente rastreadas e visíveis no seu dashboard do LangSmith. Isso é extremamente útil para depuração e monitoramento do comportamento dos agentes.

## Integração com n8n

O sistema pode ser configurado para enviar detalhes de cada interação bem-sucedida (entrada do usuário e resposta do agente) para um webhook n8n. Isso permite a criação de fluxos de trabalho automatizados e integrações com outros serviços.

Para habilitar, configure a variável `N8N_WEBHOOK_URL` no seu arquivo `.env` com a URL do seu webhook n8n.

O payload enviado para o n8n terá o seguinte formato JSON:
```json
{
  "user": "IdentificadorDoUsuario", // Ex: "Usuário Anônimo via API" ou um ID de usuário fornecido na requisição
  "message": "A entrada original do usuário.",
  "response": "A resposta final fornecida pelo agente."
}
```
Com isso, você pode, por exemplo, usar o n8n para:
*   Registrar todas as conversas em um banco de dados ou Notion.
*   Enviar notificações para o Slack sobre interações específicas.
*   Criar ou atualizar leads em um CRM.
*   Disparar e-mails de acompanhamento.

---

*Este projeto serve como uma base para construir sistemas de múltiplos agentes mais complexos.*

## Testes

Para executar os testes unitários, navegue até o diretório raiz do projeto e execute:

```bash
python -m unittest discover tests
```
Isso descobrirá e executará todos os testes nos arquivos `test_*.py` dentro do diretório `tests`.
É recomendado executar os testes em um ambiente onde a `OPENAI_API_KEY` não esteja definida ou esteja mockada para evitar chamadas reais à API durante os testes unitários. Os testes são projetados para mockar essas dependências externas.
