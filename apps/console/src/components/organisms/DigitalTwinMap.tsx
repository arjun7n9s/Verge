import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import type { RiskFinding } from '@/types';
import type { PlantGeoJson } from '@/api/plant';
import { getPlantGeoJson, getZoneExclusion } from '@/api';
import type { PlumeExclusionFeature } from '@/api/platform';
import { Card, Badge, Button } from '@/components/atoms';
import { Shield, Radio, Compass, Layers, AlertCircle, Wind } from 'lucide-react';
import {
  centroidsByZone,
  enrichPlantGeoJson,
  polygonCentroid,
  sensorsWithCoords,
} from '@/lib/plantMap';

interface DigitalTwinMapProps {
  findings: RiskFinding[];
}

type MapSensor = {
  id: string;
  name: string;
  coordinates: [number, number];
  status: string;
  value: string;
};

const DEFAULT_CENTER: [number, number] = [83.228, 17.69];

const LOCAL_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {},
  layers: [{ id: 'background', type: 'background', paint: { 'background-color': '#0e1116' } }],
};

export function DigitalTwinMap({ findings }: DigitalTwinMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [activeLayers, setActiveLayers] = useState<string[]>(['zones', 'sensors', 'findings', 'plume']);
  const [plantBase, setPlantBase] = useState<PlantGeoJson | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [plumeZoneId, setPlumeZoneId] = useState<string | null>(null);
  const [plumeFeature, setPlumeFeature] = useState<PlumeExclusionFeature | null>(null);
  const [selectedSensor, setSelectedSensor] = useState<MapSensor | null>(null);
  const [markerPositions, setMarkerPositions] = useState<Record<string, { x: number; y: number }>>({});

  const centroids = useMemo(
    () => (plantBase ? centroidsByZone(plantBase) : {}),
    [plantBase],
  );

  const enrichedPlant = useMemo(
    () => (plantBase ? enrichPlantGeoJson(plantBase, findings) : null),
    [plantBase, findings],
  );

  const sensors = useMemo(
    () => (plantBase ? sensorsWithCoords(plantBase, centroids) : []),
    [plantBase, centroids],
  );

  const mapCenter = useMemo((): [number, number] => {
    if (!plantBase?.features.length) return DEFAULT_CENTER;
    const ring = plantBase.features[0].geometry.coordinates[0];
    return polygonCentroid(ring);
  }, [plantBase]);

  const updateMarkerPositions = useCallback(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    const next: Record<string, { x: number; y: number }> = {};
    for (const sensor of sensors) {
      const p = map.project(sensor.coordinates);
      next[sensor.id] = { x: p.x, y: p.y };
    }
    for (const finding of findings) {
      const c = centroids[finding.zoneId];
      if (c) {
        const p = map.project(c);
        next[finding.findingId] = { x: p.x, y: p.y };
      }
    }
    setMarkerPositions(next);
  }, [sensors, findings, centroids]);

  useEffect(() => {
    let cancelled = false;
    getPlantGeoJson()
      .then((plant) => {
        if (!cancelled) {
          setPlantBase(plant);
          setLoadError(null);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setLoadError('Plant geometry unavailable — start API with `make dev`.');
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const imminentZone = useMemo(() => {
    const hit = findings.find((f) => !f.shadow && f.leadTimeBand === 'IMMINENT');
    return hit?.zoneId ?? null;
  }, [findings]);

  useEffect(() => {
    if (!imminentZone) {
      setPlumeZoneId(null);
      setPlumeFeature(null);
      return;
    }
    let cancelled = false;
    getZoneExclusion(imminentZone)
      .then((res) => {
        if (!cancelled) {
          setPlumeZoneId(res.zoneId);
          setPlumeFeature(res.exclusion);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setPlumeZoneId(null);
          setPlumeFeature(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [imminentZone]);

  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: LOCAL_STYLE,
      center: mapCenter,
      zoom: 14.5,
      pitch: 30,
      bearing: -10,
    });

    mapRef.current = map;

    map.on('load', () => {
      map.addSource('plant-zones', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
      });

      map.addLayer({
        id: 'zones-fill',
        type: 'fill',
        source: 'plant-zones',
        paint: {
          'fill-color': [
            'match',
            ['get', 'alertState'],
            'imminent',
            'rgba(240, 99, 99, 0.15)',
            'near',
            'rgba(232, 163, 61, 0.15)',
            'watch',
            'rgba(79, 163, 199, 0.15)',
            'rgba(42, 50, 61, 0.25)',
          ],
          'fill-outline-color': '#2a323d',
        },
      });

      map.addLayer({
        id: 'zones-line',
        type: 'line',
        source: 'plant-zones',
        paint: {
          'line-color': [
            'match',
            ['get', 'alertState'],
            'imminent',
            '#f06363',
            'near',
            '#e8a33d',
            'watch',
            '#4fa3c7',
            '#2a323d',
          ],
          'line-width': 1.5,
        },
      });

      map.addSource('exclusion-plume', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
      });
      map.addLayer({
        id: 'plume-fill',
        type: 'fill',
        source: 'exclusion-plume',
        paint: {
          'fill-color': 'rgba(240, 99, 99, 0.35)',
          'fill-outline-color': '#f06363',
        },
      });
      map.addLayer({
        id: 'plume-line',
        type: 'line',
        source: 'exclusion-plume',
        paint: {
          'line-color': '#f06363',
          'line-width': 2,
          'line-dasharray': [2, 1],
        },
      });

      updateMarkerPositions();
    });

    map.on('move', updateMarkerPositions);
    map.on('resize', updateMarkerPositions);

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [mapCenter, updateMarkerPositions]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !enrichedPlant) return;

    const apply = () => {
      const source = map.getSource('plant-zones') as maplibregl.GeoJSONSource | undefined;
      source?.setData({ type: 'FeatureCollection', features: enrichedPlant.features });
      map.setCenter(mapCenter);
      updateMarkerPositions();
    };

    if (map.isStyleLoaded()) apply();
    else map.once('load', apply);
  }, [enrichedPlant, mapCenter, updateMarkerPositions]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;
    const source = map.getSource('exclusion-plume') as maplibregl.GeoJSONSource | undefined;
    if (!source) return;
    const features = plumeFeature && activeLayers.includes('plume') ? [plumeFeature] : [];
    source.setData({ type: 'FeatureCollection', features });
  }, [plumeFeature, activeLayers]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    const zonesVisible = activeLayers.includes('zones') ? 'visible' : 'none';
    const plumeVisible = activeLayers.includes('plume') && plumeFeature ? 'visible' : 'none';
    if (map.getLayer('zones-fill')) map.setLayoutProperty('zones-fill', 'visibility', zonesVisible);
    if (map.getLayer('zones-line')) map.setLayoutProperty('zones-line', 'visibility', zonesVisible);
    if (map.getLayer('plume-fill')) map.setLayoutProperty('plume-fill', 'visibility', plumeVisible);
    if (map.getLayer('plume-line')) map.setLayoutProperty('plume-line', 'visibility', plumeVisible);
  }, [activeLayers, plumeFeature]);

  useEffect(() => {
    updateMarkerPositions();
  }, [sensors, findings, updateMarkerPositions]);

  const toggleLayer = (layerId: string) => {
    setActiveLayers((prev) =>
      prev.includes(layerId) ? prev.filter((id) => id !== layerId) : [...prev, layerId],
    );
  };

  return (
    <div className="h-full w-full relative flex select-none text-ink font-sans">
      <div ref={mapContainerRef} className="flex-1 h-full w-full bg-bg relative overflow-hidden" />

      {loadError && (
        <div className="absolute top-14 left-3 right-3 z-10 bg-imminent/10 border border-imminent/30 text-imminent text-xs p-2 rounded flex items-center gap-2">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {loadError}
        </div>
      )}

      <div className="absolute top-3 left-3 flex flex-col gap-2 z-10">
        <Card className="p-2.5 bg-panel/90 border-line shadow-none flex flex-col gap-2 w-48">
          <span className="text-micro font-mono font-bold text-ink-dim uppercase tracking-wider flex items-center gap-1.5 border-b border-line pb-1.5">
            <Layers className="h-3.5 w-3.5" />
            Layer Controls
          </span>
          <div className="flex flex-col gap-1.5">
            {[
              { id: 'zones', label: 'Plant Zones', icon: <Compass className="h-3.5 w-3.5" /> },
              { id: 'sensors', label: 'IoT Sensors', icon: <Radio className="h-3.5 w-3.5" /> },
              { id: 'findings', label: 'Active Risks', icon: <Shield className="h-3.5 w-3.5" /> },
              { id: 'plume', label: 'Gas Plume', icon: <Wind className="h-3.5 w-3.5" /> },
            ].map((layer) => (
              <button
                key={layer.id}
                onClick={() => toggleLayer(layer.id)}
                className={`flex items-center gap-2 h-7 px-2 rounded border text-xs font-semibold font-mono text-left cursor-pointer transition-colors ${
                  activeLayers.includes(layer.id)
                    ? 'bg-panel-2 border-accent text-accent'
                    : 'bg-transparent border-transparent text-ink-dim hover:text-ink'
                }`}
              >
                {layer.icon}
                {layer.label}
              </button>
            ))}
          </div>
          {plumeZoneId && (
            <span className="text-micro font-mono text-imminent px-1">
              Plume overlay · zone {plumeZoneId}
            </span>
          )}
        </Card>
      </div>

      {selectedSensor && (
        <div className="absolute bottom-3 right-3 z-10 w-72">
          <Card className="p-3 bg-panel/95 border-line shadow-none flex flex-col gap-2 text-xs select-text">
            <div className="flex justify-between items-start border-b border-line pb-2">
              <div className="flex flex-col gap-0.5">
                <span className="font-bold font-mono text-ink text-sm">{selectedSensor.id}</span>
                <span className="text-micro font-mono text-ink-dim uppercase">{selectedSensor.name}</span>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="h-5 px-1 hover:bg-panel-2 text-ink-dim"
                onClick={() => setSelectedSensor(null)}
              >
                Dismiss
              </Button>
            </div>
            <div className="flex justify-between items-center bg-panel-2 p-2 rounded border border-line">
              <span className="font-mono text-ink-dim">CURRENT VALUE:</span>
              <span className="font-mono font-bold text-accent text-sm tabular-nums">{selectedSensor.value}</span>
            </div>
          </Card>
        </div>
      )}

      {activeLayers.includes('sensors') && (
        <div className="absolute inset-0 pointer-events-none z-10">
          {sensors.map((sensor) => {
            const pos = markerPositions[sensor.id];
            if (!pos) return null;
            return (
              <button
                key={sensor.id}
                onClick={() => setSelectedSensor(sensor)}
                className="absolute pointer-events-auto h-3 w-3 rounded-full border border-bg hover:scale-125 transition-transform cursor-pointer -translate-x-1/2 -translate-y-1/2"
                style={{
                  left: pos.x,
                  top: pos.y,
                  backgroundColor: '#4ec98a',
                }}
                title={`${sensor.id}: ${sensor.value}`}
              />
            );
          })}
        </div>
      )}

      {activeLayers.includes('findings') && (
        <div className="absolute inset-0 pointer-events-none z-10">
          {findings.map((finding) => {
            const pos = markerPositions[finding.findingId];
            if (!pos) return null;
            const color = finding.leadTimeBand === 'IMMINENT' ? '#f06363' : '#e8a33d';
            return (
              <div
                key={finding.findingId}
                className="absolute -translate-x-1/2 -translate-y-1/2 flex flex-col items-center gap-1"
                style={{ left: pos.x, top: pos.y }}
              >
                <div
                  className="h-6 w-6 rounded-full flex items-center justify-center animate-ping absolute opacity-30"
                  style={{ backgroundColor: color }}
                />
                <div
                  className="h-4 w-4 rounded-full border border-bg flex items-center justify-center relative shadow-sm"
                  style={{ backgroundColor: color }}
                >
                  <Shield className="h-2.5 w-2.5 text-bg" />
                </div>
                <Badge variant="band" band={finding.leadTimeBand} className="text-micro font-bold py-0 scale-90">
                  {finding.findingId}
                </Badge>
              </div>
            );
          })}
        </div>
      )}

      <div className="sr-only">
        <table>
          <caption>Active Plant Digital Twin Hazard Locations</caption>
          <thead>
            <tr>
              <th>Finding ID</th>
              <th>Location / Zone</th>
              <th>Risk Severity</th>
              <th>Model Confidence</th>
            </tr>
          </thead>
          <tbody>
            {findings.map((f) => (
              <tr key={f.findingId}>
                <td>{f.findingId}</td>
                <td>{f.zoneId}</td>
                <td>{f.leadTimeBand}</td>
                <td>{(f.confidence * 100).toFixed(0)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
