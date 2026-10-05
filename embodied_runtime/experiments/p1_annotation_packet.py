"""Build a blinded local RGB annotation packet and evaluate human exports offline.

No semantic model, simulator, policy, depth display or existing result overlay is
loaded into the annotation page. Generated packets contain no completed labels.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path

from ..contracts import canonical_json, require
from ..perception.evaluation_annotations import (
    ANNOTATION_SCHEMA, PACKET_SCHEMA, RULES_VERSION, evaluate_grounding,
    load_packet, packet_identity, validate_annotations, validate_packet_manifest,
)
from ..perception.recording import replay_frames


HTML = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>P1 primary human RGB annotation</title><style>
body{font:16px system-ui;margin:24px;max-width:1200px;color:#17202a;background:#fafafa}
fieldset{margin:12px 0;padding:12px;border:1px solid #bbb}label{display:block;margin:8px 0}
button,select,input{font:inherit;margin:4px;padding:5px}textarea{width:min(90%,700px);height:52px}
canvas{width:768px;max-width:100%;height:auto;border:1px solid #777;cursor:crosshair;background:#333}
#notice{white-space:pre-wrap;color:#8b1800}#progress{font-weight:bold}.row{display:flex;gap:12px;flex-wrap:wrap}
.muted{color:#555}kbd{border:1px solid #bbb;padding:1px 4px}</style></head><body>
<h1>P1 人工 RGB 標註：專案主要人工標註者</h1>
<p>Only recorded RGB is shown. No model boxes, depth, candidate points, fit results or success labels are provided.</p>
<section style="border:2px solid #345;padding:12px"><h2>開始前請閱讀：已凍結的規則</h2><p>本次由使用者本人標註，不宣稱獨立第三方審核。部分匯出只能保存進度，不能進入正式評測。</p><pre style="white-space:pre-wrap;font:inherit">__RULES_TEXT__</pre><p id="rulesHash" class="muted"></p></section>
<fieldset><legend>Annotator self-attestation</legend>
<label>Your distinct human annotator ID <input id="annotator" autocomplete="off" placeholder="Enter your own ID"></label>
<label><input type="checkbox" id="isHuman"> I am a human annotator.</label>
<label><input type="checkbox" id="independent"> I have not inspected this round's model ROI/candidates/results or visual outcomes for these images.</label>
<label><input type="checkbox" id="rgbOnly"> I am labeling from the supplied raw RGB only.</label>
<p class="muted">Role: project_primary_human. These statements are self-attestations; neither identity nor third-party independence is verified or claimed.</p></fieldset>
<div class="row"><button id="prev">Previous</button><select id="imageSelect"></select><button id="next">Next</button></div>
<p id="progress"></p><p id="identity" class="muted"></p>
<canvas id="canvas"></canvas>
<p>Click vertices; finish a polygon with the button. Multiple polygons are allowed. Coordinates use original image pixels. No region is preselected.</p>
<fieldset><legend>Current region</legend><select id="entity"><option value="drawer_front_pushable">Drawer-front visible pushable region</option><option value="fixed_cabinet_reference">Fixed cabinet reference region(s)</option></select>
<label>Status <select id="status"><option value="">Choose explicitly</option><option>VISIBLE</option><option>UNKNOWN</option><option>NOT_VISIBLE</option></select></label>
<label>Reason / observation <textarea id="reason" placeholder="Describe the visible evidence or uncertainty"></textarea></label>
<div id="referenceControls"><label>New fixed-reference polygon type <select id="referenceKind"><option value="">Choose explicitly</option><option>FRONT_FRAME</option><option>FIXED_EDGE</option><option>ADJACENT_FIXED_BODY</option><option>UNKNOWN</option></select></label><div id="referenceTypeList"></div></div>
<button id="finish">Finish polygon</button><button id="undo">Undo vertex</button><button id="deletePolygon">Delete last polygon</button><button id="clear">Clear this entity</button>
<p id="polygonCount"></p><button id="saveImage">Mark this image complete</button></fieldset>
<button id="exportPartial">Export partial work</button><button id="exportFull">Export complete annotations</button>
<label>Resume a saved JSON export <input id="import" type="file" accept="application/json,.json"></label>
<p id="notice" role="status"></p>
<script id="packet" type="application/json">__PACKET__</script><script>
'use strict';
const packet=JSON.parse(document.getElementById('packet').textContent), entities=['drawer_front_pushable','fixed_cabinet_reference'];
const bindingKeys=['image_id','frame_id','rgb_blob_sha256','rgb_pixel_sha256','png_sha256','width','height'];
const $=id=>document.getElementById(id), canvas=$('canvas'),ctx=canvas.getContext('2d');
let index=0,draft=[],image=new Image(),imageReady=false;
let work={},completed=new Set();
const storageKey='p1-human-annotation/'+packet.dataset_id;
function empty(name){return name==='fixed_cabinet_reference'?{status:'',reason:'',polygons:[],reference_types:[]}:{status:'',reason:'',polygons:[]};}
function row(){const id=packet.images[index].image_id; if(!work[id])work[id]={drawer_front_pushable:empty('drawer_front_pushable'),fixed_cabinet_reference:empty('fixed_cabinet_reference')};return work[id];}
function current(){return row()[$('entity').value];}
function notice(text){$('notice').textContent=text;}
function persist(){try{localStorage.setItem(storageKey,JSON.stringify({work,completed:[...completed],annotator:$('annotator').value,isHuman:$('isHuman').checked,independent:$('independent').checked,rgbOnly:$('rgbOnly').checked}));}catch(e){notice('Local autosave unavailable; export partial JSON to preserve work.');}}
function dirty(){completed.delete(packet.images[index].image_id);persist();updateProgress();}
function saveFields(){const e=current();e.status=$('status').value;e.reason=$('reason').value;}
function fields(){const e=current();$('status').value=e.status;$('reason').value=e.reason;$('polygonCount').textContent=e.polygons.length+' polygon(s) saved for this entity; '+draft.length+' pending vertices';$('referenceControls').hidden=$('entity').value!=='fixed_cabinet_reference';const list=$('referenceTypeList');list.replaceChildren();if(e.reference_types)for(const [n,kind] of e.reference_types.entries()){const label=document.createElement('label'),select=document.createElement('select');label.textContent='Polygon '+(n+1)+' type ';for(const value of ['','FRONT_FRAME','FIXED_EDGE','ADJACENT_FIXED_BODY','UNKNOWN']){const option=document.createElement('option');option.value=value;option.textContent=value||'Choose explicitly';select.appendChild(option);}select.value=kind;select.onchange=()=>{e.reference_types[n]=select.value;dirty();};label.appendChild(select);list.appendChild(label);}draw();}
function updateProgress(){$('progress').textContent='Image '+(index+1)+' / '+packet.expected_image_count+'; '+completed.size+' complete';}
function polygon(points,color,closed){if(!points.length)return;ctx.beginPath();ctx.moveTo(...points[0]);for(const p of points.slice(1))ctx.lineTo(...p);if(closed)ctx.closePath();ctx.strokeStyle=color;ctx.lineWidth=1.5;ctx.stroke();for(const p of points){ctx.fillStyle=color;ctx.fillRect(p[0]-1.5,p[1]-1.5,3,3);}}
function draw(){ctx.clearRect(0,0,canvas.width,canvas.height);if(imageReady)ctx.drawImage(image,0,0);for(const entity of entities)for(const p of row()[entity].polygons)polygon(p,entity==='drawer_front_pushable'?'#ff9f00':'#50c8ff',true);polygon(draft,'#ffffff',false);}
function navigate(next){saveFields();persist();index=Math.max(0,Math.min(packet.images.length-1,next));draft=[];const entry=packet.images[index];canvas.width=entry.width;canvas.height=entry.height;$('imageSelect').value=String(index);$('identity').textContent=entry.image_id+' | '+entry.width+' x '+entry.height+' | '+entry.camera_id;imageReady=false;image=new Image();image.onload=()=>{imageReady=true;draw();};image.src=entry.image_path;fields();updateProgress();notice('');}
function entityValid(e,name){if(!e||!['VISIBLE','UNKNOWN','NOT_VISIBLE'].includes(e.status))return 'Choose a status for both entities.';if(!e.reason.trim())return 'Enter a reason for both entities.';if(e.status==='VISIBLE'&&e.polygons.length===0)return 'VISIBLE regions need at least one polygon.';if(e.status==='NOT_VISIBLE'&&e.polygons.length)return 'NOT_VISIBLE cannot have polygons; clear them or change status.';if(name==='fixed_cabinet_reference'){if(!Array.isArray(e.reference_types)||e.reference_types.length!==e.polygons.length)return 'Each fixed reference polygon needs its own explicit type.';const allowed=e.status==='UNKNOWN'?['UNKNOWN']:['FRONT_FRAME','FIXED_EDGE','ADJACENT_FIXED_BODY'];if(e.reference_types.some(kind=>!allowed.includes(kind)))return 'Reference type must match identity certainty; UNKNOWN status requires UNKNOWN polygon type.';}return null;}
function saveImage(){saveFields();if(draft.length)return notice('Finish or undo the pending polygon first.');for(const entity of entities){const error=entityValid(row()[entity],entity);if(error)return notice(error);}completed.add(packet.images[index].image_id);persist();updateProgress();notice('Image saved. Offline validation will additionally check polygon intersections and bindings.');}
function exportWork(full){saveFields();if(!$('annotator').value.trim()||!$('isHuman').checked||!$('independent').checked||!$('rgbOnly').checked)return notice('Provide your own ID and all three self-attestations before export.');if(draft.length)return notice('Finish or undo the pending polygon before export.');if(full&&completed.size!==packet.expected_image_count)return notice('Complete every image before final export. Partial exports cannot enter evaluation.');const records=[];for(const entry of packet.images){if(!completed.has(entry.image_id))continue;const record={};for(const key of bindingKeys)record[key]=entry[key];record.entities=work[entry.image_id];records.push(record);}const value={schema:'p1-human-annotations/2',dataset_id:packet.dataset_id,rules_version:packet.rules_version,rules_sha256:packet.rules_sha256,annotator_id:$('annotator').value.trim(),annotator_role:'project_primary_human',attestations:{is_human:true,independent_of_model_outputs:true,raw_rgb_only:true},exported_at_utc:new Date().toISOString(),annotations:records};const blob=new Blob([JSON.stringify(value,null,2)],{type:'application/json'}),link=document.createElement('a');link.href=URL.createObjectURL(blob);link.download=full?'annotations.complete.json':'annotations.partial.json';link.click();setTimeout(()=>URL.revokeObjectURL(link.href),1000);notice(records.length+' image records exported; partial exports cannot enter evaluation. Run offline validation before evaluation.');}
for(const [n,entry] of packet.images.entries()){const option=document.createElement('option');option.value=n;option.textContent=(n+1)+' '+entry.image_id;$('imageSelect').appendChild(option);}
try{const saved=JSON.parse(localStorage.getItem(storageKey)||'null');if(saved){work=saved.work||{};completed=new Set(saved.completed||[]);$('annotator').value=saved.annotator||'';$('isHuman').checked=saved.isHuman===true;$('independent').checked=saved.independent===true;$('rgbOnly').checked=saved.rgbOnly===true;}}catch(e){}
canvas.addEventListener('click',event=>{if(!imageReady)return;const r=canvas.getBoundingClientRect();draft.push([Math.max(0,Math.min(canvas.width,(event.clientX-r.left)*canvas.width/r.width)),Math.max(0,Math.min(canvas.height,(event.clientY-r.top)*canvas.height/r.height))]);dirty();fields();});
$('finish').onclick=()=>{if(draft.length<3)return notice('At least three vertices are required.');if($('entity').value==='fixed_cabinet_reference'){if(!$('referenceKind').value)return notice('Choose a type for this fixed-reference polygon, or UNKNOWN.');current().reference_types.push($('referenceKind').value);}current().polygons.push(draft);draft=[];dirty();fields();};
$('undo').onclick=()=>{draft.pop();fields();};$('deletePolygon').onclick=()=>{current().polygons.pop();if(current().reference_types)current().reference_types.pop();dirty();fields();};
$('clear').onclick=()=>{row()[$('entity').value]=empty($('entity').value);draft=[];dirty();fields();};
$('entity').onchange=()=>{draft=[];fields();};$('status').onchange=()=>{saveFields();dirty();};$('reason').oninput=()=>{saveFields();dirty();};
$('prev').onclick=()=>navigate(index-1);$('next').onclick=()=>navigate(index+1);$('imageSelect').onchange=()=>navigate(Number($('imageSelect').value));
$('saveImage').onclick=saveImage;$('exportPartial').onclick=()=>exportWork(false);$('exportFull').onclick=()=>exportWork(true);
for(const name of ['annotator','isHuman','independent','rgbOnly'])$(name).onchange=persist;
$('import').onchange=async event=>{try{const value=JSON.parse(await event.target.files[0].text());if(value.schema!=='p1-human-annotations/2'||value.dataset_id!==packet.dataset_id||value.rules_version!==packet.rules_version||value.rules_sha256!==packet.rules_sha256||value.annotator_role!=='project_primary_human')throw Error('Schema/dataset/frozen rules/role mismatch');const nextWork={},done=new Set();for(const record of value.annotations){const entry=packet.images.find(x=>x.image_id===record.image_id);if(!entry||bindingKeys.some(key=>record[key]!==entry[key])||done.has(record.image_id))throw Error('Image binding/coverage mismatch');for(const name of entities){const error=entityValid(record.entities[name],name);if(error)throw Error(error);}nextWork[record.image_id]=record.entities;done.add(record.image_id);}work=nextWork;completed=done;$('annotator').value=value.annotator_id;$('isHuman').checked=value.attestations.is_human===true;$('independent').checked=value.attestations.independent_of_model_outputs===true;$('rgbOnly').checked=value.attestations.raw_rgb_only===true;fields();persist();navigate(index);notice('Imported '+done.size+' completed images. Offline validator remains authoritative.');}catch(e){notice('Import rejected: '+e.message);}};
// Initial load must not manufacture a saved status or annotation.
const first=packet.images[0];canvas.width=first.width;canvas.height=first.height;image.onload=()=>{imageReady=true;draw();};image.src=first.image_path;$('identity').textContent=first.image_id+' | '+first.width+' x '+first.height+' | '+first.camera_id;fields();updateProgress();
$('rulesHash').textContent=packet.rules_version+' | SHA256 '+packet.rules_sha256;
</script></body></html>'''


def build_packet(source, output, *, expected_count=50):
    from PIL import Image

    source, output = Path(source), Path(output)
    source_manifest_bytes = (source/"manifest.json").read_bytes()
    source_manifest = json.loads(source_manifest_bytes)
    rules_bytes = (Path(__file__).resolve().parents[2]/"docs/p1-annotation-rules.md").read_bytes()
    require(RULES_VERSION.encode() in rules_bytes, "tracked rules version differs from annotation schema")
    indices = source_manifest["config"]["init_indices"]
    require(isinstance(indices, list) and len(indices) == len(set(indices)), "source init indices must be unique")
    output.mkdir(parents=True, exist_ok=False)
    (output/"images").mkdir()
    (output/"annotation_rules.md").write_bytes(rules_bytes)
    images = []
    for init_index in indices:
        # Exhaust replay to validate identity chain and closed-recording tail.
        frames = list(replay_frames(source/f"init-{init_index:03d}"))
        require(bool(frames), "source recording has no frames")
        env, views = frames[0]
        raw_refs = {entry["camera_id"]: entry["rgb_blob"] for entry in env.payload["views"]}
        for view in views:
            rgb = view["rgb"]
            relative = f"images/{len(images):03d}.png"
            Image.fromarray(rgb).save(output/relative)
            h, w = rgb.shape[:2]
            images.append({
                "image_id": view["canonical_frame_id"], "frame_id": view["canonical_frame_id"],
                "source_frame_id": view["frame_id"], "episode_id": env.episode_id,
                "init_index": init_index, "camera_id": view["camera_id"], "width": w, "height": h,
                "rgb_blob_sha256": raw_refs[view["camera_id"]]["sha256"],
                "rgb_pixel_sha256": hashlib.sha256(rgb.tobytes()).hexdigest(),
                "png_sha256": hashlib.sha256((output/relative).read_bytes()).hexdigest(),
                "image_path": relative,
            })
    manifest = {"schema": PACKET_SCHEMA, "dataset_id": None,
                "source_run_manifest_sha256": hashlib.sha256(source_manifest_bytes).hexdigest(),
                "selection_rule": "first_bundle_each_camera_per_init_raw_rgb_only",
                "rules_version": RULES_VERSION, "rules_sha256": hashlib.sha256(rules_bytes).hexdigest(),
                "rules_path": "annotation_rules.md",
                "expected_image_count": expected_count, "images": images}
    manifest["dataset_id"] = packet_identity(manifest)
    validate_packet_manifest(manifest, expected_count=expected_count)
    (output/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    encoded = canonical_json(manifest).replace("<", "\\u003c")
    (output/"index.html").write_text(HTML.replace("__PACKET__", encoded).replace("__RULES_TEXT__", html.escape(rules_bytes.decode("utf-8"))))
    # Deliberately invalid as completed evidence until a person fills and attests.
    empty = {"schema": ANNOTATION_SCHEMA, "dataset_id": manifest["dataset_id"], "annotator_id": None,
             "annotator_role": "project_primary_human", "rules_version": RULES_VERSION, "rules_sha256": manifest["rules_sha256"],
             "attestations": {"is_human": False, "independent_of_model_outputs": False, "raw_rgb_only": False},
             "exported_at_utc": None, "annotations": []}
    (output/"annotations.empty.json").write_text(json.dumps(empty, indent=2)+"\n")
    (output/"README.txt").write_text(
        "Open index.html locally in a browser. No server or network is needed.\n"
        "The packet contains raw RGB only and ZERO completed annotations.\n"
        "Read annotation_rules.md first; its version and SHA256 bind every export.\n"
        "Primary annotator: project user; no independent third-party review is claimed.\n"
        "Draw observed regions, select status and enter a reason for both entities on all images.\n"
        "Save each image; export complete JSON when all images are done. Partial exports cannot enter evaluation.\n"
        "Run: python -m embodied_runtime.experiments.p1_annotation_packet validate --packet PACKET --annotations EXPORT.json\n"
        "Identity and independence are self-attested, not verified by software.\n"
        "Annotations are for offline evaluation only; do not feed them into runtime target selection.\n")
    return {"output": str(output), "dataset_id": manifest["dataset_id"],
            "image_count": len(images), "completed_annotations": 0,
            "rules_version": RULES_VERSION, "rules_sha256": manifest["rules_sha256"],
            "label_status": "AWAITING_PRIMARY_HUMAN_ANNOTATION"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build")
    build.add_argument("--source", required=True)
    build.add_argument("--output", required=True)
    for command in ("validate", "evaluate"):
        sub = commands.add_parser(command)
        sub.add_argument("--packet", required=True)
        sub.add_argument("--annotations", required=True)
        if command == "validate":
            sub.add_argument("--allow-partial", action="store_true")
        else:
            sub.add_argument("--predictions", required=True)
            sub.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.command == "build":
        result = build_packet(args.source, args.output)
    else:
        manifest = load_packet(args.packet)
        annotations = json.loads(Path(args.annotations).read_text())
        if args.command == "validate":
            result = validate_annotations(annotations, manifest, require_complete=not args.allow_partial)
        else:
            predictions = json.loads(Path(args.predictions).read_text())
            result = evaluate_grounding(predictions, annotations, manifest)
            with Path(args.output).open("x") as stream:
                stream.write(json.dumps(result, indent=2, allow_nan=False)+"\n")
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
