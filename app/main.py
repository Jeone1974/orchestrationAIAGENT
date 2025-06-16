# app/main.py
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import Tool, initialize_agent, AgentType
from langchain.chains.router.llm_router import LLMRouterChain, RouterOutputParser
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory

from app.tools import agent_tools

load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")

# LangSmith Configuration Check
langchain_tracing_v2 = os.getenv("LANGCHAIN_TRACING_V2")
langchain_api_key = os.getenv("LANGCHAIN_API_KEY") # For LangSmith
langchain_project = os.getenv("LANGCHAIN_PROJECT") # For LangSmith

if langchain_tracing_v2 == "true" and (not langchain_api_key or langchain_api_key == "SUA_LANGSMITH_API_KEY"):
    print("AVISO: LangSmith tracing está habilitado (LANGCHAIN_TRACING_V2='true'), mas a LANGCHAIN_API_KEY não parece estar configurada ou é o placeholder. O rastreamento pode não funcionar.")
elif langchain_tracing_v2 == "true" and langchain_api_key and langchain_api_key != "SUA_LANGSMITH_API_KEY":
    print(f"LangSmith tracing está habilitado. As execuções devem ser rastreadas no projeto '{langchain_project}'.")
else:
    print("LangSmith tracing não está explicitamente habilitado (LANGCHAIN_TRACING_V2 não é 'true').")


llm = None
llm_router_chain = None
lead_agent_executor = None

# --- Definição das Memórias ---
# Memória para a conversa entre o usuário e o Lead Agent
user_lead_memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True,
    output_key="output" # Garantir que a saída do agente seja capturada corretamente pelo AgentExecutor
)

# Memória para as interações entre o Lead Agent (via router) e os agentes da equipe
# Esta memória registrará as chamadas que o Lead Agent faz para os sub-agentes.
lead_team_memory = ConversationBufferMemory(
    memory_key="team_interaction_history", # Chave diferente para não colidir com a user_lead_memory
    return_messages=True, # Pode ser útil para depuração, mas o formato pode não ser ideal para todos os usos
    input_key="sub_agent_input", # Chave para a entrada que o Lead Agent envia ao sub-agente
    output_key="sub_agent_output" # Chave para a saída que o Lead Agent recebe do sub-agente
)
# --- Fim da Definição das Memórias ---

if not openai_api_key or openai_api_key == "SUA_CHAVE_API_AQUI":
    print("AVISO: A variável de ambiente OPENAI_API_KEY não está configurada ou é o placeholder. O Lead Agent e o Router não funcionarão corretamente.")
else:
    llm = ChatOpenAI(temperature=0, openai_api_key=openai_api_key)

    tool_names_and_descriptions = "\n".join([f"{tool.name}: {tool.description}" for tool in agent_tools])
    router_template_str = """
Dada uma entrada do usuário, classifique-a para um dos seguintes agentes com base em suas descrições.
Retorne APENAS o NOME do agente. Não adicione nenhuma outra palavra ou pontuação.

Descrições dos Agentes:
{destinations}

Entrada do Usuário:
{input}

Agente Selecionado (apenas o nome):"""

    filled_router_template = router_template_str.format(destinations=tool_names_and_descriptions)
    router_prompt = PromptTemplate(
        template=filled_router_template,
        input_variables=["input"],
        output_parser=RouterOutputParser(),
    )
    llm_router_chain = LLMRouterChain(llm=llm, prompt=router_prompt)

