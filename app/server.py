# app/server.py
from flask import Flask, request, jsonify
import os
import requests # Importar a biblioteca requests
import json # Para o caso de precisarmos formatar o payload

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

# Carregar a URL do Webhook n8n do .env
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")

if not N8N_WEBHOOK_URL or N8N_WEBHOOK_URL == "SUA_URL_WEBHOOK_N8N_AQUI":
    print("AVISO: N8N_WEBHOOK_URL não está configurada no arquivo .env ou é o placeholder. A integração com n8n estará desabilitada.")
    N8N_WEBHOOK_URL = None # Garante que não tentaremos usá-la se for o placeholder ou não existir

# Verificar se as chaves de API da OpenAI estão configuradas
if not openai_api_key or openai_api_key == "SUA_CHAVE_API_AQUI":
    print("*********************************************************************************")
    print("AVISO URGENTE: OPENAI_API_KEY não está configurada no arquivo .env!")
    print("O servidor Flask iniciará, mas o endpoint /chat não funcionará corretamente.")
    print("Por favor, configure a OPENAI_API_KEY e reinicie o servidor.")
    print("*********************************************************************************")
elif not llm: # Se a chave existe mas o llm não inicializou por outra razão
    print("*********************************************************************************")
    print("AVISO: O LLM não foi inicializado, mesmo com uma OPENAI_API_KEY aparente.")
    print("O endpoint /chat provavelmente não funcionará como esperado.")
    print("*********************************************************************************")


def notify_n8n(user_query: str, agent_answer: str, user_identifier: str = "Usuário Anônimo"):
    """
    Envia uma notificação para o webhook do n8n.
    """
    if not N8N_WEBHOOK_URL:
        print("Chamada para n8n não realizada: N8N_WEBHOOK_URL não configurada.")
        return False

    payload = {
        "user": user_identifier,
        "message": user_query,
        "response": agent_answer,
        # "userEmail": "email_do_usuario@exemplo.com" # Adicionar se disponível
    }

    headers = {"Content-Type": "application/json"}

    try:
        print(f"Enviando para n8n webhook ({N8N_WEBHOOK_URL}) payload: {json.dumps(payload)}")
        response = requests.post(N8N_WEBHOOK_URL, json=payload, headers=headers, timeout=10) # Timeout de 10 segundos
        response.raise_for_status() # Levanta um erro para status HTTP 4xx/5xx
        print(f"Notificação para n8n enviada com sucesso. Status: {response.status_code}")
        return True
    except requests.exceptions.Timeout:
        print(f"Erro ao notificar n8n: Timeout para {N8N_WEBHOOK_URL}")
    except requests.exceptions.ConnectionError:
        print(f"Erro ao notificar n8n: Erro de conexão com {N8N_WEBHOOK_URL}")
    except requests.exceptions.HTTPError as e:
        print(f"Erro ao notificar n8n: Erro HTTP {e.response.status_code} para {N8N_WEBHOOK_URL}. Resposta: {e.response.text}")
    except requests.exceptions.RequestException as e: # Captura genérica para outros erros de requests
        print(f"Erro ao notificar n8n: {e}")
    except Exception as e: # Captura qualquer outra exceção inesperada
        print(f"Erro inesperado ao notificar n8n: {e}")

    return False

