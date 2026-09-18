import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Platform,
  Pressable,
  SafeAreaView,
  StatusBar,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { StatusBar as ExpoStatusBar } from "expo-status-bar";
import { WebView } from "react-native-webview";

const STORAGE_KEY = "constellasim.expo.serverUrl";

function defaultServerUrl(): string {
  // iOS Simulator / Expo web on the same Mac can use loopback.
  // Physical phones must use the Mac mini LAN IP (shown in Expo QR terminal).
  if (Platform.OS === "android") return "http://10.0.2.2:5001";
  return "http://127.0.0.1:5001";
}

function normalizeUrl(raw: string): string {
  const trimmed = raw.trim().replace(/\/$/, "");
  if (!trimmed) throw new Error("Server URL is required");
  if (!/^https?:\/\//i.test(trimmed)) return `http://${trimmed}`;
  return trimmed;
}

export default function App() {
  const [draftUrl, setDraftUrl] = useState(defaultServerUrl());
  const [serverUrl, setServerUrl] = useState<string | null>(null);
  const [booting, setBooting] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [webKey, setWebKey] = useState(0);
  const webRef = useRef<WebView>(null);

  useEffect(() => {
    void (async () => {
      try {
        const saved = await AsyncStorage.getItem(STORAGE_KEY);
        if (saved) setDraftUrl(saved);
      } finally {
        setBooting(false);
      }
    })();
  }, []);

  const probeAndConnect = useCallback(async () => {
    setError(null);
    setConnecting(true);
    try {
      const url = normalizeUrl(draftUrl);
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 5000);
      const res = await fetch(`${url}/api/health`, { signal: controller.signal });
      clearTimeout(timer);
      if (!res.ok) throw new Error(`Health check failed (HTTP ${res.status})`);
      const data = await res.json();
      if (data.status !== "ok") throw new Error("Unexpected health payload");
      await AsyncStorage.setItem(STORAGE_KEY, url);
      setServerUrl(url);
      setWebKey((k) => k + 1);
    } catch (e) {
      const msg =
        e instanceof Error
          ? e.message
          : "Cannot reach backend. Same Wi‑Fi? Is ./scripts/demo.sh running?";
      setError(msg);
      setServerUrl(null);
    } finally {
      setConnecting(false);
    }
  }, [draftUrl]);

  const hint = useMemo(() => {
    if (Platform.OS === "ios") {
      return "Simulator: 127.0.0.1 is fine. iPhone: use your Mac mini LAN IP (e.g. 192.168.1.42).";
    }
    return "Emulator: 10.0.2.2. Physical Android: use your Mac mini LAN IP.";
  }, []);

  if (booting) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color="#3ee0c5" />
        <ExpoStatusBar style="light" />
      </View>
    );
  }

  if (!serverUrl) {
    return (
      <SafeAreaView style={styles.safe}>
        <ExpoStatusBar style="light" />
        <View style={styles.panel}>
          <Text style={styles.brand}>ConstellaSim</Text>
          <Text style={styles.lede}>
            Expo Go shell — connect to the FastAPI + React demo running on your Mac mini.
          </Text>
          <Text style={styles.label}>Backend URL</Text>
          <TextInput
            style={styles.input}
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="url"
            placeholder="http://192.168.1.42:5001"
            placeholderTextColor="#5b6b84"
            value={draftUrl}
            onChangeText={setDraftUrl}
          />
          <Text style={styles.hint}>{hint}</Text>
          {error ? <Text style={styles.error}>{error}</Text> : null}
          <Pressable
            style={[styles.button, connecting && styles.buttonDisabled]}
            onPress={probeAndConnect}
            disabled={connecting}
          >
            <Text style={styles.buttonText}>{connecting ? "Connecting…" : "Open in Expo Go"}</Text>
          </Pressable>
          <Text style={styles.footer}>
            On the Mac: run `./scripts/demo.sh`, then `cd expo-app && npx expo start`, scan the QR
            with Expo Go.
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe}>
      <ExpoStatusBar style="light" />
      <View style={styles.toolbar}>
        <Pressable onPress={() => setServerUrl(null)} hitSlop={8}>
          <Text style={styles.toolBtn}>Change server</Text>
        </Pressable>
        <Text style={styles.toolUrl} numberOfLines={1}>
          {serverUrl}
        </Text>
        <Pressable
          onPress={() => {
            setWebKey((k) => k + 1);
            webRef.current?.reload();
          }}
          hitSlop={8}
        >
          <Text style={styles.toolBtn}>Reload</Text>
        </Pressable>
      </View>
      <WebView
        key={webKey}
        ref={webRef}
        source={{ uri: serverUrl }}
        style={styles.webview}
        allowsBackForwardNavigationGestures
        startInLoadingState
        renderLoading={() => (
          <View style={styles.center}>
            <ActivityIndicator color="#3ee0c5" />
          </View>
        )}
        onError={() => setError("WebView failed to load. Check the backend URL.")}
        // Allow geolocation prompts from the embedded mission console.
        geolocationEnabled
        mixedContentMode="always"
        allowsInlineMediaPlayback
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: "#05080f",
    paddingTop: Platform.OS === "android" ? StatusBar.currentHeight ?? 0 : 0,
  },
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#05080f",
  },
  panel: {
    flex: 1,
    paddingHorizontal: 22,
    paddingTop: 36,
    gap: 10,
  },
  brand: {
    fontSize: 34,
    fontWeight: "800",
    color: "#9ef5e4",
    letterSpacing: 0.5,
  },
  lede: {
    color: "#8b9bb4",
    fontSize: 15,
    lineHeight: 22,
    marginBottom: 12,
  },
  label: {
    color: "#8b9bb4",
    fontSize: 13,
  },
  input: {
    borderWidth: 1,
    borderColor: "rgba(120,160,200,0.25)",
    backgroundColor: "#0a1628",
    color: "#e8eef7",
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 16,
  },
  hint: {
    color: "#5b6b84",
    fontSize: 12,
    lineHeight: 18,
  },
  error: {
    color: "#ff6b6b",
    fontSize: 13,
  },
  button: {
    marginTop: 8,
    backgroundColor: "#3ee0c5",
    borderRadius: 999,
    paddingVertical: 14,
    alignItems: "center",
  },
  buttonDisabled: { opacity: 0.6 },
  buttonText: {
    color: "#042019",
    fontWeight: "700",
    fontSize: 16,
  },
  footer: {
    marginTop: 18,
    color: "#5b6b84",
    fontSize: 12,
    lineHeight: 18,
  },
  toolbar: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: "rgba(120,160,200,0.18)",
  },
  toolBtn: {
    color: "#3ee0c5",
    fontWeight: "600",
    fontSize: 13,
  },
  toolUrl: {
    flex: 1,
    color: "#8b9bb4",
    fontSize: 12,
  },
  webview: { flex: 1, backgroundColor: "#05080f" },
});
