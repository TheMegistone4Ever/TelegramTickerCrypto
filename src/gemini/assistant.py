import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Tuple

import google.generativeai as genai
import pandas as pd

from bot.models import PairData


@dataclass
class ConversationState:
    is_active: bool = False
    conversation_started: bool = False


class CryptoAIProcessor:
    def __init__(
            self,
            model_name: str,
            api_key: str,
            database_path: str = "crypto_pairs.csv",
    ):
        self.database_path = Path(database_path)
        self.conversation = ConversationState()

        # Configure the technical model
        genai.configure(api_key=api_key)

        self.technical_model = genai.GenerativeModel(
            model_name,
            system_instruction=[
                """
                You are a cryptocurrency data analyzer. Follow these steps EXACTLY:
                If the message is the start of a conversation, output `<conversation>` on its own line.
                If the message is the end of a conversation, output `<conversation/>` on its own line.
                Identify any cryptocurrency mentions in the user message. For each one, output a tag exactly as `<coin name=\"SYMBOL/SOL\">` (append `/SOL` if missing).
                Output a single technical sentence in the following format:
                   `User asks about [coin tags] and [query summary]`
                Do not include any additional text, explanations, markdown formatting, or line breaks (except for the `<conversation>` and `<conversation/>` tags if needed).
                Examples:
                Input: 'Привіт! Які перспективи у BTC?'
                Output:
                <conversation>
                User asks about <coin name=\"BTC/SOL\"> and prospects in Ukrainian
                Input: 'Is ETH a good investment?'
                Output:
                User asks about <coin name=\"ETH/SOL\"> and investment
                Input: 'Bye'
                Output:
                <conversation/>
                """
            ],
        )

        self.user_model = genai.GenerativeModel(
            model_name,
            system_instruction=[
                """
                You are a multilingual crypto assistant. Your response must be in the user's language.
                Follow this template exactly:
                Acknowledge the coin(s) from the provided info.
                Provide key metrics from the database (for example, trading volume, volatility, liquidity).
                Include a concise risk/reward analysis.
                End with a neutral recommendation (for example, advise to diversify or exercise caution).
                Style guidelines:
                Limit your response to a maximum of 3 sentences, ensuring it is concise yet informative.
                Use a friendly tone, as if you were talking to a friend.
                Include an emoji if the user's message contained one.
                Do not mention tags, technical processing details, or any model limitations.
                Make sure your answer is tailored to the user's language and remains strictly within these guidelines.
                """
            ],
        )

    def save_pair_data(self, pair_data: List[PairData]):
        """Save pair data to CSV database"""
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
            writer = csv.DictWriter(f, fieldnames=fieldnames)
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
        """Get raw coin data from database"""
        try:
            df = pd.read_csv(self.database_path)
            coin_data = df[df["token"].str.lower() == coin_name.lower()]
            return (
                coin_data.to_dict("records")[0] if not coin_data.empty else None
            )
        except (FileNotFoundError, IndexError):
            return None

    def _should_respond(self, message: str) -> bool:
        """Check if message requires a response"""
        triggers = ["?", "ВОПРОС", "ПИТАННЯ", "QUESTION"]
        return any(trigger in message.upper() for trigger in triggers)

    def _is_farewell(self, message: str) -> bool:
        """Check for conversation end"""
        farewells = [
            "bye",
            "goodbye",
            "пока",
            "до свидания",
            "бувай",
            "до побачення",
        ]
        return any(farewell in message.lower() for farewell in farewells)

    def process_message(self, message: str) -> Tuple[str, str]:
        """Two-stage message processing"""
        # Stage 1: Technical Processing
        technical_response_parts = []

        # Handle conversation start
        if (
                self._should_respond(message)
                and not self.conversation.conversation_started
        ):
            self.conversation.conversation_started = True
            self.conversation.is_active = True

        # Handle conversation end
        if (
                self._is_farewell(message)
                and self.conversation.conversation_started
        ):
            self.conversation.is_active = False
            self.conversation.conversation_started = False

        if self.conversation.is_active:
            technical_response = self.technical_model.generate_content(message)
            technical_response_parts.append(technical_response.text)

        technical_output = "\n".join(technical_response_parts)
        print(f"Preprocessed {technical_output = }")

        if not self.conversation.is_active:
            return technical_output, ""

        coin_regex = re.compile(r"<coin name=\"(?P<coin_name>.*?)\">")
        for match in coin_regex.finditer(technical_output):
            coin_name = match.group("coin_name")
            coin_data = self._get_coin_data(coin_name)
            if coin_data:
                technical_output = technical_output.replace(
                    match.group(0), str(coin_data)
                )

        # Stage 2: User-Facing Processing
        user_response = ""
        if self.conversation.is_active or technical_output:
            user_context = f"Processed message: {technical_output}"
            user_response = self.user_model.generate_content(
                [
                    ("What is the style of this message: " + message),
                    "The style is "
                    + (
                        "casual"
                        if "!" in message or "?" in message
                        else "formal"
                    ),
                    user_context,
                ]
            ).text

        return technical_output, user_response

    def handle_command(self, command: str) -> str:
        """Handle bot commands with user-friendly responses"""
        commands = {
            "start": "Welcome to CryptoTicker! I'm your crypto assistant. Ask me questions about cryptocurrencies or specific coins in our database. 🚀",
            "help": """Here's how I can help:
- Ask about specific coins
- Get market information
- Check trending cryptocurrencies
- Get real-time updates
Just ask your question! 📊""",
            "info": "I'm here to provide real-time crypto information. What would you like to know?",
            "trends": "Let me show you what's trending in the crypto world right now.",
            "support": "Need help? Just ask your question and I'll assist you!",
        }
        return commands.get(
            command, "Unknown command. Try /help to see what I can do!"
        )
