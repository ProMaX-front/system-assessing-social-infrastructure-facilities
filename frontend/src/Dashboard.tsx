import { useEffect, useRef, useState } from "react";
import maplibregl, {
  GeoJSONSource,
  Map,
  Marker,
  type StyleSpecification,
} from "maplibre-gl";
import {
  AnalysisResponse,
  analyzePoint,
  getSocialObjects,
  SocialObject,
} from "./api";

type Props = {
  user: { username: string };
  onLogout: () => void;
};

const CATEGORY_ICONS: Record<string, string> = {
  school: "Ш",
  kindergarten: "Д",
  polyclinic: "П",
  hospital: "Б",
  shop: "М",
  stop: "О",
  sport: "С",
  pharmacy: "А",
  culture: "К",
  other: "СО",
};

const CATEGORY_COLORS: Record<string, string> = {
  school: "#2563eb",
  kindergarten: "#8b5cf6",
  polyclinic: "#06b6d4",
  hospital: "#ef4444",
  shop: "#f59e0b",
  stop: "#0f766e",
  sport: "#16a34a",
  pharmacy: "#db2777",
  culture: "#7c3aed",
  other: "#64748b",
};

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

export default function Dashboard({ user, onLogout }: Props) {
  const mapContainer = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<Map | null>(null);
  const analysisMarker = useRef<Marker | null>(null);
  const objectMarkers = useRef<Marker[]>([]);

  const [objects, setObjects] = useState<SocialObject[]>([]);
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const [status, setStatus] = useState(
    "Нажмите на карту для анализа выбранной точки",
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

    map.on("load", () => {
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
          "fill-opacity": 0.24,
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
    });

    map.on("click", async (event) => {
      analysisMarker.current?.remove();
      analysisMarker.current = new maplibregl.Marker({ color: "#111827" })
        .setLngLat(event.lngLat)
        .addTo(map);

      setStatus("Выполняется расчёт доступности…");

      try {
        const result = await analyzePoint(event.lngLat.lat, event.lngLat.lng);
        setAnalysis(result);

        const hasOsmRoutes = result.results.some((item) => item.route_is_osm);
        setStatus(
          hasOsmRoutes
            ? "Расстояния рассчитаны по пешеходному графу OpenStreetMap"
            : "Граф OSM не загружен: временно показаны расстояния по прямой",
        );
      } catch (e) {
        setStatus(e instanceof Error ? e.message : "Ошибка анализа");
      }
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    getSocialObjects()
      .then(setObjects)
      .catch(() => setObjects([]));
  }, []);

  useEffect(() => {
    const map = mapRef.current;

    if (!map || !mapReady) {
      return;
    }

    objectMarkers.current.forEach((marker) => marker.remove());

    objectMarkers.current = objects.map((object) => {
      const element = document.createElement("div");
      element.className = "object-marker";
      element.textContent = CATEGORY_ICONS[object.category] || "•";
      element.title = object.name;
      element.style.backgroundColor =
        CATEGORY_COLORS[object.category] || CATEGORY_COLORS.other;

      return new maplibregl.Marker({ element })
        .setLngLat([object.longitude, object.latitude])
        .setPopup(
          new maplibregl.Popup({ offset: 16 }).setHTML(
            `<strong>${object.name}</strong><br/>${object.category_label}<br/>${object.address || ""}`,
          ),
        )
        .addTo(map);
    });
  }, [objects, mapReady]);

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
          <span>{user.username}</span>
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
              Поставьте точку на карте. Система найдёт ближайший объект каждой
              категории, построит маршрут и сравнит расстояние с нормативом.
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
                      className={`compliance ${item.compliant === true ? "ok" : item.compliant === false ? "bad" : "neutral"}`}
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
                          ? `Норматив: не более ${formatDistance(item.normative_distance_m)}`
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
          <div className="map-hint">Нажмите на карту для расчёта</div>
          <div ref={mapContainer} className="map" />
        </main>
      </div>
    </div>
  );
}
