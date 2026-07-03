import asyncio
import logging
import os
from datetime import datetime

logger = logging.getLogger("mirrordash.modules.mirrordash_namnsdag")

def fetch_namnsdag() -> list[str]:
    import urllib.request
    import json
    
    # Try api.dryg.net first
    try:
        req = urllib.request.Request(
            "https://api.dryg.net/dagar/v2.1/",
            headers={"User-Agent": "MirrorDash/0.1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                dagar = data.get("dagar", [])
                if dagar:
                    return dagar[0].get("namnsdag", [])
    except Exception as e:
        logger.debug(f"Failed to fetch from api.dryg.net: {e}. Trying fallback...")

    # Fallback to sholiday.faboul.se
    try:
        req = urllib.request.Request(
            "https://sholiday.faboul.se/dagar/v2.1/",
            headers={"User-Agent": "MirrorDash/0.1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                dagar = data.get("dagar", [])
                if dagar:
                    return dagar[0].get("namnsdag", [])
    except Exception as e:
        logger.error(f"Fallback fetch from sholiday.faboul.se failed: {e}")
        
    return []

class NamnsdagModule:
    def __init__(self, config):
        self.config = config
        self.name = "mirrordash_namnsdag"
        self.interval = config.get("interval", 60)
        
        # Writable data directory and cache directory
        self.data_dir = config.get("data_dir")
        self.cache_dir = config.get("cache_dir")
        
        # Translations dictionary loaded automatically from translations/*.json
        self.translations = config.get("translations", {})
        
        # Event Bus for pub/sub
        self.event_bus = config.get("event_bus")
        
        # Internal state
        self.last_fetch_date = None
        self.names = []
        self.fetch_error = False
        
        logger.info(f"Initializing {self.name} module")

    async def run_loop(self, broadcast_func):
        """Main lifecycle loop. Periodically checks if the date changed and fetches new names."""
        logger.info(f"Starting {self.name} run loop")
        while True:
            try:
                today_str = datetime.now().strftime("%Y-%m-%d")
                
                # Fetch if date changed, first run, or last run failed
                if not self.last_fetch_date or self.last_fetch_date != today_str or self.fetch_error:
                    logger.info(f"Fetching Swedish name days for {today_str}")
                    try:
                        names = await asyncio.to_thread(fetch_namnsdag)
                        self.names = names
                        self.last_fetch_date = today_str
                        self.fetch_error = False
                    except Exception as fetch_err:
                        logger.error(f"Error fetching name days: {fetch_err}")
                        self.fetch_error = True
                        if not hasattr(self, 'names'):
                            self.names = []
                
                # Render Jinja2 HTML template
                html = self.render_template(
                    "widget.html",
                    names=self.names,
                    error=self.fetch_error,
                    last_checked=datetime.now().strftime("%H:%M")
                )
                
                # Broadcast update
                await broadcast_func(self.name, html)
                
            except Exception as e:
                logger.error(f"Error in module {self.name} run_loop: {e}", exc_info=True)
                
            await asyncio.sleep(self.interval)
