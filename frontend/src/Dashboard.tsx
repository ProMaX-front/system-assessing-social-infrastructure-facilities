import { useEffect, useMemo, useRef, useState } from "react";
import maplibregl, {
  GeoJSONSource,
  Map,
  Marker,
  type ExpressionSpecification,
  type MapGeoJSONFeature,
  type StyleSpecification,
} from "maplibre-gl";
import type { Theme } from "./App";
import {
  AnalysisResponse,
  AnalysisResult,
  analyzePoint,
  getMapLayers,
} from "./api";

type Props = {
  user: { username: string };
  theme: Theme;
  onToggleTheme: () => void;
  onLogout: () => void;
};

const CATEGORY_COLORS: Record<string, string> = {
  school: "#2563eb",
  kindergarten: "#8b5cf6",
  college: "#0ea5e9",
  university: "#1d4ed8",
  polyclinic: "#06b6d4",
  hospital: "#ef4444",
  pharmacy: "#db2777",
  shop: "#f59e0b",
  stop: "#0f766e",
  sport: "#16a34a",
  culture: "#7c3aed",
  social: "#9333ea",
  other: "#64748b",
};

const CATEGORY_LETTERS: Record<string, string> = {
  school: "Ш",
  kindergarten: "Д",
  college: "К",
  university: "В",
  polyclinic: "П",
  hospital: "Б",
  pharmacy: "А",
  shop: "М",
  stop: "О",
  sport: "С",
  culture: "К",
  social: "СО",
  other: "•",
};

const CATEGORY_COLOR_EXPRESSION: ExpressionSpecification = [
  "match",
  ["get", "category"],
  "school",
  CATEGORY_COLORS.school,
  "kindergarten",
  CATEGORY_COLORS.kindergarten,
  "college",
  CATEGORY_COLORS.college,
  "university",
  CATEGORY_COLORS.university,
  "polyclinic",
  CATEGORY_COLORS.polyclinic,
  "hospital",
  CATEGORY_COLORS.hospital,
  "pharmacy",
  CATEGORY_COLORS.pharmacy,
  "shop",
  CATEGORY_COLORS.shop,
  "stop",
  CATEGORY_COLORS.stop,
  "sport",
  CATEGORY_COLORS.sport,
  "culture",
  CATEGORY_COLORS.culture,
  "social",
  CATEGORY_COLORS.social,
  CATEGORY_COLORS.other,
];

const OSM_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution:
        '© <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a>',
      maxzoom: 19,
    },
  },
  layers: [
    {
      id: "osm",
      type: "raster",
      source: "osm",
    },
  ],
};

const EMPTY_GEOJSON: GeoJSON.FeatureCollection = {
  type: "FeatureCollection",
  features: [],
};

type IconName =
  | "layers"
  | "route"
  | "database"
  | "crosshair"
  | "sun"
  | "moon"
  | "logout"
  | "check"
  | "sparkles"
  | "map";

