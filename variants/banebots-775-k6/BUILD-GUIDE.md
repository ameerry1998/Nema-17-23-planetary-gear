# D1 prototype build guide

This is an experimental build for fit and controlled load testing. No parts have been printed or physically tested for this project. Do the small fit checks first. Do not buy the full bill of materials or connect the grinder based solely on a clean CAD report.

## Printed plastic and purchased metal

You do not need a metal printer. All sun gears, planet gears, stationary ring gears, carrier plates and housing pieces are plastic prints. The separate grinder adapter is also a plastic test part. A carrier is the plate holding the small planet gears; it turns the next shaft.

Bearings, shoulder bolts, shafts, shaft connectors, two clamping hubs and fasteners are purchased hardware. Some spacer tubes and housing tie rods require cutting and finishing to length, or a supplier's cutting service. A hub is a small connector bolted onto a printed carrier that grips its shaft. The later two carriers use metal hubs because their short plastic shaft sockets concentrated too much load into too little contact area. This does not replace any of the gear teeth with metal.

STLs named `spacer` are dimensional fit samples for the metal pieces. Their existence does not mean they should be printed for powered operation. `REFERENCE.step` files show an assembly and must not be printed as one object. The part material and quantity are recorded in each validation report.

## Exact filament and why

**Next-test candidate: Prusament PC Blend Carbon Fiber, PCCF.** This is polycarbonate blend containing chopped carbon fibers. It is a filament for an appropriately equipped FDM printer. No continuous-fiber or metal-printing equipment is required. This choice replaces the earlier provisional unfilled-PC baseline, not a successful physical material test.

| Candidate | Evidence relevant to this design | Decision |
| --- | --- | --- |
| Prusament PCCF | Manufacturer horizontal printed tensile yield 64 ± 3 MPa, horizontal tensile modulus 2.6 ± 0.1 GPa; separate interlayer adhesion test 23 ± 2 MPa. No gear fatigue or wear rating supplied. | Use for next fit and controlled stage tests. Dimensional stability is useful for multiple bearing seats. |
| Unfilled Prusament PC Blend | Earlier baseline: published tensile yield 63 ± 1 MPa. The numbers do not show a large tensile-strength improvement simply from adding CF. | Retain as an alternative comparison material; do not silently substitute. |
| Bambu PAHT-CF | Manufacturer dry XY/Z bending values 125/61 MPa and wet values 115/49 MPa. These are different tests and processing conditions from Prusa's tensile values. | Credible nylon-CF alternative if PCCF wear or print results are poor. Requires separate conditioning and fit trials. |
| Prusament PA11 Natural | Manufacturer emphasizes sliding behavior and layer bonding; as-printed heat deflection at 0.45 MPa is only 58.7 C, versus 122.5 C after its annealing process. | Possible wear-test alternative. Annealing and dimensional change make it a separate process to qualify. |

