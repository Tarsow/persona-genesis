from persona_genesis.data import load_locations, load_occupations, load_ua_pool


def test_locations_have_required_keys() -> None:
    for locale in ("en_US", "pt_BR"):
        rows = load_locations(locale)
        assert rows and all({"country", "region", "city", "timezone"} <= r.keys() for r in rows)


def test_ua_pool_profiles_are_coherent_shape() -> None:
    pool = load_ua_pool()
    assert pool
    for p in pool:
        assert {"device", "os", "browser", "ua", "resolutions"} <= p.keys()
        assert p["resolutions"]


def test_occupations_pairs() -> None:
    occ = load_occupations()
    assert occ and all({"occupation", "industry"} <= o.keys() for o in occ)
