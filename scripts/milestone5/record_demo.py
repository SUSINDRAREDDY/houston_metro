"""Guided live recording: real Kubernetes actions, with evidence saved per run."""
import argparse
import datetime
import json
from pathlib import Path
import shlex
import subprocess
import sys
import time
import urllib.request

PROJECT = 'metroai-vm-milestone-20260922'
CONTEXT = f'gke_{PROJECT}_us-central1_metroai-gke'
URL = 'https://metroai.136.81.119.160.sslip.io'
ROOT = Path(__file__).resolve().parents[2]
KUBE = ['kubectl', '--context', CONTEXT, '-n', 'metroai']
EVIDENCE = None
LOAD_STARTED = False


def command(args, filename=None, show=True, timeout=45):
    if show:
        print('\n$ ' + shlex.join(args), flush=True)
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if show:
        print(result.stdout.rstrip(), flush=True)
        if result.stderr:
            print(result.stderr.rstrip(), flush=True)
    if filename and EVIDENCE:
        (EVIDENCE / filename).write_text(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(f'Command failed: {shlex.join(args)}\n{result.stderr.strip()}')
    return result.stdout


def state(kind, name=None):
    args = KUBE + ['get', kind]
    args += [name] if name else ['-l', 'app=metroai']
    return json.loads(command(args + ['-o', 'json'], show=False))


def ready(pod):
    return not pod['metadata'].get('deletionTimestamp') and any(
        c['type'] == 'Ready' and c['status'] == 'True'
        for c in pod.get('status', {}).get('conditions', [])
    )


def pause(message):
    print('\n' + '=' * 70 + '\n' + message, flush=True)
    input('\nPress Enter when ready to continue: ')


def preflight():
    current = command(['kubectl', 'config', 'current-context'], show=False).strip()
    if current != CONTEXT:
        raise RuntimeError('Wrong cluster context. Connect to metroai-gke first.')
    if not (ROOT / 'k8s/demo/load-test.yaml').is_file():
        raise RuntimeError('The k8s/demo/load-test.yaml file is missing.')
    pods = state('pods')['items']
    deployment = state('deployment', 'metroai')
    if deployment['spec']['replicas'] != 2 or sum(ready(p) for p in pods) != 2:
        raise RuntimeError('Start with exactly two ready replicas. Let any earlier load test and automatic scale-down finish first.')
    active = command(KUBE + ['get', 'job', 'metroai-load-test', '--ignore-not-found', '-o', 'json'], show=False)
    if active and json.loads(active).get('status', {}).get('active', 0):
        raise RuntimeError('An earlier load test is still running. Wait for it to finish.')
    for path in ['/', '/api/health/live', '/api/health/ready']:
        with urllib.request.urlopen(URL + path, timeout=20) as response:
            if response.status != 200:
                raise RuntimeError(f'HTTPS check failed: {path}')
    print('READY: correct cluster, two ready replicas, valid HTTPS and both probes working.', flush=True)


def replacement():
    before = state('pods')['items']
    old_names = {p['metadata']['name'] for p in before}
    victim = next(p['metadata']['name'] for p in before if ready(p))
    command(KUBE + ['get', 'pods', '-l', 'app=metroai', '-o', 'wide'], 'pods-before-deletion.txt')
    command(KUBE + ['delete', 'pod', victim, '--wait=false'], 'deleted-pod.txt')
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        command(KUBE + ['get', 'pods', '-l', 'app=metroai', '-o', 'wide'])
        pods = state('pods')['items']
        replacements = [p for p in pods if p['metadata']['name'] not in old_names and ready(p)]
        if replacements and victim not in {p['metadata']['name'] for p in pods}:
            command(KUBE + ['get', 'pods', '-l', 'app=metroai', '-o', 'wide'], 'pods-after-deletion.txt')
            print('\nVERIFIED: Kubernetes replaced ' + victim + ' with ' + replacements[0]['metadata']['name'], flush=True)
            return
        time.sleep(5)
    raise RuntimeError('Replacement did not become ready within three minutes. Inspect pod events before continuing.')


def autoscaling():
    global LOAD_STARTED
    baseline = state('deployment', 'metroai')['spec']['replicas']
    if baseline != 2:
        raise RuntimeError('Autoscaling demonstration must start at two replicas. Allow earlier load to subside.')
    command(KUBE + ['get', 'hpa', 'metroai'], 'hpa-before-load.txt')
    command(KUBE + ['delete', 'job', 'metroai-load-test', '--ignore-not-found'])
    command(KUBE + ['apply', '-f', str(ROOT / 'k8s/demo/load-test.yaml')])
    LOAD_STARTED = True
    print('\nThe Job sends real HTTP requests for 180 seconds. Replica counts below are live.', flush=True)
    print('While it runs, explain slide 2: liveness checks the app; readiness also checks PostgreSQL.', flush=True)
    scaled = False
    deadline = time.monotonic() + 360
    while time.monotonic() < deadline:
        command(KUBE + ['get', 'hpa', 'metroai'])
        command(KUBE + ['get', 'pods', '-l', 'app=metroai'])
        deployment = state('deployment', 'metroai')
        count = deployment['spec']['replicas']
        if count > baseline and deployment.get('status', {}).get('readyReplicas', 0) > baseline:
            if not scaled:
                command(KUBE + ['get', 'hpa', 'metroai', '-o', 'yaml'], 'hpa-during-load.yaml')
                command(KUBE + ['get', 'pods', '-l', 'app=metroai', '-o', 'wide'], 'pods-during-load.txt')
                print(f'\nVERIFIED: HPA increased replicas from {baseline} to {count}.', flush=True)
            scaled = True
        job = state('job', 'metroai-load-test')
        conditions = job.get('status', {}).get('conditions', [])
        if any(c['type'] == 'Failed' and c['status'] == 'True' for c in conditions):
            raise RuntimeError('Load Job failed. Inspect its logs before claiming a successful demonstration.')
        if any(c['type'] == 'Complete' and c['status'] == 'True' for c in conditions):
            LOAD_STARTED = False
            command(KUBE + ['logs', 'job/metroai-load-test'], 'load-test-results.json')
            command(KUBE + ['describe', 'hpa', 'metroai'], 'autoscaling-events.txt')
            if not scaled:
                raise RuntimeError('The Job finished but scaling was not observed. Do not claim autoscaling was demonstrated.')
            print('\nLoad finished. HPA will reduce replicas automatically as CPU falls.', flush=True)
            return
        time.sleep(15)
    raise RuntimeError('Load/scaling demonstration timed out. Evidence is saved; inspect the Job and HPA.')


def show_checks():
    command(['curl', '-fsS', '-I', URL.replace('https://', 'http://') + '/'], 'http-redirect.txt')
    command(['curl', '-fsS', '-I', URL + '/'], 'https-headers.txt')
    certificate = state('managedcertificate', 'metroai-certificate')['status']['certificateName']
    command(['gcloud', 'compute', 'ssl-certificates', 'describe', certificate,
             '--project=' + PROJECT, '--format=yaml(managed.status,managed.domainStatus)'], 'certificate-active.txt')
    for endpoint in ['live', 'ready']:
        command(['curl', '-fsS', URL + '/api/health/' + endpoint], 'probe-' + endpoint + '.json')


def staged_demo(stage):
    global EVIDENCE
    marker = ROOT / 'evidence' / '.last-demo-evidence'
    if stage == 1:
        preflight()
        stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        EVIDENCE = ROOT / 'evidence' / ('recording-' + stamp)
        EVIDENCE.mkdir(parents=True)
        marker.write_text(EVIDENCE.name)
        command(KUBE + ['get', 'pods', '-l', 'app=metroai', '-o', 'wide'], 'healthy-replicas.txt')
        command(KUBE + ['get', 'deployment,hpa,pdb'], 'deployment-hpa-pdb.txt')
        print('\nShow the app and slide 1. Keep your camera visible. Next command: demo.sh 2', flush=True)
    else:
        if not marker.is_file():
            raise RuntimeError('Run demo.sh 1 first to start a new recording evidence folder.')
        folder = marker.read_text().strip()
        if not folder.startswith('recording-') or Path(folder).name != folder:
            raise RuntimeError('Invalid evidence folder marker. Run demo.sh 1 again.')
        EVIDENCE = ROOT / 'evidence' / folder
        if not EVIDENCE.is_dir():
            raise RuntimeError('The evidence folder is missing. Run demo.sh 1 again.')
        if stage in (2, 3):
            preflight()
        if stage == 2:
            print('\nLIVE POD DELETION: keep the terminal visible until replacement is verified.', flush=True)
            replacement()
            print('\nNext command: demo.sh 3', flush=True)
        elif stage == 3:
            autoscaling()
            print('\nNext command: demo.sh 4', flush=True)
        else:
            show_checks()
            print('\nALSO SHOW IN THE VIDEO: HTTPS app, browser certificate/security details,\nGoogle Cloud ACTIVE certificate page, browser HTTP-to-HTTPS navigation,\nslide 2, and committed Deployment/Service/ingress/HPA/PDB on GitHub.\nExplain liveness versus database readiness and voluntary-eviction PDB limits.\nKeep all presenters visible during their portions; aim for ten minutes.\nSubmit slides, analysis, Active screenshot and live evidence. Upload video\nto OneDrive, share with all three instructors, and submit the link in Canvas.', flush=True)
    print('\nEvidence folder: ' + str(EVIDENCE), flush=True)


def main():
    global EVIDENCE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Read-only preflight; do not delete pods or start load.')
    parser.add_argument('stage', nargs='?', type=int, choices=[1, 2, 3, 4],
                        help='1: healthy pods; 2: live replacement; 3: actual autoscaling; 4: HTTPS and probes.')
    args = parser.parse_args()
    if args.check:
        preflight()
        return
    if args.stage:
        staged_demo(args.stage)
        return
    preflight()
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    EVIDENCE = ROOT / 'evidence' / ('recording-' + stamp)
    EVIDENCE.mkdir(parents=True)
    pause('START YOUR RECORDING WITH CAMERAS ON.\n0:00-1:00: show the HTTPS app and a journey search. Show slide 1 and explain\nload balancer -> ingress -> Service -> pods -> managed database and storage.\nApp: ' + URL)
    print('\n1:00-2:00: show at least two healthy application replicas.', flush=True)
    command(KUBE + ['get', 'pods', '-l', 'app=metroai', '-o', 'wide'], 'healthy-replicas.txt')
    command(KUBE + ['get', 'deployment,hpa,pdb'], 'deployment-hpa-pdb.txt')
    pause('2:00-3:30: keep the terminal on camera. The next step deletes ONE pod\nand shows Kubernetes replacing it LIVE. Explain the changing pod names.')
    replacement()
    pause('3:30-7:00: the next step starts HTTP load and shows actual autoscaling.\nKeep the terminal visible when the replica count increases. You can explain\nslide 2 while load runs; return to the terminal to show the changed count.')
    autoscaling()
    pause('7:00-8:00: show the browser HTTPS URL and its certificate/security details.\nShow the Google Cloud certificate page with ACTIVE. Enter the HTTP URL in the\nbrowser to show the HTTPS result. The next output proves the SERVER redirect.')
    command(['curl', '-fsS', '-I', URL.replace('https://', 'http://') + '/'], 'http-redirect.txt')
    command(['curl', '-fsS', '-I', URL + '/'], 'https-headers.txt')
    certificate = state('managedcertificate', 'metroai-certificate')['status']['certificateName']
    command(['gcloud', 'compute', 'ssl-certificates', 'describe', certificate,
             '--project=' + PROJECT, '--format=yaml(managed.status,managed.domainStatus)'], 'certificate-active.txt')
    pause('8:00-9:00: show slide 2. Explain why a database failure must affect\nreadiness without triggering container restart loops. Show these two endpoints.')
    for endpoint in ['live', 'ready']:
        command(['curl', '-fsS', URL + '/api/health/' + endpoint], 'probe-' + endpoint + '.json')
    pause('9:00-10:00: open the repository link and show COMMITTED deployment, Service,\ningress, autoscaler and PDB files. Explain: the PDB preserves one available pod\nduring supported voluntary evictions; direct deletion bypasses it.\nRepository: https://github.com/SUSINDRAREDDY/houston_metro/tree/codex/milestone5-orchestration/k8s')
    print('\nRECORDING CHECKLIST: two ready replicas; live deletion AND ready replacement;\nactual HPA count increase; valid browser certificate; HTTP redirect; both slides;\ncommitted manifests; presenters visible. Stop recording after your explanation.', flush=True)
    print('\nSaved live evidence: ' + str(EVIDENCE), flush=True)
    print('Submit the two-slide PPTX, half-page analysis, Active certificate screenshot,\nbefore/after pod output and accessible repository link. Upload the video to\nOneDrive, share with sdesini@cougarnet.uh.edu, krajan@cougarnet.uh.edu,\nskolanu@cougarnet.uh.edu, then submit its shareable link in Canvas.\nDo not upload the video file directly to Canvas.', flush=True)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, subprocess.TimeoutExpired, urllib.error.URLError) as exc:
        print('\nSTOP: ' + str(exc), file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print('\nDemo stopped. Saved evidence remains available.', file=sys.stderr)
        sys.exit(130)
    finally:
        if LOAD_STARTED:
            subprocess.run(KUBE + ['delete', 'job', 'metroai-load-test', '--ignore-not-found'], timeout=45)
