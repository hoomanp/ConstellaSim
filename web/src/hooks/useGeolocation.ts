import { useCallback, useEffect, useState } from "react";

export type GeoState =
  | { status: "idle" | "pending" }
  | { status: "ready"; lat: number; lon: number; source: "gps" | "capacitor" }
  | { status: "denied" | "unavailable" };

type CapGeo = {
  getCurrentPosition: (opts?: {
    enableHighAccuracy?: boolean;
    timeout?: number;
  }) => Promise<{ coords: { latitude: number; longitude: number } }>;
};

function capacitorGeolocation(): CapGeo | null {
  const w = window as Window & {
    Capacitor?: { Plugins?: { Geolocation?: CapGeo }; isNativePlatform?: () => boolean };
  };
  return w.Capacitor?.Plugins?.Geolocation ?? null;
}

export function useGeolocation() {
  const [geo, setGeo] = useState<GeoState>({ status: "idle" });

  const refresh = useCallback(() => {
    setGeo({ status: "pending" });

    void (async () => {
      const cap = capacitorGeolocation();
      if (cap) {
        try {
          const pos = await cap.getCurrentPosition({ enableHighAccuracy: true, timeout: 8000 });
          setGeo({
            status: "ready",
            lat: pos.coords.latitude,
            lon: pos.coords.longitude,
            source: "capacitor",
          });
          return;
        } catch {
          /* fall through to browser GPS */
        }
      }

      if (!navigator.geolocation) {
        setGeo({ status: "unavailable" });
        return;
      }

      navigator.geolocation.getCurrentPosition(
        (pos) =>
          setGeo({
            status: "ready",
            lat: pos.coords.latitude,
            lon: pos.coords.longitude,
            source: "gps",
          }),
        () => setGeo({ status: "denied" }),
        { enableHighAccuracy: true, timeout: 8000, maximumAge: 60_000 },
      );
    })();
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { geo, refresh };
}
