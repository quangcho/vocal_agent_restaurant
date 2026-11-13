"""The waiter: Claude answering the phone, with the menu tools.

The loop is written out by hand on purpose: it is short, and it lets us
record every tool call so the website can show what the agent checked.
"""

import json

from .llm import create, text_of
from .menu import TOOLS, Menu

MAX_WORDS = 30  # a phone reply longer than this gets a second, shorter take

SHORTEN = """Rewrite this phone reply from a pizzeria waiter in under 25 words.
Keep every price, dish name and fact exactly as they are. Drop the rest.
Reply with the new text only.

{text}"""

SYSTEM = """You answer the phone at {restaurant}, a small pizzeria.

How you speak:
- This is a phone call that will be read aloud. Plain spoken English, no lists, no markdown.
- Very short turns: one or two sentences, under 25 words. Offer two options at most.
- Warm, quick, a little playful, never pushy.
- Pick up with "Gino Pizza, good evening!" and a short question, nothing more.
- Prices are in euros. Say them the way people speak: "thirteen euros", "four fifty".

What you know:
- You know nothing about the menu except what your tools return. Check before you answer.
- Never guess a price, an ingredient or a total: use get_item, get_order and the other tools.
- If a guest asks for something vegetarian, check the kitchen notes: some cheeses are made
  with animal rennet. Say it simply and honestly, then suggest what does fit. Trust the
  kitchen notes: they are what the kitchen told you.
- If something is unknown (for example today's dessert is not announced), say so and offer
  an alternative.
- When the guest is done, confirm the order and the total from get_order, then say goodbye.
"""


class Waiter:
    def __init__(self, client, menu: Menu | None = None):
        self.client = client
        self.menu = menu or Menu()
        self.system = SYSTEM.format(restaurant=self.menu.data["restaurant"])
        self.messages: list = []

    def reply(self, guest_says: str) -> tuple[str, list[dict]]:
        """Answer one guest turn. Returns the spoken reply and the tool calls made."""
        self.messages.append({"role": "user", "content": guest_says})
        trace: list[dict] = []
        while True:
            response = create(self.client, system=self.system, tools=TOOLS,
                              messages=self.messages)
            self.messages.append({"role": "assistant", "content": response.content})
            calls = [b for b in response.content if b.type == "tool_use"]
            if not calls:
                return self._phone_length(text_of(response)), trace
            results = []
            for call in calls:
                output = self.menu.call(call.name, call.input)
                trace.append({"tool": call.name, "input": call.input, "output": output})
                results.append({
                    "type": "tool_result",
                    "tool_use_id": call.id,
                    "content": json.dumps(output),
                    "is_error": "error" in output,
                })
            self.messages.append({"role": "user", "content": results})

    def _phone_length(self, text: str) -> str:
        """Long answers are boring on the phone: ask for a shorter take.

        The waiter's own memory keeps the full answer; only the spoken line
        changes, and the guest hears the short one.
        """
        if len(text.split()) <= MAX_WORDS:
            return text
        response = create(self.client, effort="low",
                          messages=[{"role": "user", "content": SHORTEN.format(text=text)}])
        return text_of(response)
