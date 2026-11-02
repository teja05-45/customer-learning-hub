# Demo script

Twelve minutes, one browser window, no slides. Everything below exists in the seeded dataset,
so you can follow it literally. Reset the demo first (Settings → Reset) if someone has already
been clicking around.

Screenshots for each step are in [screenshots/](screenshots/).

---

## 0. Open the workspace (30s)

`http://localhost:8081` (Docker) or `http://localhost:5173` (dev).

> "Everyday Goods runs research in the gaps between campaigns and support queues. This
> workspace holds the whole loop: plan a study, recruit, talk to customers, capture what they
> said, turn it into a finding, and connect that finding to a decision with an owner.
>
> Everything you see is synthetic — seven invented colleagues, ten invented participants, no
> real customer and no connection to any Everyday Goods system."

Point at the demonstration entry screen.

> "The role picker is a demonstration convenience, not authentication. Every request is served
> with the same permissions; the only thing the choice changes is the starting view and the
> name attached to the audit trail. I would rather say that out loud than let it look like
> security."

Choose **Priya Menon — Customer Research Coordinator**.

## 1. The overview answers the CEO's question (2 min)

> "Asha, our CEO, does not want to know how many interviews we ran. She wants to know whether
> we are learning anything and whether it is being used."

Point to the signals row:

- **Decisions with evidence** — "Three of the four decisions here link to an insight or an
  evidence record, and the fourth is labelled as an internal judgement. That label is a
  feature, not a failure."
- **Insights awaiting review** — "findings nobody has signed off yet."
- **Overdue actions** — "the honest bit: four follow-ups are late."
- **Response rate** — "shown as a fraction with its denominator, not a bare percentage."

Scroll to "Are we learning something useful?".

> "Deliberately not a count of conversations. Traceability and reuse are what we can actually
> observe."

## 2. Trace a claim back to a customer (3 min) — the centrepiece

Go to **Insights** → open **"Price is not the first explanation customers offer"**.

> "This is a draft finding from the repeat-purchase study. Confidence is *low*, and the reason
> is written next to it."

Point at the evidence list:

> "Underneath: the verbatim quotes it rests on. Each one keeps the customer's words, the
> researcher's interpretation of them, the segment, and where it came from — the interview code
> and the participant code. Separate fields, never merged into one paragraph."

Open the linked evidence **EV-0007**.

> "Here is the quote in full, with the interpretation below it as its own field, provenance
> marked *recorded*, and the interview and participant attached."

Follow the interview link to **INT-0002 "Bought on a promotion"**.

> "And this is the session it came from: consent records per type — participation, recording,
> quoting, sharing internally — the guide that was used, and the notes."

Click back to the insight. Point at the **related** and **reuse** panels.

> "Same project, overlapping segments, and whether this insight was ever picked up again. An
> insight nobody reused is the quiet failure mode of research teams."

## 3. Where the evidence disagrees (1 min)

Go to **Evidence**, filter type **Contradictory**.

> "EV-0006: 'I did buy it again actually, the second one is in the cupboard.' That contradicts
> the working hypothesis. It lives in the record as a first-class type, and an insight can link
> it as *contradictory* rather than quietly dropping it. Any research tool can produce a
> highlight reel; this one refuses to."

Filter back to **All** before moving on.

## 4. A decision with its sources, and one without (2 min)

Go to **Decisions** → open **DEC-001 "Run a bottle-size test before changing price"**.

> "Owner, business function, problem statement, rationale, limitations. Below: the insights and
> evidence it leans on, and the actions it created."

Point at the evidence-sufficiency flag.

> "DEC-001 links two insights and two evidence records, and it is still marked *evidence not
> sufficient* — because the team accepted a size test as an internal judgement, not because a
> customer study proved it. The label travels with the decision."

Open **DEC-004 "Do not re-run the shampoo study this quarter"**.

> "A resourcing decision, not a research finding. It carries one link but no sufficiency
> assessment at all — 'not assessed' is a different state from 'assessed and insufficient',
> and the register keeps them apart."

Use the **has no evidence** filter on the decisions list.

> "One click lists every decision the business made without customer research. That is the
> report nobody volunteers."

## 5. Recruitment is a pipeline, not an inbox (1 min)

Go to **Recruitment**.

> "Ten stages from identified to completed, with the side exits that actually happen: declined,
> no response, cancelled, withdrawn. Non-responders are kept, because a pipeline that deletes
> them cannot report a true response rate."

Open a card at `invited`.

> "Each stage change is an event with an actor and a timestamp. Illegal jumps are rejected by
> the API, not just hidden in the UI."

## 6. Analytics states its limits (1 min)

Go to **Analytics**.

> "Segment coverage, decision funnel, action completion, insight reuse — all from records in
> this workspace."

Scroll to **Measurement gaps**.

> "These read *pending baseline* because the business has not agreed how to measure them. And
> the note says plainly: this tool cannot attribute a change in repeat purchase or revenue to
> research activity. It has one cause among several, and none of these numbers prove otherwise."

## 7. Search and export (1 min)

Press `Ctrl/⌘+K`, type `shampoo`.

> "One search across projects, participants, interviews, evidence, insights, decisions and
> actions. It is deliberately deterministic — all the words must appear. No embeddings, no
> model, no guessing. Results name the entity and the project so two similar hits are
> distinguishable."

Type a nonsense word like `zzz` to show the suggestion state rather than an empty box.

Then **Settings → Exports** → download **Evidence CSV**.

> "Every export carries an `is_synthetic` column and an export timestamp. Nobody can take one
> of these files to a meeting and mistake it for real customer data."

## 8. Close (30s)

> "Three things this prototype does that a deck cannot: every claim is one click from the
> customer words behind it, contradictions stay in the record, and decisions without evidence
> are visible instead of dressed up.
>
> What it deliberately does not do: authentication, audio recording, email sending, real data,
> or statistics it cannot support. `docs/AUTH.md` and `docs/17-limitations-and-next-steps.md`
> say exactly what it would take to close each gap."

---

## If something goes wrong

| Symptom | Fix |
| --- | --- |
| Data looks edited from a previous run | Settings → Demo data → Reset (type `RESET`) |
| A record was deleted mid-demo | Reset restores the seeded dataset exactly |
| API looks down | `docker compose ps` — the API container should be `healthy`; `docker compose logs -f backend` |
| Screens are slow on a laptop | Close the Analytics tab; the bundle is largest there |

## Short version (4 minutes)

1. Overview — decisions with evidence, overdue actions.
2. Insight "Price is not the first explanation" → evidence → interview.
3. Decisions → filter "has no evidence".
4. Analytics → Measurement gaps.
