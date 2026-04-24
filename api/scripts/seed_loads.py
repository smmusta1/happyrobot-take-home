"""Populate the DB with a set of sample loads for demo and local development.

Idempotent: existing loads with matching reference numbers are skipped.

Usage:
    python -m scripts.seed_loads
"""

from datetime import datetime
from decimal import Decimal

from happyrobot_api.db import SessionLocal
from happyrobot_api.models import Load

LOADS = [
    {
        "reference_number": "HR-1001",
        "equipment_type": "Dry Van",
        "commodity_type": "Consumer Electronics",
        "origin": ("Chicago", "IL", "60601"),
        "destination": ("Dallas", "TX", "75201"),
        "pickup": datetime(2026, 4, 23, 8, 0),
        "pickup_close": datetime(2026, 4, 23, 14, 0),
        "delivery": datetime(2026, 4, 25, 9, 0),
        "delivery_close": datetime(2026, 4, 25, 17, 0),
        "miles": 925,
        "weight": Decimal("38000.00"),
        "pieces": 24,
        "dimensions": "53' dry van",
        "posted_carrier_rate": Decimal("2150.00"),
        "max_buy": Decimal("2450.00"),
        "sale_notes": "Drop trailer available at origin. No-touch freight.",
    },
    {
        "reference_number": "HR-1002",
        "equipment_type": "Reefer",
        "commodity_type": "Frozen Produce",
        "origin": ("Fresno", "CA", "93701"),
        "destination": ("Phoenix", "AZ", "85001"),
        "pickup": datetime(2026, 4, 23, 10, 0),
        "pickup_close": datetime(2026, 4, 23, 16, 0),
        "delivery": datetime(2026, 4, 24, 6, 0),
        "delivery_close": datetime(2026, 4, 24, 12, 0),
        "miles": 595,
        "weight": Decimal("42000.00"),
        "pieces": 18,
        "dimensions": "53' reefer, set at 34°F",
        "posted_carrier_rate": Decimal("1650.00"),
        "max_buy": Decimal("1900.00"),
        "sale_notes": "Temp-critical. Reefer download required at delivery.",
    },
    {
        "reference_number": "HR-1003",
        "equipment_type": "Flatbed",
        "commodity_type": "Steel Coils",
        "origin": ("Pittsburgh", "PA", "15222"),
        "destination": ("Detroit", "MI", "48201"),
        "pickup": datetime(2026, 4, 24, 7, 0),
        "pickup_close": datetime(2026, 4, 24, 13, 0),
        "delivery": datetime(2026, 4, 24, 19, 0),
        "delivery_close": datetime(2026, 4, 25, 2, 0),
        "miles": 285,
        "weight": Decimal("46500.00"),
        "pieces": 6,
        "dimensions": "48' flatbed, coil racks required",
        "posted_carrier_rate": Decimal("1200.00"),
        "max_buy": Decimal("1380.00"),
        "sale_notes": "Tarps + 4 chains min. Crane loading at origin.",
    },
    {
        "reference_number": "HR-1004",
        "equipment_type": "Dry Van",
        "commodity_type": "Paper Products",
        "origin": ("Atlanta", "GA", "30303"),
        "destination": ("Charlotte", "NC", "28202"),
        "pickup": datetime(2026, 4, 23, 13, 0),
        "pickup_close": datetime(2026, 4, 23, 19, 0),
        "delivery": datetime(2026, 4, 24, 8, 0),
        "delivery_close": datetime(2026, 4, 24, 14, 0),
        "miles": 245,
        "weight": Decimal("32000.00"),
        "pieces": 22,
        "dimensions": "53' dry van",
        "posted_carrier_rate": Decimal("725.00"),
        "max_buy": Decimal("850.00"),
        "sale_notes": "Live unload. Appointment required at delivery.",
    },
    {
        "reference_number": "HR-1005",
        "equipment_type": "Reefer",
        "commodity_type": "Dairy",
        "origin": ("Milwaukee", "WI", "53202"),
        "destination": ("Minneapolis", "MN", "55401"),
        "pickup": datetime(2026, 4, 24, 5, 0),
        "pickup_close": datetime(2026, 4, 24, 10, 0),
        "delivery": datetime(2026, 4, 24, 15, 0),
        "delivery_close": datetime(2026, 4, 24, 20, 0),
        "miles": 340,
        "weight": Decimal("40000.00"),
        "pieces": 16,
        "dimensions": "53' reefer, set at 38°F",
        "posted_carrier_rate": Decimal("950.00"),
        "max_buy": Decimal("1100.00"),
        "sale_notes": "Time-sensitive. FIFO unload order.",
    },
    {
        "reference_number": "HR-1006",
        "equipment_type": "Dry Van",
        "commodity_type": "Automotive Parts",
        "origin": ("Nashville", "TN", "37203"),
        "destination": ("Louisville", "KY", "40202"),
        "pickup": datetime(2026, 4, 23, 9, 0),
        "pickup_close": datetime(2026, 4, 23, 15, 0),
        "delivery": datetime(2026, 4, 23, 19, 0),
        "delivery_close": datetime(2026, 4, 24, 1, 0),
        "miles": 175,
        "weight": Decimal("28000.00"),
        "pieces": 12,
        "dimensions": "53' dry van",
        "posted_carrier_rate": Decimal("625.00"),
        "max_buy": Decimal("720.00"),
        "sale_notes": "JIT delivery for assembly line. On-time premium offered.",
    },
    {
        "reference_number": "HR-1007",
        "equipment_type": "Step Deck",
        "commodity_type": "Construction Equipment",
        "origin": ("Kansas City", "MO", "64101"),
        "destination": ("Denver", "CO", "80202"),
        "pickup": datetime(2026, 4, 25, 8, 0),
        "pickup_close": datetime(2026, 4, 25, 14, 0),
        "delivery": datetime(2026, 4, 26, 10, 0),
        "delivery_close": datetime(2026, 4, 26, 16, 0),
        "miles": 600,
        "weight": Decimal("44000.00"),
        "pieces": 2,
        "dimensions": "48' step deck, 8.5' wide load",
        "posted_carrier_rate": Decimal("1850.00"),
        "max_buy": Decimal("2100.00"),
        "sale_notes": "Permits included. Chains + tarps required.",
    },
    {
        "reference_number": "HR-1008",
        "equipment_type": "Dry Van",
        "commodity_type": "Retail Merchandise",
        "origin": ("Memphis", "TN", "38103"),
        "destination": ("Houston", "TX", "77002"),
        "pickup": datetime(2026, 4, 24, 11, 0),
        "pickup_close": datetime(2026, 4, 24, 17, 0),
        "delivery": datetime(2026, 4, 25, 13, 0),
        "delivery_close": datetime(2026, 4, 25, 19, 0),
        "miles": 580,
        "weight": Decimal("36000.00"),
        "pieces": 30,
        "dimensions": "53' dry van",
        "posted_carrier_rate": Decimal("1475.00"),
        "max_buy": Decimal("1700.00"),
        "sale_notes": "DC delivery, dock-high. Driver assist unload.",
    },
    {
        "reference_number": "HR-1009",
        "equipment_type": "Power Only",
        "commodity_type": "Preloaded Trailer",
        "origin": ("Columbus", "OH", "43215"),
        "destination": ("Indianapolis", "IN", "46204"),
        "pickup": datetime(2026, 4, 23, 14, 0),
        "pickup_close": datetime(2026, 4, 23, 20, 0),
        "delivery": datetime(2026, 4, 24, 6, 0),
        "delivery_close": datetime(2026, 4, 24, 12, 0),
        "miles": 175,
        "weight": Decimal("34000.00"),
        "pieces": None,
        "dimensions": "53' preloaded trailer, hook-and-go",
        "posted_carrier_rate": Decimal("525.00"),
        "max_buy": Decimal("600.00"),
        "sale_notes": "Trailer ready at shipping office. Bring a padlock.",
    },
    {
        "reference_number": "HR-1010",
        "equipment_type": "Reefer",
        "commodity_type": "Pharmaceuticals",
        "origin": ("Boston", "MA", "02110"),
        "destination": ("Philadelphia", "PA", "19103"),
        "pickup": datetime(2026, 4, 25, 7, 0),
        "pickup_close": datetime(2026, 4, 25, 13, 0),
        "delivery": datetime(2026, 4, 25, 19, 0),
        "delivery_close": datetime(2026, 4, 26, 1, 0),
        "miles": 310,
        "weight": Decimal("18000.00"),
        "pieces": 40,
        "dimensions": "53' reefer, set at 36°F",
        "posted_carrier_rate": Decimal("1350.00"),
        "max_buy": Decimal("1550.00"),
        "sale_notes": "Hazmat-adjacent pharma. CDL w/ TWIC preferred. Sealed trailer.",
    },
]


