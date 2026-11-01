import { Router } from 'express';
import { AuditLedger, sharedAuditLedger } from '../server/auditLedger';

/** Read-only: GET /api/audit/ledger?limit=N returns the last N entries; the whole chain is verified. */
export function createAuditLedgerRouter(ledger: AuditLedger = sharedAuditLedger()): Router {
  const router = Router();
  router.get('/api/audit/ledger', (req, res) => {
    res.set('Cache-Control', 'no-store');
    try {
      const verification = ledger.verify();
      const requested = Number(req.query.limit);
      const limit = Number.isInteger(requested) && requested > 0 ? Math.min(requested, 5000) : 500;
      res.json({ ...verification, totalEntries: verification.entries.length, entries: verification.entries.slice(-limit) });
    } catch (error) {
      console.error('[Audit ledger]', error);
      res.status(503).json({ error: 'Audit ledger unavailable.' });
    }
  });
  return router;
}
