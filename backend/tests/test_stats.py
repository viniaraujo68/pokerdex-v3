"""Stats and evolution maths: ranking, averages, ROI, record seeding and the
shared-x-axis contract the frontend chart depends on."""
import pytest

from conftest import entry


def records_by_label(stats: dict) -> dict:
    return {r["label"]: r for r in stats["records"]}


def ranking_by_name(stats: dict) -> dict:
    return {r["name"]: r for r in stats["ranking"]}


# ---------- records ----------
def test_no_phantom_zero_win_record_when_nobody_ever_won(api):
    """Records seed as None, not 0 — otherwise a group of pure losers reports a
    'R$ 0,00 by nobody' best win."""
    gid = api.group()
    q1, q2 = api.participant(gid, "Q1"), api.participant(gid, "Q2")
    api.night(gid, "2026-02-01", [entry(q1, 10000, 0), entry(q2, 10000, 2000)])

    recs = records_by_label(api.get(f"/api/groups/{gid}/stats").json())
    win = recs["Maior vitória numa noite"]
    loss = recs["Maior derrota numa noite"]
    assert win["value_cents"] is None and win["participant_name"] is None
    assert win["night_date"] is None
    assert loss["value_cents"] == -10000 and loss["participant_name"] == "Q1"
    assert loss["night_date"] == "2026-02-01"


def test_records_track_the_extremes_across_nights(api):
    gid = api.group()
    a, b = api.participant(gid, "A"), api.participant(gid, "B")
    api.night(gid, "2026-02-01", [entry(a, 10000, 15000), entry(b, 10000, 5000)])
    api.night(gid, "2026-02-08", [entry(a, 10000, 40000), entry(b, 10000, 0)])  # both extremes here
    api.night(gid, "2026-02-15", [entry(a, 10000, 12000), entry(b, 10000, 8000)])

    recs = records_by_label(api.get(f"/api/groups/{gid}/stats").json())
    assert (recs["Maior vitória numa noite"]["participant_name"],
            recs["Maior vitória numa noite"]["value_cents"],
            recs["Maior vitória numa noite"]["night_date"]) == ("A", 30000, "2026-02-08")
    assert (recs["Maior derrota numa noite"]["participant_name"],
            recs["Maior derrota numa noite"]["value_cents"]) == ("B", -10000)


def test_break_even_night_sets_no_record(api):
    """profit == 0 counts as neither a win nor a loss."""
    gid = api.group()
    p = api.participant(gid, "Zero")
    api.night(gid, "2026-02-01", [entry(p, 10000, 10000)])
    recs = records_by_label(api.get(f"/api/groups/{gid}/stats").json())
    assert all(r["value_cents"] is None for r in recs.values())


# ---------- ranking / averages / ROI ----------
def test_nights_played_counts_distinct_nights(api):
    gid = api.group()
    p = api.participant(gid, "Solo")
    api.night(gid, "2026-02-01", [entry(p, 10000, 0)])
    stats = api.get(f"/api/groups/{gid}/stats").json()
    assert stats["total_nights"] == 1
    assert ranking_by_name(stats)["Solo"]["nights_played"] == 1


def test_nights_played_ignores_duplicate_legacy_entries(api):
    """Legacy imports can hold two entries for one participant in one night. They must
    still count as a single night played, or averages get halved."""
    from sqlmodel import Session as DBSession

    from app.db import engine
    from app.models import NightEntry

    gid = api.group()
    p = api.participant(gid, "Duplicado")
    night = api.night(gid, "2026-02-01", [entry(p, 10000, 12000)])
    with DBSession(engine) as db:  # bypass the API, which rightly rejects duplicates
        db.add(NightEntry(night_id=night["id"], participant_id=p,
                          buy_in_cents=10000, cash_out_cents=12000, profit_cents=2000))
        db.commit()

    row = ranking_by_name(api.get(f"/api/groups/{gid}/stats").json())["Duplicado"]
    assert row["nights_played"] == 1
    assert row["total_profit_cents"] == 4000        # both entries still count for money
    assert row["avg_profit_cents"] == 4000          # ...but over one night, not two


def test_avg_profit_is_rounded_to_the_nearest_cent(api):
    gid = api.group()
    p = api.participant(gid, "Media")
    for i, profit in enumerate((33, 33, 34)):       # total 100 over 3 nights -> 33.33...
        api.night(gid, f"2026-02-{i + 1:02d}", [entry(p, 1000, 1000 + profit)])
    row = ranking_by_name(api.get(f"/api/groups/{gid}/stats").json())["Media"]
    assert row["total_profit_cents"] == 100
    assert row["nights_played"] == 3
    assert row["avg_profit_cents"] == 33
    assert isinstance(row["avg_profit_cents"], int)


def test_avg_profit_is_negative_for_a_losing_player(api):
    gid = api.group()
    p = api.participant(gid, "Perdedor")
    api.night(gid, "2026-02-01", [entry(p, 10000, 0)])
    api.night(gid, "2026-02-02", [entry(p, 10000, 5000)])
    row = ranking_by_name(api.get(f"/api/groups/{gid}/stats").json())["Perdedor"]
    assert row["total_profit_cents"] == -15000
    assert row["avg_profit_cents"] == -7500


