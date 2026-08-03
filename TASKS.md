# 🧠 NOUS — TASK BOARD
**Repo:** https://github.com/ali-amjad52114/NOUS · **Submission: 3:30 PM (submit 3:10)**

**What Nous is (context for every AI agent):** a personal brain connected to your
life stream (Gmail/Slack/calendar, simulated). It (1) catches promises you type
("I'm coming to see you soon"), turns them into Commitments with deadlines,
proposes a calendar slot, and after one human approval books it + sends the
message + schedules a follow-up; (2) learns any routine by *watching* the human
handle it once, compiles it into a typed Protocol, and — after a Safety-Critic
review and one approval — runs it autonomously forever. Every learned skill is
also compiled into a **RocketRide `.pipe` pipeline**. The Python core already
works: `python3 demo.py` prints `ALL CHECKS PASSED`.

---

## ⓪ ABHINAV (do this FIRST, 2 min) — push the kit

```bash
cd ~/Downloads && unzip nous.zip && cd nous
git init && git add -A && git commit -m "Nous core — demo green"
git remote add origin https://github.com/ali-amjad52114/NOUS.git
git branch -M main && git push -u origin main
```

**Ground rules for everyone (post with the tasks):**
- `python3 server.py` = the running brain on **http://127.0.0.1:7200**. `python3 demo.py` must print `ALL CHECKS PASSED` before every push. If your change breaks it → revert.
- Work on your own branch (`ui`, `rocketride-guild`, `data-layer`), PR to main, **Abhinav merges**. Nobody edits `kit/brain.py` or `server.py` except where a task says so.
- Built during the event with AI assistance — we disclose that in the submission. No code from prior projects.

**THE CONTRACT (give this to your AI agent verbatim):**
```
GET  /state  → {"log": [str], "scoreboard": "actions — you: N · brain: N · receipts: N",
                "graph": str, "pending_queue": [event_ids], "watching": event_id|null}
POST /events {"id","type":"message_in|message_out","channel":"gmail|slack",
              "from"/"to","person","subject","body","attachment"?}
POST /watch/action {"action":"forward|label|archive|reply","params":{...}}
POST /watch/done {}                      → returns the distilled protocol
POST /approve {"protocol_id":"P-001"}    → arms protocol, drains refused queue
POST /approve-commitment {"commitment_id":"C-001"} → books the promise
POST /actions/execute {"event_id","action","params","protocol"?}  ← RocketRide pipes call THIS
GET  /memory/similar?trigger_class=&q=
Demo storyline events (exact JSON): kit/feed.py STORY (6 events, evt-1..evt-6)
```

---

# 🅰 PERSON A — UI/UX · FRONTEND (branch: `ui`)

**Mission:** the single screen judges stare at for 3 minutes. Dark, projector-
readable, three panels. All demo beats drivable by clicking — no terminal on stage.

