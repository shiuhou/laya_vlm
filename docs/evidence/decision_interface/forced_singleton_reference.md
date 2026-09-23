# Forced-singleton continuation in Privileged Drawer Reference v1

Current authority: [current_state.md](../../current_state.md). This record continues the [original Jev two-step witness audit](two_step_lookahead.md). It changes only the treatment of a one-candidate contract pool and records the first fresh closed-loop run.

## Original Jev singleton behavior

Original Jev commit `3bdad985b225aeccc39fbe5863c6eea2e81c515a` has no singleton branch in `ValidatedPolicy.choose()`. Once contracts, intent and strategy determine a motor pool, it always calls `api.choose()`, even when that pool contains one primitive. `Decisions.choose()` always sends and logs that request. The archived successful top-drawer run contains four one-option model calls: step 0 intent `approach_target`, step 5 motor `z-40mm`, step 12 motor `y-3mm`, and step 14 intent `advance_target`. They are recorded as ordinary model answers; original Jev neither executes them outside the model nor labels them forced continuations.

Because the original implementation does not define an explicit attribution rule, the human-specified minimal reference rule was used: zero candidates invoke existing two-step witness processing; one candidate executes once as a deterministic forced continuation; two or more physically distinct candidates call Laya. A forced continuation records `forced_singleton=true`, `model_called=false`, an empty probability map and zero model confidence. It is never counted as model competence. No stored witness action is executed.

## Implementation boundary

The candidate builder and existing contracts are unchanged except that a non-empty singleton is allowed to reach the reference provider. The provider intercepts it before serialization or Laya. Every boundary retains the complete oracle preview, contract pools, rejected actions, candidate provenance and real outcome. Multi-option state text and the fixed instruction are unchanged. Commit: `8075713793f6efcb99c4d9e573f9e430d29d0904`.

Pre-run verification: **421 pytest tests passed**, ruff passed, compileall passed and `git diff --check` passed. The run started from that clean commit.

## Fresh episode result

Run `forced-singleton-episode-01`, benchmark init 0 / seed 1, used the unchanged local Laya checkpoint on CUDA/bfloat16. It executed 92 primitives before failing closed at boundary 92:

- genuine Laya decisions: **86**;
- deterministic forced-singleton continuations: **6**;
- executed zero-pool lookahead recoveries: **2** (steps 18 and 64);
- total zero-pool lookahead invocations: **3**, including the unexecuted terminal boundary;
- low-level controls: **736**;
- opening: `151.659012956 -> 136.486425914 mm`, or `15.172587041 mm` net closure;
- official environment success: **false**;
- every selected prediction matched real execution exactly;
- control replay: **829 boundaries**, maximum error `0`.

The six forced continuations were steps 19 `z-3mm`, 45 `rotate_x+10deg`, 65 `rotate_x+10deg`, 72 `rotate_x-10deg`, 82 `rotate_x-10deg`, and 91 `z-3mm`. No Laya call or fabricated probability was recorded at those steps.

## Complete executed trace

Effects are `closure mm / gap reduction mm / target contact / obstacle peak N / success`. Opening, gap and contact are independently measured after execution.

