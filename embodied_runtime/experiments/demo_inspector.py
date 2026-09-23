"""Portable HTML presentation of the demo audit; no model or simulator needed."""
from __future__ import annotations

import base64
from html import escape
from io import BytesIO
import json
from pathlib import Path

import numpy as np


def _text(value):
    if value is None:
        return "unknown / not recorded"
    return escape(str(value))


def _details(label, value, *, opened=False):
    return (f'<details{" open" if opened else ""}><summary>{escape(label)}</summary>'
            f'<pre>{escape(json.dumps(value, indent=2, ensure_ascii=False))}</pre></details>')


def _picture(directory, record, key, label):
    if not record:
        return f'<p>{escape(label)}: not recorded</p>'
    from PIL import Image
    with np.load(directory / record["artifact"], allow_pickle=False) as archive:
        pixels = archive[key]
        if key == "frames":
            if len(pixels) == 0:
                return '<p>No execution frames recorded.</p>'
            pixels = pixels[-1]
        image = Image.fromarray(pixels)
        image.thumbnail((384, 384))
        buffer = BytesIO()
        image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f'<figure><img alt="{escape(label)}" src="data:image/png;base64,{encoded}"><figcaption>{escape(label)}</figcaption></figure>'


def write_inspector(directory, data):
    """Embed sensor/endpoint images and escaped evidence; safe to open via file://."""
    directory = Path(directory)
    terminal = data["termination"][-1] if data["termination"] else {}
    success = terminal.get("success")
    issues = sum(len(a["issues"]) for a in data["attempts"]) + sum(len(t["issues"]) for t in data['feedback']['transitions'])
    parts = ['''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Laya embodied demonstration — evidence inspector</title>
<style>
:root{color-scheme:dark;font:16px/1.5 system-ui,sans-serif;background:#101923;color:#e8eef5}
body{max-width:1150px;margin:auto;padding:24px}h1,h2,h3{line-height:1.2}a{color:#94d9ff}
header,article,.panel{border:1px solid #40566b;border-radius:10px;padding:22px;margin:18px 0;background:#172534}
.banner{border-left:5px solid #f4b860;padding:12px;background:#302a24}.flow{font-size:18px;color:#a2e3d1}
nav{display:flex;gap:12px;flex-wrap:wrap}nav a{padding:6px 12px;background:#24394d;border-radius:6px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px}
figure{margin:0}img{width:100%;max-width:384px}figcaption,.muted{color:#b0c3d5;font-size:14px}
table{border-collapse:collapse;width:100%;font-size:14px}td,th{border-bottom:1px solid #40566b;text-align:left;padding:8px;overflow-wrap:anywhere}
pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:480px;overflow:auto;font-size:13px;background:#101923;padding:14px}
summary{cursor:pointer;padding:10px 0;color:#94d9ff}code{overflow-wrap:anywhere}.bar{background:#83d6c2;height:5px;display:block}
.bad{color:#ffc58a}article{scroll-margin-top:15px}.selected{background:#24483f}
</style><header><p class="muted">Laya Embodied Runtime · engineering demonstration</p>
<h1>Follow observations through decisions and back</h1>
<p class="flow">RGB-D → visual belief → compact state → Laya → executor → MuJoCo → next observation</p>
<p class="banner">This demonstrates connectivity when the recorded chain verifies. A selected command is not evidence of task understanding or task competence. No E0 or research validation follows.</p>''']
    parts.append(f'<p><b>{data["verified_laya_executions"]} verified Laya executions</b> · '
                 f'{len(data["attempts"])} decision attempts · {len(data["failures"])} failure events · {issues} audit issues</p>')
    parts.append(f'<p>Run termination: <b>{_text(terminal.get("reason"))}</b> · '
                 f'Recorded task success: <b>{_text(success)}</b> · Incomplete run: <b>{data["run_incomplete"]}</b></p>')
    parts.append('<p>Simulation pauses for sensing and inference. Contact, holding and drawer progress remain unknown to Laya. '
                 'Simulator outcome measurements below are evaluator-only. Gates and model probabilities are not safety or confidence certificates.</p>')
    parts.append(f'<p class="muted">Raw log SHA-256: <code>{data["source_sha256"]}</code>. '
                 'Hashes establish consistency of this recording, not independent attestation of the model or machine.</p></header>')
    parts.append('<nav>' + ''.join(f'<a href="#step-{a["step"]}">Step {a["step"]}</a>' for a in data["attempts"])
                 + '<a href="#failures">Failures</a><a href="#provenance">Reproduce / audit</a></nav>')
    feedback = data['feedback']
    parts.append('<section class="panel"><h2>Feedback and task progress</h2>')
    parts.append(f'<p>Verified deliveries into the next Laya execution: <b>{feedback["verified_feedback_deliveries"]}</b> · '
                 f'Final observations verified: <b>{feedback["terminal_observations"]}</b> · '
                 f'Translation actions: <b>{feedback["translation_actions"]}</b></p>')
    parts.append(f'<p>Net drawer closure (evaluator only): <b>{_text(feedback["net_drawer_closure_mm_evaluator_only"])} mm</b>.</p>')
    parts.append('<p class="banner">The embodied loop predates this inspector. Feedback reaching a model and changes in its output '
                 'do not by themselves prove task-directed sensitivity. Candidate gates can remove the previous choice. '
                 'Laya selects atomic decisions; deterministic controllers own geometry and motor control.</p></section>')
    for attempt in data["attempts"]:
        step = attempt["step"]
        decision, intent, execution = attempt["decision"] or {}, attempt["intent"] or {}, attempt["execution"] or {}
        model = attempt["model_input"] or {}
        parts.append(f'<article id="step-{step}"><h2>Step {step}: {_text(decision.get("token"))} → '
                     f'{_text(execution.get("token"))}</h2><p><b>{escape(attempt["classification"])}</b> · '
                     f'Verified Laya execution: {attempt["verified_laya_execution"]}</p>')
        if attempt["issues"]:
            parts.append('<p class="banner">Audit issues: ' + '; '.join(map(escape, attempt["issues"])) + '</p>')
        parts.append('<h3>1. World and sensors</h3><div class="grid">')
        parts.append(_picture(directory, attempt["capture"], "rgb", "Sensor RGB at decision boundary; no oracle annotation"))
        parts.append(_picture(directory, attempt["trajectory"], "frames", "Recorded physical endpoint after this action"))
        parts.append('</div><p>RGB-D arrays, camera calibration and detector output are linked below. '
                     'The live estimator uses the first query box and interior median depth; extra detections are retained. '
                     'This is not a validated grasp-point estimate.</p>')
        parts.append(_details('Capture, calibration identity and detector output',
                              {"capture": attempt["capture"], "detection": attempt["detection"]}))
        parts.append(_details('Accepted observations and full visual belief (audit only)',
                              {"observations": attempt.get("observations"), "snapshot": attempt["snapshot"]}))
        parts.append('<h3>2. Exactly what Laya received</h3><p>The following state and question are the recorded API arguments. '
                     'The full canonical audit and actual consumed token IDs remain available below.</p>')
        parts.append(_details('Model state argument', model.get('state'), opened=True))
        parts.append(_details('Model question, instructions and option meanings', model.get('questions'), opened=True))
        parts.append(_details('Full model input audit, provenance and token IDs', model))
        parts.append('<h3>3. Available candidates and returned choice</h3><p>Offered order is recovered from the canonical candidate list; '
                     'JSON object keys in the raw log are sorted for hashing. Consumed token IDs preserve the actual model sequence. '
                     'Veto reasons and natural soft metadata are audit-only. Returned probabilities are uncalibrated.</p>')
        natural = {c["token"]: c for c in attempt["snapshot"]["snapshot"]["candidates"]}
        allowed = model.get('questions', {}).get('action', {}).get('criteria', {})
        tokens = attempt['option_order'] + [token for token in natural if token not in allowed]
        parts.append('<table><tr><th>Token</th><th>Offered to model</th><th>Meaning / gate veto</th><th>Returned P</th></tr>')
        for token in tokens:
            probability = decision.get('probabilities', {}).get(token)
            meaning = allowed.get(token) or ', '.join(natural[token]['reason_codes'])
            bar = '' if probability is None else f'<span class="bar" style="width:{max(0,min(100,probability*100)):.2f}%"></span>'
            parts.append(f'<tr class="{"selected" if token == decision.get("token") else ""}"><td>{escape(token)}</td>'
                         f'<td>{token in allowed}</td><td>{escape(meaning)}</td><td>{_text(probability)}{bar}</td></tr>')
        parts.append('</table>' + _details('Raw Laya response, logits and consumed tokens', attempt['raw_response']))
        parts.append('<h3>4. Validation and atomic execution</h3>')
        parts.append(f'<p>Proposed source: <b>{_text(decision.get("source"))}</b> · '
                     f'Executor source: <b>{_text(intent.get("decision", {}).get("source"))}</b> · '
                     f'Fallback reason: <b>{escape(str(intent.get("fallback_reason"))) if intent else "not recorded"}</b></p>')
        parts.append(_details('Typed proposal and validated executor intent', {"proposal": decision, "intent": intent}))
        delta = execution.get('delta_m')
        measured_delta = ', '.join(f'{v*1000:+.3f}' for v in delta) if delta is not None else 'unknown'
        parts.append(f'<p>Measured TCP displacement XYZ: <b>{measured_delta} mm</b> · '
                     f'Control steps: <b>{_text(execution.get("environment_step_count"))}</b></p>')
        parts.append(_details('Actual controls, measured TCP/gripper and contract checks', execution, opened=False))
        parts.append('<h3>5. Physical outcome — evaluator only</h3><p>These simulator measurements did not enter the model state above.</p>')
        parts.append('<table><tr><th>Measurement</th><th>Before</th><th>After</th></tr>')
        before = (attempt['evaluation']['before'] or {}).get('features', {})
        after = (attempt['evaluation']['after'] or {}).get('features', {})
        for key in ('remaining_open_mm', 'moving_contact', 'finger_gap_mm', 'success'):
            parts.append(f'<tr><td>{key}</td><td>{_text(before.get(key))}</td><td>{_text(after.get(key))}</td></tr>')
        parts.append(f'</table><p>Atomic contract violation: <b>{_text(execution.get("execution_contract_violation"))}</b>. '
                     'A clear flag is not a general safety certificate. STOP is an active controller command.</p>')
        parts.append(_details('Raw evaluator records and trajectory identity',
                              {"evaluation": attempt['evaluation'], "trajectory": attempt['trajectory']}))
        transition = next((t for t in feedback['transitions'] if t['from_step'] == step), None)
        if transition:
            parts.append('<h3>6. Outcome → next observation → next decision</h3>')
            parts.append(_picture(directory, transition['post_capture'], 'rgb',
                                  'Fresh post-action sensor capture; separate from the execution frame'))
            parts.append(f'<p>Next proposed choice: <b>{_text(transition["proposed_after"])}</b> · '
                         f'Feedback delivery verified: <b>{transition["feedback_delivery_verified"]}</b> · '
                         f'Final observation only: <b>{transition["terminal_observation"]}</b></p>')
            parts.append(f'<p class="banner">{escape(transition["interpretation"])}</p>')
            if transition['issues']:
                parts.append('<p class="bad">Feedback audit issues: ' + '; '.join(map(escape, transition['issues'])) + '</p>')
            parts.append('<table><tr><th>Model input field</th><th>Before</th><th>Next decision</th></tr>')
            for key, delta in transition['changed_model_state'].items():
                if key.startswith(('robot.', 'relations.', 'target.')):
                    parts.append(f'<tr><td>{escape(key)}</td><td>{_text(delta["before"])}</td><td>{_text(delta["after"])}</td></tr>')
            parts.append('</table>')
            parts.append(_details('Changed candidates, raw admitted observations and complete feedback audit', transition))
            if transition['to_step'] is not None:
                parts.append(f'<p><a href="#step-{transition["to_step"]}">Inspect the next exact model input and choice</a></p>')
        parts.append(_details('Raw record sequence and content identities', attempt.get('record_links')) + '</article>')
    parts.append('<section class="panel" id="failures"><h2>Failures and unfinished work</h2>')
    parts.append(_details('All recorded failure events', data['failures'], opened=True))
    parts.append(_details('Termination and captures without a decision snapshot',
                          {"termination": data['termination'], "unassigned_captures": data['unassigned_captures']}))
    parts.append('</section><section class="panel" id="provenance"><h2>Reproduce and audit</h2>')
    parts.append('<p>Control replay replays saved commands; it is not a second model-driven rollout. '
                 'A replay report is relevant only when its raw-source hash matches this log.</p>')
    parts.append(_details('Replay result and source match', data['replay'], opened=True))
    parts.append(_details('Resolved configuration and source/model/environment manifest',
                          {"invocation": data['invocation'], "config": data['config'], "manifest": data['manifest']}))
    parts.append(_details('Report generator identity (separate from collected run)', data['report_generator']))
    parts.append('<p><a href="demo-evidence.json">Derived evidence JSON</a> · <a href="episodes.jsonl">Raw chained records</a> · '
                 '<a href="manifest.json">Manifest</a> · <a href="summary.csv">Actions CSV</a> · <a href="failures.csv">Failures CSV</a></p>')
    parts.append('<p>The embedded images and evidence work offline. Share the entire run directory for independent verification, '
                 'including frames/ and trajectory/. Local model paths require equivalent checkpoint bytes on another machine.</p></section></html>')
    path = directory / 'demo.html'
    path.write_text('\n'.join(parts), encoding='utf-8')
    (directory / 'demo-evidence.json').write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    return str(path)
