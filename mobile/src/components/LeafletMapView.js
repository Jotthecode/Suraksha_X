import React, { useMemo } from 'react';
import { StyleSheet, View, Platform } from 'react-native';
import { WebView } from 'react-native-webview';

export const LeafletMapView = ({
  centerLat = 22.9734,
  centerLon = 78.6569,
  zoom = 13,
  markers = [],
  hotspots = [],
  safestRoute = null,
  shortestRoute = null,
  style,
}) => {
  const htmlContent = useMemo(() => {
    const markersJson = JSON.stringify(markers || []);
    const hotspotsJson = JSON.stringify(hotspots || []);
    const safeRouteJson = JSON.stringify(safestRoute || []);
    const shortestRouteJson = JSON.stringify(shortestRoute || []);

    return `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    body, html, #map {
      margin: 0; padding: 0; width: 100%; height: 100%; background: #F1F5F9;
    }
    .leaflet-popup-content-wrapper {
      border-radius: 12px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .custom-badge {
      display: inline-block; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 11px;
    }
    .badge-safe { background: #E8F5E9; color: #2E7D32; }
    .badge-high { background: #FFEBEE; color: #D32F2F; }
  </style>
</head>
<body>
  <div id="map"></div>
  <script>
    var map = L.map('map', {
      zoomControl: false
    }).setView([${centerLat}, ${centerLon}], ${zoom});

    // Free OpenStreetMap tiles (no API key). The attribution is required by the tile usage policy.
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);
    map.attributionControl.setPrefix(false);

    L.control.zoom({ position: 'bottomright' }).addTo(map);

    // 1. Hotspots
    var hotspots = ${hotspotsJson};
    // Server grid cells: { lat, lon, risk_score, category } — only medium / high cells are drawn
    hotspots.forEach(function(h) {
      var lat = h.lat != null ? h.lat : h.latitude;
      var lon = h.lon != null ? h.lon : h.longitude;
      var category = h.category || h.risk_level || '';
      if (lat == null || lon == null || category.indexOf('Low') === 0) return;
      var color = category === 'High Risk' ? '#D32F2F' : '#F57C00';
      var circle = L.circle([lat, lon], {
        color: color,
        fillColor: color,
        fillOpacity: 0.2,
        radius: h.radius_meters || 250,
        weight: 1
      }).addTo(map);
      var score = h.risk_score != null ? ' (' + Math.round(h.risk_score * 100) + '%)' : '';
      circle.bindPopup('<span class="custom-badge badge-high">' + category + score + '</span>');
    });

    // 2. Shortest Route (Dashed orange/red)
    var shortest = ${shortestRouteJson};
    if (shortest && shortest.length > 0) {
      var shortLine = L.polyline(shortest, {
        color: '#E65100',
        weight: 4,
        dashArray: '6, 8',
        opacity: 0.8
      }).addTo(map);
      shortLine.bindPopup('<b>Shortest route</b>');
    }

    // 3. Safest Route (Solid Green with glow)
    var safest = ${safeRouteJson};
    if (safest && safest.length > 0) {
      var safeLine = L.polyline(safest, {
        color: '#2E7D32',
        weight: 6,
        opacity: 0.95
      }).addTo(map);
      safeLine.bindPopup('<b>Safest route</b>');
      map.fitBounds(safeLine.getBounds(), { padding: [30, 30] });
    }

    // 4. Markers
    var markers = ${markersJson};
    markers.forEach(function(m) {
      var marker = L.marker([m.lat, m.lon]).addTo(map);
      if (m.title || m.description) {
        marker.bindPopup('<b>' + (m.title || '') + '</b><br/>' + (m.description || ''));
      }
      if (m.open) {
        marker.openPopup();
      }
    });
  </script>
</body>
</html>`;
  }, [centerLat, centerLon, zoom, markers, hotspots, safestRoute, shortestRoute]);

  if (Platform.OS === 'web') {
    return (
      <View style={[styles.container, style]}>
        <iframe
          title="Leaflet Map"
          srcDoc={htmlContent}
          style={{ width: '100%', height: '100%', border: 'none' }}
        />
      </View>
    );
  }

  return (
    <View style={[styles.container, style]}>
      <WebView
        originWhitelist={['*']}
        // A real https base URL gives tile requests a Referer; OpenStreetMap blocks tiles without one
        source={{ html: htmlContent, baseUrl: 'https://surakshax.app/' }}
        style={styles.webview}
        javaScriptEnabled={true}
        domStorageEnabled={true}
        startInLoadingState={true}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    overflow: 'hidden',
    backgroundColor: '#E2E8F0',
    borderRadius: 20,
  },
  webview: {
    flex: 1,
    backgroundColor: 'transparent',
  },
});
