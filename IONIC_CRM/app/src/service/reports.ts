/**
 * Assemble a report from the repository.
 *
 * One place that maps ticket summaries to `ReportInput`, so the on-screen report
 * and the CSV export can never disagree about the numbers. An export that quietly
 * computes differently from the page it sits under is a genuinely bad failure: it
 * is the version that gets emailed to someone.
 */

import { buildReport, type Report, type ReportInput } from '../domain/reports';
import { istDateOf } from '../domain/calendar';
import type { Category, Employee, Repository, TicketSummary } from '../repo/types';

export interface ReportBundle {
  readonly report: Report;
  readonly rows: readonly ReportInput[];
  readonly employees: readonly Employee[];
  readonly categories: readonly Category[];
  readonly nameOf: ReadonlyMap<string, string>;
  readonly categoryNameOf: ReadonlyMap<string, string>;
}

function toReportInput(s: TicketSummary): ReportInput {
  return {
    id: s.ticket.id,
    ref: s.ticket.ref,
    title: s.ticket.title,
    assigneeId: s.ticket.assigneeId,
    categoryId: s.ticket.categoryId,
    priority: s.ticket.priority,
    status: s.ticket.status,
    deadline: s.ticket.deadline,
    originalDeadline: s.ticket.originalDeadline,
    // istDateOf, not a substring of the ISO instant: the substring is the UTC date
    // and lands a day early for anything raised after 18:30 UTC.
    createdDate: istDateOf(new Date(s.ticket.createdAt)),
    closedDate: s.ticket.closedDate,
    lastPunchDate: s.lastPunchDate,
    punchCount: s.punchCount,
  };
}

export async function loadReport(repo: Repository, now: Date = new Date()): Promise<ReportBundle> {
  const [summaries, employees, categories, holidays] = await Promise.all([
    // No filter: closed tickets are the whole basis of on-time reporting.
    repo.tickets.listSummaries(),
    repo.employees.listActive(),
    repo.reference.categories(),
    repo.calendar.holidays(),
  ]);

  const rows = summaries.map(toReportInput);

  return {
    report: buildReport(rows, holidays, now),
    rows,
    employees,
    categories,
    nameOf: new Map(employees.map((e) => [e.id, e.displayName])),
    categoryNameOf: new Map(categories.map((c) => [c.id, c.name])),
  };
}
