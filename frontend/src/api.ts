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

export type MapLayersResponse = {
  social_objects: GeoJSON.FeatureCollection<GeoJSON.Point>;
  buildings: GeoJSON.FeatureCollection<GeoJSON.Polygon | GeoJSON.MultiPolygon>;
  meta: {
    zoom: number;
    social_objects_count: number;
    buildings_count: number;
    social_objects_truncated: boolean;
    buildings_truncated: boolean;
    all_buildings_visible: boolean;
  };
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

const ERROR_TRANSLATIONS: Array<[string, string]> = [
  [
    "No active account found with the given credentials",
    "Неверный логин или пароль.",
  ],
  [
    "Authentication credentials were not provided",
    "Необходимо выполнить вход в систему.",
  ],
  [
    "Given token not valid for any token type",
    "Сеанс авторизации недействителен. Выполните вход заново.",
  ],
  [
    "Token is invalid or expired",
    "Срок действия сеанса истёк. Выполните вход заново.",
  ],
  ["Invalid token", "Недействительный токен авторизации."],
  ["Not found", "Запрошенный ресурс не найден."],
  ["Permission denied", "Недостаточно прав для выполнения операции."],
  ["Failed to fetch", "Не удалось подключиться к серверу."],
  ["NetworkError", "Ошибка сетевого подключения."],
];

function translateError(message: string) {
  for (const [english, russian] of ERROR_TRANSLATIONS) {
    if (message.includes(english)) {
      return russian;
    }
  }

  const containsLatinLetters = /[A-Za-z]{3,}/.test(message);
  return containsLatinLetters
    ? "Произошла ошибка при выполнении запроса."
    : message;
}

function extractErrorMessage(data: unknown): string | null {
  if (typeof data === "string") {
    return data;
  }

  if (Array.isArray(data)) {
    for (const item of data) {
      const message = extractErrorMessage(item);
      if (message) return message;
    }
  }

  if (data && typeof data === "object") {
    const record = data as Record<string, unknown>;
    if (typeof record.detail === "string") {
      return record.detail;
    }

    for (const value of Object.values(record)) {
      const message = extractErrorMessage(value);
      if (message) return message;
    }
  }

  return null;
}

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

  let response: Response;

  try {
    response = await fetch(`${API_URL}${path}`, { ...options, headers });
  } catch {
    throw new Error(
      "Не удалось подключиться к серверу. Проверьте, что локальный проект запущен.",
    );
  }

  if (!response.ok) {
    const data = await response.json().catch(() => null);
    const message = extractErrorMessage(data) || "Ошибка выполнения запроса.";
    throw new Error(translateError(message));
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

export async function getMapLayers(
  bbox: [number, number, number, number],
  zoom: number,
  categories: string[] = [],
) {
  const params = new URLSearchParams({
    bbox: bbox.join(","),
    zoom: String(zoom),
  });

  if (categories.length) {
    params.set("categories", categories.join(","));
  }

  return request<MapLayersResponse>(`/map/layers/?${params.toString()}`);
}

export async function analyzePoint(latitude: number, longitude: number) {
  return request<AnalysisResponse>("/analysis/nearest/", {
    method: "POST",
    body: JSON.stringify({ latitude, longitude }),
  });
}
