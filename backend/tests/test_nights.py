"""Night CRUD: cross-group reference rejection (IDOR), money bounds, pot balance
reporting and the listing contract. Ported from the throwaway smoke script."""
import pytest

from conftest import entry


@pytest.fixture
def scene(api, other_api):
    """Two tenants side by side, so every 'foreign id' case has a real foreign id."""
    mine = api.group("Meu Grupo")
    theirs = other_api.group("Grupo Alheio")
    return {
        "api": api, "other": other_api, "gid": mine, "other_gid": theirs,
        "p1": api.participant(mine, "Ana"), "p2": api.participant(mine, "Artur"),
        "place": api.place(mine, "Casa da Ana"),
        "other_p": other_api.participant(theirs, "Beto"),
        "other_place": other_api.place(theirs, "Casa do Beto"),
    }


# ---------- IDOR / scoping ----------
def test_create_rejects_foreign_participant(scene):
    r = scene["api"].post(f"/api/groups/{scene['gid']}/nights", json={
        "date": "2026-01-10", "entries": [entry(scene["other_p"], 5000, 0)]})
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "participant_in_other_group"


def test_create_rejects_foreign_place(scene):
    r = scene["api"].post(f"/api/groups/{scene['gid']}/nights", json={
        "date": "2026-01-10", "place_id": scene["other_place"],
        "entries": [entry(scene["p1"], 5000, 0)]})
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "place_in_other_group"


def test_create_rejects_duplicate_participant(scene):
    r = scene["api"].post(f"/api/groups/{scene['gid']}/nights", json={
        "date": "2026-01-10",
        "entries": [entry(scene["p1"], 5000, 0), entry(scene["p1"], 5000, 10000)]})
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "duplicate_participant"


def test_update_rejects_foreign_participant_and_place(scene):
    api, gid = scene["api"], scene["gid"]
    night = api.night(gid, "2026-01-10", [entry(scene["p1"], 10000, 10000)])
    r = api.put(f"/api/groups/{gid}/nights/{night['id']}", json={
        "date": "2026-01-10", "place_id": scene["other_place"],
        "entries": [entry(scene["p1"], 100, 100)]})
    assert r.status_code == 400
    r = api.put(f"/api/groups/{gid}/nights/{night['id']}", json={
        "date": "2026-01-10", "entries": [entry(scene["other_p"], 100, 100)]})
    assert r.status_code == 400


def test_foreign_group_can_still_be_deleted(scene):
    """A night pointing at another tenant's rows used to leave dangling FKs that blocked
    the other group's delete. Rejecting the reference keeps that group deletable."""
    assert scene["other"].delete(f"/api/groups/{scene['other_gid']}").status_code == 204


def test_night_from_another_group_is_not_reachable(scene):
    """Right owner, wrong group in the path: must 404, never serve another group's night."""
    api, other = scene["api"], scene["other"]
    theirs = other.group()
    p = other.participant(theirs)
    night = other.night(theirs, "2026-01-05", [entry(p, 1000, 1000)])
    assert api.get(f"/api/groups/{scene['gid']}/nights/{night['id']}").status_code == 404


# ---------- money bounds ----------
@pytest.mark.parametrize(
    "buy_in,cash_out",
    [
        (-100, 0),        # negative buy-in
        (0, -1),          # negative cash-out
        (2 ** 63, 0),     # would raise OverflowError on insert without the bound
        (0, 2 ** 63),
        (10 ** 12 + 1, 0),  # just past MONEY_MAX_CENTS
    ],
)
def test_money_out_of_bounds_is_422(scene, buy_in, cash_out):
    r = scene["api"].post(f"/api/groups/{scene['gid']}/nights", json={
        "date": "2026-01-10", "entries": [entry(scene["p1"], buy_in, cash_out)]})
    assert r.status_code == 422


def test_money_at_the_bounds_is_accepted(scene):
    from app.schemas import MONEY_MAX_CENTS

    r = scene["api"].post(f"/api/groups/{scene['gid']}/nights", json={
        "date": "2026-01-11",
        "entries": [entry(scene["p1"], MONEY_MAX_CENTS, 0), entry(scene["p2"], 0, 0)]})
    assert r.status_code == 201
    assert r.json()["total_pot_cents"] == MONEY_MAX_CENTS