def test_roi_is_profit_over_buy_in(api):
    gid = api.group()
    p = api.participant(gid, "Roi")
    api.night(gid, "2026-02-01", [entry(p, 10000, 15000)])   # +5000 on 10000 staked
    row = ranking_by_name(api.get(f"/api/groups/{gid}/stats").json())["Roi"]
    assert row["total_buy_in_cents"] == 10000
    assert row["roi"] == pytest.approx(0.5)


def test_roi_is_none_when_buy_in_is_zero(api):
    """Never divide by zero: a freeroll-style night has no denominator, so ROI is null
    rather than 0 or infinity."""
    gid = api.group()
    p = api.participant(gid, "Freeroll")
    api.night(gid, "2026-02-01", [entry(p, 0, 5000)])
    row = ranking_by_name(api.get(f"/api/groups/{gid}/stats").json())["Freeroll"]
    assert row["total_buy_in_cents"] == 0
    assert row["roi"] is None
    assert row["total_profit_cents"] == 5000


def test_ranking_is_sorted_by_total_profit_descending(api):
    gid = api.group()
    names = {n: api.participant(gid, n) for n in ("Rico", "Medio", "Pobre")}
    api.night(gid, "2026-02-01", [
        entry(names["Rico"], 10000, 30000),
        entry(names["Medio"], 10000, 11000),
        entry(names["Pobre"], 10000, 0),
    ])
    stats = api.get(f"/api/groups/{gid}/stats").json()
    assert [r["name"] for r in stats["ranking"]] == ["Rico", "Medio", "Pobre"]
    assert [r["total_profit_cents"] for r in stats["ranking"]] == [20000, 1000, -10000]


def test_ranking_excludes_participants_who_never_played(api):
    gid = api.group()
    played = api.participant(gid, "Jogou")
    api.participant(gid, "Nunca Jogou")
    api.night(gid, "2026-02-01", [entry(played, 1000, 1000)])
    assert [r["name"] for r in api.get(f"/api/groups/{gid}/stats").json()["ranking"]] == ["Jogou"]


def test_deactivated_participant_keeps_their_stats(api):
    """Soft delete exists precisely so history survives."""
    gid = api.group()
    p = api.participant(gid, "Saiu")
    api.night(gid, "2026-02-01", [entry(p, 10000, 15000)])
    assert api.delete(f"/api/groups/{gid}/participants/{p}").status_code == 204
    row = ranking_by_name(api.get(f"/api/groups/{gid}/stats").json())["Saiu"]
    assert row["total_profit_cents"] == 5000


# ---------- evolution ----------
@pytest.fixture
def evolution_group(api):
    gid = api.group()
    early = api.participant(gid, "Dudu")
    late = api.participant(gid, "Zeca")
    api.night(gid, "2026-03-01", [entry(early, 10000, 15000)])
    api.night(gid, "2026-03-08", [entry(early, 10000, 5000)])
    api.night(gid, "2026-03-15", [entry(early, 10000, 12000), entry(late, 10000, 8000)])
    return api.get(f"/api/groups/{gid}/evolution").json()


def test_evolution_x_axis_is_one_point_per_night(evolution_group):
    assert evolution_group["dates"] == ["2026-03-01", "2026-03-08", "2026-03-15"]


def test_every_series_has_exactly_len_dates_points(evolution_group):
    n = len(evolution_group["dates"])
    assert all(len(s["points"]) == n for s in evolution_group["series"])


def test_late_joiner_is_left_padded_with_nulls(evolution_group):
    """data[i] must line up with labels[i] in the chart, so a player who debuts on night 3
    gets nulls (not zeros) for nights 1-2."""
    late = next(s for s in evolution_group["series"] if s["name"] == "Zeca")
    assert [p["cumulative_cents"] for p in late["points"]] == [None, None, -2000]
    assert [p["date"] for p in late["points"]] == evolution_group["dates"]


def test_absent_player_carries_their_total_forward(evolution_group):
    early = next(s for s in evolution_group["series"] if s["name"] == "Dudu")
    assert [p["cumulative_cents"] for p in early["points"]] == [5000, 0, 2000]


def test_evolution_series_sorted_by_final_total(evolution_group):
    finals = [s["points"][-1]["cumulative_cents"] for s in evolution_group["series"]]
    assert finals == sorted(finals, reverse=True)


def test_evolution_ignores_soft_deleted_nights(api):
    gid = api.group()
    p = api.participant(gid, "P")
    api.night(gid, "2026-03-01", [entry(p, 10000, 15000)])
    doomed = api.night(gid, "2026-03-08", [entry(p, 10000, 0)])
    api.delete(f"/api/groups/{gid}/nights/{doomed['id']}")
    ev = api.get(f"/api/groups/{gid}/evolution").json()
    assert ev["dates"] == ["2026-03-01"]
    assert ev["series"][0]["points"][-1]["cumulative_cents"] == 5000
