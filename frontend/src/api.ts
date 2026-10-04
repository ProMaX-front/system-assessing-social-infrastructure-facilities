const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

export type GeoJsonGeometry = {
  type: "Point" | "LineString" | "Polygon" | "MultiPolygon";
  coordinates: unknown;
};

export type SocialObject = {
  id: number;
  name: string;
  category: string;
  category_label: string;
  address: string;
  longitude: number;
  latitude: number;
  footprint: GeoJsonGeometry | null;
  capacity: number | null;
  capacity_unit: string;
  source: string;
  source_id: string;
};

export type AnalysisResult = {
  category: string;
  category_label: string;
  object: SocialObject | null;
  distance_m: number | null;
  direct_distance_m: number | null;
  normative_distance_m: number | null;
  compliant: boolean | null;
  route_geometry: {
    type: "LineString";
    coordinates: number[][];
  } | null;
  route_is_osm: boolean;
  distance_method: string;
  normative?: {
    legal_document: string;
    legal_clause: string;
  } | null;
  message?: string;
};

export type AnalysisResponse = {
  point: { latitude: number; longitude: number };
  calculation_method: string;
  results: AnalysisResult[];
};

export function getAccessToken() {
  return localStorage.getItem("access_token");
}

export function setTokens(access: string, refresh: string) {
  localStorage.setItem("access_token", access);
  localStorage.setItem("refresh_token", refresh);
}

export function clearTokens() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getAccessToken();
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "Ошибка запроса");
  }

  return response.json();
}

export async function login(username: string, password: string) {
  const data = await request<{ access: string; refresh: string }>("/auth/token/", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });

  setTokens(data.access, data.refresh);
}

export async function getMe() {
  return request<{
    id: number;
    username: string;
    email: string;
    is_staff: boolean;
  }>("/auth/me/");
}

export async function getSocialObjects() {
  return request<SocialObject[]>("/social-objects/");
}

export async function analyzePoint(latitude: number, longitude: number) {
  return request<AnalysisResponse>("/analysis/nearest/", {
    method: "POST",
    body: JSON.stringify({ latitude, longitude }),
  });
}
