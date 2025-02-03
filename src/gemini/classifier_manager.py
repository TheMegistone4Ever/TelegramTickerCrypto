from pathlib import Path
from pickle import load, dump
from typing import List

from nltk import download, NaiveBayesClassifier
from nltk.corpus import nps_chat

from gemini.utils import translate_text, dialogue_act_features


class ClassifierManager:
    _instance = None

    def __new__(cls, model_path=None):
        if cls._instance is None:
            cls._instance = super(ClassifierManager, cls).__new__(cls)
            cls._instance.model_path = model_path or Path("models") / "classifier.pickle"
            cls._instance.classifier = None
            cls._instance._load_or_train()
        return cls._instance

    def _load_or_train(self):
        if self.model_path.exists():
            self._load_models()
        else:
            self._train_and_save_models()

    def _load_models(self):
        with open(self.model_path, "rb") as f:
            self.classifier = load(f)

    def _train_and_save_models(self):
        download("nps_chat")
        download("punkt")

        posts = nps_chat.xml_posts()[:10000]

        feature_sets = [(dialogue_act_features(post.text), post.get("class"))
                        for post in posts]
        size = int(len(feature_sets) * 0.1)
        train_set, test_set = feature_sets[size:], feature_sets[:size]

        self.classifier = NaiveBayesClassifier.train(train_set)

        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.model_path, "wb") as f:
            dump(self.classifier, f)  # type: ignore

    def is_types(self, text: str, types: List[str], translated: bool = False) -> bool:
        """Check if the text belongs to any of the types listed."""

        return self.classifier.classify(dialogue_act_features(text if translated else translate_text(text))) in types
