import { backgroundJobsAPI } from './api';

// Planning a week runs as a background job on the server. Poll it until it
// finishes; resolves with the job, or throws with the job's message on failure.
export async function waitForJob(jobId, { intervalMs = 2000, timeoutMs = 5 * 60 * 1000 } = {}) {
  const started = Date.now();
  for (;;) {
    const job = await backgroundJobsAPI.get(jobId);
    if (job.status === 'done') return job;
    if (job.status === 'failed') throw new Error(job.error || 'Something went wrong preparing your plan.');
    if (Date.now() - started > timeoutMs) throw new Error('This is taking longer than usual. Refresh in a minute.');
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
}
