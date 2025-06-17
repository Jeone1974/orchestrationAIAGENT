# app/agents/agent_a.py
from langchain.agents import initialize_agent, AgentType # Tool não é mais necessária aqui diretamente

_llm_instance = None
try:
    from app.main import llm
    if llm: # llm pode ser None se a chave API não estiver configurada em app.main
        _llm_instance = llm
        print("INFO (agent_a.py): LLM de app.main importado com sucesso.")
    else:
        print("AVISO (agent_a.py): LLM de app.main está None (não configurado ou chave API ausente).")
except ImportError:
    print("ERRO (agent_a.py): Não foi possível importar llm de app.main. Verifique o PYTHONPATH e a estrutura do projeto.")
except Exception as e:
    print(f"ERRO (agent_a.py): Exceção não esperada ao importar llm de app.main: {e}")

# Importar as ferramentas específicas do Agente A
try:
    from .agent_a_tools import tools_for_agent_a
    print("INFO (agent_a.py): 'tools_for_agent_a' importadas com sucesso de .agent_a_tools.py.")
except ImportError as e:
    print(f"ERRO (agent_a.py): Não foi possível importar 'tools_for_agent_a' de .agent_a_tools.py: {e}.")
    # Fallback para uma lista vazia ou placeholder se a importação falhar, para evitar crash total.
    from langchain.agents import Tool # Importar Tool apenas para o fallback
    tools_for_agent_a = [
        Tool(
            name="FallbackToolAgenteA",
            func=lambda x: "Erro: Ferramentas específicas do Agente A não puderam ser carregadas devido a erro de importação.",
            description="Ferramenta de fallback indicando falha no carregamento das ferramentas reais do Agente A."
        )
    ]
    print("AVISO (agent_a.py): Usando ferramentas de fallback para Agente A.")


_agent_a_executor = None # Cache para o executor do Agente A

def create_agent_a_executor():
    """
    Cria e retorna um AgentExecutor para o Agente A.
    Este executor terá suas próprias ferramentas (de agent_a_tools.py) e usará o LLM global.
    Retorna None se o LLM não estiver disponível.
    O executor é recriado se as ferramentas mudarem (embora neste setup as ferramentas sejam fixas após a importação).
    """
    global _agent_a_executor

    if not _llm_instance:
        print("AVISO (create_agent_a_executor): LLM não está disponível. Não é possível criar AgentExecutor para Agente A.")
        return None

    # A lógica de cache simples (recriar apenas se None) é mantida.
    # Se as tools_for_agent_a pudessem mudar dinamicamente em tempo de execução (não é o caso aqui),
    # seria necessário invalidar o cache _agent_a_executor.
    if _agent_a_executor is None:
        print("INFO (create_agent_a_executor): Criando uma nova instância do AgentExecutor para Agente A com ferramentas de agent_a_tools.py.")
        current_tools = tools_for_agent_a # Usar as ferramentas importadas de agent_a_tools.py

        try:
            _agent_a_executor = initialize_agent(
                tools=current_tools, # <<< AQUI ESTÁ A MUDANÇA PRINCIPAL
                llm=_llm_instance,
                agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                verbose=True,
                handle_parsing_errors=True, # Ajuda com LLMs que podem não seguir o formato de saída perfeitamente
            )
            print("INFO (create_agent_a_executor): AgentExecutor para Agente A foi criado/atualizado com ferramentas de agent_a_tools.py.")
        except Exception as e:
            print(f"ERRO (create_agent_a_executor): Falha ao criar AgentExecutor para Agente A com ferramentas de agent_a_tools.py: {e}")
            _agent_a_executor = None

    return _agent_a_executor

def agent_a_func(input_str: str) -> str:
    """
    Função principal para o Agente A.
    Obtém o AgentExecutor do Agente A (que agora usa ferramentas de agent_a_tools.py) e o invoca.
    """
    if not _llm_instance:
        return "[Agent A] LLM global não configurado. Agente A não pode processar a requisição."

    agent_executor_instance = create_agent_a_executor()
    if not agent_executor_instance:
        # Mensagem de erro já foi impressa por create_agent_a_executor
        return "[Agent A] Executor interno não pôde ser criado. Verifique logs para detalhes (LLM, ferramentas)."

    print(f"INFO [Agent A Executor] Recebendo input: '{input_str}' para usar suas ferramentas especializadas.")
    try:
        response = agent_executor_instance.invoke({"input": input_str})
        output = response.get("output", f"Agente A (Executor) não produziu uma chave 'output' padrão. Resposta completa: {response}")
        print(f"INFO [Agent A Executor] Produziu output: '{output}'")
        return output
    except Exception as e:
        print(f"ERRO [Agent A Executor] durante a execução interna com suas ferramentas: {e}")
        return f"[Agent A] Erro durante o processamento interno com ferramentas especializadas: {str(e)}"

