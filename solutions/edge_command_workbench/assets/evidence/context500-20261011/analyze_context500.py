#!/usr/bin/env python3
"""Derive paired accuracy and timing slices from a completed context500 JSONL run."""
from __future__ import annotations
import argparse, hashlib, json, math, statistics
from pathlib import Path

EXECUTION = {"clarify", "reject"}

def stats(values):
    if not values: return None
    xs = sorted(float(x) for x in values)
    return {"n": len(xs), "mean_ms": statistics.fmean(xs), "min_ms": xs[0], "p50_ms": statistics.median(xs), "p95_ms": xs[min(len(xs)-1, math.ceil(.95*len(xs))-1)], "max_ms": xs[-1]}

def accuracy(rs):
    return {"n":len(rs),"http_success":sum(r.get("status")==200 for r in rs),"correct":sum(bool(r.get("correct")) for r in rs),"accuracy":sum(bool(r.get("correct")) for r in rs)/len(rs) if rs else None}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--dataset", required=True); ap.add_argument("--results", required=True); ap.add_argument("--out", required=True); args=ap.parse_args()
    dataset_path=Path(args.dataset); results_path=Path(args.results); dataset=[json.loads(x) for x in dataset_path.read_text().splitlines() if x.strip()]; result=[json.loads(x) for x in results_path.read_text().splitlines() if x.strip()]
    if len(dataset)!=120: raise SystemExit(f"expected 120 dataset rows, got {len(dataset)}")
    group_count=len({r["group"] for r in dataset})
    if group_count!=60: raise SystemExit(f"expected 60 paired semantic groups, got {group_count}")
    if len(result)!=240: raise SystemExit(f"expected exactly 240 result rows, got {len(result)}")
    expected={}
    for row in dataset:
        expected[("original",row["id"])]=(row,row["request_500_sha256"],{x["id"] for x in row["request_500"]["options"]})
        expected[("reverse",row["id"])]=(row,row["reverse_request_500_sha256"],{x["id"] for x in row["reverse_request_500"]["options"]})
    dataset_sha=hashlib.sha256(dataset_path.read_bytes()).hexdigest(); results_sha=hashlib.sha256(results_path.read_bytes()).hexdigest(); by_key={}
    for rec in result:
        key=(rec.get("pass"),rec.get("id"))
        if key not in expected: raise SystemExit(f"unknown result key: {key}")
        if key in by_key: raise SystemExit(f"duplicate result key: {key}")
        row,request_sha,option_ids=expected[key]
        for field,want in (("dataset_sha256",dataset_sha),("request_sha256",request_sha),("expected_id",row["expected_id"]),("assembled_tokens",500)):
            if rec.get(field)!=want: raise SystemExit(f"result {key} field {field} mismatch: {rec.get(field)!r} != {want!r}")
        by_key[key]=rec
    if set(by_key)!=set(expected): raise SystemExit("result keys do not exactly match dataset original/reverse keys")
    result=list(by_key.values())
    def rows_for(field,value): return [r for r in result if r[field]==value]
    expected_by={r["id"]:r["expected_id"] for r in dataset}
    false_action=[]; protocol_invalid=[]
    for r in result:
        row,_,option_ids=expected[(r["pass"],r["id"])]
        selected=r.get("selected_option_id"); valid_selected=selected in option_ids
        if r.get("status")==200 and not valid_selected:
            protocol_invalid.append({"pass":r["pass"],"id":r["id"],"selected_option_id":selected,"candidate_ids":sorted(option_ids)})
        expected_id=expected_by[r["id"]]
        if r.get("status")==200 and expected_id in EXECUTION and selected in option_ids and selected not in EXECUTION:
            false_action.append({"pass":r["pass"],"id":r["id"],"expected_id":expected_id,"selected_option_id":selected})
    false_by_expected={}
    for expected_id in ("clarify","reject"):
        denominator=[r for r in result if expected_by[r["id"]]==expected_id]; actions=[r for r in false_action if r["expected_id"]==expected_id]
        false_by_expected[expected_id]={"n":len(denominator),"false_action_count":len(actions),"false_action_rate":len(actions)/len(denominator) if denominator else None,"rows":actions}
    paired=[]
    for row in dataset:
        a=by_key[("original",row["id"])]; b=by_key[("reverse",row["id"])]
        paired.append({"id":row["id"],"original_selected":a.get("selected_option_id"),"reverse_selected":b.get("selected_option_id"),"selected_id_changed":a.get("selected_option_id")!=b.get("selected_option_id"),"original_correct":bool(a.get("correct")),"reverse_correct":bool(b.get("correct")),"correctness_changed":bool(a.get("correct"))!=bool(b.get("correct"))})
    successful=[r for r in result if r.get("status")==200]; complete=[r for r in successful if isinstance(r.get("server_timings"),dict) and all(isinstance(r["server_timings"].get(k),(int,float)) and math.isfinite(float(r["server_timings"][k])) for k in ("encoding_ms","inference_ms","total_ms"))]
    categories={x:accuracy(rows_for("category",x)) for x in sorted({r["category"] for r in result})}
    for category in ("ambiguous","OOS"):
        if categories.get(category,{}).get("n") != 40: raise SystemExit(f"{category} denominator is not 40: {categories.get(category)}")
    out={"dataset_sha256":dataset_sha,"results_file_sha256":results_sha,"paired_semantic_group_count":group_count,"language_sample_count":len(dataset),"dataset_cases":len(dataset),"scored_requests":len(result),"semantic_sample_denominator":120,"request_denominator":240,"overall":accuracy(result),"by_pass":{p:accuracy(rows_for("pass",p)) for p in ("original","reverse")},"by_language":{x:accuracy(rows_for("language",x)) for x in sorted({r["language"] for r in result})},"by_category":categories,"false_action":{"definition":"HTTP 200 with expected clarify/reject and selected option outside {clarify,reject}; selected must be one of that request's candidate IDs; invalid/unknown selections are excluded and listed separately","by_expected":false_by_expected,"count":len(false_action)},"protocol_invalid":{"count":len(protocol_invalid),"rows":protocol_invalid},"paired_option_order":{"pairs":len(paired),"selected_id_changed_count":sum(x["selected_id_changed"] for x in paired),"selected_id_changed_rate":sum(x["selected_id_changed"] for x in paired)/len(paired),"correctness_changed_count":sum(x["correctness_changed"] for x in paired),"rows":paired},"performance":{"client_e2e_http200":stats([r["client_elapsed_ms"] for r in successful]),"server_encoding_complete":stats([r["server_timings"]["encoding_ms"] for r in complete]),"server_inference_complete":stats([r["server_timings"]["inference_ms"] for r in complete]),"server_total_complete":stats([r["server_timings"]["total_ms"] for r in complete]),"http200_count":len(successful),"timings_complete_count":len(complete),"timings_missing_count":len(successful)-len(complete)},"timing_scope_note":"Kev NativeBackend currently sets encoding_ms=0.0 as instrumentation; decision.py measures KevCodec.encode inside infer_request together with RKLLM hidden inference and FP32 head, so encoding_ms must not be reported as tokenizer wall time or as a measured zero-cost claim.","method_note":"120 semantic cases are evaluated twice (original/reverse option order), not 240 independent semantic samples; five warmups are excluded by the runner."}
    Path(args.out).write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"out":args.out,"false_action_count":len(false_action),"protocol_invalid_count":len(protocol_invalid),"paired_selected_change_count":out["paired_option_order"]["selected_id_changed_count"],"http200":len(successful),"timings_complete":len(complete)},ensure_ascii=False))
if __name__=="__main__": main()
