"""Query-count regression guards.

These assert the *shape* of the query load, not an exact number: a request's query count
must not grow with the number of nights or groups it renders. That is what distinguishes
"one selectinload" from "one lazy load per row", and it is what regresses silently when
someone drops an eager-load option or moves a count back inside a loop.
"""
from conftest import entry


def count_for(queries, fn):
    with queries:
        r = fn()
        assert r.status_code == 200, r.text
    return queries.count


def build_group(api, nights: int, participants: int = 4):
    gid = api.group()
    pids = [api.participant(gid) for _ in range(participants)]
    place = api.place(gid)
    for n in range(nights):
        api.night(gid, f"2026-01-{(n % 28) + 1:02d}",
                  [entry(p, 10000, 10000 + (100 if i else -100)) for i, p in enumerate(pids)],
                  place_id=place)
    return gid


def build_group_more(api, gid, extra: int):
    pids = [p["id"] for p in api.get(f"/api/groups/{gid}/participants").json()]
    for n in range(extra):
        api.night(gid, f"2026-02-{(n % 28) + 1:02d}", [entry(p, 10000, 10000) for p in pids])


def test_stats_query_count_is_independent_of_night_count(api, queries):
    """Was ~1 + N (one lazy entries load per night); now a fixed handful."""
    gid = build_group(api, nights=3)
    few = count_for(queries, lambda: api.get(f"/api/groups/{gid}/stats"))
    build_group_more(api, gid, extra=17)
    many = count_for(queries, lambda: api.get(f"/api/groups/{gid}/stats"))
    assert few == many, f"N+1 on stats: 3 nights={few}, 20 nights={many}"
    assert many <= 8, f"stats got chattier: {many} queries"


def test_evolution_query_count_is_independent_of_night_count(api, queries):
    gid = build_group(api, nights=3)
    few = count_for(queries, lambda: api.get(f"/api/groups/{gid}/evolution"))
    build_group_more(api, gid, extra=17)
    many = count_for(queries, lambda: api.get(f"/api/groups/{gid}/evolution"))
    assert few == many, f"N+1 on evolution: 3 nights={few}, 20 nights={many}"
    assert many <= 8


def test_nights_listing_query_count_is_independent_of_night_count(api, queries):
    """Two N+1s used to live here: the entries lazy load and one db.get(Place) per night."""
    gid = build_group(api, nights=3)
    few = count_for(queries, lambda: api.get(f"/api/groups/{gid}/nights"))
    build_group_more(api, gid, extra=17)
    many = count_for(queries, lambda: api.get(f"/api/groups/{gid}/nights"))
    assert few == many, f"N+1 on nights listing: 3 nights={few}, 20 nights={many}"
    assert many <= 9


def test_nights_listing_does_not_query_per_place(api, queries):
    """Distinct place per night: place names must come from one prebuilt dict."""
    gid = api.group()
    p = api.participant(gid)
    with_one_place = api.place(gid)
    for n in range(6):
        api.night(gid, f"2026-05-{n + 1:02d}", [entry(p, 1000, 1000)], place_id=with_one_place)
    one = count_for(queries, lambda: api.get(f"/api/groups/{gid}/nights"))

    gid2 = api.group()
    p2 = api.participant(gid2)
    for n in range(6):
        api.night(gid2, f"2026-05-{n + 1:02d}", [entry(p2, 1000, 1000)],
                  place_id=api.place(gid2))  # 6 distinct places
    six = count_for(queries, lambda: api.get(f"/api/groups/{gid2}/nights"))
    assert one == six, f"place lookups scale with distinct places: {one} vs {six}"


def test_group_listing_query_count_is_independent_of_group_count(api, queries):
    """The 2-count-queries-per-group pattern is now 2 grouped queries per request."""
    api.group()
    one = count_for(queries, lambda: api.get("/api/groups"))
    for _ in range(5):
        gid = api.group()
        api.participant(gid)
    six = count_for(queries, lambda: api.get("/api/groups"))
    assert one == six, f"counts still run per group: 1 group={one}, 6 groups={six}"
    assert six <= 7


def test_public_listing_query_count_is_independent_of_group_count(api, queries):
    q = "Consulta Publica Epsilon"
    api.group(f"{q} A", visibility="public")
    one = count_for(queries, lambda: api.get("/api/public", params={"q": q}))
    for i in range(4):
        gid = api.group(f"{q} {i}", visibility="public")
        api.participant(gid)
    five = count_for(queries, lambda: api.get("/api/public", params={"q": q}))
    assert one == five, f"counts still run per group: 1={one}, 5={five}"
    assert five <= 4


def test_public_detail_query_count_is_independent_of_night_count(api, queries):
    gid = api.group(visibility="public")
    slug = api.last_group["slug"]
    pids = [api.participant(gid) for _ in range(4)]
    place = api.place(gid)
    for n in range(3):
        api.night(gid, f"2026-01-{n + 1:02d}", [entry(p, 1000, 1000) for p in pids], place_id=place)
    few = count_for(queries, lambda: api.get(f"/api/public/{slug}"))
    for n in range(17):
        api.night(gid, f"2026-02-{n + 1:02d}", [entry(p, 1000, 1000) for p in pids], place_id=place)
    many = count_for(queries, lambda: api.get(f"/api/public/{slug}"))
    assert few == many, f"N+1 on public detail: 3 nights={few}, 20 nights={many}"
    assert many <= 12


def test_entries_are_eager_loaded_by_active_nights(api, queries):
    """Unit-level: touching night.entries after active_nights() must issue no SQL."""
    from sqlmodel import Session as DBSession

    from app import services
    from app.db import engine

    gid = build_group(api, nights=5)
    with DBSession(engine) as db:
        with queries:
            nights = services.active_nights(db, gid)
            total = sum(e.profit_cents for n in nights for e in n.entries)
        assert len(nights) == 5
        assert total is not None
        # 1 for the nights, 1 selectinload for all their entries.
        assert queries.count == 2, queries.statements


def test_busy_timeout_pragma_is_set_on_every_connection():
    """SQLite serializes writers; without busy_timeout a concurrent write fails instantly
    with 'database is locked' instead of waiting."""
    from sqlalchemy import text

    from app.db import engine

    with engine.connect() as conn:
        assert conn.execute(text("PRAGMA busy_timeout")).scalar() == 5000
        assert conn.execute(text("PRAGMA foreign_keys")).scalar() == 1
        assert conn.execute(text("PRAGMA journal_mode")).scalar().lower() == "wal"
