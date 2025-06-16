# tests/test_router.py
import unittest
from unittest.mock import patch, MagicMock

# Importar a função a ser testada e as ferramentas/agentes que ela usa
# Isso pode exigir ajustes dependendo de como as variáveis são expostas em app.main
# Para este teste, vamos assumir que podemos importar execute_router_chain e agent_tools
# Se app.main executa muita lógica na importação (como inicializar LLM),
# pode ser necessário refatorar app.main para que as funções sejam mais facilmente importáveis
# ou mockar mais coisas.

# Supondo que app.main pode ser importado sem efeitos colaterais problemáticos para teste,
# ou que os mocks cuidam disso.
# O ideal é que as variáveis OPENAI_API_KEY e LANGSMITH_API_KEY não estejam setadas no ambiente de teste
# para que `llm` e `llm_router_chain` em `app.main` não sejam inicializados com LLMs reais.
# Os prints de aviso em app.main sobre as chaves não configuradas são esperados durante os testes se as chaves não estiverem lá.

# Tentamos importar os componentes necessários. Se app.main.llm é None, os testes que
# mockam llm_router_chain ainda podem funcionar se llm_router_chain for o alvo direto do mock.
try:
    from app.main import execute_router_chain, agent_tools, llm_router_chain as main_llm_router_chain
    # ^ Renomeado para main_llm_router_chain para evitar conflito com o argumento do patch
except ImportError:
    print("Falha ao importar de app.main em test_router.py. Certifique-se que app.main está acessível.")
    # Definir fallbacks se a importação falhar, para que a classe de teste possa ser definida
    execute_router_chain = None
    agent_tools = []
    main_llm_router_chain = None


class TestRouterLogic(unittest.TestCase):

    def setUp(self):
        # Garante que os testes não dependam de um LLM real, mockando llm_router_chain globalmente em app.main
        # para a maioria dos testes, ou especificamente onde necessário.
        # Se 'app.main.llm' for None (porque a chave API não está setada),
        # então 'app.main.llm_router_chain' já será None.
        # O patch no nível do método é mais granular e preferível.
        pass

    @patch('app.main.llm_router_chain') # Mocka o router chain baseado em LLM DENTRO de app.main
    def test_execute_router_chain_directs_to_agent_a(self, mock_llm_router_in_main):
        if not execute_router_chain or not agent_tools: self.skipTest("Componentes de app.main não importados.")

        # Configura o mock para retornar uma decisão para o Agente A
        mock_llm_router_in_main.invoke.return_value = {"destination": "AgentA"}

        test_input = "Preciso de X"
        # Assumindo que agent_tools é importado corretamente e tem pelo menos um agente.
        expected_output_from_agent_a = agent_tools[0].func(test_input) # AgentA é o primeiro na lista

        actual_output = execute_router_chain(test_input)

        mock_llm_router_in_main.invoke.assert_called_once_with({"input": test_input})
        self.assertEqual(actual_output, expected_output_from_agent_a)

    @patch('app.main.llm_router_chain')
    def test_execute_router_chain_directs_to_agent_b(self, mock_llm_router_in_main):
        if not execute_router_chain or not agent_tools or len(agent_tools) < 2: self.skipTest("Componentes de app.main ou agentes insuficientes não importados.")

        mock_llm_router_in_main.invoke.return_value = {"destination": "AgentB"}
        test_input = "Quero saber sobre Y"
        expected_output_from_agent_b = agent_tools[1].func(test_input) # AgentB é o segundo

        actual_output = execute_router_chain(test_input)
        mock_llm_router_in_main.invoke.assert_called_once_with({"input": test_input})
        self.assertEqual(actual_output, expected_output_from_agent_b)

    @patch('app.main.llm_router_chain')
    def test_execute_router_chain_fallback_on_no_destination(self, mock_llm_router_in_main):
        if not execute_router_chain or not agent_tools: self.skipTest("Componentes de app.main não importados.")

        mock_llm_router_in_main.invoke.return_value = {} # Router não retorna destino
        test_input = "Pergunta genérica"
        # Espera-se fallback para o primeiro agente (AgentA)
        # A mensagem de fallback é construída em execute_router_chain
        # expected_fallback_output = f"(Fallback to {agent_tools[0].name}) {agent_tools[0].func(test_input)}"
        # Acessando a mensagem diretamente da função do agente, e o wrapper de fallback é adicionado por execute_router_chain
        actual_output = execute_router_chain(test_input) # Isso vai chamar a lógica de fallback

        # Verifica se a saída contém o nome do agente de fallback e a saída da função do agente
        self.assertIn(f"(Fallback to {agent_tools[0].name}", actual_output)
        self.assertIn(agent_tools[0].func(test_input), actual_output)


    @patch('app.main.llm_router_chain')
    def test_execute_router_chain_fallback_on_agent_not_found(self, mock_llm_router_in_main):
        if not execute_router_chain or not agent_tools: self.skipTest("Componentes de app.main não importados.")

        mock_llm_router_in_main.invoke.return_value = {"destination": "AgentDesconhecido"}
        test_input = "Pergunta para agente que não existe"

        actual_output = execute_router_chain(test_input)

        self.assertIn(f"(Fallback to {agent_tools[0].name} due to not found)", actual_output)
        self.assertIn(agent_tools[0].func(test_input), actual_output)


    def test_router_without_llm_configured(self):
        if not execute_router_chain: self.skipTest("execute_router_chain não importado.")
        # Testar o comportamento se llm (e portanto llm_router_chain) não estiver configurado
        # Isso requer que possamos simular a ausência do llm_router_chain em app.main.
        # O patch('app.main.llm_router_chain', None) faz isso.
        with patch('app.main.llm_router_chain', None):
            response = execute_router_chain("qualquer coisa")
            self.assertEqual(response, "Router não configurado devido à ausência da chave OpenAI.")

if __name__ == '__main__':
    unittest.main()
