from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict


class Multiplier(Enum):
    """Enum to represent different multipliers for money strings."""

    K = 1000
    M = 1000000
    B = 1000000000


class RiskLevel(Enum):
    """Enum to represent the different risk levels."""

    CRITICAL = ("c", "Critical", "⚠️⚠️")
    HIGH = ("h", "High", "⚠️")
    MEDIUM = ("m", "Medium", "⚡️")
    LOW = ("n", "Low", "🍏")

    def __init__(self, value: str, label: str, emoji: str):
        self._value_ = value
        self.label = label
        self.emoji = emoji


class TimeFrame(Enum):
    """Enum to represent different time frames for price changes."""

    FIVE_MIN = ("5m", "five_min_change")
    ONE_HOUR = ("1h", "one_hour_change")
    SIX_HOUR = ("6h", "six_hour_change")
    TWENTY_FOUR_HOUR = ("24h", "twenty_four_hour_change")

    def __init__(self, label: str, attribute: str):
        self.label = label
        self.attribute = attribute


@dataclass(frozen=True)
class ScoringWeight:
    """Dataclass to represent scoring weights for a specific issue."""

    birdeye: float
    goplus: float


@dataclass(frozen=True)
class SecurityData:
    """Dataclass to hold security information for a token."""

    c: Dict[str, Dict[str, Optional[str]]]
    h: Dict[str, Dict[str, Optional[str]]]
    m: Dict[str, Dict[str, Optional[str]]]
    n: Dict[str, Dict[str, Optional[str]]]
    score: Optional[float] = None
    error: Optional[str] = None


@dataclass(frozen=True)
class PairData:
    """Dataclass to represent a token pair's data from Dexscreener."""

    token: str
    description: str
    address: str
    price: float
    age: int
    buys: int
    sells: int
    volume: float
    makers: int
    five_min_change: Optional[float]
    one_hour_change: Optional[float]
    six_hour_change: Optional[float]
    twenty_four_hour_change: Optional[float]
    liquidity: float
    market_cap: float
    security: Optional[SecurityData] = None


@dataclass(frozen=True)
class RiskScoring:
    """Dataclass to hold scoring weights for each risk level."""

    level: RiskLevel
    weights: Dict[str, ScoringWeight]
