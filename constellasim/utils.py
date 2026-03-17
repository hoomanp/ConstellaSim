import threading
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

class Geocoder:
    """Utility to resolve ground station locations from names or ZIP codes."""

    def __init__(self, user_agent="ConstellaSim"):
        self.geolocator = Nominatim(user_agent=user_agent)
        # Optimization: cache resolved locations to avoid redundant Nominatim API calls
        # and stay within the Nominatim ToS (1 request/second limit).
        self._cache = {}
        # Thread safety: guard cache writes against concurrent Flask requests.
        self._lock = threading.Lock()

    def resolve_location(self, query):
        """Returns (lat, lon) for a given query string."""
        with self._lock:
            if query in self._cache:
                return self._cache[query]
        try:
            # Explicit timeout prevents the Flask worker from blocking indefinitely.
            location = self.geolocator.geocode(query, timeout=5)
            if location:
                result = location.latitude, location.longitude
            else:
                result = None, None
            with self._lock:
                self._cache[query] = result
            return result
        except GeocoderTimedOut:
            return None, None
        except Exception:
            return None, None
