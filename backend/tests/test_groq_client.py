from app.services.groq_client import GroqClientPool


def test_clients_are_selected_in_round_robin_order():
    created_keys = []

    def fake_client_factory(**kwargs):
        created_keys.append(kwargs["api_key"])
        return kwargs["api_key"]

    pool = GroqClientPool(
        ("first", "second", "third"),
        client_factory=fake_client_factory,
    )

    selected = [
        pool.get_client(timeout=60.0, max_retries=2)
        for _ in range(5)
    ]

    assert selected == ["first", "second", "third", "first", "second"]
    assert created_keys == ["first", "second", "third"]


def test_empty_pool_returns_no_client():
    pool = GroqClientPool(())

    assert not pool.is_configured
    assert pool.get_client(timeout=60.0, max_retries=2) is None
