"""Codex (secondary agent, 2026-10-21): reproduce D1 and identify only current checked artifacts."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
from brake_math import report as brake_report
from dynamic_review import generate as dynamic_report

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / 'drive-artifacts.json'
REPORTS = [('drive-candidate', 'validation-all.json', 'DIGITAL STAGE CHECKS PASSED'),
           ('drive-assembly', 'assembly-validation.json', 'MODELED FIXED/MOVING INTERFERENCE CHECK PASSED'),
           ('socket-adapter', 'validation.json', 'DIGITAL SOCKET-CASE CLEARANCE CHECK PASSED'),
           ('static-fixture', 'validation.json', 'DIGITAL STATIC-FIXTURE CLEARANCE CHECK PASSED')]
SOURCES = ['drive.json', 'hardware.json', 'size_drive.py', 'test_sizing.py', 'build_drive.py',
           'assemble_drive.py', 'build_all.py', 'requirements-lock.txt', 'README.md', 'BUILD-GUIDE.md',
           'test-results-template.csv', 'connection_review.py', 'socket-adapter.json', 'build_socket_adapter.py',
           'static-fixture.json', 'fixture_math.py', 'test_fixture.py', 'build_static_fixture.py',
           'brake-rotor.json', 'brake_math.py', 'test_brake.py',
           'dynamic-inputs.json', 'dynamic_review.py', 'test_dynamics.py']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect():
    files = set(SOURCES + ['sizing-report.json', 'connection-review.json', 'brake-load-report.json', 'dynamic-report.json'])
    files.update(str(p.relative_to(ROOT)) for p in (ROOT / 'evidence').glob('*.json'))
    assert json.loads((ROOT / 'brake-load-report.json').read_text()) == brake_report(
        json.loads((ROOT / 'brake-rotor.json').read_text())), 'Stale brake feasibility report'
    assert json.loads((ROOT / 'dynamic-report.json').read_text()) == dynamic_report(), 'Stale orbital-load report'
    for folder, report_name, status in REPORTS:
        report_path = ROOT / folder / report_name
        r = json.loads(report_path.read_text())
        assert r['status'].startswith(status), f'Incomplete build: {report_path}'
        assert r['physical_testing'] == 'NOT PERFORMED'
        for name, value in r['source_sha256'].items():
            assert digest(ROOT / name) == value, f'Stale report for {name}'
        files.add(str(report_path.relative_to(ROOT)))
        for name, data in r['parts'].items():
            for suffix in ['step', 'stl']:
                relative = f'{folder}/{name}.{suffix}'
                assert digest(ROOT / relative) == data[suffix + '_sha256'], f'Changed part: {relative}'
                files.add(relative)
    assembly = json.loads((ROOT / 'drive-assembly/assembly-validation.json').read_text())
    assert assembly['cartridge_validation_sha256'] == digest(ROOT / 'drive-candidate/validation-all.json')
    for stage in ['S1', 'S2', 'S3']:
        files.add(f'drive-candidate/{stage}-cartridge-REFERENCE.step')
        files.add(f'drive-candidate/{stage}-internal-preview.png')
    files.add('drive-assembly/D1-gearbox-REFERENCE.step')
    files.add('socket-adapter/SA1-REFERENCE.step')
    files.add('socket-adapter/SA1-printed-and-bought.png')
    files.add('static-fixture/TF1-STATIC-REFERENCE.step')
    files.add('static-fixture/TF1-static-test-setup.png')
    for stem in ['motor-face-slotted-TEMPLATE-NO-POWER', 'shaft-fit-5.2mm-NO-POWER', 'shaft-fit-5.3mm-NO-POWER']:
        for suffix in ['step', 'stl']:
            files.add(f'fit-tests/{stem}.{suffix}')
    return {name: digest(ROOT / name) for name in sorted(files)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify-only', action='store_true')
    parser.add_argument('--package', action='store_true', help='Write an experimental build ZIP, never a physical-validation claim')
    args = parser.parse_args()
    if args.verify_only:
        recorded = json.loads(MANIFEST.read_text())
        assert recorded['status'] == 'DIGITAL CHECKS ONLY; PHYSICAL VALIDATION PENDING'
        assert collect() == recorded['sha256'], 'Artifact/source changed after recorded build'
    else:
        MANIFEST.write_text(json.dumps({'status': 'BUILDING; PREVIOUS PACKAGE MAY BE STALE'}, indent=2) + '\n')
        for argv in [['-m', 'unittest', 'test_sizing', 'test_fixture', 'test_brake', 'test_dynamics'], ['size_drive.py'], ['connection_review.py'], ['brake_math.py'], ['build_drive.py'], ['dynamic_review.py'], ['assemble_drive.py'], ['build_socket_adapter.py'], ['build_static_fixture.py']]:
            subprocess.run([sys.executable, *argv], cwd=ROOT, check=True)
        recorded = {'status': 'DIGITAL CHECKS ONLY; PHYSICAL VALIDATION PENDING',
                    'physical_tests': 0, 'sha256': collect()}
        MANIFEST.write_text(json.dumps(recorded, indent=2) + '\n')
    if args.package:
        package = ROOT / 'D1-EXPERIMENTAL-NOT-LOAD-VALIDATED.zip'
        with zipfile.ZipFile(package, 'w', zipfile.ZIP_DEFLATED) as z:
            for name in recorded['sha256']:
                z.write(ROOT / name, 'banebots-775-k6/' + name)
            z.write(MANIFEST, 'banebots-775-k6/' + MANIFEST.name)
            z.write(ROOT.parents[1] / 'LICENSE', 'LICENSE')
        print(package)
    print(f"Verified {len(recorded['sha256'])} source/artifact hashes. No physical performance claim.")


if __name__ == '__main__':
    main()
