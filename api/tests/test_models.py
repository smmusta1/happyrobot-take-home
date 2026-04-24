from datetime import datetime
from decimal import Decimal

from happyrobot_api.models import Call, Carrier, Load, Offer


def test_load_roundtrip(db_session):
    load = Load(
        reference_number="LOAD-001",
        equipment_type="Dry Van",
        commodity_type="Automobile Parts",
        posted_carrier_rate=Decimal("1500.00"),
        max_buy=Decimal("1725.00"),
        origin_city="Chicago",
        origin_state="IL",
        origin_zip="60601",
        origin_open=datetime(2026, 5, 1, 14, 0),
        origin_close=datetime(2026, 5, 1, 16, 0),
        destination_city="New York",
        destination_state="NY",
        destination_zip="10001",
        destination_open=datetime(2026, 5, 2, 14, 0),
        destination_close=datetime(2026, 5, 2, 16, 0),
        miles=790,
    )
    db_session.add(load)
    db_session.commit()

    fetched = db_session.query(Load).filter_by(reference_number="LOAD-001").one()
    assert fetched.equipment_type == "Dry Van"
    assert fetched.posted_carrier_rate == Decimal("1500.00")
    assert fetched.max_buy == Decimal("1725.00")
    assert fetched.status == "available"  # default
    assert fetched.origin_city == "Chicago"
    assert fetched.miles == 790


def test_carrier_roundtrip(db_session):
    carrier = Carrier(
        mc_number="123456",
        dot_number="987654",
        carrier_name="ABC Trucking Inc.",
        status="active",
        allowed_to_operate=True,
        fmcsa_raw={"legalName": "ABC Trucking Inc.", "statusCode": "A"},
    )
    db_session.add(carrier)
    db_session.commit()

    fetched = db_session.query(Carrier).filter_by(mc_number="123456").one()
    assert fetched.carrier_name == "ABC Trucking Inc."
    assert fetched.status == "active"
    assert fetched.allowed_to_operate is True
    assert fetched.fmcsa_raw["statusCode"] == "A"


def test_call_roundtrip(db_session):
    call = Call(
        mc_number="123456",
        carrier_name="ABC Trucking",
        load_reference_number="LOAD-001",
        outcome="booked",
        sentiment="positive",
        final_rate=Decimal("1650.00"),
        loadboard_rate=Decimal("1500.00"),
        rounds_used=2,
        agreement_reached=True,
        transcript="Agent: Hello ... Carrier: I'll take it.",
        extracted_fields={"equipment_type": "Dry Van", "pickup_window": "May 1"},
    )
    db_session.add(call)
    db_session.commit()

    fetched = db_session.query(Call).filter_by(mc_number="123456").one()
    assert fetched.outcome == "booked"
    assert fetched.sentiment == "positive"
    assert fetched.rounds_used == 2
    assert fetched.final_rate == Decimal("1650.00")
    assert fetched.extracted_fields["equipment_type"] == "Dry Van"


def test_offer_roundtrip_and_cascade(db_session):
    call = Call(mc_number="123456", load_reference_number="LOAD-001", outcome="booked")
    db_session.add(call)
    db_session.flush()

    offers = [
        Offer(
            call_id=call.id,
            mc_number="123456",
            load_reference_number="LOAD-001",
            round_number=1,
            carrier_offer=Decimal("1800.00"),
            agent_counter=Decimal("1650.00"),
            decision="counter",
        ),
        Offer(
            call_id=call.id,
            mc_number="123456",
            load_reference_number="LOAD-001",
            round_number=2,
            carrier_offer=Decimal("1700.00"),
            agent_counter=None,
            decision="accept",
        ),
    ]
    db_session.add_all(offers)
    db_session.commit()

    fetched_call = db_session.query(Call).filter_by(id=call.id).one()
    assert len(fetched_call.offers) == 2
    assert fetched_call.offers[0].carrier_offer == Decimal("1800.00")
    assert fetched_call.offers[1].decision == "accept"

    # cascade: deleting the call removes its offers
    db_session.delete(fetched_call)
    db_session.commit()
    assert db_session.query(Offer).count() == 0
