from tools.talert_campaign import live_bus


def test_publish_run_waits_for_two_subscriptions(monkeypatch):
    observed: dict[str, int] = {}

    class FakePublisher:
        send_failures = 0

        def __init__(self, endpoint: str) -> None:
            observed["endpoint"] = endpoint

        def wait_for_subscriber(self, timeout_ms: int, expected: int = 1) -> bool:
            observed["timeout_ms"] = timeout_ms
            observed["expected"] = expected
            return True

        def publish(self, topic: str, source_id: str, payload: bytes) -> None:
            pass

        def publish_run_finished(self, control_run_id: str, status: str) -> None:
            pass

        def close(self) -> None:
            pass

    monkeypatch.setattr(live_bus, "AlertBusPublisher", FakePublisher)

    result = live_bus.publish_run([], "run-1", "tcp://127.0.0.1:5558")

    assert observed == {
        "endpoint": "tcp://127.0.0.1:5558",
        "timeout_ms": 5000,
        "expected": 2,
    }
    assert result.subscriptions_ready is True
