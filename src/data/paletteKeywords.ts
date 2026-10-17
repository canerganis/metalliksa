import type { ModuleId } from './workspaces';

// Sub-views that live inside a module's own tabs, so a search for them finds the module (review S5).
export const SUBVIEW_KEYWORDS: Partial<Record<ModuleId, string>> = {
  'phase-diagram': 'calphad gibbs tdb equilibrium liquidus solidus',
  'research-hub': 'blind test your data upload measurements',
};