function UiIcon({
  name,
  size = 18,
}: {
  name: IconName;
  size?: number;
}) {
  const common = {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };

  const paths: Record<IconName, JSX.Element> = {
    layers: (
      <>
        <path d="m12 2 9 5-9 5-9-5 9-5Z" />
        <path d="m3 12 9 5 9-5" />
        <path d="m3 17 9 5 9-5" />
      </>
    ),
    route: (
      <>
        <circle cx="6" cy="19" r="2" />
        <circle cx="18" cy="5" r="2" />
        <path d="M8 19h3a4 4 0 0 0 4-4V9a2 2 0 0 1 2-2h1" />
      </>
    ),
    database: (
      <>
        <ellipse cx="12" cy="5" rx="8" ry="3" />
        <path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5" />
        <path d="M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6" />
      </>
    ),
    crosshair: (
      <>
        <circle cx="12" cy="12" r="7" />
        <path d="M12 2v3M12 19v3M2 12h3M19 12h3" />
        <circle cx="12" cy="12" r="1.6" />
      </>
    ),
    sun: (
      <>
        <circle cx="12" cy="12" r="4" />
        <path d="M12 2v2M12 20v2M4.93 4.93l1.42 1.42M17.65 17.65l1.42 1.42M2 12h2M20 12h2M4.93 19.07l1.42-1.42M17.65 6.35l1.42-1.42" />
      </>
    ),
    moon: <path d="M20.5 14.2A8.5 8.5 0 0 1 9.8 3.5 8.5 8.5 0 1 0 20.5 14.2Z" />,
    logout: (
      <>
        <path d="M10 5H5v14h5" />
        <path d="m14 8 4 4-4 4M18 12H9" />
      </>
    ),
    check: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="m8 12 2.5 2.5L16.5 8.5" />
      </>
    ),
    sparkles: (
      <>
        <path d="m12 3 1.3 3.2L16.5 7.5l-3.2 1.3L12 12l-1.3-3.2-3.2-1.3 3.2-1.3L12 3Z" />
        <path d="m18.5 14 .8 2 2 .8-2 .8-.8 2-.8-2-2-.8 2-.8.8-2Z" />
        <path d="m5 14 .7 1.7 1.8.8-1.8.7L5 19l-.8-1.8-1.7-.7 1.7-.8L5 14Z" />
      </>
    ),
    map: (
      <>
        <path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3V6Z" />
        <path d="M9 3v15M15 6v15" />
      </>
    ),
  };

  return <svg {...common}>{paths[name]}</svg>;
}

function formatDistance(distance: number) {
  if (distance < 1000) {
    return `${Math.round(distance)} м`;
  }

  return `${(distance / 1000).toFixed(1).replace(".", ",")} км`;
}

function popupNode(
  title: unknown,
  rows: Array<[string, unknown]>,
) {
  const root = document.createElement("div");
  root.className = "map-popup";

  const heading = document.createElement("strong");
  heading.textContent = String(title || "Объект");
  root.appendChild(heading);

  for (const [label, value] of rows) {
    if (value === null || value === undefined || value === "") {
      continue;
    }

    const row = document.createElement("div");
    const rowLabel = document.createElement("span");
    rowLabel.textContent = `${label}: `;
    const rowValue = document.createElement("b");
    rowValue.textContent = String(value);
    row.append(rowLabel, rowValue);
    root.appendChild(row);
  }

  return root;
}

function featureProperties(feature: MapGeoJSONFeature | undefined) {
  return (feature?.properties || {}) as Record<string, unknown>;
}

type RouteCoordinate = [number, number];

type RouteProfile = {
  coordinates: RouteCoordinate[];
  cumulative: number[];
  total: number;
};

function haversineMeters(a: RouteCoordinate, b: RouteCoordinate) {
  const radius = 6_371_008.8;
  const toRadians = (value: number) => (value * Math.PI) / 180;
  const lat1 = toRadians(a[1]);
  const lat2 = toRadians(b[1]);
  const dLat = toRadians(b[1] - a[1]);
  const dLon = toRadians(b[0] - a[0]);

  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1) *
      Math.cos(lat2) *
      Math.sin(dLon / 2) ** 2;

  return 2 * radius * Math.asin(Math.sqrt(h));
}

function routeBearing(a: RouteCoordinate, b: RouteCoordinate) {
  const toRadians = (value: number) => (value * Math.PI) / 180;
  const toDegrees = (value: number) => (value * 180) / Math.PI;
  const lat1 = toRadians(a[1]);
  const lat2 = toRadians(b[1]);
  const dLon = toRadians(b[0] - a[0]);

  const y = Math.sin(dLon) * Math.cos(lat2);
  const x =
    Math.cos(lat1) * Math.sin(lat2) -
    Math.sin(lat1) * Math.cos(lat2) * Math.cos(dLon);

  return (toDegrees(Math.atan2(y, x)) + 360) % 360;
}

