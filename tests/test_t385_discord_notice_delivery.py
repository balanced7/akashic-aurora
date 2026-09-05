"""RED pins for direct Discord notices returned by the pure inbound policy.

The core already distinguishes "landed, but nobody is home" from transport
failure and returns a cold_seat explanation. The socket shell must actually
deliver that explanation to the message's channel; a dict key in process memory
is not an operator-visible warning.
"""
import asyncio

from scripts import bifrost_runner_discord as gateway


class _Message:
    def __init__(self):
        self.replies = []

    async def reply(self, text, *, mention_author):
        self.replies.append((text, mention_author))


def test_cold_seat_notice_reaches_the_originating_discord_message():
    message = _Message()
    notice = "📭 Sunshine is not live; the durable message is waiting."

    asyncio.run(gateway._relay_direct_notices(message, {"cold_seat": notice}))

    assert message.replies == [(notice, False)]


def test_existing_help_reply_and_discord_clip_bound_are_preserved():
    message = _Message()

    asyncio.run(gateway._relay_direct_notices(message, {"help": "x" * 2500}))

    assert message.replies == [("x" * 1900, False)]