**Tasks:**
1. `frontend/` folder in the repo. Vite+React OR a single `index.html` — whatever ships in 90 min. Poll `GET http://127.0.0.1:7200/state` every 1s. (If CORS bites with a dev server, add `self.send_header("Access-Control-Allow-Origin","*")` in `server.py::_send` — the ONE server edit you're allowed.)
2. **Left panel — Life Stream:** a "Next event ▶" button that POSTs the next hardcoded event from `kit/feed.py` STORY (copy the 6 JSON objects into the frontend). Render each sent event as a card: channel icon, sender, subject. Sam's cards get a 💙 accent; the newsletter renders dimmed.
3. **Center panel — Brain Feed (the hero):** render `state.log` lines as a terminal-style feed, styled by content match:
   - line contains `PROMISE DETECTED` → big amber hero card: promise text, person, **"day 0 of 15" deadline countdown**, proposed slot, one large **[Book it with Sam]** button → `POST /approve-commitment {"commitment_id":"C-001"}`
   - contains `REFUSING to act` → red card "⏸ waiting for your approval"
   - contains `done autonomously` or `RocketRide pipeline` → green card, show receipt id
   - contains `watched:` → subtle purple "👀 learning…" chip
4. **Watch-mode controls:** when `state.watching` is set, show 3 buttons: [Forward to accounting] → `POST /watch/action {"action":"forward","params":{"to":"accounting@myfirm.com"}}`, [Label invoices], [Archive], then [Done — distill it] → `POST /watch/done`.
5. **Right rail:** giant scoreboard parsed from `state.scoreboard` (**you: N vs brain: N**); commitments + protocols parsed from `state.graph` text (or just render the raw lines with ARMED/PENDING chips); [Approve P-001] button → `POST /approve`; link button "Open Memory Graph" → `http://localhost:3000` (FalkorDB browser).

**Definition of done:** full 3-beat demo click-through with zero terminal use; readable from 3 meters; nothing overflows.

**PASTE THIS TO YOUR AI AGENT:**
> Build a single-page dark dashboard for "Nous", a personal-brain demo. Backend is running at http://127.0.0.1:7200 with: GET /state returning {"log":[strings],"scoreboard":string,"graph":string,"pending_queue":[ids],"watching":id|null}; POST endpoints /events, /watch/action, /watch/done, /approve {"protocol_id"}, /approve-commitment {"commitment_id"}. Three-panel layout: left = event cards + a "Next event" button that POSTs these 6 hardcoded events in order [PASTE THE STORY ARRAY FROM kit/feed.py]; center = state.log rendered as a live feed where lines matching "PROMISE DETECTED" become a large amber card with a [Book it] button posting {"commitment_id":"C-001"} to /approve-commitment, lines matching "REFUSING" become red cards, "done autonomously" green cards; when state.watching is non-null show three action buttons that POST to /watch/action with {"action":"forward","params":{"to":"accounting@myfirm.com"}} / {"action":"label","params":{"name":"invoices"}} / {"action":"archive","params":{}} plus a Done button POSTing to /watch/done; right rail = huge you-vs-brain scoreboard parsed from state.scoreboard, raw state.graph lines with ARMED/PENDING chips, an [Approve P-001] button, and a link to http://localhost:3000. Dark theme, big fonts, no login, no router, one file preferred. Poll /state every 1000ms.

---

# 🅱 PERSON B — ROCKETRIDE + GUILD (branch: `rocketride-guild`)

**Mission:** make RocketRide the visible muscle (WE ARE TARGETING THEIR PRIZE)
and Guild the visible judgment. Spend real time at BOTH booths — mentor minutes
are judging minutes.

**RocketRide tasks:**
1. Local engine: `docker run -d -p 5565:5565 ghcr.io/rocketride-org/rocketride-engine:latest` · `pip install rocketride` · install VS Code extension "RocketRide".
2. Run `python3 demo.py` once → the brain auto-writes `pipes/P-KEEPER.pipe` and `pipes/P-001.pipe`. Open them — this is our story: **Nous compiles its learned skills into RocketRide pipelines.**
3. **With a RocketRide mentor**, recreate P-KEEPER on the VS Code visual canvas using their canonical node schema: webhook source `/protocol/P-KEEPER` → HTTP node POST `http://127.0.0.1:7200/actions/preconditions` → HTTP node POST `/actions/execute` body `{"event_id":"evt-2","action":"book","params":{"slot":"Saturday Aug 15, 2:00–6:00 PM","with_person":"Sam"},"protocol":"P-KEEPER"}` → HTTP node same URL with `{"action":"send_message",...}` → HTTP node POST `/actions/verify`. Save the canvas version into `pipes/` and commit.
4. **Deploy that pipe to RocketRide Cloud** (promo code from their Discord). Keep the cloud dashboard + observability trace tab open — that's judge evidence, and it's the prize criterion ("build the most with RocketRide").
5. Python SDK proof (10 min): tiny script `integrations/rr_run.py` using `rocketride.RocketRideClient(uri="ws://localhost:5565")` → `client.use(filepath="pipes/P-KEEPER.pipe")` → `client.send(token, anomaly_json)`. Commit it even if rough.

**Guild tasks:**
6. `npm i -g @guildai/cli && guild auth login` → create/select workspace.
7. Publish both agents (recipe per agent, ~10 min): `guild agent init --name nous-distiller --template LLM` → replace generated `agent.ts` with `kit/guild/distiller.agent.ts` → `guild agent test` → `guild agent save --message "v1" --wait --publish`. Repeat with `nous-critic` + `critic.agent.ts`. Install one pre-built Hub agent into the workspace.
8. Open a session with **nous-critic**, paste the JSON of Protocol P-001 (from `state/brain_memory.json` after a demo run), get its adversarial review, KEEP THE SESSION TAB OPEN — during the pitch, the human approval moment is narrated as "our Guild critic reviewed it; only the human can arm it."
9. **Prize ops:** `/submit` in the RocketRide Discord · lunch LinkedIn post tagging RocketRide + the CEO + follow their Instagram + join Discord ($250 social track) · record the demo video during rehearsal.

**Definition of done:** pipe on local engine ✓ same pipe on RocketRide Cloud ✓ trace visible ✓ two Guild agents published + critic session open ✓ submission in ✓.

**PASTE THIS TO YOUR AI AGENT:**
> I have auto-generated RocketRide pipeline JSON files (format: {name, version, source:{type:webhook,path}, nodes:[{id,type,...}], lanes:[[from,to]]}) that call back into a local API at http://127.0.0.1:7200 (POST /actions/preconditions, /actions/execute {"event_id","action","params","protocol"}, /actions/verify). Help me (1) adapt this JSON to the canonical RocketRide .pipe schema shown in their VS Code extension / docs at docs.rocketride.org, (2) write a ~20-line Python script using the `rocketride` SDK: RocketRideClient(uri="ws://localhost:5565"), await client.use(filepath=...), await client.send(token, payload), (3) troubleshoot deployment of the same pipe to wss://cloud.rocketride.ai with an API key. Also: I need two Guild.ai agents published via `guild agent init --template LLM` from existing agent.ts files — help me debug any CLI/auth errors I paste.

---

# 🅲 PERSON C — FALKORDB + LASERDATA (branch: `data-layer`)

**Mission:** make memory and real-time visibly REAL — the graph growing in
FalkorDB's browser, the life stream ticking in LaserData's console.

**FalkorDB tasks (do first — 30 min):**
1. `docker run -d -p 6379:6379 -p 3000:3000 falkordb/falkordb:latest` · `pip install falkordb`.
2. Flip the backend: `MEMORY_BACKEND=falkor python3 demo.py` → must still print `ALL CHECKS PASSED`. The Cypher mirror already exists in `kit/memory.py::FalkorStore` — you're validating, not writing from scratch. If a Cypher line errors, fix THAT line only and re-run.
3. Open http://localhost:3000 → graph `personal_brain` → run + screenshot the two judge queries: `MATCH (c:Commitment)-[r]->(x) RETURN c,r,x` and `MATCH (p:Protocol)-[r]->(x) RETURN p,r,x`. Bookmark both on the demo laptop. This browser tab IS the "watch the brain grow" moment.
4. For `server.py` runs, export `MEMORY_BACKEND=falkor` in the launch command and tell Abhinav when it's stable.

**LaserData tasks (booth-assisted — 45 min):**
5. Sign up at laserdata.cloud (free tier) OR run their local **Laser Stack** (officially sanctioned in the problem statement, and more reliable than venue wifi). FIRST QUESTION AT THEIR BOOTH: "fastest Python path to publish to a stream?" **Pin whatever SDK/API version works — never upgrade after it works.**
6. Wire publishing: in `kit/feed.py::publish` there is ONE marked line (`# VENUE TODO`) — publish every enriched event dict to stream `nous`, topic `life-events`. Add the same 3-line publish in `kit/actions.py::execute` after the receipt is appended → topic `receipts`.
7. Verify their console shows both topics ticking while `python3 demo.py` runs. Screenshot. Bookmark the console on the demo laptop.
8. **Stretch (only if done early):** a replay script that re-reads the stream from offset 0 and re-POSTs to `/events` — "replay my day" is LaserData's native superpower and judges love it.

**Definition of done:** demo green with `MEMORY_BACKEND=falkor` ✓ both judge queries bookmarked ✓ LaserData console ticking during a run ✓ screenshots committed to `evidence/` ✓.

**PASTE THIS TO YOUR AI AGENT:**
> I have a Python class FalkorStore (in kit/memory.py) that mirrors writes to FalkorDB via the `falkordb` pip client: FalkorDB(host,port).select_graph("personal_brain").query("<cypher>"). Nodes: Event, Contact, TriggerClass, Protocol, Commitment, Receipt, Person; edges: OF_CLASS, TAUGHT_BY, LEARNED_FROM, HANDLES, APPROVED_BY, PROMISED_TO, DETECTED_IN, RAN, ON. Help me debug any Cypher syntax errors I paste from running MEMORY_BACKEND=falkor python3 demo.py. Separately: I need to publish JSON dicts to a LaserData Cloud stream from Python — their docs are at docs.laserdata.com (Apache-Iggy-based; TS SDK is @laserdata/laser-sdk; REST at api.laserdata.cloud/docs). Given the API surface I paste, write a minimal `publish_event(evt: dict)` function with a 2-second timeout that NEVER raises (log-and-continue on failure), so the demo can't die if the network drops.

---

## 🔀 MERGE PLAN (Abhinav runs this)

1. **T+45 min — Integration 1:** merge `ui` (dashboard shows /state live) + `data-layer` FalkorDB flip. Run demo green.
2. **T+1h45 — Integration 2:** merge `rocketride-guild` + LaserData wiring. Full click-through of all 3 beats on the dashboard with all four sponsor tabs open (FalkorDB browser, LaserData console, RocketRide cloud trace, Guild session).
3. **T+2h15 — CODE FREEZE.** Only `evidence/`, README, pitch after this.
4. Rehearse ×2 on the merged main · record backup video on a phone · screenshots into `evidence/`.
5. **3:10 — SUBMIT:** Discord `/submit` + form. Repo README gets: what it does, the 3 beats, sponsor table (from PITCH.md), team names, "built during the event with AI assistance."

**Final product =** main branch where: `python3 server.py` + frontend = clickable 3-beat demo · all four sponsor surfaces live · demo.py green · PITCH.md is the script · evidence/ full of screenshots.
