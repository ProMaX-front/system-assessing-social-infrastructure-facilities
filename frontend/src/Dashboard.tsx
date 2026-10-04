import { useEffect, useRef, useState } from "react";
import maplibregl, { Map, Marker } from "maplibre-gl";
import { AnalysisResponse, analyzePoint, getSocialObjects, SocialObject } from "./api";

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
  other: "•",
};

export default function Dashboard({ user, onLogout }: Props) {
  const mapContainer = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<Map | null>(null);
  const analysisMarker = useRef<Marker | null>(null);
  const objectMarkers = useRef<Marker[]>([]);
  const [objects, setObjects] = useState<SocialObject[]>([]);
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [status, setStatus] = useState("Нажмите на карту для анализа точки");

  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: "https://demotiles.maplibre.org/style.json",
      center: [65.5412, 57.1522],
      zoom: 12,
    });
    map.addControl(new maplibregl.NavigationControl(), "top-right");

    map.on("click", async (event) => {
      analysisMarker.current?.remove();
      analysisMarker.current = new maplibregl.Marker({ color: "#111827" })
        .setLngLat(event.lngLat)
        .addTo(map);

      setStatus("Выполняется анализ…");
      try {
        const result = await analyzePoint(event.lngLat.lat, event.lngLat.lng);
        setAnalysis(result);
        setStatus("Расчёт выполнен");
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
    if (!map) return;
    objectMarkers.current.forEach((marker) => marker.remove());
    objectMarkers.current = objects.map((object) => {
      const element = document.createElement("div");
      element.className = "object-marker";
      element.textContent = CATEGORY_ICONS[object.category] || "•";
      element.title = object.name;
      return new maplibregl.Marker({ element })
        .setLngLat([object.longitude, object.latitude])
        .setPopup(new maplibregl.Popup({ offset: 16 }).setHTML(
          `<strong>${object.name}</strong><br/>${object.category_label}<br/>${object.address || ""}`
        ))
        .addTo(map);
    });
  }, [objects]);

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <strong>Социальная инфраструктура</strong>
          <span>Оценка обеспеченности урбанизированной территории</span>
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
              Поставьте точку на карте. Система найдёт ближайший объект каждой категории и сравнит расстояние с нормативом.
            </div>
          )}

          <div className="results">
            {analysis?.results.map((item) => (
              <article className="result-card" key={item.category}>
                <div className={`status-dot ${item.compliant === true ? "ok" : item.compliant === false ? "bad" : "neutral"}`} />
                <div>
                  <strong>{item.object?.category_label || item.category}</strong>
                  <span>{item.object?.name || item.message}</span>
                  {item.distance_m !== null && (
                    <small>
                      {Math.round(item.distance_m)} м
                      {item.normative_distance_m ? ` · норматив ≤ ${item.normative_distance_m} м` : " · норматив не задан"}
                    </small>
                  )}
                </div>
              </article>
            ))}
          </div>
        </aside>
        <main className="map-area">
          <div className="map-hint">Выберите точку на карте</div>
          <div ref={mapContainer} className="map" />
        </main>
      </div>
    </div>
  );
}
