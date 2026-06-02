"""Import legacy Pokerdex data (MongoDB exports) into the new SQLite schema.

The old model only stored each player's NET PROFIT per night (no buy-in/cash-out),
so we import with buy_in = 0 and cash_out = profit. Profit is preserved exactly;
legacy nights will show pot = R$ 0 and no ROI (by design — these are old records,
kept in a separate group from the better-tracked future ones).

players.json is used as a checksum: after import we recompute each participant's
total profit and night count from the imported entries and assert they match.

Usage (run from the backend/ directory, with the venv active):

    python scripts/import_legacy.py \
        --players ../players.json \
        --nights ../nights.json \
        --owner laura \
        --group-name "Sextodex Legacy" \
        --visibility public

If the owner user doesn't exist, pass --owner-password to create it.
The target database is taken from POKERDEX_DATABASE_URL (same as the app).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

# Make `app` importable when running as a plain script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, select  # noqa: E402

from app.db import engine, init_db  # noqa: E402
from app import models  # noqa: E402
from app.security import hash_password  # noqa: E402
from app.services import unique_slug  # noqa: E402


def to_cents(value: float) -> int:
    """Round a float amount (reais) to integer cents, killing float noise."""
    return round(float(value) * 100)


def parse_date(raw) -> date:
    # Mongo export: {"$date": "2024-09-16T00:00:00.000Z"}
    s = raw["$date"] if isinstance(raw, dict) else raw
    return date.fromisoformat(s[:10])


def load(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def get_or_create_owner(db: Session, username: str, password: str | None) -> models.User:
    user = db.exec(select(models.User).where(models.User.username == username)).first()
    if user:
        return user
    if not password:
        sys.exit(
            f"Usuário '{username}' não existe. Passe --owner-password para criá-lo, "
            f"ou registre a conta primeiro."
        )
    user = models.User(username=username, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    print(f"  + criado usuário dono '{username}'")
    return user


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--players", required=True)
    ap.add_argument("--nights", required=True)
    ap.add_argument("--owner", required=True, help="username do dono do grupo")
    ap.add_argument("--owner-password", default=None, help="cria o dono se ele não existir")
    ap.add_argument("--group-name", default="Sextodex Legacy")
    ap.add_argument("--visibility", default="public", choices=["public", "private"])
    ap.add_argument("--force", action="store_true", help="importa mesmo se o grupo já existir")
    args = ap.parse_args()

    players = load(args.players)
    nights = load(args.nights)
    print(f"Lidos {len(players)} players e {len(nights)} nights.")

    init_db()
    with Session(engine) as db:
        owner = get_or_create_owner(db, args.owner, args.owner_password)

        existing = db.exec(
            select(models.Group).where(models.Group.name == args.group_name)
        ).first()
        if existing and not args.force:
            sys.exit(
                f"Já existe um grupo '{args.group_name}'. Use --force para importar mesmo assim "
                f"(vai criar um grupo duplicado)."
            )

        group = models.Group(
            name=args.group_name,
            slug=unique_slug(db, args.group_name),
            description="Histórico importado do Pokerdex original.",
            visibility=args.visibility,
        )
        db.add(group)
        db.commit()
        db.refresh(group)
        db.add(models.GroupOwner(group_id=group.id, user_id=owner.id))
        db.commit()
        print(f"  + grupo '{group.name}' (slug: {group.slug}) criado para '{owner.username}'")

        # Participants — seed from players.json, create on the fly if a night has extras.
        participants: dict[str, models.Participant] = {}

        def participant(name: str) -> models.Participant:
            if name not in participants:
                p = models.Participant(group_id=group.id, name=name)
                db.add(p)
                db.commit()
                db.refresh(p)
                participants[name] = p
            return participants[name]

        for pl in players:
            participant(pl["name"])

        # Places — dedupe by name.
        places: dict[str, models.Place] = {}

        def place(name: str) -> models.Place | None:
            if not name:
                return None
            if name not in places:
                pl = models.Place(group_id=group.id, name=name)
                db.add(pl)
                db.commit()
                db.refresh(pl)
                places[name] = pl
            return places[name]

        # Nights + entries (buy_in = 0, cash_out = profit).
        for n in nights:
            place_obj = place(n.get("place", "").strip())
            night = models.Night(
                group_id=group.id,
                date=parse_date(n["date"]),
                place_id=place_obj.id if place_obj else None,
            )
            for entry in n.get("players", []):
                profit_cents = to_cents(entry["profit"])
                night.entries.append(
                    models.NightEntry(
                        participant_id=participant(entry["playerName"]).id,
                        buy_in_cents=0,
                        cash_out_cents=profit_cents,
                        profit_cents=profit_cents,
                    )
                )
            db.add(night)
        db.commit()
        print(f"  + {len(nights)} noites importadas, {len(participants)} participantes, "
              f"{len(places)} locais")

        # ---- Validation against players.json (the checksum) ----
        recomputed_profit: dict[int, int] = defaultdict(int)
        recomputed_nights: dict[int, int] = defaultdict(int)
        all_nights = db.exec(
            select(models.Night).where(models.Night.group_id == group.id)
        ).all()
        for night in all_nights:
            for e in night.entries:
                recomputed_profit[e.participant_id] += e.profit_cents
                recomputed_nights[e.participant_id] += 1

        print("\nValidação (recalculado x backup):")
        mismatches = 0
        for pl in sorted(players, key=lambda x: x["name"]):
            p = participants[pl["name"]]
            got_profit = recomputed_profit[p.id]
            exp_profit = to_cents(pl["totalProfit"])
            got_nights = recomputed_nights[p.id]
            exp_nights = pl["nightNumber"]
            ok = got_profit == exp_profit and got_nights == exp_nights
            mark = "✓" if ok else "✗"
            if not ok:
                mismatches += 1
            print(
                f"  {mark} {pl['name']:<10} lucro {got_profit/100:>8.2f} "
                f"(backup {exp_profit/100:>8.2f}) | noites {got_nights} (backup {exp_nights})"
            )

        if mismatches:
            print(f"\n⚠️  {mismatches} divergência(s) — revise antes de usar em produção.")
            sys.exit(1)
        print(f"\n✅ Importação validada: todos os {len(players)} participantes batem com o backup.")


if __name__ == "__main__":
    main()