function buildRouteProfile(coordinates: number[][]): RouteProfile | null {
  if (coordinates.length < 2) {
    return null;
  }

  const routeCoordinates = coordinates.map(
    ([lon, lat]) => [lon, lat] as RouteCoordinate,
  );
  const cumulative = [0];

  for (let index = 1; index < routeCoordinates.length; index += 1) {
    cumulative.push(
      cumulative[index - 1] +
        haversineMeters(
          routeCoordinates[index - 1],
          routeCoordinates[index],
        ),
    );
  }

  return {
    coordinates: routeCoordinates,
    cumulative,
    total: cumulative[cumulative.length - 1],
  };
}

function pointAtRouteDistance(profile: RouteProfile, distance: number) {
  const safeDistance = Math.max(0, Math.min(distance, profile.total));

  let segmentIndex = 1;
  while (
    segmentIndex < profile.cumulative.length &&
    profile.cumulative[segmentIndex] < safeDistance
  ) {
    segmentIndex += 1;
  }

  if (segmentIndex >= profile.coordinates.length) {
    const last = profile.coordinates.length - 1;
    return {
      coordinate: profile.coordinates[last],
      bearing: routeBearing(
        profile.coordinates[Math.max(0, last - 1)],
        profile.coordinates[last],
      ),
    };
  }

  const start = profile.coordinates[segmentIndex - 1];
  const end = profile.coordinates[segmentIndex];
  const segmentStartDistance = profile.cumulative[segmentIndex - 1];
  const segmentLength =
    profile.cumulative[segmentIndex] - segmentStartDistance;
  const ratio =
    segmentLength > 0
      ? (safeDistance - segmentStartDistance) / segmentLength
      : 0;

  return {
    coordinate: [
      start[0] + (end[0] - start[0]) * ratio,
      start[1] + (end[1] - start[1]) * ratio,
    ] as RouteCoordinate,
    bearing: routeBearing(start, end),
  };
}

function createOriginMarker() {
  const shell = document.createElement("div");
  shell.className = "origin-marker-shell";

  const visual = document.createElement("div");
  visual.className = "analysis-origin-marker";
  visual.innerHTML =
    '<span class="origin-ring origin-ring-a"></span>' +
    '<span class="origin-ring origin-ring-b"></span>' +
    '<span class="origin-dot"></span>';

  shell.appendChild(visual);
  return shell;
}

function createTargetMarker(item: AnalysisResult) {
  const shell = document.createElement("div");
  shell.className = "target-marker-shell";

  const visual = document.createElement("div");
  visual.className = "analysis-target-marker";
  visual.style.setProperty(
    "--marker-color",
    CATEGORY_COLORS[item.category] || CATEGORY_COLORS.other,
  );

  const pulse = document.createElement("span");
  pulse.className = "target-marker-pulse";

  const core = document.createElement("span");
  core.className = "target-marker-core";
  core.textContent = CATEGORY_LETTERS[item.category] || "•";

  visual.append(pulse, core);
  visual.title = `${item.category_label}: ${item.object?.name || ""}`;
  shell.appendChild(visual);

  return shell;
}

function createWalkerMarker(item: AnalysisResult) {
  const shell = document.createElement("div");
  shell.className = "walker-marker-shell";
  shell.style.setProperty(
    "--walker-color",
    CATEGORY_COLORS[item.category] || CATEGORY_COLORS.other,
  );

  const rotator = document.createElement("div");
  rotator.className = "walker-rotator";

  const person = document.createElement("div");
  person.className = "walker-person";
  person.innerHTML =
    '<span class="walker-shadow"></span>' +
    '<span class="walker-head"></span>' +
    '<span class="walker-torso"></span>' +
    '<span class="walker-arm walker-arm-left"></span>' +
    '<span class="walker-arm walker-arm-right"></span>' +
    '<span class="walker-leg walker-leg-left"></span>' +
    '<span class="walker-leg walker-leg-right"></span>';

  const badge = document.createElement("span");
  badge.className = "walker-limit-badge";

  rotator.appendChild(person);
  shell.append(rotator, badge);
  shell.title = `Пешеход: ${item.category_label}`;

  return { shell, rotator, badge };
}

