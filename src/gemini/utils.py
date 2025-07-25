from typing import Dict

from nltk import word_tokenize
from requests import get


def translate_text(text: str) -> str:
    """Synchronous translation using requests"""

    try:
        response = get(
            "https://translate.googleapis.com/translate_a/single",
            params={
                "client": "gtx",
                "sl": "auto",
                "tl": "en",
                "dt": "t",
                "q": text
            }
        )
        data = response.json()
        return "\n".join(line[0] for line in data[0])
    except Exception as e:
        print(f"Translation error: {e}")
        return text


def dialogue_act_features(post: str) -> Dict[str, bool]:
    """Extract features from a post"""

    return {f"contains({word.lower()})": True for word in word_tokenize(post)}
