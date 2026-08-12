"""The unauthenticated surface: public directory, share-token access to private groups,
and the guarantee that nothing private leaks through it."""
from conftest import entry


def make_public_group(api, name):
    gid = api.group(name, visibility="public")
    slug = api.last_group["slug"]
    p = api.participant(gid, "Ana")
    api.night(gid, "2026-01-10", [entry(p, 10000, 12000)])
    return gid, slug


def test_public_group_is_listed_and_searchable(api, client):
    _, slug = make_public_group(api, "Publico Buscavel Alfa")
    listed = client.get("/api/public").json()
    assert slug in [g["slug"] for g in listed]

    found = client.get("/api/public", params={"q": "Buscavel Alfa"}).json()
    assert [g["slug"] for g in found] == [slug]
    assert found[0]["night_count"] == 1 and found[0]["participant_count"] == 1


def test_search_is_case_insensitive_and_matches_slug(api, client):
    _, slug = make_public_group(api, "Noite Do Zeca Beta")
    assert slug in [g["slug"] for g in client.get("/api/public", params={"q": "zeca beta"}).json()]
    assert slug in [g["slug"] for g in client.get("/api/public", params={"q": slug}).json()]


def test_private_group_is_not_in_the_directory(api, client):
    gid = api.group("Privado Oculto")
    slug = api.last_group["slug"]
    assert gid  # created private by default
    assert slug not in [g["slug"] for g in client.get("/api/public").json()]


def test_search_limit_is_respected(api, client):
    for i in range(3):
        make_public_group(api, f"Limite Gamma {i}")
    assert len(client.get("/api/public", params={"q": "Limite Gamma", "limit": 2}).json()) == 2


def test_public_counts_are_correct_per_group(api, client):
    """Batched counts: each listed group must carry its own numbers."""
    _, one_slug = make_public_group(api, "Contagem Um Delta")
    many = api.group("Contagem Muitos Delta", visibility="public")
    many_slug = api.last_group["slug"]
    p1, p2 = api.participant(many, "P1"), api.participant(many, "P2")
    for d in range(1, 4):
        api.night(many, f"2026-02-{d:02d}", [entry(p1, 1000, 1000), entry(p2, 1000, 1000)])

    listed = {g["slug"]: g for g in client.get("/api/public", params={"q": "Delta"}).json()}
    assert (listed[one_slug]["night_count"], listed[one_slug]["participant_count"]) == (1, 1)
    assert (listed[many_slug]["night_count"], listed[many_slug]["participant_count"]) == (3, 2)


def test_public_detail_serves_stats_evolution_and_nights(api, client):
    _, slug = make_public_group(api, "Detalhe Publico")
    body = client.get(f"/api/public/{slug}").json()
    assert body["slug"] == slug
    assert body["stats"]["total_nights"] == 1
    assert body["stats"]["ranking"][0]["name"] == "Ana"
    assert body["evolution"]["dates"] == ["2026-01-10"]
    assert len(body["nights"]) == 1
    assert body["nights"][0]["entries"][0]["participant_name"] == "Ana"


def test_public_detail_resolves_place_names(api, client):
    gid = api.group("Com Local Publico", visibility="public")
    slug = api.last_group["slug"]
    p = api.participant(gid, "Ana")
    place = api.place(gid, "Casa da Ana")
    api.night(gid, "2026-01-10", [entry(p, 1000, 1000)], place_id=place)
    api.night(gid, "2026-01-11", [entry(p, 1000, 1000)])  # no place

    nights = client.get(f"/api/public/{slug}").json()["nights"]
    by_date = {n["date"]: n for n in nights}
    assert by_date["2026-01-10"]["place_name"] == "Casa da Ana"
    assert by_date["2026-01-11"]["place_name"] is None


def test_public_detail_nights_are_newest_first(api, client):
    gid = api.group("Ordem Publica", visibility="public")
    slug = api.last_group["slug"]
    p = api.participant(gid, "Ana")
    for d in (1, 5, 3):
        api.night(gid, f"2026-01-{d:02d}", [entry(p, 1000, 1000)])
    dates = [n["date"] for n in client.get(f"/api/public/{slug}").json()["nights"]]
    assert dates == ["2026-01-05", "2026-01-03", "2026-01-01"]


def test_unknown_slug_is_404(client):
    assert client.get("/api/public/nao-existe-esse-slug").status_code == 404


def test_private_group_without_token_is_403(api, client):
    api.group("Privado Sem Token")
    slug = api.last_group["slug"]
    r = client.get(f"/api/public/{slug}")
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "group_private"


def test_private_group_with_the_share_token_is_readable(api, client):
    gid = api.group("Privado Com Token")
    slug = api.last_group["slug"]
    p = api.participant(gid, "Ana")
    api.night(gid, "2026-01-10", [entry(p, 10000, 12000)])
    token = api.post(f"/api/groups/{gid}/rotate-share-token").json()["share_token"]

    assert client.get(f"/api/public/{slug}", params={"t": token}).status_code == 200
    assert client.get(f"/api/public/{slug}", params={"t": "token-errado"}).status_code == 403


def test_rotating_the_token_revokes_the_old_link(api, client):
    gid = api.group("Revogavel")
    slug = api.last_group["slug"]
    old = api.post(f"/api/groups/{gid}/rotate-share-token").json()["share_token"]
    assert client.get(f"/api/public/{slug}", params={"t": old}).status_code == 200
    api.post(f"/api/groups/{gid}/rotate-share-token")
    assert client.get(f"/api/public/{slug}", params={"t": old}).status_code == 403


def test_public_payload_exposes_no_secrets(api, client):
    _, slug = make_public_group(api, "Sem Segredos")
    body = client.get(f"/api/public/{slug}").json()
    assert set(body) == {"name", "slug", "description", "currency", "stats", "evolution", "nights"}
    assert "share_token" not in body and "id" not in body
    assert all(set(g) == {"name", "slug", "description", "night_count", "participant_count"}
               for g in client.get("/api/public").json())
