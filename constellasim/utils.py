import re
import threading
import logging
from collections import OrderedDict
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

logger = logging.getLogger(__name__)

# V-08: allowlist pattern — accept only printable letters, digits, spaces, commas,
# hyphens, periods, and parentheses (covers city names, ZIP codes, and addresses).
_LOCATION_RE = re.compile(r'^[\w\s,.\-()+]+$', re.UNICODE)
_CACHE_MAX = 1_000  # V-02: cap to prevent unbounded memory growth


class Geocoder:
    """Utility to resolve ground station locations from names or ZIP codes."""

    def __init__(self, user_agent="ConstellaSim"):
        self.geolocator = Nominatim(user_agent=user_agent)
        # V-02: bounded LRU-style cache using OrderedDict (evicts oldest on overflow).
        self._cache: OrderedDict = OrderedDict()
        self._lock = threading.Lock()

    def resolve_location(self, query):
        """Returns (lat, lon) for a given query string."""
        # V-08: reject queries that don't match the location allowlist.
        if not query or not _LOCATION_RE.match(query.strip()):
            logger.warning("Rejected invalid location query")
            return None, None

        with self._lock:
            if query in self._cache:
                self._cache.move_to_end(query)
                return self._cache[query]
        try:
            location = self.geolocator.geocode(query, timeout=5)
            if location:
                result = location.latitude, location.longitude
            else:
                result = None, None
            with self._lock:
                self._cache[query] = result
                self._cache.move_to_end(query)
                # V-02: evict oldest entry when cache exceeds max size.
                if len(self._cache) > _CACHE_MAX:
                    self._cache.popitem(last=False)
            return result
        except GeocoderTimedOut:
            return None, None
        except Exception:
            logger.exception("Geocoding error")
            return None, None
