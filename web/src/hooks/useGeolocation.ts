import { useEffect, useState } from "react";

export type GeoState =
  | { status: "idle" | "pending" }
  | { status: "ready"; lat: number; lon: number }
  | { status: "denied" | "unavailable" };

export function useGeolocation() {
  const [geo, setGeo] = useState<GeoState>({ status: "idle" });

  useEffect(() => {
    if (!navigator.geolocation) {
      setGeo({ status: "unavailable" });
      return;
    }
    setGeo({ status: "pending" });
    navigator.geolocation.getCurrentPosition(
      (pos) => setGeo({ status: "ready", lat: pos.coords.latitude, lon: pos.coords.longitude }),
      () => setGeo({ status: "denied" }),
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 60_000 },
    );
  }, []);

  return geo;
}
