"""Cross-tenant authorization matrix: every group-scoped route must refuse a logged-in
user who does not own the group (403) and an anonymous caller (401). This is the check
that catches a router being added without `Depends(require_owner)`."""
import pytest

from conftest import entry


@pytest.fixture(scope="module")
def victim():
    """Owner of a fully populated group, built once for the whole matrix."""
    from conftest import Api

    api = Api()
    gid = api.group()
    pid = api.participant(gid)
    plid = api.place(gid)
    night = api.night(gid, "2026-01-10", [entry(pid, 10000, 12000)], place_id=plid)
    return {"api": api, "group_id": gid, "participant_id": pid, "place_id": plid,
            "night_id": night["id"]}


def routes(v):
    """(method, path, json_body) for every group-scoped endpoint."""
    g, p, pl, n = v["group_id"], v["participant_id"], v["place_id"], v["night_id"]
    night_body = {"date": "2026-02-02", "entries": []}
    return [
        ("GET", f"/api/groups/{g}", None),
        ("PATCH", f"/api/groups/{g}", {"name": "Invadido"}),
        ("DELETE", f"/api/groups/{g}", None),
        ("POST", f"/api/groups/{g}/rotate-share-token", None),
        ("GET", f"/api/groups/{g}/participants", None),
        ("POST", f"/api/groups/{g}/participants", {"name": "Intruso"}),
        ("PATCH", f"/api/groups/{g}/participants/{p}", {"id": p, "name": "Zé", "active": True}),
        ("DELETE", f"/api/groups/{g}/participants/{p}", None),
        ("GET", f"/api/groups/{g}/places", None),
        ("POST", f"/api/groups/{g}/places", {"name": "Casa Invadida"}),
        ("DELETE", f"/api/groups/{g}/places/{pl}", None),
        ("GET", f"/api/groups/{g}/nights", None),
        ("POST", f"/api/groups/{g}/nights", night_body),
        ("GET", f"/api/groups/{g}/nights/{n}", None),
        ("PUT", f"/api/groups/{g}/nights/{n}", night_body),
        ("DELETE", f"/api/groups/{g}/nights/{n}", None),
        ("GET", f"/api/groups/{g}/stats", None),
        ("GET", f"/api/groups/{g}/evolution", None),
    ]


def _ids(v):
    return [f"{m} {path}" for m, path, _ in routes(v)]


def test_matrix_covers_every_group_scoped_route(victim):
    """Guard against the matrix silently going stale when a route is added."""
    from app.main import app

    declared = {
        (method, route.path)
        for route in app.routes
        for method in getattr(route, "methods", set())
        if getattr(route, "path", "").startswith("/api/groups/{group_id}")
    }
    # /api/groups/{group_id}... templates covered by the matrix above:
    covered = {
        ("GET", "/api/groups/{group_id}"), ("PATCH", "/api/groups/{group_id}"),
        ("DELETE", "/api/groups/{group_id}"),
        ("POST", "/api/groups/{group_id}/rotate-share-token"),
        ("GET", "/api/groups/{group_id}/participants"),
        ("POST", "/api/groups/{group_id}/participants"),
        ("PATCH", "/api/groups/{group_id}/participants/{participant_id}"),
        ("DELETE", "/api/groups/{group_id}/participants/{participant_id}"),
        ("GET", "/api/groups/{group_id}/places"),
        ("POST", "/api/groups/{group_id}/places"),
        ("DELETE", "/api/groups/{group_id}/places/{item_id}"),
        ("GET", "/api/groups/{group_id}/nights"),
        ("POST", "/api/groups/{group_id}/nights"),
        ("GET", "/api/groups/{group_id}/nights/{night_id}"),
        ("PUT", "/api/groups/{group_id}/nights/{night_id}"),
        ("DELETE", "/api/groups/{group_id}/nights/{night_id}"),
        ("GET", "/api/groups/{group_id}/stats"),
        ("GET", "/api/groups/{group_id}/evolution"),
    }
    missing = declared - covered
    assert not missing, f"group-scoped routes missing from the authz matrix: {sorted(missing)}"


def test_non_owner_gets_403_on_every_route(victim, other_api):
    """One user, many routes: a 200/204 anywhere here is a tenant isolation break."""
    failures = []
    for method, path, body in routes(victim):
        r = other_api.client.request(method, path, json=body)
        if r.status_code != 403:
            failures.append((method, path, r.status_code, r.text[:120]))
    assert not failures, f"expected 403 on all, got: {failures}"


def test_anonymous_gets_401_on_every_route(victim, client):
    failures = []
    for method, path, body in routes(victim):
        r = client.request(method, path, json=body)
        if r.status_code != 401:
            failures.append((method, path, r.status_code))
    assert not failures, f"expected 401 on all, got: {failures}"


def test_victims_data_survived_the_matrix(victim):
    """The 403s must have been refusals, not partially applied writes."""
    v = victim
    api = v["api"]
    assert api.get(f"/api/groups/{v['group_id']}").status_code == 200
    assert len(api.get(f"/api/groups/{v['group_id']}/nights").json()) == 1
    assert len(api.get(f"/api/groups/{v['group_id']}/participants").json()) == 1
    assert len(api.get(f"/api/groups/{v['group_id']}/places").json()) == 1


def test_group_list_only_returns_own_groups(api, other_api):
    mine = api.group()
    theirs = other_api.group()
    assert mine in [g["id"] for g in api.get("/api/groups").json()]
    assert theirs not in [g["id"] for g in api.get("/api/groups").json()]
    assert mine not in [g["id"] for g in other_api.get("/api/groups").json()]


def test_nonexistent_group_is_403_not_404(api):
    """require_owner runs before the row lookup, so a probe can't enumerate group ids."""
    assert api.get("/api/groups/99999999").status_code == 403
