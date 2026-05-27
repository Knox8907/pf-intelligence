"""
Seed initial poll questions for the intelligence platform.
Run once after database init:  python -m database.seed_polls
"""
import asyncio
from .connection import AsyncSessionLocal
from .models import Poll, PollOption

POLLS = [
    {
        "question": "What is your single biggest financial concern right now?",
        "options": [
            "Cost of mealie meal and food prices",
            "Fuel and transport costs",
            "Electricity bills and ZESCO load shedding",
            "Job loss or inability to find work",
            "School fees and medical costs",
        ],
    },
    {
        "question": "Has your household's cost of living improved, stayed the same, or worsened since the UPND took power in 2021?",
        "options": [
            "Significantly worsened — we are much worse off",
            "Slightly worsened — things are a bit harder",
            "Stayed the same — no change",
            "Slightly improved — a little better",
            "Significantly improved — much better off",
        ],
    },
    {
        "question": "Which party do you trust most to reduce the cost of living in Zambia?",
        "options": [
            "Patriotic Front (PF)",
            "UPND",
            "Neither party — I don't trust any party",
            "Another opposition party",
        ],
    },
    {
        "question": "If the election were held today, which way would you lean?",
        "options": [
            "I would vote for PF / the opposition",
            "I would vote for UPND",
            "I am undecided",
            "I would not vote",
        ],
    },
    {
        "question": "What is the most urgent change the next government should make in the first 100 days?",
        "options": [
            "Fix mealie meal prices — cap or subsidise immediately",
            "Reduce fuel prices to affordable levels",
            "End ZESCO load shedding or expand power capacity",
            "Create a youth employment programme",
            "Stabilise the kwacha and control inflation",
        ],
    },
]


async def seed_polls():
    async with AsyncSessionLocal() as session:
        for i, poll_data in enumerate(POLLS):
            poll = Poll(question=poll_data["question"], is_active=True, is_public=True)
            session.add(poll)
            await session.flush()

            for j, opt_text in enumerate(poll_data["options"]):
                opt = PollOption(poll_id=poll.id, text=opt_text, order=j)
                session.add(opt)

        await session.commit()
        print(f"Seeded {len(POLLS)} polls with options.")


if __name__ == "__main__":
    asyncio.run(seed_polls())
