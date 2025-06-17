# tests/test_api.py
import unittest
import json
from unittest.mock import patch, MagicMock, ANY # ANY é útil para argumentos que não queremos especificar
import requests # Importar requests para poder mockar requests.exceptions.Timeout

# Importar o app Flask de app.server
try:
    from app.server import app as flask_app # Renomear para evitar conflito
except ImportError:
    print("Falha ao importar flask_app de app.server em test_api.py.")
    flask_app = None

class TestAPIEndpoints(unittest.TestCase):

    def setUp(self):
        if not flask_app:
            self.skipTest("Aplicação Flask não importada. Pulando testes de API.")

        flask_app.config['TESTING'] = True
        self.client = flask_app.test_client()

        # Mock para o lead_agent_executor em app.server, para isolar os testes da API
        self.mock_agent_executor_patcher = patch('app.server.lead_agent_executor')
        self.mock_agent_executor = self.mock_agent_executor_patcher.start()
        # Configurar um retorno padrão para o mock do agente
        self.mock_agent_executor.invoke.return_value = {"output": "Resposta mockada do agente"}

        # Mock para o llm e openai_api_key em app.server para o /health check e outros
        # Isso garante que o servidor pense que o LLM está pronto.
        self.mock_llm_patcher = patch('app.server.llm', MagicMock())
        self.mock_llm_in_server = self.mock_llm_patcher.start()

        self.mock_openai_key_patcher = patch('app.server.openai_api_key', "fake_openai_key_for_testing")
        self.mock_openai_key_in_server = self.mock_openai_key_patcher.start()

        # Mock para as memórias, para evitar erros se forem None durante os testes de outros endpoints
        self.mock_user_memory_patcher = patch('app.server.user_lead_memory', MagicMock())
        self.mock_user_memory_in_server = self.mock_user_memory_patcher.start()
        self.mock_user_memory_in_server.load_memory_variables.return_value = {"history": "mock user history"}

        self.mock_team_memory_patcher = patch('app.server.lead_team_memory', MagicMock())
        self.mock_team_memory_in_server = self.mock_team_memory_patcher.start()
        self.mock_team_memory_in_server.load_memory_variables.return_value = {"history": "mock team history"}


    def tearDown(self):
        self.mock_agent_executor_patcher.stop()
        self.mock_llm_patcher.stop()
        self.mock_openai_key_patcher.stop()
        self.mock_user_memory_patcher.stop()
        self.mock_team_memory_patcher.stop()

    # Testes básicos (re-adicionados/verificados)
    def test_health_endpoint_ok(self):
        # Com os mocks em setUp, lead_agent_executor e llm são MagicMock, e openai_api_key é uma string.
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertEqual(json_data['status'], 'ok')

    def test_health_endpoint_no_api_key(self):
        with patch('app.server.openai_api_key', None): # Sobrescreve o mock do setUp para este teste
            response = self.client.get('/health')
            self.assertEqual(response.status_code, 503)
            json_data = response.get_json()
            self.assertIn("OPENAI_API_KEY não configurada", json_data['message'])

    def test_chat_endpoint_no_agent_initialized(self):
        # Parar o patcher do executor para este teste específico para simular None
        self.mock_agent_executor_patcher.stop()
        with patch('app.server.lead_agent_executor', None):
             payload = {"user_input": "Olá"}
             response = self.client.post('/chat', json=payload)
             self.assertEqual(response.status_code, 503)
        self.mock_agent_executor_patcher.start() # Reinicia para outros testes

    def test_chat_endpoint_invalid_input(self):
        payload = {"wrong_key": "Olá"}
        response = self.client.post('/chat', json=payload)
        self.assertEqual(response.status_code, 400)
        json_data = response.get_json()
        self.assertIn("'user_input' é esperado", json_data['error'])

    # Testes para n8n
    @patch('app.server.notify_n8n') # Mockar a função notify_n8n diretamente DENTRO de app.server
    def test_chat_endpoint_calls_n8n_when_url_configured(self, mock_notify_n8n_func_in_server):
        # Simular que N8N_WEBHOOK_URL está configurada em app.server
        with patch('app.server.N8N_WEBHOOK_URL', 'http://fake-n8n-webhook.com/test'):
            payload = {"user_input": "Olá n8n test", "user_id": "test_user_n8n"}
            agent_response_text = "Resposta do agente para o teste n8n"
            # Configurar o mock_agent_executor (que já está mockado no setUp)
            self.mock_agent_executor.invoke.return_value = {"output": agent_response_text}

            response = self.client.post('/chat', json=payload)

            self.assertEqual(response.status_code, 200)
            # Verificar se notify_n8n foi chamado com os argumentos corretos
            mock_notify_n8n_func_in_server.assert_called_once_with(
                user_query=payload['user_input'],
                agent_answer=agent_response_text,
                user_identifier=payload['user_id']
            )

    @patch('app.server.notify_n8n')
    def test_chat_endpoint_does_not_call_n8n_when_url_not_configured(self, mock_notify_n8n_func_in_server):
        # Simular que N8N_WEBHOOK_URL NÃO está configurada (é None) em app.server
        with patch('app.server.N8N_WEBHOOK_URL', None):
            payload = {"user_input": "Olá sem n8n"}
            self.mock_agent_executor.invoke.return_value = {"output": "Resposta sem n8n"}

            response = self.client.post('/chat', json=payload)

            self.assertEqual(response.status_code, 200)
            # Verificar que notify_n8n NÃO foi chamado
            mock_notify_n8n_func_in_server.assert_not_called()

    # Teste para a função notify_n8n em si (mockando requests.post)
    @patch('app.server.requests.post') # Mockar requests.post usado por notify_n8n
    def test_notify_n8n_function_makes_correct_post_request(self, mock_requests_post_in_server):
        # Configurar um mock de resposta para requests.post
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None # Simula resposta HTTP OK
        mock_requests_post_in_server.return_value = mock_response

        from app.server import notify_n8n # Importar a função real que estamos testando

        test_url = 'http://dummy-n8n-url.com/webhook'
        user_q = "minha pergunta para n8n"
        agent_a = "resposta do agente para n8n"
        user_id = "usuarioteste_n8n_func"

        # Forçar a N8N_WEBHOOK_URL dentro do escopo de app.server para este teste específico
        with patch('app.server.N8N_WEBHOOK_URL', test_url):
            result = notify_n8n(user_query=user_q, agent_answer=agent_a, user_identifier=user_id)

        self.assertTrue(result) # A função deve retornar True em sucesso
        expected_payload = {
            "user": user_id,
            "message": user_q,
            "response": agent_a
        }
        mock_requests_post_in_server.assert_called_once_with(
            test_url,
            json=expected_payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )

    @patch('app.server.requests.post')
    def test_notify_n8n_function_handles_requests_exception(self, mock_requests_post_in_server):
        # Simular um erro na chamada requests.post (ex: Timeout)
        mock_requests_post_in_server.side_effect = requests.exceptions.Timeout("Simulated timeout")

        from app.server import notify_n8n # Importar a função real
        test_url = 'http://dummy-n8n-url-timeout.com/webhook'

        with patch('app.server.N8N_WEBHOOK_URL', test_url):
            # Mockar print para verificar se a mensagem de erro é logada
            with patch('builtins.print') as mock_builtin_print:
                result = notify_n8n(user_query="q_timeout", agent_answer="a_timeout", user_identifier="u_timeout")

        self.assertFalse(result) # Deve retornar False em caso de erro
        # Verificar se uma mensagem de erro de timeout foi impressa
        # ANY usado porque podem haver outras chamadas a print.
        mock_builtin_print.assert_any_call(f"Erro ao notificar n8n: Timeout para {test_url}")

    # Testes de memória (verificando se os mocks de setUp não quebraram)
    def test_get_user_lead_memory(self):
        response = self.client.get('/memory/user_lead')
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertEqual(json_data, {"history": "mock user history"})

    def test_get_lead_team_memory(self):
        response = self.client.get('/memory/lead_team')
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertEqual(json_data, {"history": "mock team history"})


if __name__ == '__main__':
    unittest.main()
