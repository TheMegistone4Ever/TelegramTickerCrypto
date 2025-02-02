import pickle
from pathlib import Path
from typing import Dict

import nltk
import requests


class ClassifierManager:
    _instance = None

    def __new__(cls, model_path=None):
        if cls._instance is None:
            cls._instance = super(ClassifierManager, cls).__new__(cls)
            cls._instance.model_path = model_path or Path("models") / "classifier.pickle"
            cls._instance.question_classifier = None
            cls._instance.farewell_classifier = None
            cls._instance._load_or_train()
        return cls._instance

    def _load_or_train(self):
        if self.model_path.exists():
            self._load_models()
        else:
            self._train_and_save_models()

    def _load_models(self):
        with open(self.model_path, "rb") as f:
            self.question_classifier, self.farewell_classifier = pickle.load(f)

    def _train_and_save_models(self):
        nltk.download('nps_chat')
        nltk.download('punkt')

        posts = nltk.corpus.nps_chat.xml_posts()[:10000]

        featuresets = [(self._dialogue_act_features(post.text), post.get('class'))
                       for post in posts]
        size = int(len(featuresets) * 0.1)
        train_set, test_set = featuresets[size:], featuresets[:size]

        self.question_classifier = nltk.NaiveBayesClassifier.train(train_set)
        self.farewell_classifier = nltk.NaiveBayesClassifier.train(train_set)

        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.model_path, "wb") as f:
            pickle.dump((self.question_classifier, self.farewell_classifier), f)

    def _translate_text(self, text: str) -> str:
        """Synchronous translation using requests"""
        try:
            params = {
                'client': 'gtx',
                'sl': 'auto',
                'tl': 'en',
                'dt': 't',
                'q': text
            }
            response = requests.get(
                'https://translate.googleapis.com/translate_a/single',
                params=params
            )
            data = response.json()
            return data[0][0][0]
        except Exception as e:
            print(f"Translation error: {e}")
            return text

    def is_question(self, text: str) -> bool:
        translated_text = self._translate_text(text)
        question_types = ["whQuestion", "ynQuestion"]
        question_type = self.question_classifier.classify(
            self._dialogue_act_features(translated_text)
        )
        return question_type in question_types

    def is_farewell(self, text: str) -> bool:
        translated_text = self._translate_text(text)
        farewell_types = ["Bye"]
        farewell_type = self.farewell_classifier.classify(
            self._dialogue_act_features(translated_text)
        )
        return farewell_type in farewell_types

    def _dialogue_act_features(self, post: str) -> Dict[str, bool]:
        features = {}
        for word in nltk.word_tokenize(post):
            features[f'contains({word.lower()})'] = True
        return features
