from unittest import TestCase

from wargames.core.control.cua import WaitAction


class ReprTests(TestCase):
    def test_dataclass_repr_names_type(self) -> None:
        self.assertIn("WaitAction", repr(WaitAction(id="a", ticks=1)))