def seed() -> None:
    db = SessionLocal()
    try:
        inserted = 0
        skipped = 0
        for data in LOADS:
            exists = (
                db.query(Load)
                .filter(Load.reference_number == data["reference_number"])
                .one_or_none()
            )
            if exists:
                skipped += 1
                continue

            origin_city, origin_state, origin_zip = data["origin"]
            dest_city, dest_state, dest_zip = data["destination"]
            db.add(
                Load(
                    reference_number=data["reference_number"],
                    type="owned",
                    status="available",
                    equipment_type=data["equipment_type"],
                    commodity_type=data["commodity_type"],
                    is_partial=False,
                    is_hazmat=False,
                    posted_carrier_rate=data["posted_carrier_rate"],
                    max_buy=data["max_buy"],
                    weight=data["weight"],
                    number_of_pieces=data["pieces"],
                    miles=data["miles"],
                    dimensions=data["dimensions"],
                    sale_notes=data["sale_notes"],
                    origin_city=origin_city,
                    origin_state=origin_state,
                    origin_zip=origin_zip,
                    origin_country="US",
                    origin_open=data["pickup"],
                    origin_close=data["pickup_close"],
                    destination_city=dest_city,
                    destination_state=dest_state,
                    destination_zip=dest_zip,
                    destination_country="US",
                    destination_open=data["delivery"],
                    destination_close=data["delivery_close"],
                )
            )
            inserted += 1
        db.commit()
        print(f"Seed complete: {inserted} inserted, {skipped} skipped (already present).")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