Sources: [PCCF datasheet](https://prusament.com/wp-content/uploads/2023/04/TDS_Prusament-PCCF_2023_EN.pdf), [unfilled PC datasheet](https://prusament.com/wp-content/uploads/2022/10/PCBlend_Prusament_TDS_2022_16_EN.pdf), [Bambu PAHT-CF](https://au.store.bambulab.com/collections/pa-pet/products/paht-cf), [Prusa PA11 Natural explanation](https://blog.prusa3d.com/prusament-pa11-natural-material-with-extreme-mechanical-and-chemical-resistance_137458/). These data are not directly comparable fatigue allowables. Prusa's "vertical xz" coupon result is not substituted for its separately measured interlayer adhesion.

The calculator keeps the same provisional **8 MPa tooth-bending screen** after switching to PCCF. It uses 2.6 GPa for its simplified contact calculation, with an assumed Poisson ratio of 0.38. CF does not earn an automatic increase in permitted torque. The final stage's peak Lewis screen is approximately 7.85 MPa, close to that unvalidated 8 MPa assumption. Physical fatigue, wear, ring stress and uneven planet loading remain unresolved.

## Printing the next test pieces

Start with the existing motor-face and shaft coupons in `fit-tests`, plus one `drive-candidate/S3-planet.stl`. Use the intended final filament for the bearing-fit sample. The old 3 mm hand-test gears are not powered-test parts.

Provisional project profile for PCCF, to be calibrated on the actual printer:

- Enclosed Prusa or Bambu with a **0.4 mm abrasion-resistant nozzle** and filament path appropriate for CF. The exact shop Prusa model and installed nozzle still need checking. A larger nozzle is not assumed to reproduce the small first-stage teeth equally well.
- Start at **285 C nozzle, 110 C bed**, within the manufacturer's 285 ± 10 / 110 ± 10 C ranges. Do not exceed the printer's bed limit; the P2S limit is 110 C. Use the printer manufacturer's filament/profile guidance for its hardware.
- Dry PCCF at **90 C for 4 hours** in equipment capable of that temperature, with a heat-compatible spool. Follow [Prusa's drying and spool instructions](https://help.prusa3d.com/article/drying-filament_332086/). Keep it dry while printing.
- 0.15 mm layers, 0.2 mm first layer, 0.42 mm nominal extrusion width, 6 perimeters, 100% rectilinear infill for gears, carriers, bearing caps and adapter. These are project starting settings, not a demonstrated strength recipe. Use 40 mm/s outer walls, 60 mm/s other solid paths, initially limit flow to 5 mm3/s.
- Flat gear faces on the bed, shafts vertical in the slicer. Tooth outlines then lie within the layer plane. All carriers lie flat. Bearing caps and retainers lie flat with their bearing shoulders inspected after printing. Avoid supports inside teeth, bearing seats and shaft sockets; supports outside functional faces may be needed on other parts.
- Begin with 0% part cooling except required bridges up to 20%, following the PCCF datasheet. Use the appropriate plate and separation agent for the selected sheet. Add a removable outer brim if needed, and remove every trace from teeth and fits.
- Check the sliced small sun gear: continuous tooth walls, no missing tips, no isolated gaps at roots. Do not globally scale an entire gearbox to fix a bearing fit. Adjust the fit parameter and regenerate.

Inspect every part for layer splits, warped bearing seats, underextrusion and damaged teeth. For a bearing, press only its outer race into a housing. If it needs hammering or excessive force, revise the fit. The nominal CAD bearing bores are 13.10, 16.10 and 28.10 mm; actual printed bores have not been measured.

## Hardware and dimensions

The complete candidate procurement list is `hardware.json`, with quantities, specifications, source links and fit caveats. No orders have been placed. Key mechanical pieces:

| Item | Quantity | Purpose |
| --- | ---: | --- |
| BaneBots M7-RS775-18 | 1 | Existing motor |
| 695 shielded bearings, 5 x 13 x 4 mm | 20 | Two per planet |
| 688 shielded bearings, 8 x 16 x 5 mm | 6 | Three carrier journals and three stationary shaft supports |
| 6001 shielded bearings, 12 x 28 x 8 mm | 2 | Output shaft |
| 5 mm shoulder bolts, shoulder lengths 25/30/35 mm, M4 thread | 3 / 3 / 4 | Supported planet pins |
| 8 mm REX shafts, 40/48 mm | 2 / 1 | Input and interstage torque paths |
| 12 mm REX shaft, 64 mm | 1 | Output |
| ServoCity 625228, 5-to-8 mm shaft coupler | 1 | Motor to input shaft |
| goBILDA 1309-0016-4008 / 1301-0016-4012 | 1 / 1 | S2 / S3 carrier hubs |
| goBILDA 2910-1026-4012 collar | 1 | Output axial retention |
| M4 x 10 DIN7991 countersunk bolts, heads no larger than 8 mm | 8 | Metal hub to carrier |
| M4 tie rods, nominal 225 mm, nuts and washers | 6 | Clamp casing stack |
| ruthex RX-M2x4 inserts / M2 x 6 screws | 15 / 15 | Bearing retainers |

Manufacturer bearing abutment data matter. For the selected [NSK 695](https://www.oss.nsk.com/products/bearings/ball-bearings/deep-groove-ball-bearings/extra-small-ball-bearings-and-miniature-ball-bearings-metric-series/695zz1mc5p6-apn.html), inner-race contact diameter must not exceed 6.6 mm. The revised spacers use [K&S 9824 tube](https://ksmetals.com/products/br45mm-6), 6 mm OD and approximately 5.13 mm ID. Measure the tube, account for sideways clearance on the pin, and check it touches the inner race only. Ordinary wide M5 washers may rub the shields.

Nominal planet spacer cuts: 3 x 4 mm, 3 x 9 mm, 4 x 14 mm between bearings; 20 x 0.5 mm outside the bearings. The thin cuts need careful square finishing or supplier/shop help. Adjust lengths to actual parts. Do not use short spacers and then tighten until the bearing balls carry the clamping force. Tube alloy/temper and clamp-load capacity are not established; use only enough seating force for the verified free-running, retained stack.

Current body: 98 mm diameter, 179.5 mm case length. Motor, coupling guard and adapter bring the whole CAD stack to approximately **323 mm**. This is a relatively long development prototype, not the compact final package. Reduction of length remains a design task after the working torque path is established.

Motor mounting pitch is assumed 29 mm with slots covering 26 to 32 mm. Published motor shaft protrusion is 7.62 mm, but its reference face and safe screw engagement need physical confirmation. Published K6 hex nominal is 6.35 mm. The 55 mm body diameter, 175 mm grinder height and 35 mm removal allowance are only adjustable packaging assumptions. No exact K6 clamp fit is verified.

## Assembly sequence

Keep electrical power disconnected through all fit and hand-turn steps.

1. Fit the motor-face coupon without forcing the shaft or driving screws deep. Verify the collar clears, shaft overlaps the coupler, and mounting screws cannot reach motor internals. The CAD's 2.5 mm screw engagement is an assumption. Use the shortest actual mounting screws that achieve confirmed engagement.
2. Assemble each planet with two 695 bearings and the correctly finished central metal spacer. Confirm both bearings remain parallel and turn freely. Outer-race shoulders must not touch the shields. Cut/fit parts before applying lubricant.
3. Seat the 688 journal in the lower carrier, supporting its outer race. Insert planet shoulder pins, end spacers and planets. Fit the upper carrier and M3 post screws. Check every planet by hand as fasteners are secured. Select the shim stack so it neither pinches bearings nor leaves uncontrolled axial movement. Planet pin shoulders must support both carrier plates; threads must not be the bearing surface.
4. On S2 and S3 bolt the appropriate metal hub to the upper plate with four flush M4 countersunk screws. Verify none projects into gear space. On S1 fit its captive M3 nut and radial retention screw. The keyed shaft shape transfers torque; a set screw alone is not assumed to transfer the full output torque.
5. Build from the motor end. Fix the 5-to-8 mm coupler to the motor and input shaft while it is accessible. Slide the coupler guard and input bearing cap over the free input shaft. Fit the motor plate screws before enclosing the coupler. Then add the S1 carrier journal, spacers and sun, with its M4 end washer/screw. Check the motor shaft is not axially pushed or pulled.
6. Install the fixed S1 ring and casing sections, then the S1 output bearing cap. Insert its output shaft and the next stage's input spacers/sun. Continue S2 and S3 in the same order. Use the assembled STEP and `assembly-validation.json` placement coordinates to identify each cap and sleeve. Six tie rods hold the fixed stack; tighten evenly without crushing the plastic.
7. Retain the stationary bearing outer races with the printed retainers and M2 screws into heat-set inserts. The output cap has two 6001 bearings and an inner-race separator. Fit the output collar. Adjust actual shaft stacks for approximately 0.1 to 0.3 mm endplay without bearing-ball preload. Confirm shaft grooves do not sit in a loaded hub or interfere with a bearing contact surface.
8. Apply only a thin film of verified compatible gear lubricant. Keep all grease and eventual wear particles separated from coffee. Perform hand-turn and axial-retention checks before installing the guard and test fixture.

These instructions are a proposed sequence checked against CAD, not an observed successful assembly. Physical insertion/tool-access trials may require revisions.

## Removable output interface

The fixed outer ring and housing do not turn. The last carrier turns a 12 mm REX shaft. REX here is an 11 mm across-flats hex clipped to a 12 mm circular envelope. The removable attachment grips that shaft, with 15.5 mm engagement and 0.5 mm socket-bottom clearance. Two M3 screws clamp the separate printed attachment. Allow at least 17.5 mm axial travel to remove it from the gearbox shaft, plus clearance to disengage the grinder.

The candidate K6 end has a 6.50 mm across-flats printed socket, based on the published 6.35 mm nominal plus 0.15 mm fit allowance. Its 15 mm modeled depth is not a measured K6 engagement length. Both socket strength and retention require a bench test against a metal test hex before it is put on the grinder. A metal socket insert may be needed if the printed socket rounds out. The attachment is not yet torque-rated.

## Beginner wiring and speed control

The brushed DC motor has two power terminals. The controller switches power rapidly to adjust average voltage. Its knob controls this fraction of time, called PWM duty. **A knob setting is not a guaranteed RPM.** Grinding load changes the speed; use a tachometer for the first tests. No Arduino or firmware is needed for this candidate.

Provisional controller: [Pololu Simple Motor Controller G2 18v15, assembled #1362](https://www.pololu.com/product/1362). It combines a knob input, configurable acceleration and hardware current limiting. It is expensive: the observed listing was $141.18 and backordered on October 21, 2026. Do not buy it automatically. An equivalent must have a documented adjustable current limit and stop input, not merely a large advertised amp number. Initial setup of this model uses Pololu's Windows utility; Mac-only setup has not been established.

Use a shop current-limited **12 V bench supply** for first tests. A later enclosed supply candidate is Mean Well **GST220A12-R7B, 12 V, 15 A** with its correctly rated mating connector and verified pinout. Use an enclosed commercial supply, not exposed mains wiring.

Power wiring, with the supply off:

```text
12 V supply positive -> 15 A fuse -> DC-rated disconnect -> controller VIN
12 V supply negative -------------------------------> controller GND
controller motor A ---------------------------------> motor terminal 1
controller motor B ---------------------------------> motor terminal 2

10k linear knob: outer terminals -> controller AN1 + and -
                middle terminal -> controller A1 signal
normally-closed stop contact -> controller A2 and controller GND
USB data cable -> computer for initial configuration
```

Use short 16 AWG power leads, insulated terminals and connectors rated at least 15 A. Breadboards and thin jumper wires are not motor-power connections. The fuse protects the wiring; it is not a precise gearbox torque limit. The normally-closed stop contact is a control signal, not a path for motor current. A separate DC-rated disconnect removes power.

Configure from the [Pololu manual](https://www.pololu.com/docs/0J77/all): analog input AN1, forward-only motion, calibrated zero/full knob positions, retain safe start, enable AN1 disconnection detection. Configure AN2 as a normally-closed kill input with the appropriate pull-up; disable its analog-pot disconnection behavior only as specified for the switch input. Set acceleration to roughly one second initially; stop must not wait through a long deceleration ramp. Test every input before attaching the gearbox. Stop, open-wire and power restoration must require an intentional restart at zero command.

Start the motor-only test with a low current limit that permits unloaded rotation. Do not jump straight to full power. The model estimates 7.4 A motor current at the provisional 3 Nm/100 RPM output and 10.6 A at 5 Nm/100 RPM. An eventual approximate 11 A motor limit is a candidate ceiling after calibration, not proof of a 5 Nm mechanical limit. Supply current and PWM motor current are different measurements. Stay at or below 12 V. Coast on stop initially and check supply-voltage transients; braking/regeneration and the final power supply still need verification.

## Staged tests and revision rules

Record results in `test-results-template.csv`. Each record needs the part revision, filament/spool, printer/profile, temperature/humidity conditioning and actual measured torque/RPM. Leave unknown measurements blank; do not infer physical success from a CAD report.

1. **Fit only.** First concrete task: print one S3 planet in PCCF and fit two 695 bearings by their outer races. Report actual pocket diameter and whether each bearing seats by hand/light press and stays secure. Separately use the existing unpowered motor-face template. If tight/loose, adjust only relevant fit allowances, regenerate and repeat. Do not start the motor.
2. **Measure grinder demand by hand.** With the normal handle and intended beans/espresso setting, measure handle radius and tangential force at several crank positions. Torque Nm = force N x radius m, or scale kgf x 9.81 x radius m. Start and running values must be separate. A luggage scale is only a low-speed estimate and can miss fast peaks. Record dose mass and elapsed time. The current 3/5 Nm values are design targets, not KINGrinder specifications.
3. **Retention and low-speed output stage.** Secure the housing in a rigid fixture that supports both drive and load and shields the coupling. A calibrated torque wrench and a restrained input can check a static load, but do not call that a running-load test. Increment through 1, 2 and 3 Nm, then a one-second 5 Nm peak only if no damage, movement or binding appears. Mark hubs/shafts to detect slip. Repeat on the separate output adapter against a steel test hex, not the grinder. Reinspect teeth, layer lines, bearing pockets, bolts and endplay after unloading.
4. **Motor and first-stage speed.** First run the motor alone in a secured mount with a guard. Verify direction, current limit and immediate stop behavior. Then test S1 without downstream load in increments of 10%, 25%, 50%, 75% and intended maximum speed. Measure RPM, current, temperature and vibration. The intended first-stage input is approximately 10,000 RPM; its carrier-relative pitch-line speed is about 6.0 m/s. This is a test priority, not an allowable rating. Stop for rubbing, growing vibration, loose connections or rapid heat rise.
5. **Complete drive on a controlled load fixture.** Start unloaded, then increment to 1, 2 and 3 Nm at approximately 100 RPM, with separately measured torque and speed. A brake/reaction-arm fixture must be designed and reviewed before this step; it is not included in D1 yet. Never hold the housing or shaft by hand. The 5 Nm peak lasts at most one second initially. Check current limiting at the fixture, not by deliberately jamming the grinder.
6. **Grinding milestone.** Only after the preceding stages pass, support and align the K6 with an adjustable fixture. Verify its permitted drive direction and full socket engagement. Test one dose, then 3 x 18 g doses of at most 60 seconds each, followed by 120 seconds rest. Ten successful representative doses is a prototype milestone, not a wear-life rating. Then extend the test count while inspecting backlash and teeth.

Initial stop threshold is **50 C measured accessible gear/housing surface**, or any smoke, rubbing, visible debris, binding, loose fastener, cracked tooth, increasing current or unstable noise. Surface temperature can miss hotter tooth contact; passing this threshold is not a thermal rating. Require stable temperature/current trends before longer runs.

Revise tooth geometry, stage speed, lubrication or material if the teeth wear or overheat. Revise hubs/retention if witness marks move. Revise the ratio if measured torque and motor voltage leave insufficient margin. Keep failed results and identify the revised files; do not overwrite a failure with a later unexplained pass. Final permitted torque, duty and lifetime remain unset until the corresponding evidence exists.

## Reproduce and inspect

Use Python 3.11 and `requirements-lock.txt` in a separate virtual environment. Run `python build_all.py` to execute the sizing tests, recompute the model, export each part and check the recorded geometry. `python build_all.py --verify-only` verifies current source/artifact hashes. Add `--package` to create a ZIP labeled experimental. This is a project-specific build command, not yet a general-purpose gearbox-design tool.

Digital checks cover valid single-solid CAD, watertight STL, sampled gear-mesh phases and modeled fixed-versus-moving clearance. They do not cover every tool-access path, flexible deflection, as-printed fits, dynamic operation or fatigue. Purchased-part solids are simplified clearance references. Preserve the upstream MIT license and cq_gears attribution in any distribution.
