"""
Wolfram Engine API Rate Limiter & Throttler
=============================================
Thread-safe Token Bucket rate management for Wolfram Engine / Wolfram Alpha queries.
Prevents endpoint overload, IP bans, and rate-limit errors during hypergraph rule queries.
"""

import time
import math
import random
import threading
from functools import wraps


class WolframRateLimiter:
    """
    Token bucket rate manager for Wolfram queries.
    """

    def __init__(
        self,
        max_requests_per_minute: int = 10,
        burst_capacity: int = 2,
        retry_attempts: int = 5,
        backoff_factor: float = 2.0,
    ):
        """Initializes the WolframRateLimiter.

        Args:
            max_requests_per_minute (int, optional): Maximum allowed requests per minute. Defaults to 10.
            burst_capacity (int, optional): Maximum tokens that can be accumulated. Defaults to 2.
            retry_attempts (int, optional): Number of retry attempts upon failure. Defaults to 5.
            backoff_factor (float, optional): Multiplier for exponential backoff. Defaults to 2.0.
        """
        self.max_rpm = max_requests_per_minute
        self.burst_capacity = burst_capacity
        self.retry_attempts = retry_attempts
        self.backoff_factor = backoff_factor

        # Token refill rate in tokens per second
        self.refill_rate = max_requests_per_minute / 60.0
        self.tokens = float(burst_capacity)
        self.last_refill = time.time()

        self.lock = threading.Lock()
        self.total_queries_issued = 0
        self.total_throttle_wait_sec = 0.0

    def _refill_tokens(self):
        """Refills the token bucket based on elapsed time and refill rate."""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(
            float(
                self.burst_capacity),
            self.tokens +
            elapsed *
            self.refill_rate)
        self.last_refill = now

    def acquire(self):
        """
        Blocks until a rate-limiting token is available.
        """
        with self.lock:
            while True:
                self._refill_tokens()
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    self.total_queries_issued += 1
                    return

                # Calculate sleep duration needed for 1 token
                needed = 1.0 - self.tokens
                sleep_time = needed / self.refill_rate
                self.total_throttle_wait_sec += sleep_time
                time.sleep(sleep_time)

    def execute_with_rate_limit(self, func, *args, **kwargs):
        """
        Executes func with token rate limiting and exponential backoff on failure/429.
        """
        self.acquire()

        for attempt in range(1, self.retry_attempts + 1):
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as err:
                err_str = str(err).lower()
                is_rate_limit = "429" in err_str or "rate" in err_str or "limit" in err_str or "throttled" in err_str

                if attempt == self.retry_attempts:
                    raise err

                # Exponential backoff with jitter
                sleep_duration = (self.backoff_factor **
                                  attempt) + random.uniform(0.1, 1.0)
                if is_rate_limit:
                    sleep_duration *= 2.0  # Double wait if explicitly rate-limited

                print(
                    f"⚠️ Wolfram API call failed (Attempt {attempt}/{self.retry_attempts}): {err}. Retrying in {sleep_duration:.2f}s...")
                time.sleep(sleep_duration)


def rate_limited(limiter: WolframRateLimiter):
    """
    Decorator for wrapping Wolfram query functions with rate limiting.
    """
    def decorator(func):
        """Wraps the target function with the rate limiter.

        Args:
            func: The function to be rate-limited.

        Returns:
            The wrapped function.
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            """Executes the wrapped function through the rate limiter.

            Args:
                *args: Positional arguments for the wrapped function.
                **kwargs: Keyword arguments for the wrapped function.

            Returns:
                The result of the wrapped function.
            """
            return limiter.execute_with_rate_limit(func, *args, **kwargs)
        return wrapper
    return decorator


if __name__ == "__main__":
    limiter = WolframRateLimiter(max_requests_per_minute=20, burst_capacity=2)

    @rate_limited(limiter)
    def dummy_wolfram_query(query_id: int):
        """Simulates a Wolfram Engine API query.

        Args:
            query_id (int): The ID of the simulated query.

        Returns:
            str: The simulated result.
        """
        print(f"[{time.strftime('%H:%M:%S')}] Executing Wolfram Query #{query_id}")
        return f"Result_{query_id}"

    print("Testing Wolfram Rate Limiter (20 RPM burst=2):")
    start = time.time()
    for i in range(5):
        dummy_wolfram_query(i + 1)
    print(f"Completed 5 queries in {time.time() - start:.2f}s.")
