import path from 'node:path';
import { lstatSync, statSync, readdirSync } from 'node:fs';
import { artifactDirectory, LpbfArtifactStore } from './lpbfArtifactStore';
import { LpbfRunRepository, type RunRecord, type RunSourceLink } from './lpbfRunRepository';
import { LpbfSourceRepository } from './lpbfSourceRepository';
import { dryRunRunImport, importRun, runArtifacts } from './lpbfRunImport';
import { lpbfWorker } from './lpbfWorkerBridge';
import { storeGpuPilotArtifactResolver } from './lpbfGpuPilotArtifacts';
import { verifyGpuPilotArchive } from './lpbfGpuRunArchive';
import { recordRunAudit } from './auditLedger';

const MAX_RUN_SIZE_BYTES = 50 * 1024 * 1024; // 50 MB
const MAX_ARCHIVE_SIZE_BYTES = 15 * 1024 * 1024 * 1024; // 15 GB
const QUOTA_WARNING_THRESHOLD = 0.9; // Warn at 90%
export type RunSourceBindingStatus = 'exact-revision-bound' | 'legacy-unlinked' | 'unverified-source-link';
const bindingStatus = (record: RunRecord, sources: LpbfSourceRepository | null): RunSourceBindingStatus => {
  if (!record.document.sources.length) return 'legacy-unlinked';
  if (!sources) return 'unverified-source-link';
  for (const link of record.document.sources) {
    try {
      const revision = sources.revision(link.datasetId, link.revision);
      if (!revision || revision.documentSha256 !== link.documentSha256) return 'unverified-source-link';
    } catch { return 'unverified-source-link'; }
  }
  return 'exact-revision-bound';
};

function getDirectorySizeBytes(dir: string): number {
  try {
    const stats = statSync(dir);
    if (!stats.isDirectory()) return stats.size;
    let total = 0;
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const fullPath = path.join(dir, entry.name);
      total += entry.isDirectory() ? getDirectorySizeBytes(fullPath) : statSync(fullPath).size;
    }
    return total;
  } catch {
    return 0;
  }
}

export class LpbfRunArchiveError extends Error {
  constructor(readonly status: number, message: string) { super(message); }
}

/**
 * Worker RPC rejections that are client errors, keyed by the exact worker / bridge message
 * (python/lpbf_worker.py JobQueue.get and capture, server/lpbfWorkerBridge.ts captureForArchive).
 * Anything else stays a generic 503 in the route so no worker detail or path reaches the client.
 */
const CAPTURE_CLIENT_ERRORS: Readonly<Record<string, [number, string]>> = {
  'Only completed jobs can be captured': [409, 'Only completed jobs can be archived.'],
  'Job not found': [404, 'Job not found.'],
  'Invalid job id': [400, 'Invalid job id.'],
};

/** Capture a worker job for archiving; a cancelled, failed, running or unknown job is a 4xx, not a 503. */
async function captureCompletedJob(jobId: string) {
  try { return await lpbfWorker.captureForArchive(jobId); }
  catch (error) {
    const mapped = error instanceof Error ? CAPTURE_CLIENT_ERRORS[error.message] : undefined;
    if (mapped) throw new LpbfRunArchiveError(mapped[0], mapped[1]);
    throw error;
  }
}

export class LpbfRunArchiveService {
  private busy = false;
  constructor(
    private readonly runRoot = path.resolve(process.env.METALLIKSA_LPBF_RUN_ROOT || '.lpbf-runs'),
    private readonly sourceRoot = path.resolve(process.env.METALLIKSA_LPBF_SOURCE_ROOT || '.lpbf-sources')
  ) {}

  private runRepository(readOnly: boolean) {
    const filename = path.join(this.runRoot, 'runs.sqlite');
    if (readOnly) {
      try { lstatSync(this.runRoot); } catch (error) { if ((error as NodeJS.ErrnoException).code === 'ENOENT') return null; throw error; }
      artifactDirectory(this.runRoot);
      try { lstatSync(filename); } catch (error) { if ((error as NodeJS.ErrnoException).code === 'ENOENT') return null; throw error; }
    } else artifactDirectory(this.runRoot, true);
    return new LpbfRunRepository(filename, { readOnly });
  }

