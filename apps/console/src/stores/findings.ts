import { create } from 'zustand';
import type { RiskFinding, FindingFilters, SortConfig } from '@/types';
import { BAND_SEVERITY } from '@/types';

interface FindingsState {
  findings: RiskFinding[];
  filters: FindingFilters;
  sort: SortConfig;
  selectedId: string | null;
  isLoading: boolean;
  error: string | null;
  shadow: boolean;

  // Actions
  setFindings: (findings: RiskFinding[]) => void;
  updateFinding: (id: string, updates: Partial<RiskFinding>) => void;
  setFilters: (filters: FindingFilters) => void;
  setSort: (sort: SortConfig) => void;
  setSelectedId: (id: string | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setShadow: (shadow: boolean) => void;
}

export const useFindingsStore = create<FindingsState>((set) => ({
  findings: [],
  filters: {},
  sort: { field: 'leadTimeBand', direction: 'asc' },
  selectedId: null,
  isLoading: false,
  error: null,
  shadow: false,

  setFindings: (findings) => set({ findings, error: null }),
  updateFinding: (id, updates) =>
    set((state) => ({
      findings: state.findings.map((f) =>
        f.findingId === id ? { ...f, ...updates } : f
      ),
    })),
  setFilters: (filters) => set({ filters }),
  setSort: (sort) => set({ sort }),
  setSelectedId: (selectedId) => set({ selectedId }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
  setShadow: (shadow) => set({ shadow }),
}));

import { useShallow } from 'zustand/react/shallow';

export function useFilteredFindings(): RiskFinding[] {
  return useFindingsStore(useShallow((state) => {
    let result = state.findings;

    // Filter by shadow mode
    result = result.filter((f) => f.shadow === state.shadow);

    const { filters } = state;

    if (filters.states?.length) {
      result = result.filter((f) => filters.states!.includes(f.state));
    }
    if (filters.zones?.length) {
      result = result.filter((f) => filters.zones!.includes(f.zoneId));
    }
    if (filters.leadTimeBands?.length) {
      result = result.filter((f) => filters.leadTimeBands!.includes(f.leadTimeBand));
    }
    if (filters.assignedTo?.length) {
      result = result.filter((f) => f.owner && filters.assignedTo!.includes(f.owner));
    }
    if (filters.confidenceDegraded !== undefined) {
      result = result.filter((f) => f.confidenceDegraded === filters.confidenceDegraded);
    }
    if (filters.minConfidence !== undefined) {
      result = result.filter((f) => f.confidence >= filters.minConfidence!);
    }
    if (filters.search) {
      const q = filters.search.toLowerCase();
      result = result.filter(
        (f) =>
          f.title.toLowerCase().includes(q) ||
          f.zoneId.toLowerCase().includes(q) ||
          f.findingId.toLowerCase().includes(q)
      );
    }

    // Sort
    const { sort } = state;
    const dir = sort.direction === 'asc' ? 1 : -1;
    result = [...result].sort((a, b) => {
      switch (sort.field) {
        case 'leadTimeBand':
          return (BAND_SEVERITY[a.leadTimeBand] - BAND_SEVERITY[b.leadTimeBand]) * dir;
        case 'confidence':
          return (a.confidence - b.confidence) * dir;
        case 'createdAt':
          return (new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime()) * dir;
        case 'zone':
          return a.zoneId.localeCompare(b.zoneId) * dir;
        case 'state':
          return a.state.localeCompare(b.state) * dir;
        default:
          return 0;
      }
    });

    return result;
  }));
}
