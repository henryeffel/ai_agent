import argparse
import json
import re
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "ms-2nd-project-integration-ver-1" / "Backend"
sys.path.insert(0, str(BACKEND))

from ieum.ingestion import DocumentMetadata, chunk_document  # noqa: E402


def tokens(value):
    return set(re.findall(r"[0-9A-Za-z가-힣]+", value.casefold()))


def load_dataset(path):
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return (
        [record for record in records if record["type"] == "document"],
        [record for record in records if record["type"] == "query"],
    )


def baseline_chunks(documents, size=120):
    return [
        {
            "document_id": document["id"],
            "category": document["category"],
            "text": document["text"][start : start + size],
        }
        for document in documents
        for start in range(0, len(document["text"]), size)
    ]


def improved_chunks(documents):
    rows = []
    for document in documents:
        chunks = chunk_document(
            document["text"],
            DocumentMetadata(
                document_id=document["id"],
                title=document["title"],
                category=document["category"],
                source_url=f"evaluation://{document['id']}",
            ),
            max_chars=180,
        )
        rows.extend(
            {
                "document_id": chunk.document_id,
                "category": chunk.category,
                "text": f"{chunk.title} {chunk.section or ''} {chunk.content}",
            }
            for chunk in chunks
        )
    return rows


def search(query, chunks, *, improved):
    query_tokens = tokens(query["query"])
    scored = []
    for chunk in chunks:
        if improved and query.get("category") != chunk["category"]:
            continue
        chunk_tokens = tokens(chunk["text"])
        score = len(query_tokens & chunk_tokens) / max(1, len(query_tokens))
        if improved and score < 0.2:
            continue
        scored.append((score, chunk["document_id"]))
    scored.sort(key=lambda item: item[0], reverse=True)
    if improved:
        scored = [item for item in scored if item[0] > 0]
    seen = set()
    results = []
    for score, document_id in scored:
        if document_id not in seen:
            results.append({"document_id": document_id, "score": round(score, 4)})
            seen.add(document_id)
        if len(results) == 3:
            break
    return results


def evaluate(pipeline, dataset):
    documents, queries = load_dataset(dataset)
    chunks = improved_chunks(documents) if pipeline == "improved" else baseline_chunks(documents)
    recalls = []
    evidence_hits = []
    grounded_decisions = []
    insufficient = []
    latencies = []
    failures = []
    for query in queries:
        started = time.perf_counter()
        results = search(query, chunks, improved=pipeline == "improved")
        latencies.append((time.perf_counter() - started) * 1000)
        returned = {result["document_id"] for result in results}
        expected = set(query["expected_documents"])
        if expected:
            recall = len(returned & expected) / len(expected)
            recalls.append(recall)
            evidence_hits.append(bool(returned & expected))
        grounded = bool(results)
        grounded_decisions.append(grounded == query["should_ground"])
        if not query["should_ground"]:
            insufficient.append(not grounded)
        if (expected and not returned & expected) or grounded != query["should_ground"]:
            failures.append({"query_id": query["id"], "returned": results, "expected": sorted(expected), "should_ground": query["should_ground"]})
    return {
        "pipeline": pipeline,
        "dataset": {"documents": len(documents), "queries": len(queries)},
        "chunk_count": len(chunks),
        "metrics": {
            "recall_at_3": round(sum(recalls) / len(recalls), 4),
            "evidence_hit_rate": round(sum(evidence_hits) / len(evidence_hits), 4),
            "grounded_decision_accuracy": round(sum(grounded_decisions) / len(grounded_decisions), 4),
            "insufficient_evidence_rejection_rate": round(sum(insufficient) / len(insufficient), 4),
            "average_search_latency_ms": round(sum(latencies) / len(latencies), 4),
        },
        "failure_count": len(failures),
        "failures": failures,
        "limitations": [
            "Small synthetic Korean policy dataset; results are not production quality claims.",
            "Lexical overlap evaluator does not measure embedding model quality.",
            "Latency excludes network, database, and embedding generation time.",
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pipeline", choices=("baseline", "improved"), required=True)
    parser.add_argument("--dataset", type=Path, default=Path(__file__).with_name("dataset.jsonl"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(args.pipeline, args.dataset)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["metrics"], ensure_ascii=False))


if __name__ == "__main__":
    main()
