import asyncio
from datetime import date
from unittest.mock import AsyncMock, MagicMock

from mirrordash_namnsdag.plugin import URLS, NamnsdagModule

DAY = {"dagar": [{"datum": "2026-10-08", "namnsdag": ["Nils"]}]}


def module(*answers):
    m = NamnsdagModule({})
    m.fetch_json = AsyncMock(side_effect=answers)
    m.render_template = MagicMock(return_value="<html>")
    return m


def test_names_for_the_day_in_the_address():
    m = module((DAY, None))
    assert asyncio.run(m.fetch_names(date(2026, 10, 8))) == ["Nils"]
    m.fetch_json.assert_awaited_once_with(URLS[0] + "2026/10/08")


def test_second_service_when_the_first_is_down():
    m = module((None, "offline"), (DAY, None))
    assert asyncio.run(m.fetch_names(date(2026, 10, 8))) == ["Nils"]
    assert m.fetch_json.await_args.args[0] == URLS[1] + "2026/10/08"


def test_error_shown_when_both_are_down():
    m = module((None, "offline"), (None, "offline"))
    assert asyncio.run(m.fetch_names(date(2026, 10, 8))) is None

    async def one_round():
        broadcast = AsyncMock(side_effect=asyncio.CancelledError)  # stop after the first render
        try:
            await m.run_loop(broadcast)
        except asyncio.CancelledError:
            pass
    m.fetch_json = AsyncMock(return_value=(None, "offline"))
    asyncio.run(one_round())
    assert m.render_template.call_args.kwargs["error"] is True
