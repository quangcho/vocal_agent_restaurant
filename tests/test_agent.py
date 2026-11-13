"""Offline tests: no API key, no network, no cost."""

from types import SimpleNamespace as NS

from agent.menu import Menu
from agent.waiter import Waiter


def test_only_margherita_is_strictly_vegetarian():
    menu = Menu()
    found = menu.find_dishes_without(["ham", "pepperoni", "parmesan", "gorgonzola"])
    assert [p["id"] for p in found["pizzas"]] == ["margherita"]


def test_item_carries_kitchen_notes():
    item = Menu().get_item("goat-cheese-honey")
    assert "parmesan" in item["kitchen_notes"]


def test_dessert_of_the_day():
    assert Menu().dessert_of_the_day() == {"price": 4.5, "today": "Pistachio tiramisu"}


def test_order_total_is_computed_by_code():
    menu = Menu()
    menu.add_to_order("margherita")
    order = menu.add_to_order("tiramisu", quantity=2)
    assert order["total"] == 20.0


def test_unknown_item_returns_an_error():
    assert "error" in Menu().get_item("hawaiian")


class FakeClient:
    """Plays back scripted responses in place of the Claude API."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.beta = NS(messages=NS(create=self._create))

    def _create(self, **params):
        return self.responses.pop(0)


def test_waiter_uses_a_tool_then_answers():
    tool_call = NS(type="tool_use", id="t1", name="dessert_of_the_day", input={})
    client = FakeClient([
        NS(stop_reason="tool_use", content=[tool_call]),
        NS(stop_reason="end_turn",
           content=[NS(type="text", text="Today it's a pistachio tiramisu.")]),
    ])
    text, trace = Waiter(client).reply("What's the dessert of the day?")
    assert text == "Today it's a pistachio tiramisu."
    assert trace[0]["tool"] == "dessert_of_the_day"
    assert trace[0]["output"]["today"] == "Pistachio tiramisu"


def test_long_reply_gets_a_shorter_take():
    long_text = " ".join(["word"] * 40)
    client = FakeClient([
        NS(stop_reason="end_turn", content=[NS(type="text", text=long_text)]),
        NS(stop_reason="end_turn", content=[NS(type="text", text="Short and sweet.")]),
    ])
    text, _ = Waiter(client).reply("Tell me everything.")
    assert text == "Short and sweet."