@app.route('/chat', methods=['POST'])
def chat():
    if not lead_agent_executor:
        return jsonify({
            "error": "Lead Agent não está inicializado. Verifique a configuração da OPENAI_API_KEY no arquivo .env e reinicie o servidor."
        }), 503

    data = request.get_json()
    if not data or 'user_input' not in data:
        return jsonify({"error": "Entrada inválida. 'user_input' é esperado no JSON."}), 400

    user_input = data['user_input']
    user_id_for_n8n = data.get('user_id', "Usuário Anônimo via API")

    try:
        print(f"Recebido no /chat: '{user_input}' de '{user_id_for_n8n}'")
        response_agent = lead_agent_executor.invoke({"input": user_input})
        agent_output = response_agent.get('output', "Nenhuma saída do agente.")
        print(f"Resposta do agente para '{user_input}': '{agent_output}'")

        # Após obter a resposta do agente, notificar o n8n
        if N8N_WEBHOOK_URL:
            print(f"Preparando para notificar n8n sobre a interação com '{user_id_for_n8n}'.")
            notify_n8n(user_query=user_input, agent_answer=agent_output, user_identifier=user_id_for_n8n)
        else:
            print("Skipping n8n notification: N8N_WEBHOOK_URL não está configurada.")

        return jsonify({"response": agent_output})

    except Exception as e:
        print(f"Erro crítico durante a execução do agente ou chamada n8n: {e}")
        # Considerar logar o traceback completo aqui para debugging em produção
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Erro interno ao processar sua requisição: {str(e)}"}), 500

# ... (endpoints /health, /memory/* existentes - sem alterações) ...
@app.route('/health', methods=['GET'])
def health_check():
    if lead_agent_executor and llm:
        return jsonify({"status": "ok", "message": "Servidor Flask e Lead Agent estão operacionais."}), 200
    elif not openai_api_key or openai_api_key == "SUA_CHAVE_API_AQUI":
        return jsonify({"status": "error", "message": "OPENAI_API_KEY não configurada."}), 503
    elif not llm:
         return jsonify({"status": "error", "message": "LLM não inicializado, verifique a OPENAI_API_KEY e logs."}), 503
    else:
        return jsonify({"status": "error", "message": "Lead Agent não inicializado, mas LLM parece estar configurado. Verifique logs."}), 503

@app.route('/memory/user_lead', methods=['GET'])
def get_user_lead_memory():
    if not user_lead_memory:
        return jsonify({"error": "User_lead_memory não disponível."}), 503

    try:
        history = user_lead_memory.load_memory_variables({})
        return jsonify(history)
    except Exception as e:
        print(f"Erro ao carregar user_lead_memory: {e}")
        return jsonify({"error": f"Erro ao carregar user_lead_memory: {str(e)}"}), 500


@app.route('/memory/lead_team', methods=['GET'])
def get_lead_team_memory():
    if not lead_team_memory:
        return jsonify({"error": "Lead_team_memory não disponível."}), 503

    try:
        history = lead_team_memory.load_memory_variables({})
        return jsonify(history)
    except Exception as e:
        print(f"Erro ao carregar lead_team_memory: {e}")
        return jsonify({"error": f"Erro ao carregar lead_team_memory: {str(e)}"}), 500

if __name__ == '__main__':
    print("Iniciando servidor Flask de desenvolvimento.")
    print("Para produção, use um servidor WSGI como Gunicorn ou Waitress: `gunicorn -w 4 -b 0.0.0.0:8000 app.server:app`")
    print("Certifique-se de que a OPENAI_API_KEY (e LANGSMITH_API_KEY, se aplicável) estão configuradas no arquivo .env.")

    if not N8N_WEBHOOK_URL: # Adicionado print sobre n8n no startup
        print("Lembrete: N8N_WEBHOOK_URL não está configurada no .env. Integração com n8n desabilitada.")
    else:
        print(f"Integração com n8n habilitada. Webhook URL: {N8N_WEBHOOK_URL}")

    print("Acesse os endpoints em http://localhost:8000")
    print("Ex: POST http://localhost:8000/chat com JSON {'user_input': 'sua pergunta', 'user_id': 'seu_id_opcional'}")
    print("     GET http://localhost:8000/health")
    print("     GET http://localhost:8000/memory/user_lead")
    print("     GET http://localhost:8000/memory/lead_team")

    # debug=True é útil para desenvolvimento, mas pode causar a execução de app.main (e seus prints) duas vezes.
    # Para produção ou para evitar prints duplicados de app.main, defina como False e use `flask run --debug`.
    app.run(host='0.0.0.0', port=8000, debug=False)
