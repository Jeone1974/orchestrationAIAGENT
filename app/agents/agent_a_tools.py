# app/agents/agent_a_tools.py
from langchain.agents import Tool

def busca_info_x_func(query: str) -> str:
    """
    Simula uma busca por informações especializadas sobre o tópico X.
    Responde a consultas específicas sobre X.
    """
    query = query.lower()
    if "caracteristica principal de x" in query:
        return "A característica principal de X é sua flexibilidade e adaptabilidade."
    elif "origem de x" in query:
        return "X foi desenvolvido inicialmente como um projeto de pesquisa em 2023."
    elif "componentes de x" in query:
        return "X é composto por Módulo Alpha, Módulo Beta e Conector Gamma."
    else:
        return f"Não encontrei informações específicas sobre '{query}' no domínio X. Tente perguntar sobre características principais, origem ou componentes."

def calculadora_trivial_func(expression: str) -> str:
    """
    Uma calculadora muito simples que tenta avaliar uma expressão de adição.
    Por exemplo, '5+3' ou '10 + 7'. Retorna o resultado ou uma mensagem de erro.
    Só funciona para dois números e adição.
    """
    try:
        if '+' not in expression:
            return "Calculadora Trivial: Expressão não contém o operador '+'. Formato esperado: 'numero1+numero2'."

        parts = expression.split('+', 1)
        num1_str = parts[0].strip()
        num2_str = parts[1].strip()

        num1 = int(num1_str)
        num2 = int(num2_str)
        result = num1 + num2
        return f"Calculadora Trivial: O resultado de {expression} é {result}."
    except ValueError:
        return "Calculadora Trivial: Erro ao converter números. Certifique-se de que a expressão contém apenas números e '+', como '5+3'."
    except Exception as e:
        return f"Calculadora Trivial: Erro ao processar a expressão '{expression}': {str(e)}"

tools_for_agent_a = [
    Tool(
        name="BuscaInformacaoDominioX",
        func=busca_info_x_func,
        description="Útil para buscar informações específicas sobre o domínio X. Use esta ferramenta para perguntas sobre as características, origem ou componentes de X."
    ),
    Tool(
        name="CalculadoraTrivial",
        func=calculadora_trivial_func,
        description="Útil para realizar cálculos de adição simples entre dois números. Forneça a expressão como 'numero1+numero2'."
    )
]

# Para garantir que __init__.py possa importar
__all__ = ["tools_for_agent_a"]
