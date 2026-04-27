from unittest import TestCase

from wargames.harness.turns import events_from_payload, validate_turn


class TurnTests(TestCase):
    def test_accepts_single_event_object(self) -> None:
        events = events_from_payload({"name": "wait", "arguments": {}})

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].name, "wait")

    def test_accepts_event_array_as_one_turn(self) -> None:
        events = events_from_payload(
            [
                {"name": "key_down", "arguments": {"key": "Control"}},
                {"name": "key_down", "arguments": {"key": "1"}},
                {"name": "key_up", "arguments": {"key": "1"}},
                {"name": "key_up", "arguments": {"key": "Control"}},
            ]
        )

        self.assertEqual(
            [event.name for event in events], ["key_down", "key_down", "key_up", "key_up"]
        )

    def test_rejects_overlong_turn_wait(self) -> None:
        events = events_from_payload([{"name": "wait", "arguments": {"ms": 5001}}])

        with self.assertRaisesRegex(ValueError, "max is 5000ms"):
            validate_turn(events)