# Modificando execute_router_chain para usar lead_team_memory
def execute_router_chain(input_str: str) -> str:
    if not llm_router_chain:
        return "Router não configurado devido à ausência da chave OpenAI."

    router_decision_output = llm_router_chain.invoke({"input": input_str})

    destination_agent_name = None
    if isinstance(router_decision_output, dict):
        destination_agent_name = router_decision_output.get("destination")
    elif isinstance(router_decision_output, str):
        destination_agent_name = router_decision_output

    sub_agent_output_str = "" # Para armazenar a saída do sub-agente

    if not destination_agent_name:
        print(f"Router (dentro de execute_router_chain) não conseguiu determinar o destino. Decisão: {router_decision_output}")
        selected_tool = agent_tools[0] # Fallback
        sub_agent_output_str = selected_tool.func(input_str)
        result_message = f"(Fallback to {selected_tool.name} due to router failure) {sub_agent_output_str}"
        # Log da interação de fallback na memória da equipe
        try:
            lead_team_memory.save_context(
                inputs={"sub_agent_input": input_str}, # Usando 'inputs' como um dicionário
                outputs={"sub_agent_output": result_message} # Usando 'outputs' como um dicionário
            )
            print(f"Interação de fallback com {selected_tool.name} salva na lead_team_memory.")
        except Exception as e:
            print(f"Erro ao salvar fallback na lead_team_memory: {e}")
        return result_message

    selected_tool = next((tool for tool in agent_tools if tool.name == destination_agent_name), None)

    if not selected_tool:
        print(f"Agente '{destination_agent_name}' (decidido pelo router) não encontrado nas ferramentas.")
        selected_tool = agent_tools[0] # Fallback
        sub_agent_output_str = selected_tool.func(input_str)
        result_message = f"(Fallback to {selected_tool.name} due to tool not found post-routing) {sub_agent_output_str}"
        # Log da interação de fallback na memória da equipe
        try:
            lead_team_memory.save_context(
                inputs={"sub_agent_input": input_str},
                outputs={"sub_agent_output": result_message}
            )
            print(f"Interação de fallback com {selected_tool.name} salva na lead_team_memory.")
        except Exception as e:
            print(f"Erro ao salvar fallback na lead_team_memory: {e}")
        return result_message

    print(f"Router (chamado por Lead Agent via execute_router_chain) direcionou para: {selected_tool.name}")

    # Executa a função do agente especializado
    sub_agent_output_str = selected_tool.func(input_str)

    # Salva a interação na memória da equipe (lead_team_memory)
    try:
        lead_team_memory.save_context(
            inputs={"sub_agent_input": input_str}, # Usando 'inputs' como um dicionário
            outputs={"sub_agent_output": sub_agent_output_str} # Usando 'outputs' como um dicionário
        )
        print(f"Interação com {selected_tool.name} (input: '{input_str[:50]}...', output: '{sub_agent_output_str[:50]}...') salva na lead_team_memory.")
        # Para depurar o conteúdo da memória:
        # print(f"Conteúdo atual de lead_team_memory: {lead_team_memory.load_memory_variables({})}")
    except Exception as e:
        print(f"Erro ao salvar na lead_team_memory para {selected_tool.name}: {e}")

    return sub_agent_output_str

if llm:
    router_as_tool = Tool(
        name="RouterParaAgentesEspecializados",
        func=execute_router_chain,
        description="Roteia a pergunta do usuário para o agente especializado apropriado (AgenteA, AgenteB ou AgenteC) e retorna a resposta do especialista. Use esta ferramenta para qualquer pergunta que precise de conhecimento especializado sobre X, Y ou Z."
    )
    lead_agent_tools = [router_as_tool]
    lead_agent_executor = initialize_agent(
        tools=lead_agent_tools,
        llm=llm,
        agent=AgentType.OPENAI_FUNCTIONS,
        verbose=True,
        memory=user_lead_memory # user_lead_memory (conversa Usuário <-> Lead Agent) é associada aqui
    )
    print("Lead Agent Executor inicializado com sucesso com user_lead_memory.")
    print("lead_team_memory está configurada para registrar interações Lead Agent -> Sub-Agentes via execute_router_chain.")
else:
    print("Lead Agent Executor não pôde ser inicializado (LLM não disponível - verifique OPENAI_API_KEY).")

# Código de teste (pode ser movido/refatorado para server.py ou testes unitários)
# if __name__ == "__main__":
#     if lead_agent_executor:
#         print("\nIniciando chat com o Lead Agent (digite 'sair' para terminar):")

#         test_inputs = [
#             "Preciso de ajuda com X por favor",
#             "Me fale sobre Y",
#             "Qual sua opinião sobre Z?",
#             "Uma pergunta genérica que não se encaixa bem." # Teste de fallback do router
#         ]

#         for user_input in test_inputs:
#             print(f"\nUsuário: {user_input}")
#             # A memória user_lead_memory é atualizada automaticamente pelo AgentExecutor
#             response = lead_agent_executor.invoke({"input": user_input})
#             print(f"Lead Agent: {response.get('output')}\n")

#         print("\n--- Histórico da Memória Usuário-Lead Agent (user_lead_memory) ---")
#         # Conteúdo da memória user_lead_memory (conversa com o usuário)
#         # O input aqui é apenas um placeholder, não afeta o load da ConversationBufferMemory
#         print(user_lead_memory.load_memory_variables({}))
#         print("------------------------------------------------------------------")

#         print("\n--- Histórico da Memória Lead-Equipe (lead_team_memory) ---")
#         # Conteúdo da memória lead_team_memory (interações com sub-agentes)
#         # O input aqui é apenas um placeholder
#         print(lead_team_memory.load_memory_variables({"sub_agent_input": "dummy"}))
#         print("-----------------------------------------------------------")
#     else:
#         print("Lead Agent não está pronto. Verifique a configuração da OPENAI_API_KEY.")
