# app/server.py
from flask import Flask, request, jsonify
import os

# Tentar importar o lead_agent_executor e as memórias de app.main
# Esta importação executa o código em app.main, incluindo prints de status
try:
    from app.main import lead_agent_executor, user_lead_memory, lead_team_memory, openai_api_key, llm
    print("Componentes de app.main importados com sucesso em server.py.")
except ImportError as e:
    print(f"Erro ao importar de app.main em server.py: {e}")
    lead_agent_executor = None
    user_lead_memory = None
    lead_team_memory = None
    openai_api_key = None
    llm = None
except Exception as e: # Captura outras exceções potenciais durante a importação (execução de main.py)
    print(f"Uma exceção ocorreu durante a importação (execução de app.main): {e}")
    lead_agent_executor = None
    user_lead_memory = None
    lead_team_memory = None
    openai_api_key = None
    llm = None


app = Flask(__name__)

# Verificar se as chaves de API estão configuradas antes de tentar rodar o servidor
# Isso é mais um lembrete, pois app.main já lida com a inicialização condicional.
if not openai_api_key or openai_api_key == "SUA_CHAVE_API_AQUI":
    print("*********************************************************************************")
    print("AVISO URGENTE: OPENAI_API_KEY não está configurada no arquivo .env!")
    print("O servidor Flask iniciará, mas o endpoint /chat não funcionará.")
    print("Por favor, configure a OPENAI_API_KEY e reinicie o servidor.")
    print("*********************************************************************************")
elif not llm: # Se a chave existe mas o llm não inicializou por outra razão
    print("*********************************************************************************")
    print("AVISO: O LLM não foi inicializado, mesmo com uma OPENAI_API_KEY aparente.")
    print("O endpoint /chat provavelmente não funcionará.")
    print("*********************************************************************************")


@app.route('/chat', methods=['POST'])
def chat():
    if not lead_agent_executor:
        return jsonify({
            "error": "Lead Agent não está inicializado. Verifique a configuração da OPENAI_API_KEY no arquivo .env e reinicie o servidor."
        }), 503 # Service Unavailable

    data = request.get_json()
    if not data or 'user_input' not in data:
        return jsonify({"error": "Entrada inválida. 'user_input' é esperado no JSON."}), 400

    user_input = data['user_input']

    try:
        # Invocar o lead_agent_executor com o input do usuário
        # A chave 'input' deve corresponder ao que o AgentExecutor espera
        print(f"Recebido no /chat: {user_input}")
        response = lead_agent_executor.invoke({"input": user_input})

        # A resposta de invoke é um dicionário, a saída principal geralmente está em 'output'
        agent_output = response.get('output', "Nenhuma saída do agente.")
        print(f"Resposta do agente: {agent_output}")

        return jsonify({"response": agent_output})

    except Exception as e:
        print(f"Erro durante a execução do agente no endpoint /chat: {e}")
        # Considerar logar o traceback completo aqui para debugging
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Erro interno ao processar sua requisição: {str(e)}"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    if lead_agent_executor and llm:
        return jsonify({"status": "ok", "message": "Servidor Flask e Lead Agent estão operacionais."}), 200
    elif not openai_api_key or openai_api_key == "SUA_CHAVE_API_AQUI": # Verifica a chave OpenAI primeiro
        return jsonify({"status": "error", "message": "OPENAI_API_KEY não configurada."}), 503
    elif not llm: # Se a chave está lá mas o LLM não carregou
         return jsonify({"status": "error", "message": "LLM não inicializado, verifique a OPENAI_API_KEY e logs."}), 503
    else: # Caso genérico do agente não estar pronto
        return jsonify({"status": "error", "message": "Lead Agent não inicializado, mas LLM parece estar configurado. Verifique logs."}), 503

# Opcional: endpoint para ver o histórico da memória (para debugging)
@app.route('/memory/user_lead', methods=['GET'])
def get_user_lead_memory():
    if not user_lead_memory:
        return jsonify({"error": "User_lead_memory não disponível."}), 503 # Service Unavailable

    try:
        history = user_lead_memory.load_memory_variables({})
        return jsonify(history)
    except Exception as e:
        print(f"Erro ao carregar user_lead_memory: {e}")
        return jsonify({"error": f"Erro ao carregar user_lead_memory: {str(e)}"}), 500


@app.route('/memory/lead_team', methods=['GET'])
def get_lead_team_memory():
    if not lead_team_memory:
        return jsonify({"error": "Lead_team_memory não disponível."}), 503 # Service Unavailable

    try:
        history = lead_team_memory.load_memory_variables({})
        return jsonify(history)
    except Exception as e:
        print(f"Erro ao carregar lead_team_memory: {e}")
        return jsonify({"error": f"Erro ao carregar lead_team_memory: {str(e)}"}), 500

if __name__ == '__main__':
    # Lembrar o usuário de usar `flask run` ou um servidor WSGI em produção
    print("Iniciando servidor Flask de desenvolvimento.")
    print("Para produção, use um servidor WSGI como Gunicorn ou Waitress: `gunicorn -w 4 -b 0.0.0.0:8000 app.server:app`")
    print("Certifique-se de que a OPENAI_API_KEY (e LANGSMITH_API_KEY, se aplicável) estão configuradas no arquivo .env.")
    print("Acesse os endpoints em http://localhost:8000")
    print("Ex: POST http://localhost:8000/chat com JSON {'user_input': 'sua pergunta'}")
    print("     GET http://localhost:8000/health")
    print("     GET http://localhost:8000/memory/user_lead")
    print("     GET http://localhost:8000/memory/lead_team")
    app.run(host='0.0.0.0', port=8000, debug=False) # debug=False por padrão, True pode causar recarregamento duplo e executar app.main duas vezes.
                                                  # Para dev, `flask run --debug` é melhor.
                                                  # Se debug=True aqui, pode haver prints duplicados de app.main.
