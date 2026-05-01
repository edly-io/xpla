"""
A crude script to load test the call to getState() in a sample activity
"""

from time import time
from pxc.lib.tests.samples.conftest import make_runtime


def main() -> None:
    # We test the math activity, which is fairly simple.
    batch_size = 100
    runtime = make_runtime("math")
    while True:
        time_start = time()
        for _ in range(batch_size):
            runtime.get_state()
        time_end = time()
        time_spent = time_end - time_start
        time_per_sample_ms = time_spent * 1000 / batch_size
        rate_per_s = batch_size / time_spent
        print(
            f"speed: {rate_per_s:.4f} samples/s     time: {time_per_sample_ms:.4f} ms/sample"
        )


if __name__ == "__main__":
    main()
