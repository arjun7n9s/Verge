import { useState, useEffect } from 'react';
import { WidthProvider, Responsive } from 'react-grid-layout/legacy';
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';
import type { RiskFinding } from '@/types';
import { DigitalTwinMap } from './DigitalTwinMap';
import { PermitsPanel } from './PermitsPanel';
import { KnowledgePanel } from './KnowledgePanel';
import { KnowledgeGraphViz } from './KnowledgeGraphViz';
import { AlertFatigueMetrics } from './AlertFatigueMetrics';
import { Button } from '@/components/atoms';
import { Monitor, PhoneCall, Brain, Settings, RefreshCw } from 'lucide-react';

const ResponsiveGridLayout = WidthProvider(Responsive);

interface PanelSystemProps {
  findings: RiskFinding[];
  boardComponent: React.ReactNode;
  responseComponent: React.ReactNode;
}

// Preset layouts configurations
const PRESETS = {
  monitoring: [
    { i: 'map', x: 0, y: 0, w: 7, h: 4, minW: 4, minH: 3 },
    { i: 'permits', x: 7, y: 0, w: 5, h: 4, minW: 3, minH: 3 },
    { i: 'board', x: 0, y: 4, w: 12, h: 4, minW: 6, minH: 3 },
  ],
  response: [
    { i: 'response-ctrl', x: 0, y: 0, w: 12, h: 3, minW: 6, minH: 2 },
    { i: 'map', x: 0, y: 3, w: 8, h: 5, minW: 4, minH: 3 },
    { i: 'permits', x: 8, y: 3, w: 4, h: 5, minW: 3, minH: 3 },
  ],
  analysis: [
    { i: 'graph', x: 0, y: 0, w: 6, h: 4, minW: 3, minH: 3 },
    { i: 'knowledge', x: 6, y: 0, w: 6, h: 4, minW: 3, minH: 3 },
    { i: 'map', x: 0, y: 4, w: 12, h: 4, minW: 4, minH: 3 },
  ],
  admin: [
    { i: 'metrics', x: 0, y: 0, w: 12, h: 8, minW: 6, minH: 4 },
  ],
};

type PresetType = 'monitoring' | 'response' | 'analysis' | 'admin';

import { ErrorBoundary } from '@/components/atoms/ErrorBoundary';

