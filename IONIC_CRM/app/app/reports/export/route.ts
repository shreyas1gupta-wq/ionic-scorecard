/**
 * CSV export.
 *
 * Two exports, both scoped by row-level security exactly like the pages: a
 * per-person summary and a full ticket list. Nobody can export data they could
 * not already read, because the query is the same one the page uses.
 *
 * Every export writes an access event. Someone taking the whole ticket list off
 * the system is precisely the event a reviewer will want to find later.
 */

import { withUser } from '@/server/session';
import { AccessDeniedError, denyResponse } from '@/auth/access';
import { csvFilename, toCsv, type CsvValue } from '@/domain/csv';
import { UNCATEGORISED } from '@/domain/reports';
import { loadReport } from '@/service/reports';

const PEOPLE_HEADER = [
  'person',
  'open',
  'overdue',
  'stale',
  'never_updated',
  'closed',
  'cancelled',
  'on_time_vs_original_pct',
  'on_time_vs_current_pct',
  'median_cycle_working_days',
  'p90_cycle_working_days',
  'deadlines_moved',
  'working_days_slipped',
];

const TICKETS_HEADER = [
  'ref',
  'title',
  'assignee',
  'category',
  'priority',
  'status',
  'raised',
  'original_deadline',
  'current_deadline',
  'closed',
  'deadline_moved',
  'updates',
  'last_update',
];

export async function GET(request: Request): Promise<Response> {
  const kind = new URL(request.url).searchParams.get('kind') === 'tickets' ? 'tickets' : 'people';

  try {
    const { body, filename } = await withUser(async (repo) => {
      const bundle = await loadReport(repo);
      const { report, rows, nameOf, categoryNameOf } = bundle;

      await repo.accessLog.record({ event: 'EXPORT', entity: 'tickets', entityId: kind });

      if (kind === 'people') {
        const data: CsvValue[][] = report.byPerson.map((p) => [
          nameOf.get(p.key) ?? p.key,
          p.open,
          p.overdue,
          p.stale,
          p.neverUpdated,
          p.closed,
          p.cancelled,
          p.onTimePctOriginal,
          p.onTimePctCurrent,
          p.medianCycleDays,
          p.p90CycleDays,
          p.deadlinesMoved,
          p.workingDaysSlipped,
        ]);
        return {
          body: toCsv(PEOPLE_HEADER, data),
          filename: csvFilename('ionic-crm-by-person', report.today),
        };
      }

      const data: CsvValue[][] = rows.map((t) => [
        t.ref,
        t.title,
        nameOf.get(t.assigneeId) ?? t.assigneeId,
        t.categoryId === null ? UNCATEGORISED : (categoryNameOf.get(t.categoryId) ?? t.categoryId),
        t.priority,
        t.status,
        t.createdDate,
        t.originalDeadline,
        t.deadline,
        t.closedDate,
        t.deadline !== t.originalDeadline,
        t.punchCount,
        t.lastPunchDate,
      ]);
      return {
        body: toCsv(TICKETS_HEADER, data),
        filename: csvFilename('ionic-crm-tickets', report.today),
      };
    });

    return new Response(body, {
      headers: {
        'content-type': 'text/csv; charset=utf-8',
        'content-disposition': `attachment; filename="${filename}"`,
        // An export is a point-in-time snapshot; a cached copy would be wrong and
        // would also sit in a shared cache.
        'cache-control': 'no-store',
      },
    });
  } catch (err) {
    if (err instanceof AccessDeniedError) return denyResponse();
    throw err;
  }
}