| Step | Candidates | Pool | Choice | Primitive | Predicted effect | Actual effect | Opening mm | Gap mm | Contact | Success |
|---:|---:|---|---|---|---|---|---:|---:|---|---|
| 0 | 7 | one_step | Laya | `x+3mm` | 0.000000 / 2.422937 / false / 0.000 / false | 0.000000 / 2.422937 / false / 0.000 / false | 151.659013 | 91.061468 | false | false |
| 1 | 7 | one_step | Laya | `x+3mm` | 0.000000 / 2.361356 / false / 0.000 / false | 0.000000 / 2.361356 / false / 0.000 / false | 151.659013 | 88.700113 | false | false |
| 2 | 7 | one_step | Laya | `x+3mm` | 0.000000 / 2.327704 / false / 0.000 / false | 0.000000 / 2.327704 / false / 0.000 / false | 151.659013 | 86.372408 | false | false |
| 3 | 7 | one_step | Laya | `x+3mm` | 0.000000 / 2.294475 / false / 0.000 / false | 0.000000 / 2.294475 / false / 0.000 / false | 151.659013 | 84.077934 | false | false |
| 4 | 7 | one_step | Laya | `x+3mm` | 0.000000 / 2.264828 / false / 0.000 / false | 0.000000 / 2.264828 / false / 0.000 / false | 151.659013 | 81.813105 | false | false |
| 5 | 7 | one_step | Laya | `x+3mm` | 0.000000 / 2.234256 / false / 0.000 / false | 0.000000 / 2.234256 / false / 0.000 / false | 151.659013 | 79.578849 | false | false |
| 6 | 7 | one_step | Laya | `x+3mm` | 0.000000 / 2.202249 / false / 0.000 / false | 0.000000 / 2.202249 / false / 0.000 / false | 151.659013 | 77.376601 | false | false |
| 7 | 7 | one_step | Laya | `x+3mm` | 0.000000 / 2.168427 / false / 0.000 / false | 0.000000 / 2.168427 / false / 0.000 / false | 151.659013 | 75.208173 | false | false |
| 8 | 7 | one_step | Laya | `x+3mm` | 0.000000 / 2.132341 / false / 0.000 / false | 0.000000 / 2.132341 / false / 0.000 / false | 151.659013 | 73.075832 | false | false |
| 9 | 7 | one_step | Laya | `x+3mm` | 0.000000 / 2.093566 / false / 0.000 / false | 0.000000 / 2.093566 / false / 0.000 / false | 151.659013 | 70.982266 | false | false |
| 10 | 7 | one_step | Laya | `x+10mm` | 0.000000 / 6.664731 / false / 0.000 / false | 0.000000 / 6.664731 / false / 0.000 / false | 151.659013 | 64.317535 | false | false |
| 11 | 7 | one_step | Laya | `x+10mm` | 0.000000 / 6.108374 / false / 0.000 / false | 0.000000 / 6.108374 / false / 0.000 / false | 151.659013 | 58.209161 | false | false |
| 12 | 7 | one_step | Laya | `x+40mm` | 0.000000 / 12.833122 / false / 0.000 / false | 0.000000 / 12.833122 / false / 0.000 / false | 151.659013 | 45.376039 | false | false |
| 13 | 3 | one_step | Laya | `rotate_x+10deg` | 0.000000 / 7.260748 / false / 0.000 / false | 0.000000 / 7.260748 / false / 0.000 / false | 151.659013 | 38.115292 | false | false |
| 14 | 6 | one_step | Laya | `rotate_x+10deg` | 0.000000 / 9.216930 / false / 0.000 / false | 0.000000 / 9.216930 / false / 0.000 / false | 151.659013 | 28.898362 | false | false |
| 15 | 5 | one_step | Laya | `rotate_x+10deg` | 0.000000 / 6.093271 / false / 0.000 / false | 0.000000 / 6.093271 / false / 0.000 / false | 151.659013 | 22.805091 | false | false |
| 16 | 6 | one_step | Laya | `rotate_x+10deg` | 0.000000 / 4.405707 / false / 0.000 / false | 0.000000 / 4.405707 / false / 0.000 / false | 151.659013 | 18.399384 | false | false |
| 17 | 7 | one_step | Laya | `rotate_x+10deg` | 0.000000 / 15.667060 / false / 0.000 / false | 0.000000 / 15.667060 / false / 0.000 / false | 151.659013 | 2.732324 | false | false |
| 18 | 23 | lookahead | Laya | `open` | 0.000000 / 1.225532 / false / 0.000 / false | 0.000000 / 1.225532 / false / 0.000 / false | 151.659013 | 1.506793 | false | false |
| 19 | 1 | one_step | forced singleton | `z-3mm` | 0.060077 / 1.506793 / true / 0.000 / false | 0.060077 / 1.506793 / true / 0.000 / false | 151.598936 | 0.000000 | true | false |
| 20 | 23 | one_step | Laya | `open` | 0.006108 / -0.005475 / false / 0.000 / false | 0.006108 / -0.005475 / false / 0.000 / false | 151.592828 | 0.005475 | false | false |
| 21 | 5 | one_step | Laya | `x-40mm` | 0.039478 / -20.183613 / false / 0.000 / false | 0.039478 / -20.183613 / false / 0.000 / false | 151.553350 | 20.189089 | false | false |
| 22 | 5 | one_step | Laya | `x+40mm` | 0.271311 / 19.790641 / false / 0.000 / false | 0.271311 / 19.790641 / false / 0.000 / false | 151.282038 | 0.398448 | false | false |
| 23 | 19 | one_step | Laya | `open` | 0.352541 / 0.397918 / false / 0.000 / false | 0.352541 / 0.397918 / false / 0.000 / false | 150.929497 | 0.000530 | false | false |
| 24 | 3 | one_step | Laya | `y-40mm` | 0.259586 / -0.132593 / false / 0.000 / false | 0.259586 / -0.132593 / false / 0.000 / false | 150.669911 | 0.133123 | false | false |
| 25 | 14 | one_step | Laya | `open` | 0.628754 / 0.132407 / false / 0.000 / false | 0.628754 / 0.132407 / false / 0.000 / false | 150.041158 | 0.000716 | false | false |
| 26 | 2 | one_step | Laya | `z-3mm` | 0.172887 / 0.000716 / true / 0.000 / false | 0.172887 / 0.000716 / true / 0.000 / false | 149.868270 | 0.000000 | true | false |
| 27 | 23 | one_step | Laya | `hold` | -0.066682 / 0.000000 / false / 0.000 / false | -0.066682 / 0.000000 / false / 0.000 / false | 149.934952 | 0.000000 | false | false |
| 28 | 9 | one_step | Laya | `x+3mm` | 0.045439 / -0.000518 / false / 0.000 / false | 0.045439 / -0.000518 / false / 0.000 / false | 149.889513 | 0.000518 | false | false |
| 29 | 13 | one_step | Laya | `z+40mm` | 0.030694 / -38.649549 / false / 0.000 / false | 0.030694 / -38.649549 / false / 0.000 / false | 149.858819 | 38.650067 | false | false |
| 30 | 4 | one_step | Laya | `z-40mm` | 0.052420 / 38.650067 / true / 0.000 / false | 0.052420 / 38.650067 / true / 0.000 / false | 149.806399 | 0.000000 | true | false |
| 31 | 24 | one_step | Laya | `open` | 0.156488 / 0.000000 / false / 0.000 / false | 0.156488 / 0.000000 / false / 0.000 / false | 149.649911 | 0.000000 | false | false |
| 32 | 10 | one_step | Laya | `hold` | 0.070174 / 0.000000 / false / 0.000 / false | 0.070174 / 0.000000 / false / 0.000 / false | 149.579737 | 0.000000 | false | false |
| 33 | 13 | one_step | Laya | `open` | 0.059020 / 0.000000 / false / 0.000 / false | 0.059020 / 0.000000 / false / 0.000 / false | 149.520717 | 0.000000 | false | false |
| 34 | 13 | one_step | Laya | `hold` | 0.050329 / 0.000000 / false / 0.000 / false | 0.050329 / 0.000000 / false / 0.000 / false | 149.470387 | 0.000000 | false | false |
| 35 | 8 | one_step | Laya | `hold` | 0.042019 / -0.000002 / false / 0.000 / false | 0.042019 / -0.000002 / false / 0.000 / false | 149.428368 | 0.000002 | false | false |
| 36 | 13 | one_step | Laya | `open` | 0.034790 / 0.000002 / false / 0.000 / false | 0.034790 / 0.000002 / false / 0.000 / false | 149.393579 | 0.000000 | false | false |
| 37 | 13 | one_step | Laya | `open` | 0.028918 / 0.000000 / false / 0.000 / false | 0.028918 / 0.000000 / false / 0.000 / false | 149.364660 | 0.000000 | false | false |
| 38 | 13 | one_step | Laya | `open` | 0.023965 / -0.000000 / false / 0.000 / false | 0.023965 / -0.000000 / false / 0.000 / false | 149.340695 | 0.000000 | false | false |
| 39 | 13 | one_step | Laya | `open` | 0.019851 / 0.000000 / false / 0.000 / false | 0.019851 / 0.000000 / false / 0.000 / false | 149.320845 | 0.000000 | false | false |
| 40 | 13 | one_step | Laya | `open` | 0.016505 / 0.000000 / false / 0.000 / false | 0.016505 / 0.000000 / false / 0.000 / false | 149.304339 | 0.000000 | false | false |
| 41 | 8 | one_step | Laya | `open` | 0.013942 / 0.000000 / false / 0.000 / false | 0.013942 / 0.000000 / false / 0.000 / false | 149.290397 | 0.000000 | false | false |
| 42 | 8 | one_step | Laya | `open` | 0.012019 / 0.000000 / false / 0.000 / false | 0.012019 / 0.000000 / false / 0.000 / false | 149.278378 | 0.000000 | false | false |
| 43 | 13 | one_step | Laya | `open` | 0.010575 / -0.000001 / false / 0.000 / false | 0.010575 / -0.000001 / false / 0.000 / false | 149.267803 | 0.000001 | false | false |
| 44 | 10 | one_step | Laya | `x+40mm` | 0.036038 / -1.183865 / false / 0.000 / false | 0.036038 / -1.183865 / false / 0.000 / false | 149.231766 | 1.183865 | false | false |
| 45 | 1 | one_step | forced singleton | `rotate_x+10deg` | 0.057743 / 1.183865 / true / 0.000 / false | 0.057743 / 1.183865 / true / 0.000 / false | 149.174023 | 0.000000 | true | false |
| 46 | 22 | one_step | Laya | `open` | 1.055914 / 0.000000 / true / 0.000 / false | 1.055914 / 0.000000 / true / 0.000 / false | 148.118108 | 0.000000 | true | false |
| 47 | 21 | one_step | Laya | `hold` | 0.404331 / 0.000000 / true / 0.000 / false | 0.404331 / 0.000000 / true / 0.000 / false | 147.713777 | 0.000000 | true | false |
| 48 | 23 | one_step | Laya | `hold` | 0.304003 / 0.000000 / false / 0.000 / false | 0.304003 / 0.000000 / false / 0.000 / false | 147.409775 | 0.000000 | false | false |
| 49 | 12 | one_step | Laya | `hold` | 0.233512 / 0.000000 / false / 0.000 / false | 0.233512 / 0.000000 / false / 0.000 / false | 147.176262 | 0.000000 | false | false |
| 50 | 12 | one_step | Laya | `hold` | 0.170652 / 0.000000 / false / 0.000 / false | 0.170652 / 0.000000 / false / 0.000 / false | 147.005611 | 0.000000 | false | false |
| 51 | 11 | one_step | Laya | `hold` | 0.083200 / 0.000000 / false / 0.000 / false | 0.083200 / 0.000000 / false / 0.000 / false | 146.922411 | 0.000000 | false | false |
| 52 | 6 | one_step | Laya | `open` | 0.055048 / 0.000000 / false / 0.000 / false | 0.055048 / 0.000000 / false / 0.000 / false | 146.867362 | 0.000000 | false | false |
| 53 | 4 | one_step | Laya | `hold` | 0.038946 / -0.000002 / false / 0.000 / false | 0.038946 / -0.000002 / false / 0.000 / false | 146.828416 | 0.000002 | false | false |
| 54 | 6 | one_step | Laya | `open` | 0.031034 / 0.000002 / false / 0.000 / false | 0.031034 / 0.000002 / false / 0.000 / false | 146.797382 | 0.000000 | false | false |
| 55 | 6 | one_step | Laya | `hold` | 0.025142 / 0.000000 / false / 0.000 / false | 0.025142 / 0.000000 / false / 0.000 / false | 146.772240 | 0.000000 | false | false |
| 56 | 6 | one_step | Laya | `open` | 0.020824 / 0.000000 / false / 0.000 / false | 0.020824 / 0.000000 / false / 0.000 / false | 146.751416 | 0.000000 | false | false |
| 57 | 6 | one_step | Laya | `open` | 0.017495 / 0.000000 / false / 0.000 / false | 0.017495 / 0.000000 / false / 0.000 / false | 146.733921 | 0.000000 | false | false |
| 58 | 6 | one_step | Laya | `open` | 0.014995 / 0.000000 / false / 0.000 / false | 0.014995 / 0.000000 / false / 0.000 / false | 146.718925 | 0.000000 | false | false |
| 59 | 6 | one_step | Laya | `open` | 0.013136 / 0.000000 / false / 0.000 / false | 0.013136 / 0.000000 / false / 0.000 / false | 146.705790 | 0.000000 | false | false |
| 60 | 6 | one_step | Laya | `open` | 0.011645 / 0.000000 / false / 0.000 / false | 0.011645 / 0.000000 / false / 0.000 / false | 146.694145 | 0.000000 | false | false |
| 61 | 6 | one_step | Laya | `hold` | 0.010459 / 0.000000 / false / 0.000 / false | 0.010459 / 0.000000 / false / 0.000 / false | 146.683686 | 0.000000 | false | false |
| 62 | 4 | one_step | Laya | `rotate_x-10deg` | 0.966753 / -7.033327 / false / 0.000 / false | 0.966753 / -7.033327 / false / 0.000 / false | 145.716933 | 7.033327 | false | false |
| 63 | 3 | one_step | Laya | `rotate_z+10deg` | 0.001669 / 2.212090 / false / 0.000 / false | 0.001669 / 2.212090 / false / 0.000 / false | 145.715264 | 4.821237 | false | false |
| 64 | 18 | lookahead | Laya | `open` | 0.000002 / -0.854712 / false / 0.000 / false | 0.000002 / -0.854712 / false / 0.000 / false | 145.715261 | 5.675949 | false | false |
| 65 | 1 | one_step | forced singleton | `rotate_x+10deg` | -0.004282 / 5.675949 / true / 0.000 / false | -0.004282 / 5.675949 / true / 0.000 / false | 145.719543 | 0.000000 | true | false |
| 66 | 23 | one_step | Laya | `open` | -0.123831 / 0.000000 / false / 0.000 / false | -0.123831 / 0.000000 / false / 0.000 / false | 145.843374 | 0.000000 | false | false |
| 67 | 3 | one_step | Laya | `rotate_x-10deg` | 1.870465 / -5.197210 / false / 0.000 / false | 1.870465 / -5.197210 / false / 0.000 / false | 143.972910 | 5.197210 | false | false |
| 68 | 2 | one_step | Laya | `rotate_x+10deg` | 0.131536 / 5.181189 / false / 0.000 / false | 0.131536 / 5.181189 / false / 0.000 / false | 143.841374 | 0.016021 | false | false |
| 69 | 15 | one_step | Laya | `open` | 0.361524 / 0.016021 / true / 0.000 / false | 0.361524 / 0.016021 / true / 0.000 / false | 143.479850 | 0.000000 | true | false |
| 70 | 22 | one_step | Laya | `hold` | 0.219665 / 0.000000 / true / 0.000 / false | 0.219665 / 0.000000 / true / 0.000 / false | 143.260184 | 0.000000 | true | false |
| 71 | 24 | one_step | Laya | `open` | -0.050973 / -0.017949 / false / 0.000 / false | -0.050973 / -0.017949 / false / 0.000 / false | 143.311157 | 0.017949 | false | false |
| 72 | 1 | one_step | forced singleton | `rotate_x-10deg` | 1.966667 / -4.597348 / false / 0.000 / false | 1.966667 / -4.597348 / false / 0.000 / false | 141.344490 | 4.615297 | false | false |
| 73 | 2 | one_step | Laya | `rotate_x+10deg` | 0.004911 / 4.015182 / false / 0.000 / false | 0.004911 / 4.015182 / false / 0.000 / false | 141.339580 | 0.600115 | false | false |
| 74 | 10 | one_step | Laya | `hold` | 0.138415 / 0.597247 / false / 0.000 / false | 0.138415 / 0.597247 / false / 0.000 / false | 141.201165 | 0.002868 | false | false |
| 75 | 10 | one_step | Laya | `hold` | 0.293920 / -0.001340 / false / 0.000 / false | 0.293920 / -0.001340 / false / 0.000 / false | 140.907245 | 0.004208 | false | false |
| 76 | 4 | one_step | Laya | `y-3mm` | 1.012571 / 0.004208 / false / 0.000 / false | 1.012571 / 0.004208 / false / 0.000 / false | 139.894673 | 0.000000 | false | false |
| 77 | 19 | one_step | Laya | `open` | 0.113917 / -0.032564 / false / 0.000 / false | 0.113917 / -0.032564 / false / 0.000 / false | 139.780756 | 0.032564 | false | false |
| 78 | 5 | one_step | Laya | `x+3mm` | 0.011907 / 0.030402 / false / 0.000 / false | 0.011907 / 0.030402 / false / 0.000 / false | 139.768849 | 0.002161 | false | false |
| 79 | 14 | one_step | Laya | `x+40mm` | 0.016573 / -0.401206 / false / 0.000 / false | 0.016573 / -0.401206 / false / 0.000 / false | 139.752276 | 0.403367 | false | false |
| 80 | 13 | one_step | Laya | `open` | 0.250363 / 0.403367 / true / 0.000 / false | 0.250363 / 0.403367 / true / 0.000 / false | 139.501913 | 0.000000 | true | false |
| 81 | 24 | one_step | Laya | `hold` | 0.091963 / -0.153007 / false / 0.000 / false | 0.091963 / -0.153007 / false / 0.000 / false | 139.409950 | 0.153007 | false | false |
| 82 | 1 | one_step | forced singleton | `rotate_x-10deg` | 1.603593 / -4.307417 / false / 0.000 / false | 1.603593 / -4.307417 / false / 0.000 / false | 137.806357 | 4.460424 | false | false |
| 83 | 2 | one_step | Laya | `rotate_x+10deg` | 0.003795 / 3.800058 / false / 0.000 / false | 0.003795 / 3.800058 / false / 0.000 / false | 137.802562 | 0.660367 | false | false |
| 84 | 9 | one_step | Laya | `hold` | 0.035514 / 0.643561 / false / 0.000 / false | 0.035514 / 0.643561 / false / 0.000 / false | 137.767049 | 0.016806 | false | false |
| 85 | 10 | one_step | Laya | `hold` | 0.376805 / 0.005632 / false / 0.000 / false | 0.376805 / 0.005632 / false / 0.000 / false | 137.390244 | 0.011174 | false | false |
| 86 | 4 | one_step | Laya | `y-40mm` | 0.902181 / -15.692310 / false / 0.000 / false | 0.902181 / -15.692310 / false / 0.000 / false | 136.488063 | 15.703484 | false | false |
| 87 | 3 | one_step | Laya | `x+40mm` | 0.001635 / 2.596298 / false / 0.000 / false | 0.001635 / 2.596298 / false / 0.000 / false | 136.486428 | 13.107186 | false | false |
| 88 | 2 | one_step | Laya | `y+10mm` | 0.000002 / 4.969044 / false / 0.000 / false | 0.000002 / 4.969044 / false / 0.000 / false | 136.486426 | 8.138143 | false | false |
| 89 | 6 | one_step | Laya | `rotate_y+10deg` | 0.000000 / 2.459040 / false / 0.000 / false | 0.000000 / 2.459040 / false / 0.000 / false | 136.486426 | 5.679102 | false | false |
| 90 | 5 | one_step | Laya | `rotate_z+10deg` | 0.000000 / 3.072941 / false / 0.000 / false | 0.000000 / 3.072941 / false / 0.000 / false | 136.486426 | 2.606161 | false | false |
| 91 | 1 | one_step | forced singleton | `z-3mm` | 0.000000 / 2.356911 / false / 0.000 / false | 0.000000 / 2.356911 / false / 0.000 / false | 136.486426 | 0.249249 | false | false |

