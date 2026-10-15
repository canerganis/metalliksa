/**
 * Side-effect module imported first by server.ts. python/, dist/ and the default data directories are
 * resolved against the working directory, so a server started elsewhere would launch a Python worker that
 * cannot find its script or serve 404s for the UI. Exit at once with a clear message instead.
 */
import dotenv from 'dotenv';
import { startupLayoutError } from './pythonRoot';

// NODE_ENV may come from .env (server.ts and the Python runtime load it later too; existing values win).
dotenv.config({ quiet: true });
const layoutError = startupLayoutError(process.cwd(), process.env.NODE_ENV === 'production');
if (layoutError) {
  console.error(`[Metalliksa-Server] ${layoutError}`);
  process.exit(1);
}
