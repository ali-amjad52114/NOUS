# 🧠 NOUS — TEAM PLAYBOOK (read this whole page, then build)

**What we're building (one line):** a personal brain that catches promises you
make in messages ("I'm coming to see you soon") and keeps them — books the
time, sends the message, follows up — plus learns any routine by watching you
once. Every learned skill compiles into a **RocketRide pipeline**.

**The demo we must not break (3 beats):**
1. Sam's diagnosis message → your reply → **PROMISE DETECTED → C-001, 15-day
   deadline → "You're free Sat 2–6, book it?" → approve → booked + message
   sent + follow-up scheduled**
2. First invoice → brain **watches you** → Protocol P-001 distilled → critic
   review → **compiled to a .pipe**
3. Second vendor **before** approval → **REFUSES** ✋ → approve once → third
   vendor handled autonomously → scoreboard *you: 3, brain: 8* → restart →
   still knows everything

**Ground truth:** `python3 demo.py` runs the entire arc headless and must say
`ALL CHECKS PASSED` at every point today. If your change breaks it, revert.
`python3 server.py` = the same brain on **http://127.0.0.1:7200**.

**The contract (already running — don't redesign, extend):**
```
POST /events            {id,type,channel,from/to,person,subject,body}  → brain reacts
GET  /state             → {log[], scoreboard, graph, pending_queue, watching}
POST /watch/action      {action, params}      POST /watch/done  {}
POST /approve           {protocol_id}         (commitments: approve via brain API — see Lane 1 task 4)
POST /actions/execute   {event_id, action, params, protocol?}   ← RocketRide pipes call THIS
GET  /memory/similar    ?trigger_class=&q=
```

---

## LANE 1 — KEWIN · UI/UX + Dashboard (React/TS, your home turf)

**Own the thing judges look at.** Vite + React (or one index.html if faster —
speed > elegance). Poll `GET /state` every 1s. Dark theme, three panels:

1. **Life stream (left):** every event as a card — channel icon (gmail/slack),
   sender, subject. Sam's messages get a 💙 accent. Noise renders dimmed.
2. **Brain feed (center, the hero):** render `state.log` as a terminal-style
   feed. Three moments get BIG visual treatment:
   - `PROMISE DETECTED` → amber hero card: promise text, person, **deadline
     countdown ("day 0 of 15")**, proposed slot, one big **[Book it]** button
   - `REFUSING to act` → red card ("waiting for your approval")
   - autonomous act → green card with receipt id + "using the protocol
     Abhinav taught me"
3. **Right rail:** scoreboard (**you: N / brain: N** — make it huge),
   commitments list with status chips (OPEN→PROPOSED→BOOKED), protocols with
   ARMED/PENDING chips + **[Approve]** buttons, and an iframe/tab link to the
   FalkorDB browser (`http://localhost:3000`).

**Buttons wire to:** `[Book it]` → POST `/approve-commitment` (task 4),
`[Approve P-XXX]` → POST `/approve`, watch-mode buttons → `/watch/action` +
`/watch/done`. Demo driver buttons (feed next event) → POST `/events` with the
next item from `kit/feed.py` STORY (hardcode the 6 events client-side).

**Task 4 (10 min, Python):** add to `server.py`:
`POST /approve-commitment {commitment_id}` → `brain.approve_commitment(id)`.
Copy the `/approve` handler shape exactly.

**Definition of done:** all 3 beats drivable entirely by clicking, projector-
readable fonts, nothing scrolls off screen. **Fallback if time dies:** skip
React, serve one static HTML polling /state — ugly beats broken.

---

## LANE 2 — STREAMS + MEMORY · LaserData + FalkorDB

**Make the two data sponsors visibly real.**

1. **FalkorDB (do first, 30 min):**
   `docker run -d -p 6379:6379 -p 3000:3000 falkordb/falkordb:latest` +
   `pip install falkordb` → run `MEMORY_BACKEND=falkor python3 demo.py` →
   must still pass → open :3000, run the judge query and screenshot it:
   `MATCH (c:Commitment)-[r]->(x) RETURN c,r,x` and
   `MATCH (p:Protocol)-[r]->(x) RETURN p,r,x`
2. **LaserData (booth-assisted, 45 min):** sign up (free tier) OR run their
   local Laser Stack (officially sanctioned — most reliable on stage). Wire
   `kit/feed.py::publish` (the single `# VENUE TODO` line) to publish every
   event to stream `brain`, topic `life-events`. Also publish receipts from
   `kit/actions.py::execute` (add 3 lines, same pattern). **Pin whatever SDK
   version works at 12:30 — do not upgrade after.** Get their console showing
   topics ticking — that's judge evidence on THEIR surface.
3. **Stretch:** offset-replay button ("replay my day") — LaserData's native
   party trick, huge with judges.

**DoD:** demo passes with `MEMORY_BACKEND=falkor`; LaserData console shows
events during a live run; both browser tabs bookmarked for the demo machine.
**Fallback:** LocalStore + JSONL mirror already work — the demo NEVER blocks
on a sponsor outage; you just lose evidence, so screenshot everything early.

---

## LANE 3 — AGENTS · Guild.ai + Nebius brain-upgrade

**Make the judgment layer real on Guild's platform.**

1. `npm i -g @guildai/cli && guild auth login` → workspace.
2. Publish both agents (recipe, ~10 min each):
   `guild agent init --name brain-distiller --template LLM` → replace agent.ts
   with `kit/guild/distiller.agent.ts` → `guild agent test` →
   `guild agent save --message v1 --wait --publish`. Repeat for
   `brain-critic` with `critic.agent.ts`. Install one pre-built Hub agent too.
3. **The HITL story:** during the demo, the approval moment IS the Guild beat.
   Open a session with brain-critic, paste P-001's JSON, get its review live
   (or pre-run it and keep the session tab open — sessions log = evidence).
4. **Nebius (30 min max):** put NEBIUS_API_KEY / NEBIUS_MODEL in env; test
   `kit/distill.py::llm_upgrade` on P-001's transcript. Better prose in the
   distilled protocol = nice. **If it fights you, stop — the deterministic
   path is the demo's safety net and it already passes.**

**DoD:** two published agents visible in the workspace + one Hub install + a
critic session reviewing P-001, tab open on the demo machine.
**Fallback:** web UI no-code path at app.guild.ai if the CLI misbehaves.

---

## LANE 4 — ROCKETRIDE · pipelines, cloud, prize ops (THE PRIZE LANE)

**We are trying to win this specific prize. Spend face time at their booth.**

1. Engine: `docker run -d -p 5565:5565 ghcr.io/rocketride-org/rocketride-engine:latest`
   + `pip install rocketride` + VS Code extension "RocketRide".
2. Run `python3 demo.py` once → grab `pipes/P-KEEPER.pipe` + `pipes/P-001.pipe`
   (the brain auto-compiles them). **Recreate P-KEEPER on the VS Code canvas
   WITH A ROCKETRIDE MENTOR** — their node schema is canonical, and every
   mentor-minute is face time with the people who pick the prize. Flow:
   webhook `/protocol/P-KEEPER` → preconditions (POST :7200/actions/preconditions)
   → book (POST :7200/actions/execute) → send_message → verify.
3. **Deploy the pipe to RocketRide Cloud** (promo code = their Discord).
   Keep the observability trace view open — judge evidence.
4. Tell the CEO: *"every skill our brain learns compiles into one of these —
   your engine is our brain's muscle"* and invite him to Beat 1.
5. **Prize ops (yours too):** `/submit` in their Discord · record the demo
   video during rehearsal · lunch social post on LinkedIn tagging RocketRide +
   the CEO + Instagram follow + Discord join ($250 track) · disclose AI
   assistance in the submission text.

**DoD:** one pipeline running on the engine + one deployed on Cloud + trace
visible + submission in. **Fallback:** if canvas schema fights you, demo the
auto-generated .pipe files + engine + the SDK call — still real usage.

---

## TIMELINE (hard checkpoints — integrator calls them out loud)

| Time | Checkpoint |
|---|---|
| now | Lanes start. Everyone: `python3 demo.py` green on your machine first |
| +45 min | **Integration 1:** UI shows /state live · FalkorDB backend green |
| +1h45 | **Integration 2:** all four sponsors demonstrably on · full click-through of 3 beats |
| +2h15 | **CODE FREEZE.** Only pitch, polish, screenshots after this |
| +2h20 | Rehearse ×2 · **record backup video on a phone** · screenshot every sponsor surface |
| 3:10 PM | **SUBMIT** (Discord /submit + form). Deadline 3:30 — submit at 3:10, not 3:29 |

**Abhinav (integrator):** owns demo.py staying green, merges, the pitch
(PITCH.md), driving the demo, and CEO relations. When two lanes conflict, he
decides in 60 seconds and everyone moves.

**Rules, non-negotiable:** built during the event with AI assistance —
disclosed in the submission. No code from prior projects. If judges ask how it
was built, the answer is the truth and it's a good answer.
