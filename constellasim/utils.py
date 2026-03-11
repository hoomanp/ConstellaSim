from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

class Geocoder:
    """Utility to resolve ground station locations from names or ZIP codes."""
    
    def __init__(self, user_agent="ConstellaSim"):
        self.geolocator = Nominatim(user_agent=user_agent)

    def resolve_location(self, query):
        """Returns (lat, lon) for a given query string."""
        try:
            location = self.geolocator.geocode(query)
            if location:
                return location.latitude, location.longitude
            return None, None
        except Exception:
            return None, None