  private sourceRepository() {
    const filename = path.join(this.sourceRoot, 'metadata.sqlite');
    try { lstatSync(filename); } catch (error) { if ((error as NodeJS.ErrnoException).code === 'ENOENT') return null; throw error; }
    return new LpbfSourceRepository(filename, { readOnly: true });
  }

  list(): { runId: string; createdAt: string; evidenceStatus: string; sourceBindingStatus: RunSourceBindingStatus; runKind: RunRecord['runKind'] }[] {
    const repository = this.runRepository(true);
    if (!repository) return [];
    let sources: LpbfSourceRepository | null = null;
    try {
      try { sources = this.sourceRepository(); } catch { /* Keep run history visible, but do not claim source links are verified. */ }
      const runs = [];
      for (const record of repository.allRuns()) {
        runs.push({ runId: record.document.runId, createdAt: record.createdAt,
          evidenceStatus: record.evidenceStatus, sourceBindingStatus: bindingStatus(record, sources), runKind: record.runKind });
      }
      return runs;
    } finally { sources?.close(); repository.close(); }
  }

  get(runId: string): RunRecord & { sourceBindingStatus: RunSourceBindingStatus } {
    const repository = this.runRepository(true);
    if (!repository) throw new LpbfRunArchiveError(404, 'Run repository not found.');
    let sources: LpbfSourceRepository | null = null;
    try {
      try { sources = this.sourceRepository(); } catch { /* Preserve run visibility when source verification is unavailable. */ }
      const record = repository.get(runId);
      if (!record) throw new LpbfRunArchiveError(404, 'Run not found.');
      return { ...record, sourceBindingStatus: bindingStatus(record, sources) };
    } finally { sources?.close(); repository.close(); }
  }

  async getVerified(runId: string): Promise<RunRecord & { sourceBindingStatus: RunSourceBindingStatus }> {
    const record = this.get(runId);
    if (record.runKind === 'gpu-thermal-pilot') {
      const store = new LpbfArtifactStore(path.join(this.runRoot, 'artifacts'), { readOnly: true });
      try {
        for (const ref of runArtifacts(record.document)) await store.verify(ref);
        await verifyGpuPilotArchive(JSON.parse(record.document.capture.resultJson), record.document.runId,
          storeGpuPilotArtifactResolver(store));
      } catch { throw new LpbfRunArchiveError(409, 'GPU pilot field archive integrity or numerical verification failed.'); }
    }
    return record;
  }

  private async exclusive<T>(action: () => Promise<T>): Promise<T> {
    if (this.busy) throw new LpbfRunArchiveError(409, 'A run archive operation is already running.');
    this.busy = true;
    try { return await action(); } finally { this.busy = false; }
  }

  private checkQuota(runSize: number) {
    if (runSize > MAX_RUN_SIZE_BYTES) {
      throw new LpbfRunArchiveError(413, `Run size (${(runSize / 1024 / 1024).toFixed(2)} MB) exceeds the maximum allowed size per run (50 MB).`);
    }
    const currentArchiveSize = getDirectorySizeBytes(this.runRoot);
    if (currentArchiveSize + runSize > MAX_ARCHIVE_SIZE_BYTES) {
      throw new LpbfRunArchiveError(413, `Importing this run would exceed the maximum archive quota of 15 GB.`);
    }
    return {
      totalArchiveSizeBytes: currentArchiveSize,
      maxArchiveSizeBytes: MAX_ARCHIVE_SIZE_BYTES,
      approachingLimit: (currentArchiveSize + runSize) / MAX_ARCHIVE_SIZE_BYTES > QUOTA_WARNING_THRESHOLD
    };
  }