# Código de teste local (opcional)
# if __name__ == '__main__':
#     print("--- Iniciando teste local de agent_a.py (com ferramentas de agent_a_tools.py) ---")
#     if not _llm_instance:
#         print("AVISO (teste local agent_a.py): LLM global de app.main não carregado.")
#         print("Mockando _llm_instance com FakeListLLM para este teste.")
#         from langchain_community.llms.fake import FakeListLLM # Atualizado para langchain_community

#         # Simular o LLM usando a ferramenta BuscaInformacaoDominioX
#         responses_busca = [
#             "Action: BuscaInformacaoDominioX\nAction Input: origem de x", # LLM decide usar a ferramenta
#             "Observation: X foi desenvolvido inicialmente como um projeto de pesquisa em 2023.", # Resultado da ferramenta
#             "Thought: A informação foi encontrada. Posso responder agora.\nFinal Answer: A origem de X é que foi desenvolvido inicialmente como um projeto de pesquisa em 2023." # LLM formula a resposta final
#         ]
#         # Simular o LLM usando a ferramenta CalculadoraTrivial
#         responses_calculo = [
#             "Action: CalculadoraTrivial\nAction Input: 22+11",
#             "Observation: Calculadora Trivial: O resultado de 22+11 é 33.",
#             "Thought: O cálculo foi feito. Posso responder agora.\nFinal Answer: O resultado do cálculo 22+11 é 33."
#         ]
#         # Para testar diferentes cenários, você precisaria reatribuir _llm_instance ou ter um mock mais dinâmico
#         _llm_instance = FakeListLLM(responses=responses_busca) # Testando busca primeiro
#         print("INFO (teste local agent_a.py): _llm_instance mockado com FakeListLLM para BuscaInformacaoDominioX.")


#     print("\n--- Testando agent_a_func (com BuscaInformacaoDominioX) ---")
#     test_input_busca = "Qual a origem de x?"
#     print(f"Input para Agente A: '{test_input_busca}'")
#     output_busca = agent_a_func(test_input_busca)
#     print(f"\nOutput Final do Agente A (Busca): '{output_busca}'")

#     # Reconfigurar o mock para testar a calculadora
#     if isinstance(_llm_instance, FakeListLLM): # Apenas se for o nosso mock
#         _llm_instance.responses = responses_calculo
#         _agent_a_executor = None # Forçar recriação do executor com o novo LLM (se a lógica de cache do executor fosse baseada no LLM)
                                 # No entanto, create_agent_a_executor não recria se já existe e _llm_instance não mudou de ID.
                                 # Para FakeListLLM, mudar responses é suficiente se o mesmo objeto LLM for usado.
                                 # Mas para ser seguro, forçar a recriação do executor se o LLM mockado muda suas respostas esperadas.

#         # Para forçar a recriação do executor com as mesmas ferramentas mas um LLM (mock) com respostas diferentes:
#         # Precisamos garantir que create_agent_a_executor() seja chamado e initialize_agent() ocorra novamente
#         # se o comportamento do _llm_instance mudou. A forma mais simples é resetar _agent_a_executor.
#         _agent_a_executor = None
#         print("\nINFO (teste local agent_a.py): _llm_instance (FakeListLLM) reconfigurado para CalculadoraTrivial.")
#         print("--- Testando agent_a_func (com CalculadoraTrivial) ---")
#         test_input_calculo = "Quanto é 22+11 usando a calculadora?" # A frase ajuda o LLM a escolher a ferramenta
#         print(f"Input para Agente A: '{test_input_calculo}'")
#         output_calculo = agent_a_func(test_input_calculo)
#         print(f"\nOutput Final do Agente A (Cálculo): '{output_calculo}'")

#     print("--- Fim do Teste Local de agent_a.py ---")
