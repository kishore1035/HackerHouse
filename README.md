# FraudGraph Agent

An agentic fraud investigator for the TigerGraph x Hacker House Goa challenge. It takes an alert (risk score, customer report or analyst request), investigates it on a TigerGraph knowledge graph, decides what kind of fraud it is, recommends the next best action under the bank's fraud policy, asks for more evidence when the picture is uncertain, explains itself, and writes the case back into the graph as memory.

## Architecture

    alert -> Investigator (agent/investigator.py)
              1 investigate  GSQL queries: card_txns, device_txns, device_closed_cases, card_closed_cases, ring_expand
              2 gather       episode model + rule detectors (card testing, structuring, device ring)
              3 GraphRAG     TigerGraph vector search over 5,565 closed-case narratives + policy/typology chunks
              4 assess       calibrated fraud probability, pattern, independent-signal count
              5 recommend    deterministic policy engine (agent/policy.py, rules R1-R10, approval routes)
              6 evidence     simulated customer reply (assumption recorded), recommendation updated
              7 explain      LLM writes summary / SAR narrative from structured facts only (via OmniRoute)
              8 remember     AgentCase vertex + edges + embedding written to TigerGraph

- **Graph** (`gsql/`): Customer, Card, Transaction, DeviceProfile, EmailDomain, BillingRegion, ClosedCase, PolicyChunk, AgentCase; 590,742 transactions, 14,893 cards. TigerGraph 4.2.5 Community Edition in Docker. Vector attributes on ClosedCase, PolicyChunk, AgentCase.
- **LLM only reasons and writes.** Actions and approval routes come from the policy engine, so the LLM cannot breach policy.
- **Models** (`scripts/train_models.py`, `scripts/train_episode.py`): gradient boosting over graph-derived features, trained on the closed cases. The bank risk score is deliberately excluded from the fraud model. Grouped 5-fold CV: fraud AUC 0.987, pattern accuracy 0.83, episode F1 0.80. The same feature code runs against an in-memory client (training) and the TigerGraph client (production); outputs were checked identical.
- **UI** (`ui/index.html`, `api/app.py`): analyst dashboard with the alert queue, live streamed investigation timeline, uncertainty gauge, initial vs final actions, evidence with sources, SAR, graph view and case memory.

## Run

    docker run -d --name tg -p 14240:14240 -p 9000:9000 --ulimit nofile=1000000:1000000 tigergraph/community:latest
    python scripts/prepare_data.py            # slim CSVs + card ids + device profiles
    # apply gsql/schema.gsql, gsql/vectors.gsql, gsql/load.gsql, gsql/queries.gsql, gsql/vector_queries.gsql
    python scripts/load_graph.py
    python scripts/embed_and_load.py          # embeddings via OmniRoute into TigerGraph vectors
    python scripts/build_training_set.py && python scripts/train_models.py && python scripts/train_episode.py
    python scripts/run_cases.py               # writes cases/HHG-001.json ... HHG-020.json
    uvicorn api.app:app --port 8088           # dashboard at http://127.0.0.1:8088

Secrets live in `.env` (git-ignored): `OMNIROUTE_BASE_URL`, `OMNIROUTE_API_KEY`, `OLLAMA_*`.

## Honest limitations

- Customer and analyst replies are simulated (allowed by the brief); every assumption is recorded in `evidence_requests`.
- No answer key is available, so benchmark accuracy is unmeasured. Cross-validated numbers above are on the closed cases only.
- The closed cases have a distribution quirk: cleared cases sit on light cards with widely shared devices. Models can pick that up, so probabilities are shrunk and the agent runs a verification loop when signals are few.
- Fraud episode reconstruction is weakest for account takeover on very heavy cards.
- TigerGraph MCP is not wired in yet; the agent calls the same installed GSQL queries directly through pyTigerGraph.
- Case memory now retrieves the agent's own prior investigations (`similar_agent_cases`, `gsql/vector_queries.gsql`) alongside closed-case history, merged by vector distance in `Investigator._graphrag`. Re-run `gsql/schema.gsql` and `gsql/vector_queries.gsql` to pick up the `AC_SIMILAR_AGENT` edge and new query before the next `run_cases.py`.

## Still to do for submission

GitHub repo, 3-5 minute demo video, technical blog post, X/LinkedIn post tagging @TigerGraphDB.
