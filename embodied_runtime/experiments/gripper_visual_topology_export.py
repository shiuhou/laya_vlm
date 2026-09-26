"""Compile only static own visual assets; exact-gate topology against calibration."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np

from .records import code_identity, file_hash

CALIBRATION_SHA256 = "c86706370d8442f85365d1e1d7e962ffb0f2346c235d968146694ed6e3fb4c98"
ASSET_HASHES = {
    "panda_gripper.xml": "d9d68123909d6910488310d0fae4e358ed4ac831c6d0957f3e30893a5412baac",
    "meshes/panda_gripper/hand_vis.stl": "fdeb1a924b8d0f1f997f47d6d8af102c7290a1d5144145efdc39501dc13f0fa1",
    "meshes/panda_gripper/finger_vis.stl": "e49613148a74f1ba9b5793813078e5becf15833e0296073dc1c523508be35ae4",
}


def run(asset_root, calibration_path, output):
    import mujoco

    asset_root, calibration_path, output = map(Path, (asset_root, calibration_path, output))
    identity = code_identity()
    if identity["dirty_status"] or file_hash(calibration_path) != CALIBRATION_SHA256:
        raise RuntimeError("Frozen code and exact visual calibration required")
    for name, expected in ASSET_HASHES.items():
        if file_hash(asset_root / name) != expected:
            raise RuntimeError("Own visual source asset mismatch: " + name)
    calibration = json.loads(calibration_path.read_text())
    source = ET.parse(asset_root / "panda_gripper.xml").getroot()
    root = ET.Element("mujoco", model="own_visual_topology_only")
    assets, world = ET.SubElement(root, "asset"), ET.SubElement(root, "worldbody")
    used_meshes = set()
    for geometry in calibration["geometries"]:
        source_name = geometry["name"].removeprefix("gripper0_")
        geom = next(node for node in source.iter("geom") if node.get("name") == source_name)
        if geom.get("group") != "1" or geom.get("contype") != "0" or geom.get("conaffinity") != "0":
            raise RuntimeError("Only noncolliding own visual geoms admitted")
        mesh_name = geom.get("mesh")
        if mesh_name not in used_meshes:
            mesh = next(node for node in source.find("asset").iter("mesh") if node.get("name") == mesh_name)
            attributes = dict(mesh.attrib)
            if attributes["file"] not in ASSET_HASHES:
                raise RuntimeError("Unregistered visual mesh asset")
            attributes["file"] = str(asset_root / attributes["file"])
            ET.SubElement(assets, "mesh", attributes)
            used_meshes.add(mesh_name)
        body = ET.SubElement(world, "body", name=geometry["body"])
        ET.SubElement(body, "geom", {**geom.attrib, "name": geometry["name"]})
    xml = ET.tostring(root, encoding="unicode")
    output.mkdir(parents=True, exist_ok=False)
    (output / "own-visual-only.xml").write_text(xml + "\n")
    # Model compilation only: no MjData, joint state, camera, renderer or scene.
    model = mujoco.MjModel.from_xml_string(xml)
    if model.ngeom != 3 or model.nmesh != 2 or model.njnt or model.nq or model.nv or model.ncam:
        raise RuntimeError("Static own-mesh-only model schema changed")
    topology, checks = {}, []
    for geometry in calibration["geometries"]:
        geom = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, geometry["name"])
        mesh = int(model.geom_dataid[geom])
        start, count = int(model.mesh_vertadr[mesh]), int(model.mesh_vertnum[mesh])
        vertices = np.asarray(model.mesh_vert[start:start + count], dtype=float)
        for label, actual, expected in (
                ("vertices", vertices, geometry["vertices_local_m"]),
                ("local_position", model.geom_pos[geom], geometry["position_body_m"]),
                ("local_quaternion", model.geom_quat[geom], geometry["quaternion_body_wxyz"])):
            if not np.array_equal(actual, expected):
                raise RuntimeError("Exact compiled calibration mismatch: " + geometry["name"] + "/" + label)
            checks.append(geometry["name"] + "/" + label)
        first, total = int(model.mesh_faceadr[mesh]), int(model.mesh_facenum[mesh])
        faces = np.asarray(model.mesh_face[first:first + total], dtype=np.int64)
        if faces.shape != (total, 3) or (faces < 0).any() or (faces >= count).any():
            raise RuntimeError("Compiled face indices outside exact vertex array")
        topology[geometry["name"]] = faces.tolist()
    result = {"parent_visual_calibration_sha256": CALIBRATION_SHA256, "triangle_faces": topology}
    def write(name, value):
        with (output / name).open("x") as stream:
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.write("\n")
    write("triangle-topology.json", result)
    write("audit.json", {"code": identity, "mujoco_version": mujoco.__version__, "source_asset_hashes": ASSET_HASHES,
          "exact_calibration_checks": checks, "ngeom": model.ngeom, "nmesh": model.nmesh,
          "joint_data_scene_or_render_created": False, "simulation_steps_or_forward_calls": 0,
          "topology_sha256": file_hash(output / "triangle-topology.json")})
    write("artifacts.json", {path.name: file_hash(path) for path in sorted(output.iterdir()) if path.is_file()})
    print(json.dumps({"status": "sealed", "topology_sha256": file_hash(output / "triangle-topology.json")}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset-root", default="/home/junhongli/miniforge3/envs/locateanything/lib/python3.10/site-packages/robosuite/models/assets/grippers")
    parser.add_argument("--calibration", default="/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/gripper-visual-calibration-01/gripper-visual-calibration.json")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    run(args.asset_root, args.calibration, args.output)
