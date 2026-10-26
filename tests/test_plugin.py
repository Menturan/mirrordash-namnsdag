import asyncio
import json
from datetime import date
from unittest.mock import AsyncMock, MagicMock

from mirrordash_namnsdag.plugin import URLS, NamnsdagModule

DAY = json.dumps({"dagar": [{"datum": "2026-10-08", "namnsdag": ["Nils"]}]}).encode()
# sholiday.faboul.se's answer in October 2026: PHP notices before the JSON
NOISY = b"<br />\n<b>Notice</b>:  Trying to access array offset on value of type null in <b>index.php</b><br />\n" + DAY


def module(*answers):
    m = NamnsdagModule({})
    m.fetch = AsyncMock(side_effect=answers)
    m.render_template = MagicMock(return_value="<html>")
    return m


def test_names_for_the_day_in_the_address():
    m = module((DAY, None))
    assert asyncio.run(m.fetch_names(date(2026, 10, 8))) == ["Nils"]
    m.fetch.assert_awaited_once_with(URLS[0] + "2026/10/08", max_age=86400)


def test_names_past_what_comes_before_the_json():
    assert asyncio.run(module((NOISY, None)).fetch_names(date(2026, 10, 8))) == ["Nils"]


def test_second_service_when_the_first_answers_no_json():
    m = module((b"error code: 1014", None), (DAY, None))
    assert asyncio.run(m.fetch_names(date(2026, 10, 8))) == ["Nils"]


def test_second_service_when_the_first_is_down():
    m = module((None, "offline"), (DAY, None))
    assert asyncio.run(m.fetch_names(date(2026, 10, 8))) == ["Nils"]
    assert m.fetch.await_args.args[0] == URLS[1] + "2026/10/08"


def test_error_shown_when_both_are_down():
    m = module((None, "offline"), (None, "offline"))
    assert asyncio.run(m.fetch_names(date(2026, 10, 8))) is None

    async def one_round():
        broadcast = AsyncMock(side_effect=asyncio.CancelledError)  # stop after the first render
        try:
            await m.run_loop(broadcast)
        except asyncio.CancelledError:
            pass
    m.fetch = AsyncMock(return_value=(None, "offline"))
    asyncio.run(one_round())
    assert m.render_template.call_args.kwargs["error"] is True
