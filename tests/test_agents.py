# tests/test_agents.py
import unittest
from app.agents.agent_a import agent_a_func
from app.agents.agent_b import agent_b_func
from app.agents.agent_c import agent_c_func

class TestSpecializedAgents(unittest.TestCase):

    def test_agent_a_func(self):
        input_str = "teste para A"
        expected_output = f"[Agent A] Processando: {input_str}"
        self.assertEqual(agent_a_func(input_str), expected_output)

    def test_agent_b_func(self):
        input_str = "teste para B"
        expected_output = f"[Agent B] Resposta especializada para: {input_str}"
        self.assertEqual(agent_b_func(input_str), expected_output)

    def test_agent_c_func(self):
        input_str = "teste para C"
        expected_output = f"[Agent C] Lidando com o input: {input_str}"
        self.assertEqual(agent_c_func(input_str), expected_output)

if __name__ == '__main__':
    unittest.main()