export function PanelSystem({ findings, boardComponent, responseComponent }: PanelSystemProps) {
  const [currentPreset, setCurrentPreset] = useState<PresetType>('monitoring');
  const [layout, setLayout] = useState(PRESETS.monitoring);

  // Load layout from localStorage on initial render if saved
  useEffect(() => {
    const savedLayout = localStorage.getItem(`verge-layout-${currentPreset}`);
    if (savedLayout) {
      try {
        setLayout(JSON.parse(savedLayout));
      } catch {
        setLayout(PRESETS[currentPreset]);
      }
    } else {
      setLayout(PRESETS[currentPreset]);
    }
  }, [currentPreset]);

  const handleLayoutChange = (newLayout: any) => {
    setLayout(newLayout);
    localStorage.setItem(`verge-layout-${currentPreset}`, JSON.stringify(newLayout));
  };

  const handlePresetSelect = (preset: PresetType) => {
    setCurrentPreset(preset);
  };

  const handleResetLayout = () => {
    localStorage.removeItem(`verge-layout-${currentPreset}`);
    setLayout(PRESETS[currentPreset]);
  };

  return (
    <div className="flex flex-col gap-4 h-full overflow-hidden text-ink select-none">
      {/* Layout preset control bar */}
      <div className="flex items-center justify-between border-b border-line pb-3 shrink-0">
        <div className="flex items-center gap-1.5 bg-panel-2 p-0.5 rounded border border-line">
          <span className="text-micro font-mono text-ink-dim px-2 uppercase font-bold">
            LAYOUT PRESETS:
          </span>
          <button
            onClick={() => handlePresetSelect('monitoring')}
            className={`flex items-center gap-1.5 h-6 px-3 text-micro font-mono font-bold rounded-sm cursor-pointer border ${
              currentPreset === 'monitoring'
                ? 'bg-panel text-ink border-line'
                : 'bg-transparent border-transparent text-ink-dim hover:text-ink'
            }`}
          >
            <Monitor className="h-3.5 w-3.5" />
            MONITORING
          </button>
          <button
            onClick={() => handlePresetSelect('response')}
            className={`flex items-center gap-1.5 h-6 px-3 text-micro font-mono font-bold rounded-sm cursor-pointer border ${
              currentPreset === 'response'
                ? 'bg-panel text-ink border-line'
                : 'bg-transparent border-transparent text-ink-dim hover:text-ink'
            }`}
          >
            <PhoneCall className="h-3.5 w-3.5" />
            EMERGENCY RESPONSE
          </button>
          <button
            onClick={() => handlePresetSelect('analysis')}
            className={`flex items-center gap-1.5 h-6 px-3 text-micro font-mono font-bold rounded-sm cursor-pointer border ${
              currentPreset === 'analysis'
                ? 'bg-panel text-ink border-line'
                : 'bg-transparent border-transparent text-ink-dim hover:text-ink'
            }`}
          >
            <Brain className="h-3.5 w-3.5" />
            GRAPH ANALYSIS
          </button>
          <button
            onClick={() => handlePresetSelect('admin')}
            className={`flex items-center gap-1.5 h-6 px-3 text-micro font-mono font-bold rounded-sm cursor-pointer border ${
              currentPreset === 'admin'
                ? 'bg-panel text-ink border-line'
                : 'bg-transparent border-transparent text-ink-dim hover:text-ink'
            }`}
          >
            <Settings className="h-3.5 w-3.5" />
            ADMIN CONFIG
          </button>
        </div>

        <Button
          variant="ghost"
          size="sm"
          onClick={handleResetLayout}
          icon={<RefreshCw className="h-3.5 w-3.5 text-accent" />}
          className="text-micro font-mono font-bold uppercase"
        >
          Reset Grid
        </Button>
      </div>

      {/* Grid container viewport */}
      <div className="flex-1 overflow-y-auto scrollbar pr-1">
        <ResponsiveGridLayout
          className="layout select-text"
          layouts={{ lg: layout }}
          breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480 }}
          cols={{ lg: 12, md: 10, sm: 6, xs: 4 }}
          rowHeight={100}
          onLayoutChange={handleLayoutChange}
          draggableHandle=".panel-drag-handle"
          isResizable={true}
          isDraggable={true}
        >
          {/* DIGITAL TWIN MAP PANEL */}
          {layout.some((p) => p.i === 'map') && (
            <div key="map" className="surface-1 overflow-hidden flex flex-col p-1 bg-panel">
              <div className="panel-drag-handle h-7 border-b border-line flex items-center justify-between px-2 shrink-0 bg-panel-2/50 font-mono text-micro select-none cursor-move">
                <span className="font-bold text-ink-dim uppercase">DIGITAL TWIN PLANT MAP</span>
              </div>
              <div className="flex-1 overflow-hidden">
                <ErrorBoundary>
                  <DigitalTwinMap findings={findings} />
                </ErrorBoundary>
              </div>
            </div>
          )}

          {/* PERMITS PANEL */}
          {layout.some((p) => p.i === 'permits') && (
            <div key="permits" className="surface-1 overflow-hidden flex flex-col p-1.5 bg-panel">
              <div className="panel-drag-handle h-7 border-b border-line flex items-center justify-between px-2 shrink-0 bg-panel-2/50 font-mono text-micro select-none cursor-move">
                <span className="font-bold text-ink-dim uppercase">ACTIVE PERMITS-TO-WORK</span>
              </div>
              <div className="flex-1 overflow-hidden pt-2">
                <ErrorBoundary>
                  <PermitsPanel />
                </ErrorBoundary>
              </div>
            </div>
          )}

          {/* KANBAN BOARD PANEL */}
          {layout.some((p) => p.i === 'board') && (
            <div key="board" className="surface-1 overflow-hidden flex flex-col p-1 bg-panel">
              <div className="panel-drag-handle h-7 border-b border-line flex items-center justify-between px-2 shrink-0 bg-panel-2/50 font-mono text-micro select-none cursor-move">
                <span className="font-bold text-ink-dim uppercase">TELETREAD ALERTS BOARD</span>
              </div>
              <div className="flex-1 overflow-hidden pt-2">
                <ErrorBoundary>
                  {boardComponent}
                </ErrorBoundary>
              </div>
            </div>
          )}

          {/* RESPONSE CONTROLLERS PANEL */}
          {layout.some((p) => p.i === 'response-ctrl') && (
            <div key="response-ctrl" className="surface-1 overflow-hidden flex flex-col p-1 bg-panel">
              <div className="panel-drag-handle h-7 border-b border-line flex items-center justify-between px-2 shrink-0 bg-panel-2/50 font-mono text-micro select-none cursor-move">
                <span className="font-bold text-ink-dim uppercase">EMERGENCY RESPONSE BROADCASTER</span>
              </div>
              <div className="flex-1 overflow-hidden overflow-y-auto pt-2 scrollbar">
                <ErrorBoundary>
                  {responseComponent}
                </ErrorBoundary>
              </div>
            </div>
          )}

          {/* KNOWLEDGE PANEL */}
          {layout.some((p) => p.i === 'knowledge') && (
            <div key="knowledge" className="surface-1 overflow-hidden flex flex-col p-1.5 bg-panel">
              <div className="panel-drag-handle h-7 border-b border-line flex items-center justify-between px-2 shrink-0 bg-panel-2/50 font-mono text-micro select-none cursor-move">
                <span className="font-bold text-ink-dim uppercase">VERGE AI RECIRCULATION REFERENCE</span>
              </div>
              <div className="flex-1 overflow-hidden pt-2">
                <ErrorBoundary>
                  <KnowledgePanel />
                </ErrorBoundary>
              </div>
            </div>
          )}

          {/* RELATIONSHIP GRAPH PANEL */}
          {layout.some((p) => p.i === 'graph') && (
            <div key="graph" className="surface-1 overflow-hidden flex flex-col p-1.5 bg-panel">
              <div className="panel-drag-handle h-7 border-b border-line flex items-center justify-between px-2 shrink-0 bg-panel-2/50 font-mono text-micro select-none cursor-move">
                <span className="font-bold text-ink-dim uppercase">LINEAGE RELATIONSHIP GRAPH</span>
              </div>
              <div className="flex-1 overflow-hidden pt-2">
                <ErrorBoundary>
                  <KnowledgeGraphViz />
                </ErrorBoundary>
              </div>
            </div>
          )}

          {/* METRICS DASHBOARD PANEL */}
          {layout.some((p) => p.i === 'metrics') && (
            <div key="metrics" className="surface-1 overflow-hidden flex flex-col p-1.5 bg-panel">
              <div className="panel-drag-handle h-7 border-b border-line flex items-center justify-between px-2 shrink-0 bg-panel-2/50 font-mono text-micro select-none cursor-move">
                <span className="font-bold text-ink-dim uppercase">ALERT FATIGUE METRICS SUMMARY</span>
              </div>
              <div className="flex-1 overflow-hidden overflow-y-auto pt-2 scrollbar">
                <ErrorBoundary>
                  <AlertFatigueMetrics />
                </ErrorBoundary>
              </div>
            </div>
          )}
        </ResponsiveGridLayout>
      </div>
    </div>
  );
}