## First new failure

At boundary 92, after the forced step-91 `z-3mm`, the independently measured state was:

- opening: `136.486425914187635 mm`;
- surface gap: `0.249249448865060 mm`;
- target / obstacle contact: `false / false`;
- finger gap: `78.076802286629274 mm`;
- context SHA-256: `e8954157cd533685bc403abf5af751082fddd1cecb1b65983a942d6ccaeb1622`;
- one-step contract pools: empty;
- original two-step witnesses: empty;
- evaluated second branches: `702`;
- Laya calls and executed actions at this boundary: `0`.

All primitives except `y-40mm` were rejected because no existing one- or two-step witnessed goal effect satisfied the configured contracts. `y-40mm` was rejected because its forecast introduced non-target contact at sampled controls. Preview processing restored the exact simulator/controller context.

This is classified as **ZERO-POOL AFTER EXISTING LOOKAHEAD**: a local contract/lookahead dead end on the trajectory produced by the reference. It is not a singleton integration bug, a model-call failure or an executor mismatch. This run alone does not distinguish an inherent coverage limit of the two-step mechanism from a trajectory regime that the original Jev hierarchy would avoid. No new contract or policy repair was introduced.

Because the first fresh episode did not satisfy the official predicate, no repeat-success episodes were started.

## Artifact identity

- `runs/privileged-reference/forced-singleton-episode-01/episodes.jsonl`: `b6852b024c1cf36564c79e371d12855e9f253989b8dbc4309055a4c88c67f9e3`
- `reference-evidence.json`: `91d2fdcf7ea439a945fc15a39ba1109cdc76fd1896354fd5998762c970f6b20f`
- `reference-report.md`: `1afa4bcc7a047f0b93ec37729b8a5dfffc3c19d8c532b651a2eb0b076ec5b761`
- `replay-check.json`: `b9626402e6876fcdf05704600c5b24cf9de3b9cba54c93bd29283ece6d5bcccb`

Raw artifacts remain ignored and local. The tracked record preserves their identities and the complete step trace.
