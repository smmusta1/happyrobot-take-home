"""Unit tests for the negotiation decision logic (pure function, no DB)."""

from decimal import Decimal

from happyrobot_api.negotiate import MAX_ROUNDS, evaluate_offer

P = Decimal("1000.00")  # posted_carrier_rate
M = Decimal("1200.00")  # max_buy


def _eval(offer: str, round_num: int, last_counter: str | None = None):
    return evaluate_offer(
        posted_carrier_rate=P,
        max_buy=M,
        carrier_offer=Decimal(offer),
        round_number=round_num,
        last_agent_counter=Decimal(last_counter) if last_counter else None,
    )


def test_accept_when_carrier_offer_at_or_below_posted():
    r = _eval("1000.00", 1)
    assert r.decision == "accept"
    assert r.agent_counter == Decimal("1000.00")

    r = _eval("950.00", 1)
    assert r.decision == "accept"
    assert r.agent_counter == Decimal("950.00")


def test_quick_accept_within_three_percent():
    # 1030.00 is exactly posted * 1.03 → accept
    r = _eval("1030.00", 1)
    assert r.decision == "accept"
    assert r.agent_counter == Decimal("1030.00")


def test_counter_at_midpoint_round_1():
    # carrier asks 1500, posted 1000 → midpoint = 1250, capped at max_buy 1200
    r = _eval("1500.00", 1)
    assert r.decision == "counter"
    assert r.agent_counter == Decimal("1200.00")  # clamped to max_buy


def test_counter_at_midpoint_uncapped():
    # carrier asks 1100, posted 1000, no cap issue → midpoint = 1050
    r = _eval("1100.00", 1)
    assert r.decision == "counter"
    assert r.agent_counter == Decimal("1050.00")


def test_counter_at_midpoint_uses_last_counter_round_2():
    # Round 1: we countered 1050. Round 2: carrier offers 1150 → midpoint = 1100
    r = _eval("1150.00", 2, last_counter="1050.00")
    assert r.decision == "counter"
    assert r.agent_counter == Decimal("1100.00")


def test_round_3_accepts_if_under_max_buy():
    r = _eval("1180.00", 3, last_counter="1100.00")
    assert r.decision == "accept"
    assert r.agent_counter == Decimal("1180.00")


def test_round_3_declines_if_over_max_buy():
    r = _eval("1300.00", 3, last_counter="1100.00")
    assert r.decision == "decline"
    assert r.agent_counter is None


def test_round_3_accepts_at_exactly_max_buy():
    r = _eval("1200.00", 3, last_counter="1100.00")
    assert r.decision == "accept"
    assert r.agent_counter == Decimal("1200.00")


def test_above_max_rounds_still_declines_when_over_max_buy():
    # Defensive: if round somehow becomes 4, we still behave like round 3
    r = _eval("1300.00", 4, last_counter="1200.00")
    assert r.decision == "decline"


def test_max_rounds_is_three():
    assert MAX_ROUNDS == 3


def test_counter_message_includes_price():
    r = _eval("1100.00", 1)
    assert "$1,050" in r.message
    assert ".00" not in r.message  # no cents in broker negotiation


def test_decline_message_mentions_the_offer():
    r = _eval("1500.00", 3, last_counter="1200.00")
    assert "$1,500" in r.message
    assert ".00" not in r.message


def test_counter_is_always_whole_dollar():
    # midpoint of 2375 and 2500 = 2437.50 → rounds to 2438
    from happyrobot_api.negotiate import evaluate_offer
    r = evaluate_offer(
        posted_carrier_rate=Decimal("2150"),
        max_buy=Decimal("2450"),
        carrier_offer=Decimal("2500"),
        round_number=2,
        last_agent_counter=Decimal("2375"),
    )
    assert r.agent_counter == Decimal("2438")
    assert "." not in str(r.agent_counter)


def test_accept_rounds_carrier_offer_to_whole_dollar():
    # Carrier offers a cent-precise amount; accept at rounded whole dollar
    r = _eval("999.50", 1)
    assert r.decision == "accept"
    assert r.agent_counter == Decimal("1000")  # rounds to nearest dollar
