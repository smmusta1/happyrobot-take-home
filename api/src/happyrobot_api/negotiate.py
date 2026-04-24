"""Negotiation policy for inbound carrier calls.

Pure function — no DB, no I/O. The HTTP layer fetches state, calls evaluate_offer,
and persists the result.

Policy:
  - Anchor to posted_carrier_rate (the broker's opening offer).
  - Cap counters at max_buy (hidden ceiling).
  - Quick-accept at posted_carrier_rate × 1.03.
  - Counter at midpoint between our last counter and the carrier's offer.
  - Round 3 is last chance.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

Decision = Literal["accept", "counter", "decline"]

MAX_ROUNDS = 3
QUICK_ACCEPT_MULTIPLIER = Decimal("1.03")


@dataclass(frozen=True)
class Evaluation:
    decision: Decision
    agent_counter: Decimal | None
    message: str


def _whole_dollar(value: Decimal) -> Decimal:
    """Round to the nearest whole dollar. Brokers don't negotiate in cents."""
    return value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def _format(value: Decimal) -> str:
    return f"${value:,.0f}"


def evaluate_offer(
    posted_carrier_rate: Decimal,
    max_buy: Decimal,
    carrier_offer: Decimal,
    round_number: int,
    last_agent_counter: Decimal | None,
) -> Evaluation:
    if carrier_offer <= posted_carrier_rate:
        accept_at = _whole_dollar(carrier_offer)
        return Evaluation(
            decision="accept",
            agent_counter=accept_at,
            message=f"{_format(accept_at)} works — let's book it.",
        )

    quick_accept = posted_carrier_rate * QUICK_ACCEPT_MULTIPLIER
    if carrier_offer <= quick_accept:
        accept_at = _whole_dollar(carrier_offer)
        return Evaluation(
            decision="accept",
            agent_counter=accept_at,
            message=f"{_format(accept_at)} works — let's book it.",
        )

    if round_number >= MAX_ROUNDS:
        if carrier_offer <= max_buy:
            accept_at = _whole_dollar(carrier_offer)
            return Evaluation(
                decision="accept",
                agent_counter=accept_at,
                message=f"Final round — I can do {_format(accept_at)}. Let's book it.",
            )
        return Evaluation(
            decision="decline",
            agent_counter=None,
            message=(
                f"That's over what I can pay on this lane. "
                f"I can't get to {_format(_whole_dollar(carrier_offer))}."
            ),
        )

    anchor = last_agent_counter if last_agent_counter is not None else posted_carrier_rate
    midpoint = (anchor + carrier_offer) / 2
    counter = _whole_dollar(min(midpoint, max_buy))
    return Evaluation(
        decision="counter",
        agent_counter=counter,
        message=f"I can stretch to {_format(counter)} — can you work with that?",
    )
