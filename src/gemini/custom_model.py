from collections import deque

from google.generativeai import configure, GenerativeModel


class CustomModel:
    def __init__(self, model_name: str, api_key: str, system_instruction: str, memory_size: int = 20):
        configure(api_key=api_key)
        self.model = GenerativeModel(model_name, system_instruction=system_instruction)
        self.memory = deque(maxlen=memory_size)

    def generate_content(self, message: str) -> str:
        prompt = f"{self.memory_to_string()}User: {message}\nCryptoAssistant: "
        response_text = self.model.generate_content(prompt).text
        self.memory.append(f"User: {message}\nCryptoAssistant: {response_text}")
        return response_text

    def clear_memory(self):
        self.memory.clear()

    def memory_to_string(self, start: str = "Previous conversations:\n") -> str:
        return start + "\n".join(self.memory)
