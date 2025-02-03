import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, Set

import pandas as pd

from bot.models import PairData
from gemini.classifier_manager import ClassifierManager
from gemini.custom_model import CustomModel
from gemini.utils import translate_text


@dataclass
class ConversationState:
    is_active: bool = False
    conversation_started: bool = False


class CryptoAIProcessor:
    def __init__(
            self,
            model_name: str,
            api_key: str,
            database_path: str = "data/crypto_pairs.csv",
            classifier_model_path: str = None
    ):
        self.database_path = Path(database_path)
        self.conversation = ConversationState()
        self.classifier_manager = ClassifierManager(classifier_model_path)

        technical_system_instruction = """
                You are a cryptocurrency data analyzer. Follow these steps EXACTLY:
                If the message is the start of a conversation, output `<conversation>` on its own line.
                If the message is the end of a conversation, output `<conversation/>` on its own line.
                Identify any cryptocurrency mentions in the user message. For each one, output a tag exactly as `<coin name=\"SYMBOL/SOL\">` (append `/SOL` if missing).
                Output a single technical sentence in the following format (for example):
                   `User asks about [coin tags] and [query summary] in [language]`
                Or any other relevant information if needed.
                Do not include any additional text, explanations, markdown formatting, or line breaks (except for the `<conversation>` and `<conversation/>` tags if needed).
                Examples:
                Input: "Привіт! Які перспективи у BTC?"
                Output:
                <conversation>
                User asks about <coin name=\"BTC/SOL\"> and prospects in Ukrainian
                Input: "Is ETH a good investment?"
                Output:
                User asks about <coin name=\"ETH/SOL\"> and investment in English
                Input: "Bye"
                Output:
                <conversation/>
                """

        user_system_instruction = """
                You are a multilingual crypto assistant. Your response must be in the user"s language.
                Follow this template exactly:
                Acknowledge the coin(s) from the provided info.
                Provide key metrics from the database (for example, trading volume, volatility, liquidity).
                Include a concise risk/reward analysis.
                End with a neutral recommendation (for example, advise to diversify or exercise caution).
                Style guidelines:
                Limit your response to a maximum of 3 sentences, ensuring it is concise yet informative.
                Use a friendly tone, as if you were talking to a friend.
                Include an emoji if the user"s message contained one.
                Do not mention tags, technical processing details, or any model limitations.
                Answer only based on the provided data, without additional research.
                Make sure your answer is tailored to the user"s language and remains strictly within these guidelines.
                """

        self.technical_model = CustomModel(model_name, api_key, technical_system_instruction)
        self.user_model = CustomModel(model_name, api_key, user_system_instruction)

    def save_pair_data(self, pair_data: Set[PairData]):
        fieldnames = [
            "token",
            "description",
            "address",
            "price",
            "age",
            "volume",
            "liquidity",
            "market_cap",
            "security_score",
        ]

        mode = "a" if self.database_path.exists() else "w"
        with open(self.database_path, mode, newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)  # type: ignore
            if mode == "w":
                writer.writeheader()

            for pair in pair_data:
                writer.writerow(
                    {
                        "token": pair.token,
                        "description": pair.description,
                        "address": pair.address,
                        "price": pair.price,
                        "age": pair.age,
                        "volume": pair.volume,
                        "liquidity": pair.liquidity,
                        "market_cap": pair.market_cap,
                        "security_score": pair.security.score
                        if pair.security
                        else None,
                    }
                )

    def _get_coin_data(self, coin_name: str) -> Optional[dict]:
        try:
            df = pd.read_csv(self.database_path)
            coin_data = df[df["token"].str.lower() == coin_name.lower()]
            return (
                coin_data.to_dict("records")[0] if not coin_data.empty else None
            )
        except (FileNotFoundError, IndexError):
            return None

    def process_message(self, message: str) -> Tuple[str, str]:
        technical_response_parts = []
        translated_message = translate_text(message)

        if (self.classifier_manager.is_types(translated_message, ["whQuestion", "ynQuestion"], True)
                and not self.conversation.conversation_started):
            self.conversation.conversation_started = True
            self.conversation.is_active = True
            technical_response_parts.append("<conversation>")

        if (self.classifier_manager.is_types(translated_message, ["Bye"], True)
                and self.conversation.conversation_started):
            self.conversation.is_active = False
            self.conversation.conversation_started = False
            technical_response_parts.append("<conversation/>")
            self.technical_model.clear_memory()
            self.user_model.clear_memory()

        if self.conversation.is_active:
            technical_response = self.technical_model.generate_content(message)
            technical_response_parts.append(technical_response)

        technical_output = "\n".join(technical_response_parts)
        print(f"Preprocessed {technical_output = }")

        if not self.conversation.is_active and technical_output == "<conversation/>":
            return technical_output, ""

        coin_regex = re.compile(r"<coin name=\"(?P<coin_name>.*?)\">")
        for match in coin_regex.finditer(technical_output):
            if coin_data := self._get_coin_data(match.group("coin_name")):
                technical_output = technical_output.replace(match.group(0), str(coin_data))

        user_response = ""
        if self.conversation.is_active or technical_output:
            user_context = f"Processed message: {technical_output}"
            user_response = self.user_model.generate_content(
                f"Style: {"casual" if "!" in message or "?" in message else "formal"}\n{user_context}"
            )

        return technical_output, user_response
