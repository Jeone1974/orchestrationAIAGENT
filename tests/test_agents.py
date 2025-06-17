# tests/test_agents.py
import unittest
from unittest.mock import patch, MagicMock

# Importar a função do Agente A
from app.agents.agent_a import agent_a_func
# Importar as ferramentas reais para referência, se necessário para construir a resposta esperada
# ou para verificar se o agente as usaria corretamente (embora aqui a gente mocke a decisão do LLM).
from app.agents.agent_a_tools import busca_info_x_func, calculadora_trivial_func

# Testes para Agentes B e C (podem ser mantidos ou movidos para outros arquivos)
from app.agents.agent_b import agent_b_func
from app.agents.agent_c import agent_c_func

class TestSpecializedAgents(unittest.TestCase):

    def setUp(self):
        # Este método é chamado antes de cada teste.
        # Mock para o _llm_instance DENTRO do módulo app.agents.agent_a
        # Este é o LLM que o AgentExecutor do Agente A usará.
        self.mock_llm_patcher = patch('app.agents.agent_a._llm_instance')
        self.mock_llm_agent_a = self.mock_llm_patcher.start()

        # É crucial resetar o executor cacheado do Agente A para que ele
        # seja recriado com o LLM mockado desta instância de teste.
        # Acessar _agent_a_executor diretamente é um pouco hacky, mas necessário pela forma como agent_a.py foi escrito.
        # Se o módulo não foi importado ainda, isso não fará nada, o que é bom.
        try:
            agent_a_module = __import__('sys').modules['app.agents.agent_a']
            agent_a_module._agent_a_executor = None  # Força a recriação do executor no próximo agent_a_func()
        except KeyError:
            # Módulo ainda não importado, o executor será None de qualquer forma.
            pass

        # Configurar um comportamento padrão para o LLM mockado, se necessário.
        # Por exemplo, se algum teste não especificar side_effect.
        # self.mock_llm_agent_a.invoke.return_value = "Final Answer: Resposta padrão do LLM mockado para Agente A."
        # No entanto, para AgentExecutor, o LLM é chamado com uma string (o prompt), não com invoke.
        # E ele espera uma string como resposta, não um objeto AIMessage, a menos que seja um ChatModel.
        # O initialize_agent prepara o prompt para o LLM.
        # A resposta do LLM (mockado) deve ser uma string que o parser do agente possa entender.
        # (e.g. contendo "Action:", "Action Input:", ou "Final Answer:")

        # Para o `initialize_agent` com `AgentType.ZERO_SHOT_REACT_DESCRIPTION`,
        # o `llm` (não `ChatOpenAI`) é chamado diretamente (não com `invoke`).
        # Se `_llm_instance` for um `ChatOpenAI`, então `invoke` seria usado pelo `LLMChain` dentro do agente.
        # O `_llm_instance` em `agent_a.py` é um `ChatOpenAI`, então `invoke` é o correto a mockar.
        self.mock_llm_agent_a.invoke.return_value = MagicMock(content="Final Answer: Não sei como processar isso sem uma Action específica.")


    def tearDown(self):
        # Para o patcher iniciado em setUp.
        self.mock_llm_patcher.stop()
        # Opcional: Limpar o cache do executor novamente após os testes.
        try:
            agent_a_module = __import__('sys').modules['app.agents.agent_a']
            agent_a_module._agent_a_executor = None
        except KeyError:
            pass

    def test_agent_a_uses_busca_info_x(self):
        user_input = "Qual a origem de x?"
        expected_tool_output = busca_info_x_func(user_input) # "X foi desenvolvido inicialmente..."

        # Configurar o mock_llm_agent_a (que é o LLM dentro do executor do Agente A)
        # para simular a cadeia de pensamento do agente.
        # O AgentExecutor chamará llm.invoke(prompt_com_input_e_scratchpad)
        # 1. LLM decide usar a ferramenta: retorna string com Action e Action Input
        # 2. AgentExecutor parseia, executa a ferramenta (BuscaInformacaoDominioX), obtém Observation
        # 3. AgentExecutor chama llm.invoke(prompt_com_input_e_scratchpad_atualizado_com_Observation)
        # 4. LLM decide que tem a resposta final: retorna string com Final Answer

        # Criamos um mock para a instância ChatOpenAI. A sua resposta deve ter um atributo 'content'.
        mock_llm_response_action = MagicMock()
        mock_llm_response_action.content = f"Action: BuscaInformacaoDominioX\nAction Input: {user_input}"

        mock_llm_response_final_answer = MagicMock()
        mock_llm_response_final_answer.content = f"Thought: A ferramenta BuscaInformacaoDominioX retornou a informação necessária. Vou fornecê-la.\nFinal Answer: {expected_tool_output}"

        self.mock_llm_agent_a.invoke.side_effect = [
            mock_llm_response_action,
            mock_llm_response_final_answer
        ]

        response = agent_a_func(user_input)
        self.assertIn(expected_tool_output, response, "A resposta final do agente deve conter a saída da ferramenta.")
        # Verificar chamadas ao LLM mockado
        self.assertEqual(self.mock_llm_agent_a.invoke.call_count, 2)


    def test_agent_a_uses_calculadora_trivial(self):
        user_input = "Quanto é 15+7?"
        expression = "15+7" # O que o LLM idealmente extrairia
        expected_tool_output = calculadora_trivial_func(expression) # "Calculadora Trivial: O resultado de 15+7 é 22."

        mock_llm_response_action = MagicMock()
        mock_llm_response_action.content = f"Action: CalculadoraTrivial\nAction Input: {expression}"

        mock_llm_response_final_answer = MagicMock()
        mock_llm_response_final_answer.content = f"Thought: A calculadora processou a expressão. Vou retornar o resultado.\nFinal Answer: {expected_tool_output}"

        self.mock_llm_agent_a.invoke.side_effect = [
            mock_llm_response_action,
            mock_llm_response_final_answer
        ]

        response = agent_a_func(user_input)
        self.assertIn(expected_tool_output, response)
        self.assertEqual(self.mock_llm_agent_a.invoke.call_count, 2)


    def test_agent_a_no_tool_needed_direct_answer(self):
        user_input = "Olá Agente A, tudo bem?"
        # O LLM (mockado) do Agente A decide responder diretamente.
        expected_final_answer = "Olá! Sou o Agente A. Tudo bem por aqui, pronto para ajudar com o domínio X e cálculos simples."

        mock_llm_response_final = MagicMock()
        mock_llm_response_final.content = f"Thought: O usuário está apenas cumprimentando e perguntando se estou bem. Vou responder diretamente.\nFinal Answer: {expected_final_answer}"

        self.mock_llm_agent_a.invoke.side_effect = [mock_llm_response_final]

        response = agent_a_func(user_input)
        self.assertEqual(response, expected_final_answer)
        self.mock_llm_agent_a.invoke.assert_called_once()


    def test_agent_a_handles_tool_not_existing_in_its_repertoire(self):
        # Este teste simula o LLM tentando usar uma ferramenta não fornecida ao Agente A.
        user_input = "Use a ferramenta 'SuperPlotadorGrafico' para visualizar meus dados."

        # O LLM do Agente A (mockado) tenta usar uma ferramenta que não está na lista de `tools_for_agent_a`
        mock_llm_response_action = MagicMock()
        mock_llm_response_action.content = "Action: SuperPlotadorGrafico\nAction Input: meus dados"

        # O AgentExecutor, ao não encontrar "SuperPlotadorGrafico", passará uma observação de erro ao LLM.
        # O LLM (mockado) então deve reagir a essa observação.
        # A observação real seria algo como: "Invalid or non-existent tool: SuperPlotadorGrafico"
        mock_llm_response_after_tool_error = MagicMock()
        expected_final_answer = "Desculpe, eu não tenho uma ferramenta chamada 'SuperPlotadorGrafico'."
        mock_llm_response_after_tool_error.content = f"Thought: Eu tentei usar 'SuperPlotadorGrafico', mas ela não existe ou é inválida. Preciso informar ao usuário.\nFinal Answer: {expected_final_answer}"

        self.mock_llm_agent_a.invoke.side_effect = [
            mock_llm_response_action,
            mock_llm_response_after_tool_error
        ]

        response = agent_a_func(user_input)
        self.assertEqual(response, expected_final_answer)
        self.assertEqual(self.mock_llm_agent_a.invoke.call_count, 2)


    # Testes para Agente B e C (mantidos do original)
    def test_agent_b_func(self):
        input_str = "teste para B"
        expected_output = f"[Agent B] Resposta especializada para: {input_str}"
        self.assertEqual(agent_b_func(input_str), expected_output)

    def test_agent_c_func(self):
        input_str = "teste para C"
        expected_output = f"[Agent C] Lidando com o input: {input_str}"
        self.assertEqual(agent_c_func(input_str), expected_output)

if __name__ == '__main__':
    # Para executar os testes, é melhor usar `python -m unittest tests.test_agents`
    # ou `python -m unittest discover tests` da raiz do projeto.
    # Isso garante que os imports relativos e o patching funcionem como esperado.
    unittest.main()
