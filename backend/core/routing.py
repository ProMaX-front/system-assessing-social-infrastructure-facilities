import heapq
import math
from collections import defaultdict

from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Polygon

from .models import RoadEdge, RoadNode


MAX_LOCAL_EDGES = 180_000


def haversine_m(lon1, lat1, lon2, lat2):
    radius = 6_371_008.8
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(a))


def _nearest_walkable_node(point):
    return (
        RoadNode.objects.filter(walkable=True)
        .annotate(distance=Distance("geometry", point))
        .order_by("distance")
        .first()
    )


def _routing_bbox(start, end):
    min_lon = min(start.x, end.x)
    max_lon = max(start.x, end.x)
    min_lat = min(start.y, end.y)
    max_lat = max(start.y, end.y)

    span = max(max_lon - min_lon, max_lat - min_lat)
    margin = max(0.015, min(0.12, span * 0.45 + 0.01))
    return Polygon.from_bbox(
        (
            min_lon - margin,
            min_lat - margin,
            max_lon + margin,
            max_lat + margin,
        )
    )


def calculate_pedestrian_route(start_point, end_point):
    if not RoadEdge.objects.filter(walkable=True).exists():
        return None

    start_node = _nearest_walkable_node(start_point)
    end_node = _nearest_walkable_node(end_point)
    if not start_node or not end_node:
        return None

    bbox = _routing_bbox(start_point, end_point)
    edges_qs = RoadEdge.objects.filter(
        walkable=True,
        geometry__bboverlaps=bbox,
    ).only(
        "source_osm_id",
        "target_osm_id",
        "length_m",
        "geometry",
        "walk_forward",
        "walk_backward",
    )

    edge_count = edges_qs.count()
    if edge_count == 0 or edge_count > MAX_LOCAL_EDGES:
        return None

    adjacency = defaultdict(list)
    for edge in edges_qs.iterator(chunk_size=5000):
        coords = list(edge.geometry.coords)

        if edge.walk_forward:
            adjacency[edge.source_osm_id].append(
                (edge.target_osm_id, edge.length_m, coords)
            )

        if edge.walk_backward:
            adjacency[edge.target_osm_id].append(
                (
                    edge.source_osm_id,
                    edge.length_m,
                    list(reversed(coords)),
                )
            )

    start_id = start_node.osm_id
    end_id = end_node.osm_id
    if start_id not in adjacency or end_id not in adjacency:
        return None

    distances = {start_id: 0.0}
    previous = {}
    queue = [(0.0, start_id)]

    while queue:
        current_distance, current = heapq.heappop(queue)
        if current == end_id:
            break
        if current_distance != distances.get(current):
            continue

        for neighbor, edge_length, coords in adjacency.get(current, []):
            candidate = current_distance + edge_length
            if candidate < distances.get(neighbor, float("inf")):
                distances[neighbor] = candidate
                previous[neighbor] = (current, coords)
                heapq.heappush(queue, (candidate, neighbor))

    if end_id not in distances:
        return None

    segments = []
    current = end_id
    while current != start_id:
        if current not in previous:
            return None
        previous_node, coords = previous[current]
        segments.append(coords)
        current = previous_node
    segments.reverse()

    route_coords = [[start_point.x, start_point.y]]
    for segment in segments:
        for lon, lat in segment:
            coord = [lon, lat]
            if coord != route_coords[-1]:
                route_coords.append(coord)
    route_coords.append([end_point.x, end_point.y])

    connector_start = haversine_m(
        start_point.x,
        start_point.y,
        start_node.geometry.x,
        start_node.geometry.y,
    )
    connector_end = haversine_m(
        end_node.geometry.x,
        end_node.geometry.y,
        end_point.x,
        end_point.y,
    )

    return {
        "distance_m": round(
            distances[end_id] + connector_start + connector_end,
            1,
        ),
        "geometry": {
            "type": "LineString",
            "coordinates": route_coords,
        },
        "start_osm_node": start_id,
        "end_osm_node": end_id,
    }
