"""Group and catalog lifecycle: atomic create, cascading delete, and the conflict paths
that must surface as 409 with a pt-BR message instead of a raw 500."""
from conftest import entry


# ---------- atomic group creation ----------
def test_create_group_is_atomic_group_plus_ownership(api):
    """Group row and ownership row land in one transaction; a half-committed create would
    leave a group nobody can reach."""
    from sqlmodel import Session as DBSession
    from sqlmodel import select

    from app.db import engine
    from app.models import Group, GroupOwner

    gid = api.group("Atomico")
    with DBSession(engine) as db:
        assert db.get(Group, gid) is not None
        owners = db.exec(select(GroupOwner).where(GroupOwner.group_id == gid)).all()
    assert [o.user_id for o in owners] == [api.user_id]
    assert gid in [g["id"] for g in api.get("/api/groups").json()]


def test_slug_is_unique_across_groups_with_the_same_name(api, other_api):
    api.group("Sexta Poker")
    first = api.last_group["slug"]
    api.group("Sexta Poker")
    second = api.last_group["slug"]
    other_api.group("Sexta Poker")
    third = other_api.last_group["slug"]
    assert first == "sexta-poker"
    assert len({first, second, third}) == 3, (first, second, third)


def test_group_counts_reflect_nights_and_active_participants(api):
    gid = api.group()
    p1 = api.participant(gid)
    p2 = api.participant(gid)
    api.night(gid, "2026-01-01", [entry(p1, 1000, 1000)])
    api.night(gid, "2026-01-02", [entry(p1, 1000, 1000)])
    body = api.get(f"/api/groups/{gid}").json()
    assert body["night_count"] == 2 and body["participant_count"] == 2

    # A soft-deleted night and a deactivated participant drop out of the counts.
    doomed = api.night(gid, "2026-01-03", [entry(p2, 1000, 1000)])
    api.delete(f"/api/groups/{gid}/nights/{doomed['id']}")
    api.patch(f"/api/groups/{gid}/participants/{p2}",
              json={"id": p2, "name": "Inativo", "active": False})
    body = api.get(f"/api/groups/{gid}").json()
    assert body["night_count"] == 2 and body["participant_count"] == 1


def test_counts_are_per_group_not_global(api):
    """Batched grouped counts must not smear one group's totals onto another."""
    busy = api.group()
    quiet = api.group()
    p = api.participant(busy)
    for d in range(1, 4):
        api.night(busy, f"2026-01-{d:02d}", [entry(p, 1000, 1000)])
    listed = {g["id"]: g for g in api.get("/api/groups").json()}
    assert listed[busy]["night_count"] == 3 and listed[busy]["participant_count"] == 1
    assert listed[quiet]["night_count"] == 0 and listed[quiet]["participant_count"] == 0


def test_update_group_fields(api):
    gid = api.group()
    r = api.patch(f"/api/groups/{gid}", json={"name": "Renomeado", "description": "desc"})
    assert r.status_code == 200
    assert r.json()["name"] == "Renomeado" and r.json()["description"] == "desc"


def test_update_group_ignores_an_invalid_visibility(api):
    gid = api.group()
    before = api.get(f"/api/groups/{gid}").json()["visibility"]
    r = api.patch(f"/api/groups/{gid}", json={"visibility": "banana"})
    assert r.status_code == 200 and r.json()["visibility"] == before


def test_rotate_share_token_issues_a_new_secret(api):
    gid = api.group()
    first = api.post(f"/api/groups/{gid}/rotate-share-token").json()["share_token"]
    second = api.post(f"/api/groups/{gid}/rotate-share-token").json()["share_token"]
    assert first and second and first != second


# ---------- cascading delete ----------
def test_delete_group_with_children_succeeds_and_is_gone(api):
    gid = api.group("Descartavel")
    p = api.participant(gid)
    pl = api.place(gid)
    api.night(gid, "2026-04-01", [entry(p, 1000, 1000)], place_id=pl)

    assert api.delete(f"/api/groups/{gid}").status_code == 204
    assert api.get(f"/api/groups/{gid}").status_code in (403, 404)
    assert gid not in [g["id"] for g in api.get("/api/groups").json()]


def test_delete_group_leaves_no_orphan_rows(api):
    from sqlmodel import Session as DBSession
    from sqlmodel import select

    from app.db import engine
    from app.models import Group, GroupOwner, Night, NightEntry, Participant, Place

    gid = api.group()
    p = api.participant(gid)
    pl = api.place(gid)
    night = api.night(gid, "2026-04-01", [entry(p, 1000, 1000)], place_id=pl)
    api.delete(f"/api/groups/{gid}")

    with DBSession(engine) as db:
        assert db.get(Group, gid) is None
        assert db.exec(select(Night).where(Night.group_id == gid)).all() == []
        assert db.exec(select(NightEntry).where(NightEntry.night_id == night["id"])).all() == []
        assert db.exec(select(Participant).where(Participant.group_id == gid)).all() == []
        assert db.exec(select(Place).where(Place.group_id == gid)).all() == []
        assert db.exec(select(GroupOwner).where(GroupOwner.group_id == gid)).all() == []


