# Stored own-state report review

PASS for the report introduced by `d4a97fa8d4dc92ca72091ec708702da32683632e` and its narrow interface finding in `add594ea52536ad0d77fb90649aa61eddaf91afa`.

Independently checked all 68 exported rows against the four sealed sensor manifests: preclose plus all sixteen suffix control endpoints per cell. Every raw joint position/velocity, TCP, capture ID, phase, step/control, read time, unknown sample time and own-source linkage agrees. All 68 joint-coordinate differences and velocity differences agree with independent scalar arithmetic. The four manifest/seal hashes and generator hash agree. No generator rerun, image, evaluator, simulator, FK, projection or model call was used.

At the first-GRASP read boundary, whole-close signed joint separation/rate are 21.848372001622124 mm and −197.32167422894818 mm/s; neck-close values are 21.856380557262057 mm and −197.075016878135 mm/s. All displayed close/open-hold and lift endpoint numbers round correctly. Endpoint read times are 0.4000000000001336 and 0.8000000000002672 s after preclose; exact observation sample times remain unknown.

Source review confirms the interface statement: `LiberoBackend.proprioception` returns TCP, signed joint positions, arithmetic width, retained command and unknown holding, with no jaw velocity. `project_belief` projects TCP, width and command; the canonical state schema contains no jaw velocity. The allowed single recent-outcome schema admits action, TCP delta, elapsed simulation time, retained jaw command and provenance, with no jaw velocity. This establishes the stated omission in these existing paths, with no claim that every possible custom model input omits it or that adding it improves decisions.

Joint separation remains arithmetic, not pad clearance/object width/contact. Archived qvel supports the moving-jaw description at the saved own-observation boundary, without establishing exact continuous timing, contact absence, causality or holding. No threshold, production interface change or altered physical schedule is introduced.

Reviewed artifact SHA-256 identities:

- Summary: `ad9d72f786ebff8b779d06e091b3445896037e32258c2a40559e629c50bec0cb`.
- Findings: `b01b89cec61666c62d07408dea5db3059c64373b3111b83292b59963ad33411e`.
- Generator: `582d1b24c3a88f8931aa7b951a8ac18d85b7019b062815efebd488fcb3ce5fdd`.
- Libero adapter: `f6988f2d72d63b8832e7323a583397eb41b5a3bc8cb6cc380ac420cf0833454f`.
- Decision interface: `92c87afe4b28e90bc50ec25293bb09ca6a93c8d52b598ae465e36d4d54f4c917`.
