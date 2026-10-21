# BaneBots 775 / KINGrinder K6

Experimental, printable planetary drive using the BaneBots M7-RS775-18 motor. **No physical fit, load, heat or wear test has passed yet.** The current files are development candidates, not an operating-strength release.

The gears, carriers and housing are printed in **Prusament PC Blend Carbon Fiber (PCCF)** for the next tests. Bearings, shafts, bolts and small connecting hubs are purchased metal hardware. No metal printer is required. Some spacer tube and tie-rod stock needs cutting/finishing. The material was changed from the earlier provisional unfilled PC baseline; the assumed tooth-load limit was not increased merely because CF was added.

Read the [build guide](BUILD-GUIDE.md) for the material comparison, print settings, assembly, wiring and test procedure. [hardware.json](hardware.json) is the complete candidate hardware list with quantities and source links.

## Smallest next physical step

Print **one [S3 planet](drive-candidate/S3-planet.stl)** in the intended PCCF and check the two 5 x 13 x 4 mm bearing seats by pressing on the outer races. Report whether they seat with hand/light pressure and stay secure. Do not power it. The existing [motor-face template](fit-tests/motor-face-slotted-TEMPLATE-NO-POWER.stl) separately checks motor-hole spacing without power.

## One outcome checklist

- [x] Preserve upstream source/license and original hand-turn fit parts.
- [x] Implement a traceable motor, ratio, tooth, pin and shaft calculation with invalid-input tests.
- [x] Generate three load-sized cartridge candidates, casing, bearing retention, motor interface and removable adapter source/STEP/STL.
- [x] Define bought hardware, PCCF trial settings, beginner wiring and staged tests.
- [x] Add a reproducible build and source/artifact hash verification command.
- [ ] Validate actual printed bearing fits, motor face, shaft engagement and assembly access.
- [ ] Measure representative K6 running torque and startup peaks.
- [ ] Complete the controlled-load fixture and validate the printed output socket/shaft retention.
- [ ] Pass low-speed load and high-speed/temperature tests, revise the drive from results.
- [ ] Demonstrate repeatable grinding and wear behavior with recorded evidence.
- [ ] Reduce package size and design the adjustable final stand around verified dimensions.
- [ ] Generalize the proven sizing/build workflow into a reusable tool and release it with explicit limits.

## Current candidate

| Parameter | D1 value and evidence |
| --- | --- |
| Ratio | 100:1, from 5 x 5 x 4 stages; still provisional |
| Target output | 3 Nm running; 5 Nm for one second; 100 RPM. Unmeasured K6 requirements. |
| Motor supply | 12 V maximum for initial development |
| Model at 3 Nm / 100 RPM | Approximately 7.4 A motor current and 9.9 V average motor voltage |
| Model at 5 Nm / 100 RPM | Approximately 10.6 A and 10.3 V average; 52.4 W mechanical output |
| Efficiencies | 90%, 90%, 85%, assumed, not measured |
| Stage module / face width | S1 0.8 / 12 mm; S2 1.0 / 17 mm; S3 1.35 / 22 mm |
| Material | Prusament PCCF, controlled-test candidate; no validated fatigue allowable |
| Housing | 98 mm OD, 179.5 mm case; approximately 323 mm including motor/guard/adapter |
| Output | 12 mm REX shaft, separate clamped attachment with 15.5 mm engagement |
| K6 interface | Published nominal 6.35 mm hex; protrusion, socket clearance and actual fit unverified |

The motor model suggests 125:1 cannot reach the provisional 5 Nm at 100 RPM point from 12 V with the assumed losses. The selected 100:1 is therefore a candidate to test, not a final answer. See [sizing-report.json](sizing-report.json) for assumptions and calculated values. The 8 MPa tooth screen is engineering judgment, not a published printed-gear fatigue rating. S3 reaches roughly 7.85 MPa in that screen.

The stationary outer ring does not drive the grinder. Each sun gear drives planets around the fixed ring; their carrier rotates more slowly and turns the next shaft. S2 and S3 use small bought metal hubs bolted onto printed carriers to grip the shafts. The final shaft turns the removable printed adapter. That adapter still requires its own torque test. A new connection review flags its small printed sockets as a weak point. The separate SA1 candidate uses a printed retaining case around bought steel sockets; it has not replaced the earlier adapter in the D1 assembly reference. See the build guide before selecting either version.

## Files and verification

- `drive.json`: editable design parameters, assumptions and sources.
- `size_drive.py`, `test_sizing.py`: engineering screens and unit checks.
- `build_drive.py`: gear and carrier generation using CadQuery and cq_gears.
- `assemble_drive.py`: casing, retention, motor interface and separate attachment.
- `drive-candidate/`: individual cartridge STEP/STL files and reference assemblies.
- `drive-assembly/`: casing/interface STEP/STL files and complete reference assembly.
- `socket-adapter/`, `socket-adapter.json`: separate SA1 printed cassette with bought steel sockets; fit/load trials pending.
- `connection_review.py`, `connection-review.json`: shaft/socket contact and heating screens, including rejected compact-stage candidate.
- `drive-artifacts.json`: hashes binding the current checked sources to artifacts.
- `test-results-template.csv`: empty physical-test log; no fabricated results.
- `evidence/`: preserved earlier failed checks where applicable.
- `fit-tests/`, `cad/`, `START-HERE.html`: original thin hand-turn/fit set, not powered parts.

STLs representing metal spacers are explicitly labeled **fit samples** in their reports. Use specified metal pieces for powered tests. Reference assemblies are not print-in-place files. No sliced G-code has been generated or printer profile validated on the shop machines.

With Python 3.11:

```sh
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python build_all.py
python build_all.py --verify-only
```

Add `--package` to produce an experimental ZIP. The command executes the sizing tests, exports CAD and checks the recorded geometry. Individual stage reports include 13 representative tooth-phase samples, all planets at their initial phase and carrier clearance. The assembly checks modeled fixed-versus-moving intersections. These checks do not establish printed tolerances, deflection, fatigue, wear or physical performance.

## Relationship to upstream and sources

[Omar Salem’s upstream NEMA 17/23 project](https://github.com/Omar-Salem/Nema-17-23-planetary-gear) supplies the original editable Fusion files and planetary architecture reference. The D1 geometry in this variant is independently generated with [cq_gears](https://github.com/meadiode/cq_gears), pinned in `requirements-lock.txt`, rather than a direct edit of the upstream Fusion assembly. Its original motor interface and default ratio are not assumed suitable for the high-speed 775.

Preserve the upstream MIT license and the Apache-2.0 attribution of the cq_gears dependency. Manufacturer data: [BaneBots motor](https://banebots.com/m7-rs775-18/), [PCCF datasheet](https://prusament.com/wp-content/uploads/2023/04/TDS_Prusament-PCCF_2023_EN.pdf), [KINGrinder K6 manual](https://uploads.strikinglycdn.com/files/ee51bf66-c9fe-40cf-85b0-a55bd71835ab/KINGrinder%20K6-EN.pdf). Additional bearing, hardware and controller sources are linked in the guide and BOM.
