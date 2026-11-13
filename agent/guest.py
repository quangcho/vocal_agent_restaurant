"""The simulated guest: Claude playing a caller with a persona and a goal.

The guest never sees the menu. It only hears what the waiter says, like a
real caller, so the waiter has to do the work.
"""

from .llm import create, text_of

SYSTEM = """You are calling a pizzeria to order. Stay in character.

Who you are: {persona}
What you want: {goal}

Rules:
- You do not know the menu. React only to what the waiter tells you.
- Plain spoken English, one or two short sentences per turn. No stage directions.
- Keep the whole call short: aim to finish in about {max_turns} turns.
- Do not re-check the waiter's maths or ask about things outside your goal.
- When your order is confirmed and you have said goodbye, reply with exactly: [HANG UP]
"""

HANG_UP = "[HANG UP]"


class Guest:
    def __init__(self, client, persona: str, goal: str, max_turns: int = 5):
        self.client = client
        self.system = SYSTEM.format(persona=persona, goal=goal, max_turns=max_turns)
        # From the guest's side, the waiter is the "user" speaking to them.
        self.messages: list = []

    def reply(self, waiter_says: str) -> str:
        self.messages.append({"role": "user", "content": waiter_says})
        response = create(self.client, effort="low", system=self.system, messages=self.messages)
        text = text_of(response)
        self.messages.append({"role": "assistant", "content": text})
        return text