export default function Dashboard({
  user,
  theme,
  onToggleTheme,
  onLogout,
}: Props) {
  const mapContainer = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<Map | null>(null);
  const analysisMarker = useRef<Marker | null>(null);
  const targetMarkers = useRef<Marker[]>([]);
  const walkerMarkers = useRef<Marker[]>([]);
  const walkerAnimationEpoch = useRef(0);
  const requestNumber = useRef(0);

  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const [layerInfo, setLayerInfo] = useState(
    "Загрузка геоданных из PostGIS…",
  );
  const [status, setStatus] = useState(
    "Выберите точку на карте для расчёта доступности",
  );

  const summary = useMemo(() => {
    const results = analysis?.results || [];
    return {
      found: results.filter((item) => item.object).length,
      routes: results.filter((item) => item.route_is_osm).length,
      compliant: results.filter((item) => item.compliant === true).length,
    };
  }, [analysis]);

  useEffect(() => {
    if (!mapContainer.current || mapRef.current) {
      return;
    }

    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: OSM_STYLE,
      center: [65.5412, 57.1522],
      zoom: 12,
      attributionControl: { compact: true },
      locale: {
        "NavigationControl.ZoomIn": "Приблизить",
        "NavigationControl.ZoomOut": "Отдалить",
        "NavigationControl.ResetBearing": "Сбросить направление",
        "AttributionControl.ToggleAttribution": "Показать источники карты",
      },
    });

    map.addControl(new maplibregl.NavigationControl(), "top-right");
    map.addControl(
      new maplibregl.ScaleControl({ maxWidth: 120, unit: "metric" }),
      "bottom-right",
    );

    const loadViewportData = async () => {
      const currentRequest = ++requestNumber.current;
      const bounds = map.getBounds();

      try {
        const result = await getMapLayers(
          [
            bounds.getWest(),
            bounds.getSouth(),
            bounds.getEast(),
            bounds.getNorth(),
          ],
          map.getZoom(),
        );

        if (currentRequest !== requestNumber.current) {
          return;
        }

        (
          map.getSource("database-social-objects") as GeoJSONSource | undefined
        )?.setData(result.social_objects);

        (
          map.getSource("database-buildings") as GeoJSONSource | undefined
        )?.setData(result.buildings);

        const parts = [
          `инфраструктура: ${result.meta.social_objects_count}`,
          `здания: ${result.meta.buildings_count}`,
        ];

        if (
          result.meta.social_objects_truncated ||
          result.meta.buildings_truncated
        ) {
          parts.push("приблизьте карту для полного набора");
        } else if (result.meta.all_buildings_visible) {
          parts.push("все здания текущей области");
        } else {
          parts.push("приблизьте для всех зданий");
        }

        setLayerInfo(parts.join(" · "));
      } catch (error) {
        if (currentRequest !== requestNumber.current) {
          return;
        }
        setLayerInfo(
          error instanceof Error
            ? error.message
            : "Не удалось загрузить геоданные.",
        );
      }
    };

    map.on("load", () => {
      map.addSource("database-buildings", {
        type: "geojson",
        data: EMPTY_GEOJSON,
      });

      map.addLayer({
        id: "database-buildings-fill",
        type: "fill",
        source: "database-buildings",
        minzoom: 11,
        paint: {
          "fill-color": CATEGORY_COLOR_EXPRESSION,
          "fill-opacity": [
            "case",
            ["==", ["get", "category"], ""],
            0.055,
            0.18,
          ],
        },
      });

      map.addLayer({
        id: "database-buildings-outline",
        type: "line",
        source: "database-buildings",
        minzoom: 11,
        paint: {
          "line-color": CATEGORY_COLOR_EXPRESSION,
          "line-opacity": [
            "case",
            ["==", ["get", "category"], ""],
            0.26,
            0.7,
          ],
          "line-width": [
            "case",
            ["==", ["get", "category"], ""],
            0.65,
            1.35,
          ],
        },
      });

      map.addSource("database-social-objects", {
        type: "geojson",
        data: EMPTY_GEOJSON,
      });

      map.addLayer({
        id: "database-social-objects-halo",
        type: "circle",
        source: "database-social-objects",
        minzoom: 10,
        paint: {
          "circle-radius": [
            "interpolate",
            ["linear"],
            ["zoom"],
            10,
            3.7,
            14,
            7.5,
            18,
            10.5,
          ],
          "circle-color": "#ffffff",
          "circle-opacity": 0.88,
        },
      });

      map.addLayer({
        id: "database-social-objects",
        type: "circle",
        source: "database-social-objects",
        minzoom: 10,
        paint: {
          "circle-radius": [
            "interpolate",
            ["linear"],
            ["zoom"],
            10,
            2.1,
            14,
            5.3,
            18,
            8,
          ],
          "circle-color": CATEGORY_COLOR_EXPRESSION,
          "circle-stroke-width": 0.6,
          "circle-stroke-color": "#ffffff",
        },
      });

      map.addSource("analysis-footprints", {
        type: "geojson",
        data: EMPTY_GEOJSON,
      });

      map.addLayer({
        id: "analysis-footprints-fill",
        type: "fill",
        source: "analysis-footprints",
        paint: {
          "fill-color": ["get", "color"],
          "fill-opacity": 0.34,
        },
      });

      map.addLayer({
        id: "analysis-footprints-outline-glow",
        type: "line",
        source: "analysis-footprints",
        paint: {
          "line-color": ["get", "color"],
          "line-width": 8,
          "line-opacity": 0.12,
          "line-blur": 4,
        },
      });

      map.addLayer({
        id: "analysis-footprints-outline",
        type: "line",
        source: "analysis-footprints",
        paint: {
          "line-color": ["get", "color"],
          "line-width": 3,
          "line-opacity": 0.94,
        },
      });

      map.addSource("analysis-routes", {
        type: "geojson",
        data: EMPTY_GEOJSON,
      });

      map.addLayer({
        id: "analysis-routes-glow",
        type: "line",
        source: "analysis-routes",
        filter: ["==", ["get", "route_is_osm"], true],
        paint: {
          "line-color": ["get", "color"],
          "line-width": 13,
          "line-opacity": 0.13,
          "line-blur": 5,
        },
      });

      map.addLayer({
        id: "analysis-routes-direct",
        type: "line",
        source: "analysis-routes",
        filter: ["==", ["get", "route_is_osm"], false],
        paint: {
          "line-color": ["get", "color"],
          "line-width": 3,
          "line-opacity": 0.68,
          "line-dasharray": [2, 2],
        },
      });

      map.addLayer({
        id: "analysis-routes-osm",
        type: "line",
        source: "analysis-routes",
        filter: ["==", ["get", "route_is_osm"], true],
        paint: {
          "line-color": ["get", "color"],
          "line-width": 4.2,
          "line-opacity": 0.96,
        },
      });

      setMapReady(true);
      void loadViewportData();
    });

    map.on("moveend", () => {
      void loadViewportData();
    });

    map.on("mouseenter", "database-social-objects", () => {
      map.getCanvas().style.cursor = "pointer";
    });
    map.on("mouseleave", "database-social-objects", () => {
      map.getCanvas().style.cursor = "";
    });
    map.on("mouseenter", "database-buildings-fill", () => {
      map.getCanvas().style.cursor = "pointer";
    });
    map.on("mouseleave", "database-buildings-fill", () => {
      map.getCanvas().style.cursor = "";
    });

    map.on("click", "database-social-objects", (event) => {
      event.preventDefault();
      const feature = event.features?.[0];
      const properties = featureProperties(feature);

      new maplibregl.Popup({ offset: 14 })
        .setLngLat(event.lngLat)
        .setDOMContent(
          popupNode(properties.name || properties.category_label, [
            ["Категория", properties.category_label],
            ["Подтип", properties.subcategory],
            ["Адрес", properties.address],
            ["OSM", properties.source_id],
          ]),
        )
        .addTo(map);
    });

    map.on("click", "database-buildings-fill", (event) => {
      if (event.defaultPrevented) {
        return;
      }

      event.preventDefault();
      const feature = event.features?.[0];
      const properties = featureProperties(feature);

      new maplibregl.Popup({ offset: 14 })
        .setLngLat(event.lngLat)
        .setDOMContent(
          popupNode(
            properties.name ||
              properties.category_label ||
              properties.building_type ||
              "Здание OSM",
            [
              ["Категория", properties.category_label],
              ["Тип здания", properties.building_type],
              ["Адрес", properties.address],
              [
                "OSM",
                properties.osm_type && properties.osm_id
                  ? `${properties.osm_type}/${properties.osm_id}`
                  : "",
              ],
            ],
          ),
        )
        .addTo(map);
    });

    map.on("click", async (event) => {
      if (event.defaultPrevented) {
        return;
      }

      analysisMarker.current?.remove();
      setAnalysis(null);
      analysisMarker.current = new maplibregl.Marker({
        element: createOriginMarker(),
        anchor: "center",
      })
        .setLngLat(event.lngLat)
        .addTo(map);

      setStatus("Анализируем пешеходную доступность…");

      try {
        const result = await analyzePoint(
          event.lngLat.lat,
          event.lngLat.lng,
        );
        setAnalysis(result);

        const routes = result.results.filter(
          (item) => item.route_is_osm,
        ).length;
        const found = result.results.filter((item) => item.object).length;

        setStatus(
          routes > 0
            ? `Построено маршрутов по графу OSM: ${routes} из ${found}`
            : "Маршрут по пешеходному графу для выбранной точки не найден",
        );
      } catch (error) {
        setStatus(
          error instanceof Error ? error.message : "Ошибка анализа.",
        );
      }
    });

    mapRef.current = map;

    return () => {
      requestNumber.current += 1;
      analysisMarker.current?.remove();
      walkerAnimationEpoch.current += 1;
      targetMarkers.current.forEach((marker) => marker.remove());
      walkerMarkers.current.forEach((marker) => marker.remove());
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;

    if (!map || !mapReady) {
      return;
    }

    const animationEpoch = ++walkerAnimationEpoch.current;

    targetMarkers.current.forEach((marker) => marker.remove());
    targetMarkers.current = [];
    walkerMarkers.current.forEach((marker) => marker.remove());
    walkerMarkers.current = [];

    const routeFeatures: GeoJSON.Feature[] =
      analysis?.results
        .filter((item) => item.route_geometry)
        .map((item) => ({
          type: "Feature",
          geometry: item.route_geometry!,
          properties: {
            category: item.category,
            color:
              CATEGORY_COLORS[item.category] || CATEGORY_COLORS.other,
            route_is_osm: item.route_is_osm,
          },
        })) || [];

    const footprintFeatures: GeoJSON.Feature[] =
      analysis?.results
        .filter((item) => item.object?.footprint)
        .map((item) => ({
          type: "Feature",
          geometry: item.object!.footprint as GeoJSON.Geometry,
          properties: {
            category: item.category,
            color:
              CATEGORY_COLORS[item.category] || CATEGORY_COLORS.other,
          },
        })) || [];

    (map.getSource("analysis-routes") as GeoJSONSource)?.setData({
      type: "FeatureCollection",
      features: routeFeatures,
    });

    (map.getSource("analysis-footprints") as GeoJSONSource)?.setData({
      type: "FeatureCollection",
      features: footprintFeatures,
    });

    const routedItems =
      analysis?.results.filter(
        (item) =>
          item.object &&
          item.route_geometry &&
          item.route_geometry.coordinates.length >= 2,
      ) || [];

    routedItems.forEach((item, index) => {
      if (!item.object || !item.route_geometry) {
        return;
      }

      const targetMarker = new maplibregl.Marker({
        element: createTargetMarker(item),
        anchor: "center",
      })
        .setLngLat([item.object.longitude, item.object.latitude])
        .setPopup(
          new maplibregl.Popup({ offset: 24 }).setDOMContent(
            popupNode(item.object.name, [
              ["Категория", item.category_label],
              [
                "Расстояние",
                item.distance_m !== null
                  ? formatDistance(item.distance_m)
                  : "",
              ],
              [
                "Норматив",
                item.normative_distance_m !== null
                  ? formatDistance(item.normative_distance_m)
                  : "",
              ],
              ["Адрес", item.object.address],
            ]),
          ),
        )
        .addTo(map);

      targetMarkers.current.push(targetMarker);

      if (!item.route_is_osm) {
        return;
      }

      const profile = buildRouteProfile(
        item.route_geometry.coordinates,
      );
      if (!profile || profile.total <= 0) {
        return;
      }

      const routeDistance = item.distance_m || profile.total;
      const normativeDistance = item.normative_distance_m;
      const exceedsNormative =
        normativeDistance !== null &&
        normativeDistance > 0 &&
        routeDistance > normativeDistance;

      const targetRatio =
        exceedsNormative && normativeDistance !== null
          ? Math.max(
              0,
              Math.min(1, normativeDistance / routeDistance),
            )
          : 1;
      const targetRouteDistance = profile.total * targetRatio;

      const { shell, rotator, badge } = createWalkerMarker(item);
      const initial = pointAtRouteDistance(profile, 0);

      const walkerMarker = new maplibregl.Marker({
        element: shell,
        anchor: "center",
      })
        .setLngLat(initial.coordinate)
        .addTo(map);

      rotator.style.transform = `rotate(${initial.bearing}deg)`;
      walkerMarkers.current.push(walkerMarker);

      const delay = 320 + index * 90;
      const duration =
        2200 + Math.min(2800, targetRouteDistance * 2.2);
      const createdAt = performance.now();

      const animate = (now: number) => {
        if (walkerAnimationEpoch.current !== animationEpoch) {
          return;
        }

        const elapsed = now - createdAt - delay;
        if (elapsed < 0) {
          requestAnimationFrame(animate);
          return;
        }

        const progress = Math.min(1, elapsed / duration);
        const current = pointAtRouteDistance(
          profile,
          targetRouteDistance * progress,
        );

        walkerMarker.setLngLat(current.coordinate);
        rotator.style.transform = `rotate(${current.bearing}deg)`;

        if (progress < 1) {
          requestAnimationFrame(animate);
          return;
        }

        shell.classList.add("is-stopped");

        if (exceedsNormative && normativeDistance !== null) {
          shell.classList.add("is-limit");
          badge.textContent = `Норма ${formatDistance(normativeDistance)}`;
          shell.title =
            `${item.category_label}: нормативная дистанция исчерпана`;
        } else {
          shell.classList.add("is-arrived");
          badge.textContent = "Доступно";
          shell.title =
            `${item.category_label}: объект достигнут в пределах норматива`;
        }
      };

      requestAnimationFrame(animate);
    });

    return () => {
      walkerAnimationEpoch.current += 1;
      targetMarkers.current.forEach((marker) => marker.remove());
      targetMarkers.current = [];
      walkerMarkers.current.forEach((marker) => marker.remove());
      walkerMarkers.current = [];
    };
  }, [analysis, mapReady]);

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">
            <UiIcon name="map" size={20} />
          </div>
          <div className="brand-copy">
            <strong>Urban Access</strong>
            <span>ГИС оценки социальной инфраструктуры</span>
          </div>
        </div>

        <div className="topbar-actions">
          <div className="system-status">
            <span className="status-dot" />
            PostGIS подключён
          </div>

          <button
            type="button"
            className="icon-button"
            onClick={onToggleTheme}
            title={
              theme === "light"
                ? "Включить тёмную тему"
                : "Включить светлую тему"
            }
            aria-label={
              theme === "light"
                ? "Включить тёмную тему"
                : "Включить светлую тему"
            }
          >
            <UiIcon name={theme === "light" ? "moon" : "sun"} />
          </button>

          <div className="user-pill">
            <span className="user-avatar">
              {user.username.slice(0, 1).toUpperCase()}
            </span>
            <span>{user.username}</span>
          </div>

          <button
            type="button"
            className="icon-button"
            onClick={onLogout}
            title="Выйти"
            aria-label="Выйти"
          >
            <UiIcon name="logout" />
          </button>
        </div>
      </header>

      <div className="workspace">
        <aside className="sidebar">
          <section className="sidebar-intro">
            <div className="section-kicker">
              <UiIcon name="sparkles" size={15} />
              Пространственный анализ
            </div>
            <h1>Ближайшая инфраструктура</h1>
            <p>{status}</p>
          </section>

          {analysis ? (
            <div className="analysis-summary">
              <div className="summary-card">
                <span className="summary-icon">
                  <UiIcon name="layers" size={17} />
                </span>
                <div>
                  <strong>{summary.found}</strong>
                  <span>объектов</span>
                </div>
              </div>
              <div className="summary-card">
                <span className="summary-icon">
                  <UiIcon name="route" size={17} />
                </span>
                <div>
                  <strong>{summary.routes}</strong>
                  <span>маршрутов</span>
                </div>
              </div>
              <div className="summary-card">
                <span className="summary-icon">
                  <UiIcon name="check" size={17} />
                </span>
                <div>
                  <strong>{summary.compliant}</strong>
                  <span>в нормативе</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="empty-state modern-empty">
              <span className="empty-icon">
                <UiIcon name="crosshair" size={24} />
              </span>
              <div>
                <strong>Укажите точку анализа</strong>
                <p>
                  Нажмите на свободную область карты. Система найдёт
                  инфраструктуру, построит пешеходные маршруты и подсветит
                  геометрию целевых объектов.
                </p>
              </div>
            </div>
          )}

          <div className="results">
            {analysis?.results.map((item) => {
              const color =
                CATEGORY_COLORS[item.category] || CATEGORY_COLORS.other;

              return (
                <article
                  className={`result-card ${
                    item.object ? "has-object" : "no-object"
                  }`}
                  key={item.category}
                >
                  <div
                    className="result-category-icon"
                    style={{
                      backgroundColor: color,
                      boxShadow: `0 10px 26px ${color}2d`,
                    }}
                  >
                    {CATEGORY_LETTERS[item.category] || "•"}
                  </div>

                  <div className="result-content">
                    <div className="result-title-row">
                      <strong>{item.category_label}</strong>
                      <span
                        className={`compliance ${
                          item.compliant === true
                            ? "ok"
                            : item.compliant === false
                              ? "bad"
                              : "neutral"
                        }`}
                      >
                        {item.compliant === true
                          ? "В нормативе"
                          : item.compliant === false
                            ? "Выше нормы"
                            : "Без оценки"}
                      </span>
                    </div>

                    <span className="object-name">
                      {item.object?.name || item.message}
                    </span>

                    {item.distance_m !== null && (
                      <div className="result-metrics">
                        <div>
                          <b>{formatDistance(item.distance_m)}</b>
                          <small>по маршруту</small>
                        </div>
                        <div>
                          <b>
                            {item.normative_distance_m
                              ? formatDistance(item.normative_distance_m)
                              : "—"}
                          </b>
                          <small>норматив</small>
                        </div>
                      </div>
                    )}

                    {item.object && (
                      <div className="result-meta">
                        <span>
                          <UiIcon name="route" size={13} />
                          {item.distance_method}
                        </span>
                        {item.object.footprint && (
                          <span>
                            <UiIcon name="layers" size={13} />
                            Геометрия объекта найдена
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        </aside>

        <main className="map-area">
          <div className="map-data-card">
            <span className="map-data-icon">
              <UiIcon name="database" size={18} />
            </span>
            <div>
              <strong>Пространственные данные</strong>
              <span>{layerInfo}</span>
            </div>
          </div>

          <div className="map-legend">
            <span>
              <i className="legend-point" />
              объект
            </span>
            <span>
              <i className="legend-target">А</i>
              цель маршрута
            </span>
            <span>
              <i className="legend-line" />
              пешеходный путь
            </span>
          </div>

          <div ref={mapContainer} className="map" />
        </main>
      </div>
    </div>
  );
}
