"""Disposable offline mock session demo; no external services or user files."""

import argparse
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from animation_studio.providers.gpu import GPUJobRequest, GPUProviderError, MockGPUProvider
from animation_studio.providers.gpu_attempts import LocalAttemptLedger
from animation_studio.providers.gpu_budget import BudgetConfig, PlannedGPUShot, RenderWorkload
from animation_studio.providers.gpu_durable_session import DurableMockRenderSession
from animation_studio.providers.gpu_lifecycle import MockLifecycle
from scripts.report_gpu_session import main as show_report


def run_demo():
    workload = RenderWorkload(
        gpu_hourly_price='0',
        startup_gpu_minutes='0',
        shots=(
            PlannedGPUShot(
                shot_id='demo-shot',
                request=GPUJobRequest(
                    operation='mock.noop',
                    prompt='Synthetic offline demo',
                    model_name='mock-worker',
                    model_version='1',
                ),
                gpu_minutes_per_attempt='1',
                attempts=1,
            ),
        ),
    )
    config = BudgetConfig(
        max_gpu_hourly_price='0',
        max_gpu_minutes_per_job='1',
        max_attempts_per_shot=1,
        max_estimated_cost_per_render='0',
    )
    print('Offline mock demo; real GPU, model বা animation তৈরি হচ্ছে না।')
    with TemporaryDirectory(prefix='animation-mock-demo-') as directory:
        path = Path(directory) / 'ledger.json'
        ledger = LocalAttemptLedger(path)
        ledger.initialize()
        with DurableMockRenderSession.create(
            MockGPUProvider(),
            MockLifecycle('demo-pod', storage='retained'),
            ledger,
            workload,
            config,
            render_id='demo-render',
            clock=lambda: 100.0,
        ) as session:
            print('\n১. Cleanup-এর আগের সংরক্ষিত অবস্থা:')
            if show_report(['--ledger', str(path), '--render-id', 'demo-render']) != 0:
                raise ValueError('Initial report failed')
            job = session.submit(shot_id='demo-shot', attempt_key='demo-attempt')
            print(f'\n২. Mock submit status: {job.status}; এটি media completion নয়।')
            session.finish()
        print('\n৩. Mock cleanup-এর পরে সংরক্ষিত অবস্থা:')
        if show_report(['--ledger', str(path), '--render-id', 'demo-render']) != 0:
            raise ValueError('Final report failed')
    print('\nঅস্থায়ী demo files সরানো হয়েছে।')


def main(argv=None):
    parser = argparse.ArgumentParser(description='অস্থায়ী local mock session ও বাংলা report demo')
    parser.parse_args(argv)
    try:
        run_demo()
    except (OSError, ValueError, GPUProviderError):
        print('Offline demo ব্যর্থ; সফল ফল হিসেবে গণ্য করবেন না।', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
