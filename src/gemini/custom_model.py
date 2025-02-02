from google.generativeai import configure, GenerativeModel


class CustomModel:
    def __init__(self, model_name: str, api_key: str, system_instruction: str):
        configure(api_key=api_key)
        self.model = GenerativeModel(model_name, system_instruction=system_instruction)
        self.memory = "Previous conversations:"

    def generate_content(self, message: str) -> str:
        prompt = self.memory + "\nUser: " + message + "\nCryptoAssistant: "
        response = self.model.generate_content(prompt)
        response_text = response.text
        self.memory += "\nUser: " + message + "\nCryptoAssistant: " + response_text
        return response_text

    def clear_memory(self):
        self.memory = "Previous conversations:"
