from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from embodied_runtime.contracts import ProtocolError, content_hash
from embodied_runtime.experiments import p1_semantic_grounding as grounding
from embodied_runtime.experiments.point_grounding_probe import generation_audit
from embodied_runtime.perception.evaluation_annotations import (
    ANNOTATION_SCHEMA, ENTITIES, PACKET_SCHEMA, RULES_VERSION, image_binding, packet_identity,
)


def write(path, value):
    Path(path).write_text(json.dumps(value))


@pytest.fixture
def packet(tmp_path):
    from PIL import Image
    directory, source = tmp_path/"packet", tmp_path/"source"
    (directory/"images").mkdir(parents=True)
    source.mkdir()
    write(source/"manifest.json", {"fixture": "unit-test-not-independent-human-evidence"})
    (directory/"annotation_rules.md").write_text("Frozen synthetic rules; no real human labels.\n")
    images = []
    for i in range(50):
        pixels = np.full((4, 4, 3), i, np.uint8)
        path = directory/"images"/f"{i}.png"
        Image.fromarray(pixels).save(path)
        init_index = i//2
        camera = ("agentview", "robot0_eye_in_hand")[i % 2]
        episode = f"p1/init{init_index}"
        images.append(dict(image_id=f"image-{i}", frame_id=f"{episode}/{camera}/1", source_frame_id=f"{camera}:1",
                           episode_id=episode, init_index=init_index, camera_id=camera, width=4, height=4,
                           image_path=f"images/{i}.png", rgb_pixel_sha256=hashlib.sha256(pixels.tobytes()).hexdigest(),
                           rgb_blob_sha256=f"{i:064x}", png_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    manifest = dict(schema=PACKET_SCHEMA, source_run_manifest_sha256=grounding._sha(source/"manifest.json"),
                    expected_image_count=50, selection_rule="first_bundle_each_camera_per_init_raw_rgb_only", images=images,
                    rules_version=RULES_VERSION, rules_path="annotation_rules.md",
                    rules_sha256=grounding._sha(directory/"annotation_rules.md"))
    manifest["dataset_id"] = packet_identity(manifest)
    write(directory/"manifest.json", manifest)
    registration = tmp_path/"registration.json"
    grounding.preregister(directory, source, registration)
    annotations = dict(schema=ANNOTATION_SCHEMA, dataset_id=manifest["dataset_id"], annotator_id="unit-test-fixture",
                       annotator_role="project_primary_human", rules_version=RULES_VERSION, rules_sha256=manifest["rules_sha256"],
                       attestations=dict(is_human=True, independent_of_model_outputs=True, raw_rgb_only=True),
                       exported_at_utc=datetime.now(timezone.utc).isoformat(), annotations=[
                           dict(**image_binding(image), entities={entity:dict(status="UNKNOWN", reason="synthetic test", polygons=[],
                                                                            **({"reference_types": []} if entity == "fixed_cabinet_reference" else {}))
                                                                 for entity in ENTITIES}) for image in images])
    annotation_path = tmp_path/"annotations.json"
    write(annotation_path, annotations)
    return directory, source, registration, annotation_path, manifest, annotations


def test_incomplete_human_gate_precedes_model_loader_or_output_directory(packet, tmp_path, monkeypatch):
    directory, _, registration, path, _, labels = packet
    labels["annotations"] = []
    write(path, labels)
    calls = []
    monkeypatch.setattr(grounding, "_load_worker", lambda: calls.append("loaded"))
    with pytest.raises(ProtocolError, match="ANNOTATION_COVERAGE"):
        grounding.run(directory, path, registration, tmp_path/"output")
    assert calls == [] and not (tmp_path/"output").exists()


def test_ai_exposed_export_rejected_before_loading_even_if_all_50_and_attested(packet, tmp_path, monkeypatch):
    directory, _, registration, path, _, labels = packet
    labels["provenance"] = dict(prior_ai_exposure=True, eligible_for_human_blind_evaluation=False)
    write(path, labels)
    calls = []
    monkeypatch.setattr(grounding, "_load_worker", lambda: calls.append("loaded"))
    with pytest.raises(ProtocolError, match="ANNOTATION_BLINDNESS_CONFLICT"):
        grounding.run(directory, path, registration, tmp_path/"output")
    assert calls == [] and not (tmp_path/"output").exists()


def test_registration_before_annotations_and_exact_queries_geometry_are_locked(packet, tmp_path):
    directory, _, registration, path, _, labels = packet
    grounding.validate_gate(directory, path, registration)
    labels["exported_at_utc"] = (datetime.now(timezone.utc)-timedelta(days=1)).isoformat()
    write(path, labels)
    with pytest.raises(ProtocolError, match="ANNOTATION_CHRONOLOGY"):
        grounding.validate_gate(directory, path, registration)
    spec = json.loads(registration.read_text())
    spec["queries"][ENTITIES[0]] = "an easier query"
    spec["registration_sha256"] = content_hash({k:v for k,v in spec.items() if k != "registration_sha256"})
    write(registration, spec)
    with pytest.raises(ProtocolError, match="CONDITION_CHANGED"):
        grounding.validate_gate(directory, path, registration)
    altered = tmp_path/"geometry.json"
    original = json.loads(Path("configs/p1_geometry.json").read_text())
    original["edge_margin_m"] = 0
    write(altered, original)
    with pytest.raises(ProtocolError, match="CONDITION_CHANGED"):
        grounding.frozen_geometry(altered)


def audit(ids=(123, 151645)):
    return generation_audit(list(ids), 20, 16384, 151645)


def test_every_box_preserved_in_order_including_duplicates_without_confidence():
    raw = "<box><100><200><700><800></box><box><200><100><300><400></box><box><100><200><700><800></box>"
    result = grounding.classify_response(raw, audit(), 100, 100)
    assert result["structurally_admitted"]
    assert result["ordered_boxes"] == [[10,20,70,80],[20,10,30,40],[10,20,70,80]]
    assert result["calibrated_confidence"] is None and result["semantic_identity_verified"] is False


@pytest.mark.parametrize("raw,status", [("<box>none</box>", "none"), ("<box><1><2></box>", "single_point"),
                                       ("<box><1><2><3><4></box><box>", "malformed")])
def test_abstentions_and_malformed_outputs_preserved_not_repaired(raw, status):
    result = grounding.classify_response(raw, audit(), 100, 100)
    assert result["parsed"]["status"] == status and not result["structurally_admitted"]


@pytest.mark.parametrize("ids", [[], [123], [123]*256, [123]*256+[151645]])
def test_missing_eos_and_budget_overrun_fail_even_if_box_text_looks_good(ids):
    with pytest.raises(ProtocolError, match="TRUNCATED"):
        grounding.classify_response("<box><0><0><1000><1000></box>", audit(ids), 100, 100)


def frame(shape=(20,20)):
    h, w = shape
    return dict(rgb=np.zeros((h,w,3),np.uint8), depth_m=np.ones((h,w),np.float32),
                intrinsics_K=np.array([[100.,0,w/2],[0,100.,h/2],[0,0,1]]), T_base_camera=np.eye(4),
                canonical_frame_id="ep/camera/1", calibration_version="cal", capture_sim_time_s=0.,
                capture_monotonic_ns=0)


def test_box_geometry_retains_all_boxes_and_subpixel_unknown():
    view = frame()
    result = dict(ordered_boxes=[[0,0,20,20],[1,1,10,10],[1.1,1.1,1.2,1.2]], structurally_admitted=True)
    geometry = grounding.box_geometry(view,{"eef_position_base_m":[0,0,0]},ENTITIES[0],result,grounding.frozen_geometry("configs/p1_geometry.json"))
    assert [r["box_index"] for r in geometry] == [0,1,2]
    assert geometry[2]["structural_reason"] == "NO_INTEGER_PIXEL_ROI_SUPPORT"
    assert all(r["for_execution"] is False for r in geometry)


def test_coverage_unknown_label_and_mask_upper_bound_are_evaluation_only():
    truth=dict(status="VISIBLE",polygons=[[[0,0],[10,0],[10,20],[0,20]]])
    metrics=grounding.coverage_metrics([[0,0,20,20]],truth,20,20)[0]
    assert metrics["annotated_pixel_coverage"]==1 and metrics["bbox_contamination"]==.5
    unknown=grounding.coverage_metrics([[0,0,20,20]],{**truth,"status":"UNKNOWN"},20,20)[0]
    assert unknown["annotated_pixel_coverage"] is None and unknown["bbox_contamination"] is None
    view=frame()
    original=view["depth_m"].copy()
    result=grounding.annotation_upper_bound(view,{"eef_position_base_m":[0,0,0]},ENTITIES[0],truth,
                                          grounding.frozen_geometry("configs/p1_geometry.json"))
    np.testing.assert_array_equal(view["depth_m"],original)
    assert result["for_execution"] is False and result["retained_depth_unchanged"]
    assert result["patch"]["provenance"]=="evaluation_human_mask_and_sensor_depth"
    assert "/evaluation-human-mask/" in result["patch"]["source_frame_id"]


@pytest.mark.parametrize("response", ["<box>none</box>", "<box><0><0><1000><1000></box>"])
def test_all_predictions_sealed_before_label_evaluation_and_only_rgb_query_enter_model(packet,tmp_path,monkeypatch,response):
    directory,_,registration,path,manifest,_=packet
    out=tmp_path/"output"
    frames={image["frame_id"]:({**frame((4,4)),"rgb":np.full((4,4,3),i,np.uint8),"canonical_frame_id":image["frame_id"]},
                               {"eef_position_base_m":[0,0,0]}) for i,image in enumerate(manifest["images"])}
    monkeypatch.setattr(grounding,"_sensor_frames",lambda *args:frames)
    calls=[]
    def load():
        assert (out/"gate.json").exists()
        return object(),{"model_content_id":"unit-test-no-real-model", "execution_allocation":{"fixture":"mocked-no-gpu"}}
    def infer(worker,rgb,query,emit):
        assert isinstance(rgb,np.ndarray) and rgb.shape==(4,4,3)
        assert query in grounding.QUERIES.values()
        assert not (out/"human-evaluation.json").exists()
        calls.append(query)
        emit("model-input",{"rgb_sha256":hashlib.sha256(rgb.tobytes()).hexdigest(),"query":query})
        emit("raw-output",{"response":response})
        return response,audit()
    original=grounding.evaluate_grounding
    def evaluate(*args):
        assert (out/"predictions-sealed.json").exists() and len(calls)==100
        return original(*args)
    monkeypatch.setattr(grounding,"_load_worker",load)
    monkeypatch.setattr(grounding,"infer_audited",infer)
    monkeypatch.setattr(grounding,"evaluate_grounding",evaluate)
    grounding.run(directory,path,registration,out)
    assert len(calls)==100
    completed=json.loads((out/"completed.json").read_text())
    assert completed["model_calls"]==100 and completed["runtime_actions"]==0
    evaluation=json.loads((out/"human-evaluation.json").read_text())
    assert all(v["mean_visible_polygon_iou"] is None for v in evaluation["summary"].values())
    predicted=json.loads((out/"predictions-evaluation-format.json").read_text())
    for row in predicted["records"]:
        ref=row["entities"]["fixed_cabinet_reference"]
        assert ref["reference_types"] == ["UNKNOWN"]*len(ref["polygons"])
    assert (out/"annotations-evaluation-input.json").exists()
    run_manifest=json.loads((out/"run-manifest.json").read_text())
    model_manifest=json.loads((out/"model.json").read_text())
    assert run_manifest["execution_allocation"]==model_manifest["execution_allocation"]=={"fixture":"mocked-no-gpu"}


def test_truncated_first_call_is_counted_and_never_retried(packet,tmp_path,monkeypatch):
    directory,_,registration,path,manifest,_=packet
    out=tmp_path/"output"
    first=manifest["images"][0]
    monkeypatch.setattr(grounding,"_sensor_frames",lambda *args:{first["frame_id"]:(frame((4,4)),{})})
    monkeypatch.setattr(grounding,"_load_worker",lambda:(object(),{"fixture":True}))
    calls=[]
    def truncated(worker,rgb,query,emit):
        calls.append(query)
        emit("raw-output",{"response":"<box><0><0><1000><1000></box>"})
        return "<box><0><0><1000><1000></box>",audit([123]*256)
    monkeypatch.setattr(grounding,"infer_audited",truncated)
    with pytest.raises(ProtocolError,match="TRUNCATED"):
        grounding.run(directory,path,registration,out)
    failure=json.loads((out/"failure.json").read_text())
    assert len(calls)==1 and failure["started_inference_calls"]==1
    assert failure["completed_model_calls"]==0 and failure["retries"]==0
    assert (out/"call-000"/"raw-output.json").exists()
    assert not (out/"predictions-sealed.json").exists()
    assert not (out/"human-evaluation.json").exists()


def test_sensor_source_failure_is_recorded_before_model_loading(packet,tmp_path,monkeypatch):
    directory,_,registration,path,_,_=packet
    out=tmp_path/"output"
    calls=[]
    def invalid_source(*args):
        raise ProtocolError("RECORDING_CORRUPT","synthetic source mismatch")
    monkeypatch.setattr(grounding,"_sensor_frames",invalid_source)
    monkeypatch.setattr(grounding,"_load_worker",lambda:calls.append("loaded"))
    with pytest.raises(ProtocolError,match="RECORDING_CORRUPT"):
        grounding.run(directory,path,registration,out)
    failure=json.loads((out/"failure.json").read_text())
    assert not calls and failure["started_inference_calls"]==0


def test_oversized_native_input_is_saved_before_failing_without_generate():
    class Tensor:
        def __init__(self,value):
            self.value=np.asarray(value)
            self.shape,self.dtype=self.value.shape,self.value.dtype
        def detach(self): return self
        def cpu(self): return self
        def to(self,*args): return self
        def contiguous(self): return self
        def view(self,dtype): return Tensor(self.value.view(dtype))
        def tolist(self): return self.value.tolist()
        def numpy(self): return self.value
    class Inputs(dict):
        def to(self,*args): return self
    class Processor:
        def py_apply_chat_template(self,*args,**kwargs): return "fixed prompt"
        def process_vision_info(self,*args): return [object()],None
        def __call__(self,**kwargs):
            assert kwargs["truncation"] is False
            return Inputs(input_ids=Tensor([[1]*80]),attention_mask=Tensor([[1]*80]),pixel_values=Tensor(np.ones((1,3,2,2))))
    worker=SimpleNamespace(processor=Processor(),device="cpu",dtype="fixture",torch=SimpleNamespace(uint8=np.uint8),
                           tokenizer=SimpleNamespace(model_max_length=100))
    evidence={}
    with pytest.raises(ProtocolError,match="TRUNCATED"):
        grounding.infer_audited(worker,np.zeros((4,4,3),np.uint8),grounding.QUERIES[ENTITIES[0]],evidence.__setitem__)
    assert evidence["model-input"]["input_token_count"]==80
    assert evidence["model-input"]["reserved_generation_tokens"]==256
    assert evidence["model-input"]["processor_truncation"] is False


@pytest.mark.parametrize("mask", [None, "", "0,1", "2,", "-1", "all", " 2 "])
def test_real_loader_requires_single_gpu_mask_before_hashing_or_model_loading(monkeypatch,mask):
    from embodied_runtime.experiments import records
    if mask is None:
        monkeypatch.delenv("CUDA_VISIBLE_DEVICES",raising=False)
    else:
        monkeypatch.setenv("CUDA_VISIBLE_DEVICES",mask)
    hashes=[]
    monkeypatch.setattr(records,"model_identity",lambda *args:hashes.append("hash"))
    with pytest.raises(ProtocolError,match="GPU_ALLOCATION_REQUIRED"):
        grounding._load_worker()
    assert hashes==[]


def fake_cuda(*,count=1,initialized=False):
    properties=SimpleNamespace(name="mocked GPU",total_memory=24*1024**3,major=8,minor=9,uuid="mocked-uuid")
    return SimpleNamespace(is_initialized=lambda:initialized,is_available=lambda:True,device_count=lambda:count,
                           get_device_properties=lambda index:properties,current_device=lambda:0)


@pytest.mark.parametrize("count,initialized", [(0,False),(2,False),(1,True)])
def test_single_mask_is_checked_against_fresh_actual_cuda_visibility(monkeypatch,count,initialized):
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES","2")
    with pytest.raises(ProtocolError,match="GPU_ALLOCATION"):
        grounding._cuda_allocation(SimpleNamespace(cuda=fake_cuda(count=count,initialized=initialized)),"2")


def test_real_loader_records_mask_and_device_identity_with_mocked_torch_worker(monkeypatch):
    from embodied_runtime.adapters import locateanything
    from embodied_runtime.experiments import records
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES","2")
    monkeypatch.setattr(records,"model_identity",lambda *args:{"content_id":grounding.MODEL_CONTENT_ID})
    monkeypatch.setitem(sys.modules,"torch",SimpleNamespace(cuda=fake_cuda()))
    loaded=[]
    def worker(path,**kwargs):
        loaded.append((path,kwargs))
        return "mocked-worker"
    monkeypatch.setattr(locateanything,"LocateAnythingWorker",worker)
    result,identity=grounding._load_worker()
    assert result=="mocked-worker"
    assert loaded==[(grounding.MODEL_PATH,{"device":"cuda","model_revision":grounding.MODEL_CONTENT_ID})]
    allocation=identity["execution_allocation"]
    assert allocation["cuda_visible_devices"]=="2" and allocation["logical_device"]=="cuda:0"
    assert allocation["name"]=="mocked GPU" and allocation["uuid"]=="mocked-uuid"
    assert allocation["pci_bus_id"] is None


def test_offline_visible_reference_box_can_have_unknown_subtype_without_claiming_fixed_identity(packet):
    _,_,_,_,manifest,annotations=packet
    reference=annotations["annotations"][0]["entities"]["fixed_cabinet_reference"]
    reference.update(status="VISIBLE",polygons=[[[0,0],[4,0],[4,4],[0,4]]],reference_types=["FRONT_FRAME"])
    records=json.loads(json.dumps(annotations["annotations"]))
    for row in records:
        for entity in row["entities"].values():
            entity["points"]=[]
    records[0]["entities"]["fixed_cabinet_reference"]["reference_types"]=["UNKNOWN"]
    predictions=dict(schema=grounding.PREDICTION_SCHEMA,dataset_id=manifest["dataset_id"],producer_id="synthetic-model",
                     revision="test-only-no-inference",records=records)
    evaluation=grounding.evaluate_grounding(predictions,annotations,manifest)
    matched=[row for row in evaluation["records"] if row["image_id"]==manifest["images"][0]["image_id"]
             and row["entity"]=="fixed_cabinet_reference"][0]
    assert matched["polygon_iou_on_visible_label"]==1
    assert matched["annotated_reference_types"]==["FRONT_FRAME"]
    assert matched["predicted_reference_types"]==["UNKNOWN"]
    assert evaluation["labels_prove_static_reference"] is False
    result=grounding.classify_response("<box><0><0><1000><1000></box>",audit(),4,4)
    assert result["semantic_identity_verified"] is False
