import subprocess
from pathlib import Path



def run_pmo_parallel(split_dir, PMO_SCRIPT, max_concurrent=32):
    """
    Run PMO across all time-split subdirectories under split_dir, bounded
    to max_concurrent simultaneous processes. max_concurrent should match
    however many CPUs your qinteractive session actually holds — 32 is the
    qinteractive default; raise it only if you explicitly requested more
    (e.g. -l select=1:ncpus=128:mpiprocs=128).

    Raises RuntimeError if any individual PMO call failed, so a partial
    failure can't silently flow into the join/reshape step below.
    """
    result = subprocess.run(
        ["bash", PMO_SCRIPT, split_dir, str(max_concurrent)],
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        raise RuntimeError(
            f"PMO failed in {result.returncode} subdirectorie(s) under "
            f"{split_dir}. See {split_dir}/pmo_logs/*.log for details.\n"
            f"stderr: {result.stderr}"
        )