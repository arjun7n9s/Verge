import { Link, NavLink, Outlet } from 'react-router-dom';
import { useFindingsStore } from '@/stores/findings';
import { useConnectionStore } from '@/stores/connection';
import { SensorRibbon } from '@/components/organisms/SensorRibbon';
import { Shield, Activity, BarChart2, Settings, History, ArrowRightLeft } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import clsx from 'clsx';

export default function AppShell() {
  const { shadow, setShadow } = useFindingsStore();
  const { status } = useConnectionStore();
  const { t, i18n } = useTranslation();

  return (
    <div className="min-h-screen bg-bg text-ink flex flex-col font-sans select-none">
      {/* Top Header Navigation */}
      <header className="h-12 border-b border-line bg-panel flex items-center justify-between px-4 shrink-0 z-30">
        <div className="flex items-center gap-6">
          <Link to="/" className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-accent" />
            <span className="font-semibold text-base tracking-tight text-ink uppercase font-mono">VERGE</span>
          </Link>
          <span className="h-4 w-[1px] bg-line" />
          <span className="text-xs text-ink-dim font-mono hidden md:inline">
            LEAD-TIME INTELLIGENCE &middot; OPERATOR CONSOLE
          </span>
        </div>

        {/* Global Navigation Links */}
        <nav className="flex items-center gap-1">
          <NavLink
            to="/"
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-1.5 h-8 px-3 rounded text-xs font-semibold font-mono transition-colors',
                isActive
                  ? 'bg-panel-2 text-ink border border-line'
                  : 'text-ink-dim hover:text-ink hover:bg-panel-2 border border-transparent'
              )
            }
          >
            <Activity className="h-3.5 w-3.5" />
            {t('board')}
          </NavLink>
          <NavLink
            to="/replay"
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-1.5 h-8 px-3 rounded text-xs font-semibold font-mono transition-colors',
                isActive
                  ? 'bg-panel-2 text-ink border border-line'
                  : 'text-ink-dim hover:text-ink hover:bg-panel-2 border border-transparent'
              )
            }
          >
            <History className="h-3.5 w-3.5" />
            {t('replay')}
          </NavLink>
          <NavLink
            to="/fleet"
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-1.5 h-8 px-3 rounded text-xs font-semibold font-mono transition-colors',
                isActive
                  ? 'bg-panel-2 text-ink border border-line'
                  : 'text-ink-dim hover:text-ink hover:bg-panel-2 border border-transparent'
              )
            }
          >
            <BarChart2 className="h-3.5 w-3.5" />
            {t('fleet')}
          </NavLink>
          <NavLink
            to="/audit"
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-1.5 h-8 px-3 rounded text-xs font-semibold font-mono transition-colors',
                isActive
                  ? 'bg-panel-2 text-ink border border-line'
                  : 'text-ink-dim hover:text-ink hover:bg-panel-2 border border-transparent'
              )
            }
          >
            <Shield className="h-3.5 w-3.5" />
            {t('audit')}
          </NavLink>
          <NavLink
            to="/admin"
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-1.5 h-8 px-3 rounded text-xs font-semibold font-mono transition-colors',
                isActive
                  ? 'bg-panel-2 text-ink border border-line'
                  : 'text-ink-dim hover:text-ink hover:bg-panel-2 border border-transparent'
              )
            }
          >
            <Settings className="h-3.5 w-3.5" />
            {t('config')}
          </NavLink>
          <NavLink
            to="/handover"
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-1.5 h-8 px-3 rounded text-xs font-semibold font-mono transition-colors',
                isActive
                  ? 'bg-panel-2 text-ink border border-line'
                  : 'text-ink-dim hover:text-ink hover:bg-panel-2 border border-transparent'
              )
            }
          >
            <ArrowRightLeft className="h-3.5 w-3.5" />
            {t('handover')}
          </NavLink>
        </nav>

        {/* Live/Shadow Toggle & Status Indicators */}
        <div className="flex items-center gap-4">
          {/* Language selector select box */}
          <select
            value={i18n.language}
            onChange={(e) => i18n.changeLanguage(e.target.value)}
            className="h-7 px-1 rounded border border-line text-micro bg-bg text-ink focus:outline-none font-mono font-bold cursor-pointer"
          >
            <option value="en">EN</option>
            <option value="hi">HI</option>
            <option value="ta">TA</option>
            <option value="te">TE</option>
            <option value="kn">KN</option>
          </select>

          {/* Connection status */}
          <div className="flex items-center gap-1.5">
            <span
              className={clsx(
                'h-2 w-2 rounded-full',
                status === 'connected' ? 'bg-ok' : status === 'reconnecting' ? 'bg-near animate-pulse' : 'bg-unknown'
              )}
            />
            <span className="text-micro font-mono text-ink-dim uppercase">{status}</span>
          </div>

          <span className="h-4 w-[1px] bg-line" />

          {/* Mode selector */}
          <div className="flex bg-bg border border-line p-0.5 rounded">
            <button
              onClick={() => setShadow(false)}
              className={clsx(
                'px-2.5 py-1 text-micro font-mono font-bold uppercase rounded-sm transition-colors cursor-pointer',
                !shadow ? 'bg-panel text-ink border border-line shadow-sm' : 'text-ink-dim hover:text-ink'
              )}
            >
              {t('live')}
            </button>
            <button
              onClick={() => setShadow(true)}
              className={clsx(
                'px-2.5 py-1 text-micro font-mono font-bold uppercase rounded-sm transition-colors cursor-pointer',
                shadow ? 'bg-near/20 text-near border border-near/30 shadow-sm' : 'text-ink-dim hover:text-near'
              )}
            >
              {t('shadow')}
            </button>
          </div>
        </div>
      </header>

      {/* Sensor health ribbon */}
      <SensorRibbon />

      {/* Shadow banner warning */}
      {shadow && (
        <div className="bg-near/10 border-b border-near/20 text-near text-xs font-mono py-1 px-4 text-center select-text">
          SHADOW MODE &mdash; SURFACING FORECASTED FINDINGS THAT ARE RECORDED BUT NOT ACTIVE IN THE LIVE SYSTEM.
        </div>
      )}

      {/* Page Content Viewport */}
      <main className="flex-1 overflow-hidden relative">
        <Outlet />
      </main>
    </div>
  );
}
