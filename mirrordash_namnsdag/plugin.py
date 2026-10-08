import asyncio
import logging
from datetime import date

logger = logging.getLogger("mirrordash.modules.mirrordash_namnsdag")

# Two services with the same API; the second is tried when the first doesn't answer.
# The date is in the address, so an answer the mirror kept from earlier is always today's.
URLS = ("https://api.dryg.net/dagar/v2.1/", "https://sholiday.faboul.se/dagar/v2.1/")


def names_from(data) -> list[str]:
    """The name day names in the API's answer for one day."""
    dagar = data.get("dagar") if isinstance(data, dict) else None
    return dagar[0].get("namnsdag", []) if dagar else []


class NamnsdagModule:
    # Keeps pytest from collecting this class as a test
    __test__ = False

    def __init__(self, config):
        # The mirror adds self.render_template, self.translate and self.fetch_json after __init__.
        self.config = config
        self.name = "mirrordash_namnsdag"
        self.interval = config.get("interval", 60)
        self.date: date | None = None  # the day self.names is for
        self.names: list[str] = []

    async def fetch_names(self, day: date) -> list[str] | None:
        """The names for that day, or None when neither service answered."""
        for base in URLS:
            data, error = await self.fetch_json(base + day.strftime("%Y/%m/%d"))
            if data is not None:
                return names_from(data)
            logger.debug(f"{base}: {error}")
        return None

    async def run_loop(self, broadcast_func):
        """Fetch once a day (and again until it works), show, wait, repeat."""
        while True:
            try:
                today = date.today()
                if self.date != today:
                    names = await self.fetch_names(today)
                    if names is not None:
                        self.names, self.date = names, today
                html = self.render_template("widget.html", names=self.names, error=self.date != today)
                await broadcast_func(self.name, html)
            except asyncio.CancelledError:
                raise  # the mirror is stopping this module: let it
            except Exception as e:
                logger.error(f"{self.name}: {e}", exc_info=True)
            await asyncio.sleep(self.interval)
