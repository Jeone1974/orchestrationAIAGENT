# app/tools.py
from langchain.agents import Tool
from app.agents import agent_a_func, agent_b_func, agent_c_func

agent_tools = [
    Tool(
        name="AgentA",
        func=agent_a_func,
        description="Especialista em X. Use este agente para todas as questões relacionadas a X."
    ),
    Tool(
        name="AgentB",
        func=agent_b_func,
        description="Especialista em Y. Este agente é o melhor para responder perguntas sobre Y."
    ),
    Tool(
        name="AgentC",
        func=agent_c_func,
        description="Especialista em Z. Acione este agente para qualquer entrada referente a Z."
    ),
]
