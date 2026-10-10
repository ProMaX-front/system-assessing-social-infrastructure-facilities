import { useEffect, useRef, useState } from "react";
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

export default function Dashboard({
  user,
  theme,
  onToggleTheme,
  onLogout,
}: Props) {
  const mapContainer = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<Map | null>(null);
  const analysisMarker = useRef<Marker | null>(null);
  const requestNumber = useRef(0);

  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const [layerInfo, setLayerInfo] = useState(
    "Загрузка геоданных из PostGIS…",
  );
  const [status, setStatus] = useState(
    "Нажмите на свободную область карты для анализа выбранной точки",
  );

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

        if (result.meta.social_objects_truncated || result.meta.buildings_truncated) {
          parts.push("показана часть объектов — приблизьте карту");
        } else if (result.meta.all_buildings_visible) {
          parts.push("показаны все типы зданий в текущей области");
        } else {
          parts.push("для всех зданий приблизьте карту");
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
            0.08,
            0.26,
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
            0.36,
            0.9,
          ],
          "line-width": [
            "case",
            ["==", ["get", "category"], ""],
            0.7,
            1.8,
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
            4,
            14,
            8,
            18,
            11,
          ],
          "circle-color": "#ffffff",
          "circle-opacity": 0.94,
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
            2.5,
            14,
            6,
            18,
            9,
          ],
          "circle-color": CATEGORY_COLOR_EXPRESSION,
          "circle-stroke-width": 0.5,
          "circle-stroke-color": "#ffffff",
        },
      });

      map.addSource("analysis-routes", {
        type: "geojson",
        data: EMPTY_GEOJSON,
      });

      map.addLayer({
        id: "analysis-routes-direct",
        type: "line",
        source: "analysis-routes",
        filter: ["==", ["get", "route_is_osm"], false],
        paint: {
          "line-color": ["get", "color"],
          "line-width": 3,
          "line-opacity": 0.72,
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
          "line-width": 5,
          "line-opacity": 0.9,
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
          "fill-opacity": 0.38,
        },
      });

      map.addLayer({
        id: "analysis-footprints-outline",
        type: "line",
        source: "analysis-footprints",
        paint: {
          "line-color": ["get", "color"],
          "line-width": 3,
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

      new maplibregl.Popup({ offset: 12 })
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

      new maplibregl.Popup({ offset: 12 })
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
      analysisMarker.current = new maplibregl.Marker({ color: "#111827" })
        .setLngLat(event.lngLat)
        .addTo(map);

      setStatus("Выполняется расчёт доступности…");

      try {
        const result = await analyzePoint(event.lngLat.lat, event.lngLat.lng);
        setAnalysis(result);

        const osmRoutes = result.results.filter(
          (item) => item.route_is_osm,
        ).length;
        const foundObjects = result.results.filter(
          (item) => item.object,
        ).length;

        setStatus(
          osmRoutes > 0
            ? `Построено маршрутов по пешеходному графу: ${osmRoutes} из ${foundObjects}`
            : "Для выбранной точки маршрут по пешеходному графу не построен",
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
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;

    if (!map || !mapReady) {
      return;
    }

    const routeFeatures: GeoJSON.Feature[] =
      analysis?.results
        .filter((item) => item.route_geometry)
        .map((item) => ({
          type: "Feature",
          geometry: item.route_geometry!,
          properties: {
            category: item.category,
            color: CATEGORY_COLORS[item.category] || CATEGORY_COLORS.other,
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
            color: CATEGORY_COLORS[item.category] || CATEGORY_COLORS.other,
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
  }, [analysis, mapReady]);

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <strong>Оценка социальной инфраструктуры</strong>
          <span>Анализ обеспеченности урбанизированной территории</span>
        </div>

        <div className="user-box">
          <button
            type="button"
            className="theme-toggle"
            onClick={onToggleTheme}
            aria-label={
              theme === "light"
                ? "Переключить на тёмную тему"
                : "Переключить на светлую тему"
            }
          >
            <span aria-hidden="true">{theme === "light" ? "☾" : "☀"}</span>
            {theme === "light" ? "Тёмная тема" : "Светлая тема"}
          </button>
          <span className="username">{user.username}</span>
          <button onClick={onLogout}>Выйти</button>
        </div>
      </header>

      <div className="workspace">
        <aside className="sidebar">
          <div className="panel-heading">
            <span className="eyebrow">АНАЛИЗ ТОЧКИ</span>
            <h2>Ближайшая инфраструктура</h2>
            <p>{status}</p>
          </div>

          {!analysis && (
            <div className="empty-state">
              Поставьте точку на свободной области карты. Система найдёт
              ближайший объект каждой категории, построит маршрут и сравнит
              расстояние с нормативом.
            </div>
          )}

          <div className="results">
            {analysis?.results.map((item) => (
              <article className="result-card" key={item.category}>
                <div
                  className="category-stripe"
                  style={{
                    backgroundColor:
                      CATEGORY_COLORS[item.category] || CATEGORY_COLORS.other,
                  }}
                />

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
                        ? "Соответствует"
                        : item.compliant === false
                          ? "Не соответствует"
                          : "Нет оценки"}
                    </span>
                  </div>

                  <span>{item.object?.name || item.message}</span>

                  {item.distance_m !== null && (
                    <>
                      <b className="distance">
                        {formatDistance(item.distance_m)}
                      </b>
                      <small>
                        {item.normative_distance_m
                          ? `Норматив: не более ${formatDistance(
                              item.normative_distance_m,
                            )}`
                          : "Норматив расстояния не задан"}
                      </small>
                      <small>{item.distance_method}</small>
                    </>
                  )}
                </div>
              </article>
            ))}
          </div>
        </aside>

        <main className="map-area">
          <div className="map-hint">
            <strong>Данные PostGIS</strong>
            <span>{layerInfo}</span>
          </div>
          <div ref={mapContainer} className="map" />
        </main>
      </div>
    </div>
  );
}
