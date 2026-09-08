# When the client asks for something the desk did not call

A Sell on an Ionic page is the firm's verdict. A client asking to exit a sleeve is not that, and
rendering it as one puts the firm's name on calls it never made.

Client instructions get **their own call, their own colour, their own word, and their own line in
every total.** A reader must always be able to tell which of the two they are looking at.

## The file

`--directives <path>.json`, per client, applied on top of the published calls. It never touches the
score file and it travels with one build only.

```json
{
  "as_of": "2026-07-26",
  "instruction": "The client has asked to exit the fixed-income sleeve and redeploy the proceeds into the growth-oriented construct.",
  "directives": [
    {
      "id": "exit-fixed-income",
      "call": "Exit (client)",
      "match": {"bucket": ["Fixed income"]},
      "except_names": ["PPF", "Senior Citizens", "SCSS"],
      "reason": "Directed by the client, not a call on the scheme. The desk's own view on these holdings is unchanged; the money is being moved to fund the growth allocation."
    },
    {
      "id": "retain-ppf",
      "call": "Retain",
      "match": {"name_contains": ["PPF"]},
      "reason": "Cannot be exited on request: a fifteen-year term with one partial withdrawal a year from year seven. Tax-free on maturity, so there is no tax reason to touch it either."
    }
  ],
  "footnote": "Client-directed exits are shown separately from the desk's Sell calls throughout this review. Nothing is executed until the client authorises it."
}
```

- `match.bucket` matches on asset class; `match.name_contains` on the holding name.
- `except_names` skips holdings the sleeve rule would otherwise catch.
- **A later directive wins.** That is how the `Retain` rules override the sleeve rule.
- Every directive needs a written `reason`. It is printed - see below.

## What the overlay sets on a matched row

```python
r["desk_call"]         = the published call, preserved
r["rec"] = r["verdict"] = the directive's call
r["action"]            = the directive's call        # the field the fund pages count
r["call_source"]       = "Client instruction"
r["structural_reason"] = the directive's reason
```

**`action` is not optional.** It is written once when the fund dict is built and knows nothing about
an overlay applied afterwards. Omitting it is exactly why a deck showing nineteen EXIT (CLIENT) rows
in its own tables told the reader, four pages later, that five schemes carried an action and
fifty-three were Holds.

## Ordering inside the build

**The directive block runs BEFORE the tax block.** Reversed, the tax page priced `₹62.8 L` of desk
sells and ignored `₹2.74 Cr` of client exits on the same page.

## Where the two calls must appear

| page | what it must say |
|---|---|
| contents / legend | a `YOURS` row with the `Exit (client)` and `Retain` pills, and a line saying they are the client's own instructions |
| mandate & method | that holdings so marked are the client's instructions, recorded and priced, not calls of ours |
| executive summary | a `Your instruction` row, first, with the count, the value and the share of the book |
| fund book closing read | desk actions, Holds, No View **and** client exits counted apart |
| fund actions | desk cards only; a line saying the client's exits carry no card here and why |
| priority actions | its own numbered row, first, with the value and the instruction in the client's terms |
| tax page | its own `EXIT (CLIENT)` pill in amber, never the desk's Sell red |
| coverage notes | the Retains, named, with the written reason for each |
| annexure | pilled in amber (`Exit (client)`) and slate (`Retain`), never bare body text |
| the holdings workbook | the directive's reason in the `Why` column, not a coverage disclaimer |

`ctx["client_directive"]` carries `on_file`, `instruction`, `as_of`, `footnote`, `exits`, `retains`,
`exit_value_inr` and `retain_value_inr`. Read it; do not re-scan the book.

## Colour

| call | fill | text | why |
|---|---|---|---|
| `Sell` / `Exit` | `SELLBG` | `SELL` red | the desk's verdict |
| `Exit (client)` | `AMBERBG` | `AMBER` | moves money, so it cannot look like a Hold; not our verdict, so it must not wear the Sell red |
| `Retain` | `PANEL` | `SLATE` | a status, not a call |

A client-directed exit rendered in the desk's Sell red, in the same column and directly above a row
that *is* a desk Sell, tells the reader the firm called for both. That is the single failure this
whole mechanism exists to prevent.

## The money

A client-directed exit carries real tax and moves real money, so it is priced exactly like a desk
Sell. The ACTION column is what tells the reader them apart, not the arithmetic.

- `totals.n_exit_client`, `totals.n_retain`, `totals.v_exit_client` are the counts
- `deployment.proceeds_inr` is the **desk's** sells and trims across the whole book
- the priority page headlines `proceeds + client exits` and labels it "sells, trims and your exits"
- the tax page's two panels cover the **same** set and both say so

Retained holdings are counted in **no** proceeds, **no** tax and **no** redeployment figure.

## What never happens

- a client instruction never becomes a desk Sell in any table, total or chart
- a client instruction never appears without the instruction being stated somewhere the client reads
- a Retain never appears as a bare word with no reason
- the score file is never edited to reflect a directive
