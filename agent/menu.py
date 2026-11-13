"""The menu and the waiter's tools.

Plain Python, no AI here: every price, ingredient and total the waiter says
comes from these functions, so the model cannot invent them.
"""

import json
from pathlib import Path

MENU_PATH = Path(__file__).resolve().parent.parent / "data" / "menu.json"


class Menu:
    def __init__(self, path: Path = MENU_PATH):
        self.data = json.loads(Path(path).read_text())
        self.items = {
            item["id"]: {**item, "section": section["name"]}
            for section in self.data["sections"]
            for item in section["items"]
        }
        self.notes = self.data.get("kitchen_notes", {})
        self.order: list[str] = []

    # --- tools -----------------------------------------------------------

    def list_menu(self) -> dict:
        """The whole menu, grouped by section, with prices."""
        return {
            section["name"]: [
                {"id": i["id"], "name": i["name"], "price": i["price"]}
                for i in section["items"]
            ]
            for section in self.data["sections"]
        }

    def get_item(self, item_id: str) -> dict:
        """One item with its ingredients and the kitchen notes that apply to it."""
        item = self.items.get(item_id)
        if item is None:
            return {"error": f"No item with id '{item_id}'. Call list_menu to see the ids."}
        result = {k: v for k, v in item.items() if k != "today"}
        ingredients = item.get("ingredients", [])
        notes = {i: self.notes[i] for i in ingredients if i in self.notes}
        if notes:
            result["kitchen_notes"] = notes
        return result

    def find_dishes_without(self, ingredients: list[str]) -> dict:
        """Pizzas that contain none of the given ingredients (e.g. ham, parmesan)."""
        banned = {i.strip().lower() for i in ingredients}
        matches = [
            {"id": i["id"], "name": i["name"], "price": i["price"]}
            for i in self.items.values()
            if "ingredients" in i and not banned & set(i["ingredients"])
        ]
        return {"without": sorted(banned), "pizzas": matches}

    def dessert_of_the_day(self) -> dict:
        item = self.items["dessert-of-the-day"]
        today = item.get("today")
        if not today:
            return {"price": item["price"], "today": None,
                    "note": "The kitchen has not announced today's dessert yet."}
        return {"price": item["price"], "today": today}

    def add_to_order(self, item_id: str, quantity: int = 1) -> dict:
        if item_id not in self.items:
            return {"error": f"No item with id '{item_id}'."}
        self.order.extend([item_id] * max(1, quantity))
        return self.get_order()

    def get_order(self) -> dict:
        lines: dict[str, int] = {}
        for item_id in self.order:
            lines[item_id] = lines.get(item_id, 0) + 1
        detail = [
            {"name": self.items[i]["name"], "quantity": q, "price": self.items[i]["price"] * q}
            for i, q in lines.items()
        ]
        return {"items": detail, "total": round(sum(d["price"] for d in detail), 2),
                "currency": self.data["currency"]}

    # --- plumbing --------------------------------------------------------

    def call(self, name: str, args: dict) -> dict:
        """Run a tool by name. Unknown names return an error the model can read."""
        tool = TOOLS_BY_NAME.get(name)
        if tool is None:
            return {"error": f"Unknown tool '{name}'."}
        return getattr(self, name)(**args)


TOOLS = [
    {"name": "list_menu", "description": "List every item on the menu with its id and price.",
     "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "get_item",
     "description": "Get one item: ingredients, price, and kitchen notes (meat, animal rennet, etc.).",
     "input_schema": {"type": "object", "properties": {"item_id": {"type": "string"}},
                      "required": ["item_id"], "additionalProperties": False}},
    {"name": "find_dishes_without",
     "description": "Find the pizzas that contain none of the given ingredients.",
     "input_schema": {"type": "object",
                      "properties": {"ingredients": {"type": "array", "items": {"type": "string"}}},
                      "required": ["ingredients"], "additionalProperties": False}},
    {"name": "dessert_of_the_day", "description": "Today's dessert and its price.",
     "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "add_to_order", "description": "Add an item to the customer's order.",
     "input_schema": {"type": "object",
                      "properties": {"item_id": {"type": "string"},
                                     "quantity": {"type": "integer", "minimum": 1}},
                      "required": ["item_id"], "additionalProperties": False}},
    {"name": "get_order", "description": "The current order and its exact total.",
     "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}},
]
TOOLS_BY_NAME = {t["name"]: t for t in TOOLS}