  private async resolveSources(repository: LpbfSourceRepository, raw: unknown): Promise<RunSourceLink[]> {
    if (!Array.isArray(raw) || raw.length < 1 || raw.length > 100) {
      throw new LpbfRunArchiveError(400, 'Select at least one registered source revision.');
    }
    const links: RunSourceLink[] = [];
    const seen = new Set<string>();
    let artifacts: LpbfArtifactStore | null = null;
    for (const item of raw) {
      if (!item || typeof item !== 'object' || Array.isArray(item)
        || !['datasetId', 'revision'].every(field => Object.hasOwn(item, field))
        || Object.keys(item).some(field => !['datasetId', 'revision', 'documentSha256'].includes(field))
        || typeof item.datasetId !== 'string' || !/^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$/.test(item.datasetId)
        || !Number.isSafeInteger(item.revision) || item.revision < 1
        || (item.documentSha256 !== undefined && (typeof item.documentSha256 !== 'string'
          || !/^[a-f0-9]{64}$/.test(item.documentSha256)))) {
        throw new LpbfRunArchiveError(400, 'Invalid source revision selection.');
      }
      const key = `${item.datasetId}:${item.revision}`;
      if (seen.has(key)) throw new LpbfRunArchiveError(400, 'Duplicate source revision selection.');
      seen.add(key);
      let revision;
      try { revision = repository.revision(item.datasetId, item.revision); }
      catch { throw new LpbfRunArchiveError(409, 'Selected source revision integrity changed.'); }
      if (!revision) throw new LpbfRunArchiveError(404, 'Selected source revision was not found.');
      if (item.documentSha256 !== undefined && item.documentSha256 !== revision.documentSha256) {
        throw new LpbfRunArchiveError(409, 'Selected source revision changed. Reload its exact revision.');
      }
      for (const artifact of revision.document.artifacts) {
        try {
          artifacts ??= new LpbfArtifactStore(path.join(this.sourceRoot, 'artifacts'), { readOnly: true });
          await artifacts.verify(artifact);
        }
        catch { throw new LpbfRunArchiveError(409, 'Selected source revision artifact bytes are missing or changed.'); }
      }
      links.push({ datasetId: revision.document.datasetId, revision: revision.revision,
        documentSha256: revision.documentSha256 });
    }
    return links;
  }

  preview(jobId: string, sources: unknown) {
    return this.exclusive(async () => {
      const sourceRepo = this.sourceRepository();
      if (!sourceRepo) throw new LpbfRunArchiveError(400, 'Source repository not initialized.');
      try {
        const links = await this.resolveSources(sourceRepo, sources);
        const { capture, root } = await captureCompletedJob(jobId);
        const previewResult = await dryRunRunImport(capture, links, sourceRepo, root);
        const quota = this.checkQuota(previewResult.byteSize);
        return { ...previewResult, quota, sourceBindingStatus: 'exact-revision-bound' as const };
      } finally { sourceRepo.close(); }
    });
  }

  import(jobId: string, sources: unknown) {
    return this.exclusive(async () => {
      const sourceRepo = this.sourceRepository();
      if (!sourceRepo) throw new LpbfRunArchiveError(400, 'Source repository not initialized.');
      try {
        const links = await this.resolveSources(sourceRepo, sources);
        const { capture, root } = await captureCompletedJob(jobId);
        // Dry run first to get size for quota check
        const previewResult = await dryRunRunImport(capture, links, sourceRepo, root);
        this.checkQuota(previewResult.byteSize);

        // Source bytes can change while the worker capture is checked.
        await this.resolveSources(sourceRepo, links);

        const repository = this.runRepository(false)!;
        try {
          const record = await importRun(repository, new LpbfArtifactStore(path.join(this.runRoot, 'artifacts')), capture, links, sourceRepo, root);
          await recordRunAudit(record);
          return { ...record, sourceBindingStatus: 'exact-revision-bound' as const };
        } catch (error) {
          if (error instanceof Error && /conflict/i.test(error.message)) throw new LpbfRunArchiveError(409, 'Run identity conflict.');
          throw error;
        } finally { repository.close(); }
      } finally { sourceRepo.close(); }
    });
  }
}
