"""Embed closed-case narratives + policy/pattern documents and load them as TigerGraph vectors (GraphRAG corpus)."""
import sys, re, pandas as pd
sys.path.insert(0, "/home/vinay/hackerhouse")
from agent.llm import embed
import pyTigerGraph as tg, subprocess

S = "/home/vinay/hackerhouse/data/slim/"
h = pd.read_csv(S + "closed_cases.csv")
texts = (h.pattern.str.replace("_", " ") + " | " + h.outcome + " | " + h.analyst_notes.fillna("")).tolist()
vecs = embed(texts)
pd.DataFrame({"id": h.case_id, "emb": [":".join(f"{x:.6f}" for x in v) for v in vecs]}).to_csv(S + "case_emb.csv", index=False)
print("closed-case embeddings", len(vecs), len(vecs[0]), flush=True)

# --- policy / pattern chunks from the dataset README
readme = open("/home/vinay/hackerhouse/data/HHGOA_IEEE/README.md").read()
chunks = []
def add(src, sec, txt):
    txt = re.sub(r"\s+", " ", txt).strip()
    if len(txt) > 40: chunks.append((f"{src}:{len(chunks):03d}", src, sec, txt))
pat = readme.split("## The five known fraud patterns")[1].split("## Regulatory references")[0]
for m in re.finditer(r"\*\*(\d)\. ([^*]+)\.\*\* (.+?)(?=\n\n\*\*\d\.|\Z)", pat, re.S):
    add("pattern", f"Pattern {m.group(1)}: {m.group(2)}", m.group(3))
pol = readme.split("# Fraud Policy")[1].split("# Answer Format")[0]
for m in re.finditer(r"\*\*(R\d+)\. ([^*]+)\*\* (.+?)(?=\n\n\*\*R\d+\.|\n\n###|\Z)", pol, re.S):
    add("policy", f"{m.group(1)} {m.group(2).strip()}", m.group(3))
for title in ["1. Actions", "2. Approval routing", "3a. A case is not a report", "3b. The next best action can change", "4. Exposure", "5. Gathering more evidence", "6. Stopping", "7. Explaining"]:
    m = re.search(rf"### {re.escape(title)}\n(.+?)(?=\n### |\Z)", pol, re.S)
    if m: add("policy", title, m.group(1))
for m in re.finditer(r"- \*\*(.+?)\*\*[^\n]*?(?=\n- \*\*|\n## |\Z)", readme.split("## Things to know")[1].split("## Rules")[0], re.S):
    add("guidance", "Things to know", m.group(0))
# FinCEN SAR narrative guidance distilled (who/what/when/where/how/why) so the writer is grounded in the regulator's own frame
add("regulatory", "FinCEN SAR narrative guidance", "A SAR narrative must stand on its own and answer who, what, when, where, how and why the activity is suspicious. Identify subjects and account numbers, give the dates and the total dollar amount, describe the method used and the pattern observed, and explain why the activity is suspicious or lacks an apparent lawful purpose. Keep it factual, chronological and complete; do not include speculation.")
add("regulatory", "FinCEN Account Takeover advisory", "Account takeover red flags: login or purchase from a new device or IP address inconsistent with the customer, anonymizing proxies, rapid changes of contact details, sudden activity across channels, and multiple accounts accessed from the same device. Shared devices across unrelated customers indicate a coordinated actor.")
add("regulatory", "FFIEC red flags", "Structuring: several transactions kept just below a reporting or authorization threshold in a short period is a red flag for evasion of controls. Repeated transactions of similar amounts just under a limit warrant escalation and reporting.")
print("policy chunks", len(chunks), flush=True)
cv = embed([c[3] for c in chunks])
df = pd.DataFrame(chunks, columns=["id", "source", "section", "text"])
df.to_csv(S + "policy_chunks.csv", index=False, quoting=1)
pd.DataFrame({"id": df.id, "emb": [":".join(f"{x:.6f}" for x in v) for v in cv]}).to_csv(S + "policy_emb.csv", index=False)

subprocess.run("docker cp /home/vinay/hackerhouse/data/slim/. tg:/home/tigergraph/slim/ && docker exec -u root tg chown -R tigergraph:tigergraph /home/tigergraph/slim", shell=True, check=True)
c = tg.TigerGraphConnection(host="http://127.0.0.1", restppPort=9000, gsPort=14240, username="tigergraph", password="tigergraph", graphname="FraudGraph")
print(c.gsql('''USE GRAPH FraudGraph
DROP JOB load_case_emb
DROP JOB load_policy
DROP JOB load_policy_emb
CREATE LOADING JOB load_case_emb FOR GRAPH FraudGraph { DEFINE FILENAME f; LOAD f TO VECTOR ATTRIBUTE emb ON VERTEX ClosedCase VALUES ($0, SPLIT($1, ":")) USING SEPARATOR=",", HEADER="true", EOL="\\n"; }
CREATE LOADING JOB load_policy FOR GRAPH FraudGraph { DEFINE FILENAME f; LOAD f TO VERTEX PolicyChunk VALUES ($0, $1, $2, $3) USING SEPARATOR=",", HEADER="true", EOL="\\n", QUOTE="double"; }
CREATE LOADING JOB load_policy_emb FOR GRAPH FraudGraph { DEFINE FILENAME f; LOAD f TO VECTOR ATTRIBUTE emb ON VERTEX PolicyChunk VALUES ($0, SPLIT($1, ":")) USING SEPARATOR=",", HEADER="true", EOL="\\n"; }
''')[-500:])
D = "/home/tigergraph/slim/"
for job, f in [("load_policy", "policy_chunks.csv"), ("load_case_emb", "case_emb.csv"), ("load_policy_emb", "policy_emb.csv")]:
    print(job, c.gsql(f'USE GRAPH FraudGraph\nRUN LOADING JOB {job} USING f="{D}{f}"')[-350:].replace("\n", " | "), flush=True)
print(c.getVertexCount("PolicyChunk"), c.getVertexCount("ClosedCase"))