# ---------- normal operation / pot balance ----------
def test_create_night_resolves_place_and_balances_a_closed_pot(scene):
    night = scene["api"].night(
        scene["gid"], "2026-01-10",
        [entry(scene["p1"], 10000, 0), entry(scene["p2"], 10000, 20000)],
        place_id=scene["place"])
    assert night["place_name"] == "Casa da Ana"
    assert night["total_pot_cents"] == 20000
    assert night["balance_cents"] == 0
    profits = {e["participant_name"]: e["profit_cents"] for e in night["entries"]}
    assert profits == {"Ana": -10000, "Artur": 10000}


def test_unbalanced_pot_saves_and_reports_the_gap(scene):
    """Chips walk off the table in real life; the API records the night and surfaces the
    imbalance instead of refusing the entry."""
    night = scene["api"].night(scene["gid"], "2026-01-17",
                               [entry(scene["p1"], 10000, 5000), entry(scene["p2"], 10000, 1000)])
    assert night["balance_cents"] == -14000
    assert night["total_pot_cents"] == 20000


def test_night_without_place_has_null_place_name(scene):
    night = scene["api"].night(scene["gid"], "2026-01-18", [entry(scene["p1"], 100, 100)])
    assert night["place_id"] is None and night["place_name"] is None


def test_update_night_replaces_entries(scene):
    api, gid = scene["api"], scene["gid"]
    night = api.night(gid, "2026-01-10", [entry(scene["p1"], 10000, 10000)])
    r = api.put(f"/api/groups/{gid}/nights/{night['id']}", json={
        "date": "2026-01-12", "place_id": scene["place"],
        "entries": [entry(scene["p2"], 5000, 7000)]})
    assert r.status_code == 200
    body = r.json()
    assert body["date"] == "2026-01-12"
    assert [e["participant_name"] for e in body["entries"]] == ["Artur"]
    assert body["balance_cents"] == 2000


def test_soft_deleted_night_disappears_from_listing_and_stats(scene):
    api, gid = scene["api"], scene["gid"]
    api.night(gid, "2026-01-10", [entry(scene["p1"], 10000, 20000)])
    doomed = api.night(gid, "2026-01-11", [entry(scene["p1"], 10000, 0)])
    assert api.delete(f"/api/groups/{gid}/nights/{doomed['id']}").status_code == 204
    assert doomed["id"] not in [n["id"] for n in api.get(f"/api/groups/{gid}/nights").json()]
    assert api.get(f"/api/groups/{gid}/nights/{doomed['id']}").status_code == 404
    # Stats are derived from live nights only.
    stats = api.get(f"/api/groups/{gid}/stats").json()
    assert stats["total_nights"] == 1
    assert stats["ranking"][0]["total_profit_cents"] == 10000


# ---------- listing contract ----------
def test_listing_returns_every_night_newest_first(scene):
    """No pagination on this endpoint: a group's whole history comes back in one call,
    ordered newest-first (ties broken by id)."""
    api, gid = scene["api"], scene["gid"]
    made = [api.night(gid, f"2026-03-{d:02d}", [entry(scene["p1"], 1000, 1000)])["id"]
            for d in range(1, 13)]
    # Two nights on the same date to pin the tie-break.
    same_a = api.night(gid, "2026-04-01", [entry(scene["p1"], 1000, 1000)])["id"]
    same_b = api.night(gid, "2026-04-01", [entry(scene["p2"], 1000, 1000)])["id"]

    listed = api.get(f"/api/groups/{gid}/nights").json()
    ids = [n["id"] for n in listed]
    assert len(ids) == len(made) + 2 and set(made) <= set(ids)
    assert ids[:2] == [same_b, same_a]
    dates = [n["date"] for n in listed]
    assert dates == sorted(dates, reverse=True)


def test_empty_group_listing_and_stats_are_empty_not_errors(api):
    gid = api.group()
    assert api.get(f"/api/groups/{gid}/nights").json() == []
    stats = api.get(f"/api/groups/{gid}/stats").json()
    assert stats["total_nights"] == 0 and stats["ranking"] == []
    assert all(rec["value_cents"] is None for rec in stats["records"])
    evolution = api.get(f"/api/groups/{gid}/evolution").json()
    assert evolution == {"dates": [], "series": []}


def test_night_with_no_entries_is_allowed(scene):
    night = scene["api"].night(scene["gid"], "2026-06-01", [])
    assert night["entries"] == []
    assert night["total_pot_cents"] == 0 and night["balance_cents"] == 0
