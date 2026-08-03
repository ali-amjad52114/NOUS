# 🧠 NOUS — READY TO GO

**Nous** (Greek: *mind*). **One-liner:** *A personal brain connected to your whole life that catches the
promises you make in passing — and keeps them for you. Runs on RocketRide.*

---

## THE PITCH (≈90 seconds, say it in this order)

**[Problem — the story]**
"A friend gets sick. You write back: *'I'm coming to see you soon, I promise.'*
And you mean it. Then life buries it — 400 emails, Slack, invoices. There's no
task, no reminder. Just an intention, and intentions don't live anywhere.
He thought he had time. He never got to see him.
Every tool you own remembers your meetings and receipts. **Nothing remembers
your promises.** That's the memory that matters — and it's the one we lose."

**[Solution]**
"This is a personal brain connected to everything — Gmail, Slack, calendar.
It caught that promise the moment I typed it. It created a commitment with a
real 15-day deadline, found the free slot on my calendar, and asked me ONE
question: *'You're free Saturday 2–6. Book it with Sam?'* I said yes — it
booked the time, sent Sam the message, and scheduled the follow-up nudge.
And it doesn't just keep promises: watch it handle anything once — an invoice,
an intro — and it compiles what I did into a Protocol it runs forever.
It starts knowing nothing. It learns *your* moves. It never forgets."

**[Demo — run it, narrate the beats]**
Beat 1: Sam's message → your reply → **PROMISE DETECTED → Commitment C-001,
15-day deadline → slot proposed → approve → booked + message sent + follow-up.**
Beat 2: first invoice ever → it watches you → **Protocol P-001 distilled,
critic-reviewed, compiled to a RocketRide `.pipe`.**
Beat 3: second vendor **before** approval → **it refuses** ✋ → you arm it once
→ queue drains + third vendor handled autonomously → *"using the protocol
Abhinav taught me"* → scoreboard: you 3, brain 8 → restart → still knows.

**[Close]**
"Memory that becomes motion — a brain that knows everything you said, so it
can protect everything you meant. And every skill it learns ships as a
RocketRide pipeline. **You said this morning you'd buy a personal brain.
This one keeps your promises.**"

---

## SPONSORS — all four, all load-bearing

| Sponsor | Role | Break it and… |
|---|---|---|
| **LaserData** — the senses | Gmail/Slack/calendar/actions flow as durable streams with offset replay; promises are detected *in the stream*; any day of your life is replayable decision-by-decision | the brain is deaf — no promise is ever caught |
| **FalkorDB** — the memory | The life graph: Contacts, Events, **Commitments** (`PROMISED_TO`, deadline, status), Protocols with provenance (`TAUGHT_BY`/`APPROVED_BY`), Receipts. "Sam → diagnosis → promise → deadline → booked Saturday" is one multi-hop query, live in the browser | the brain has amnesia — nothing survives the session |
| **Guild.ai** — the judgment | Specialist agents with division of labor: **Distiller** (compiles watched sessions into Protocols), **Safety Critic** (adversarially reviews before any human sees it), and the **concierge approval session** — the human-in-the-loop moment that arms every protocol and books every promise | the brain acts unreviewed — demo shows it *refusing* instead |
| **RocketRide** — the muscle | Every learned skill compiles into a **`.pipe`**: find-slot → book → send → follow-up runs on the engine, deployed on RocketRide Cloud, every step traced. The brain *writes RocketRide as it learns* | the brain remembers but never moves — memory without motion |

**CEO line:** "Your engine is our brain's muscle — every skill it learns
compiles into a RocketRide pipeline. Watch it learn its first one."

---

## RUN OF SHOW

```bash
python3 demo.py      # full arc headless, ends ALL CHECKS PASSED (rehearse 2×)
python3 server.py    # live version behind /events, /memory/similar,
                     # /actions/execute, /approve, /state  (for the UI)
```
- FalkorDB on: `docker run -p 6379:6379 -p 3000:3000 falkordb/falkordb` +
  `pip install falkordb` + `MEMORY_BACKEND=falkor` → browser query for judges:
  `MATCH (c:Commitment)-[r]->(x) RETURN c, r, x`
- Guild on: publish `kit/guild/*.agent.ts` (`guild agent init --template LLM`,
  paste, `guild agent save --publish`); run the approval inside a Guild session
- RocketRide on: load `pipes/P-KEEPER.pipe` + `pipes/P-001.pipe`, recreate one
  on the VS Code canvas **with their mentor**, deploy to Cloud (Discord promo)
- LaserData on: point `kit/feed.py::publish` at their stream (booth-assisted;
  pin whatever SDK version works)

## SUBMIT + WIN CHECKLIST
☐ `/submit` in the RocketRide Discord ☐ demo video recorded during rehearsal
☐ social track at lunch: LinkedIn post tagging RocketRide + the CEO, follow
Instagram, Discord ☐ disclose AI assistance ☐ invite the CEO to watch Beat 1

## Q&A AMMO
- **"It reads all my mail?!"** — Runs on YOUR graph, locally; actions are
  allowlisted; every act is receipted; nothing executes without your one-time
  approval — you watched it refuse. Demo runs on replayed data by design.
- **"How is this not a reminder app?"** — Reminders tell you. This *does it*:
  found the slot, booked it, sent the message, scheduled the nudge. Memory →
  Motion.
- **"What if it detects a promise wrong?"** — It never acts on detection; it
  *asks*. Wrong detection costs one tap. A missed promise costs the visit.