# ---------- catalog conflicts ----------
def test_duplicate_participant_name_is_409(api):
    gid = api.group()
    api.participant(gid, "Repetido")
    r = api.post(f"/api/groups/{gid}/participants", json={"name": "Repetido"})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "participant_exists"


def test_rename_onto_an_existing_name_is_409_not_500(api):
    """The rename path has no up-front guard, so it hits the DB unique constraint. The
    global IntegrityError handler must turn that into a pt-BR 409."""
    gid = api.group()
    api.participant(gid, "Dudu")
    zeca = api.participant(gid, "Zeca")
    r = api.patch(f"/api/groups/{gid}/participants/{zeca}",
                  json={"id": zeca, "name": "Dudu", "active": True})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "integrity_conflict"


def test_same_participant_name_in_different_groups_is_fine(api):
    a, b = api.group(), api.group()
    api.participant(a, "Ana")
    assert api.post(f"/api/groups/{b}/participants", json={"name": "Ana"}).status_code == 201


def test_participant_without_history_is_hard_deleted(api):
    gid = api.group()
    p = api.participant(gid, "Efemero")
    assert api.delete(f"/api/groups/{gid}/participants/{p}").status_code == 204
    assert "Efemero" not in [x["name"] for x in api.get(f"/api/groups/{gid}/participants").json()]


def test_participant_with_history_is_deactivated_not_removed(api):
    gid = api.group()
    p = api.participant(gid, "Veterano")
    api.night(gid, "2026-01-01", [entry(p, 1000, 1000)])
    assert api.delete(f"/api/groups/{gid}/participants/{p}").status_code == 204
    listed = {x["name"]: x for x in api.get(f"/api/groups/{gid}/participants").json()}
    assert listed["Veterano"]["active"] is False


def test_participant_patch_reactivates_without_echoing_the_name(api):
    """The settings UI reactivates with `{"active": true}` alone — the name must survive."""
    gid = api.group()
    p = api.participant(gid, "Voltou")
    api.night(gid, "2026-01-01", [entry(p, 1000, 1000)])
    api.delete(f"/api/groups/{gid}/participants/{p}")  # history ⇒ deactivated

    r = api.patch(f"/api/groups/{gid}/participants/{p}", json={"active": True})
    assert r.status_code == 200
    assert r.json() == {"id": p, "name": "Voltou", "active": True}


def test_participant_patch_renames_without_touching_active(api):
    gid = api.group()
    p = api.participant(gid, "Antigo")
    api.night(gid, "2026-01-01", [entry(p, 1000, 1000)])
    api.delete(f"/api/groups/{gid}/participants/{p}")

    r = api.patch(f"/api/groups/{gid}/participants/{p}", json={"name": "Novo"})
    assert r.status_code == 200
    assert r.json()["name"] == "Novo" and r.json()["active"] is False


def test_participant_patch_rejects_a_blank_name(api):
    gid = api.group()
    p = api.participant(gid, "Nomeado")
    assert api.patch(f"/api/groups/{gid}/participants/{p}", json={"name": " "}).status_code == 200
    # whitespace survives (no trimming today), but an empty string must not
    assert api.patch(f"/api/groups/{gid}/participants/{p}", json={"name": ""}).status_code == 422


def test_duplicate_place_name_is_409(api):
    gid = api.group()
    api.place(gid, "Casa")
    r = api.post(f"/api/groups/{gid}/places", json={"name": "Casa"})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "place_exists"


def test_unused_place_is_deletable(api):
    gid = api.group()
    assert api.delete(f"/api/groups/{gid}/places/{api.place(gid, 'Livre')}").status_code == 204


def test_place_in_use_is_409_with_a_pt_br_message(api):
    """Deleting a referenced place must be refused up front — letting the FK fail would
    surface as an opaque 500/409 with no explanation."""
    gid = api.group()
    p = api.participant(gid)
    used = api.place(gid, "Em uso")
    api.night(gid, "2026-03-22", [entry(p, 1000, 1000)], place_id=used)

    r = api.delete(f"/api/groups/{gid}/places/{used}")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "place_in_use"
    assert "Em uso" in [x["name"] for x in api.get(f"/api/groups/{gid}/places").json()]


def test_place_used_only_by_a_deleted_night_is_still_protected(api):
    """Soft-deleted nights keep their place reference, so the guard must still block."""
    gid = api.group()
    p = api.participant(gid)
    place = api.place(gid, "Historico")
    night = api.night(gid, "2026-03-22", [entry(p, 1000, 1000)], place_id=place)
    api.delete(f"/api/groups/{gid}/nights/{night['id']}")
    assert api.delete(f"/api/groups/{gid}/places/{place}").status_code == 409


def test_catalog_item_from_another_group_is_404(api, other_api):
    mine = api.group()
    theirs = other_api.group()
    foreign_place = other_api.place(theirs)
    assert api.delete(f"/api/groups/{mine}/places/{foreign_place}").status_code == 404


def test_health_endpoint(client):
    assert client.get("/api/health").json() == {"status": "ok"}
