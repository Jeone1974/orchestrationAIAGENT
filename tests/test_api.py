# tests/test_api.py
import unittest
import json
from unittest.mock import patch, MagicMock

# Importar o app Flask de app.server
# É importante que a definição de `app = Flask(__name__)` em server.py seja no escopo global.
# E que `app.run()` esteja dentro de `if __name__ == '__main__':`.
try:
    from app.server import app as flask_app # Renomear para evitar conflito
except ImportError:
    print("Falha ao importar flask_app de app.server em test_api.py.")
    flask_app = None # Define para None para que os testes possam ser pulados se a importação falhar

class TestAPIEndpoints(unittest.TestCase):

    def setUp(self):
        if not flask_app:
            self.skipTest("Aplicação Flask não importada. Pulando testes de API.")
        # Configura um cliente de teste do Flask
        flask_app.config['TESTING'] = True
        # Outras configurações que podem ser úteis:
        # flask_app.config['DEBUG'] = False
        # flask_app.config['WTF_CSRF_ENABLED'] = False # Se estiver usando Flask-WTF
        self.client = flask_app.test_client()

    # Testes para /health
    def test_health_endpoint_ok(self):
        # Mock para simular que tudo está OK
        with patch('app.server.lead_agent_executor', MagicMock()), \
             patch('app.server.llm', MagicMock()), \
             patch('app.server.openai_api_key', "fake_key_for_test"): # Simula chave presente
            response = self.client.get('/health')
            self.assertEqual(response.status_code, 200)
            json_data = response.get_json()
            self.assertEqual(json_data['status'], 'ok')

    def test_health_endpoint_no_api_key(self):
        # Mock para simular ausência de OPENAI_API_KEY
        with patch('app.server.openai_api_key', None):
            response = self.client.get('/health')
            self.assertEqual(response.status_code, 503)
            json_data = response.get_json()
            self.assertEqual(json_data['message'], 'OPENAI_API_KEY não configurada.')

    def test_health_endpoint_llm_not_initialized(self):
        # Mock para simular que OPENAI_API_KEY existe, mas LLM não inicializou
        with patch('app.server.openai_api_key', "fake_key_for_test"), \
             patch('app.server.llm', None):
            response = self.client.get('/health')
            self.assertEqual(response.status_code, 503)
            json_data = response.get_json()
            self.assertEqual(json_data['message'], 'LLM não inicializado, verifique a OPENAI_API_KEY e logs.')

    def test_health_endpoint_agent_not_initialized(self):
        # Mock para simular que LLM existe, mas agente não inicializou
        with patch('app.server.openai_api_key', "fake_key_for_test"), \
             patch('app.server.llm', MagicMock()), \
             patch('app.server.lead_agent_executor', None):
            response = self.client.get('/health')
            self.assertEqual(response.status_code, 503) # Ajustado conforme a lógica em server.py
            json_data = response.get_json()
            self.assertEqual(json_data['message'], 'Lead Agent não inicializado, mas LLM parece estar configurado. Verifique logs.')


    # Testes para /chat
    @patch('app.server.lead_agent_executor') # Mocka o executor do agente em app.server
    def test_chat_endpoint_success(self, mock_lead_agent_executor_in_server):
        # Configura o mock para retornar uma resposta esperada
        mock_response = {"output": "Resposta mockada do agente"}
        mock_lead_agent_executor_in_server.invoke.return_value = mock_response

        payload = {"user_input": "Olá agente"}
        response = self.client.post('/chat', json=payload)

        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertEqual(json_data['response'], mock_response['output'])
        mock_lead_agent_executor_in_server.invoke.assert_called_once_with({"input": "Olá agente"})

    def test_chat_endpoint_no_agent_initialized(self):
        # Testa o endpoint /chat quando o agente não está inicializado (mockando-o como None)
        with patch('app.server.lead_agent_executor', None):
            payload = {"user_input": "Olá"}
            response = self.client.post('/chat', json=payload)
            self.assertEqual(response.status_code, 503) # Service Unavailable
            json_data = response.get_json()
            self.assertIn("Lead Agent não está inicializado", json_data['error'])

    def test_chat_endpoint_invalid_input_missing_key(self):
        # Testa com payload JSON inválido (chave errada)
        payload = {"wrong_key": "Olá"}
        response = self.client.post('/chat', json=payload)
        self.assertEqual(response.status_code, 400) # Bad Request
        json_data = response.get_json()
        self.assertIn("'user_input' é esperado", json_data['error'])

    def test_chat_endpoint_invalid_input_not_json(self):
        # Testa com payload que não é JSON
        response = self.client.post('/chat', data="não é json")
        self.assertEqual(response.status_code, 400) # Bad Request - Flask trata isso antes da nossa lógica
        # A resposta de erro exata pode variar dependendo da configuração do Flask
        # mas geralmente será um erro de "Failed to decode JSON" ou similar.

    # Testes para os endpoints de memória
    @patch('app.server.user_lead_memory') # Mocka a memória em app.server
    def test_get_user_lead_memory_success(self, mock_user_memory_in_server):
        mock_user_memory_in_server.load_memory_variables.return_value = {"chat_history": "Histórico mockado user_lead"}
        response = self.client.get('/memory/user_lead')
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertEqual(json_data, {"chat_history": "Histórico mockado user_lead"})
        mock_user_memory_in_server.load_memory_variables.assert_called_once_with({})

    @patch('app.server.lead_team_memory') # Mocka a memória em app.server
    def test_get_lead_team_memory_success(self, mock_team_memory_in_server):
        mock_team_memory_in_server.load_memory_variables.return_value = {"team_interaction_history": "Histórico mockado lead_team"}
        response = self.client.get('/memory/lead_team')
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertEqual(json_data, {"team_interaction_history": "Histórico mockado lead_team"})
        mock_team_memory_in_server.load_memory_variables.assert_called_once_with({})

    def test_get_user_lead_memory_not_available(self):
        with patch('app.server.user_lead_memory', None):
            response = self.client.get('/memory/user_lead')
            self.assertEqual(response.status_code, 503)
            json_data = response.get_json()
            self.assertIn("User_lead_memory não disponível", json_data['error'])

    def test_get_lead_team_memory_not_available(self):
        with patch('app.server.lead_team_memory', None):
            response = self.client.get('/memory/lead_team')
            self.assertEqual(response.status_code, 503)
            json_data = response.get_json()
            self.assertIn("Lead_team_memory não disponível", json_data['error'])


if __name__ == '__main__':
    unittest.main()
