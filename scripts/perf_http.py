#!/usr/bin/env python3
"""
HTTP Performance Harness for AE v2.

This script measures HTTP performance by making concurrent requests
and calculating latency percentiles.
"""

import argparse
import asyncio
import aiohttp
import json
import time
import statistics
from typing import List, Dict, Any


async def make_request(
    session: aiohttp.ClientSession, url: str, data: Dict[str, Any]
) -> Dict[str, Any]:
    """Make a single HTTP request and return timing data."""
    start_time = time.time()

    try:
        async with session.post(url, json=data) as response:
            response_text = await response.text()
            end_time = time.time()

            return {
                "status": response.status,
                "latency_ms": (end_time - start_time) * 1000,
                "success": response.status == 200,
                "response_size": len(response_text),
            }
    except Exception as e:
        end_time = time.time()
        return {
            "status": 0,
            "latency_ms": (end_time - start_time) * 1000,
            "success": False,
            "error": str(e),
        }


async def run_performance_test(
    base_url: str, total_requests: int, concurrency: int, test_queries: List[str]
) -> Dict[str, Any]:
    """Run performance test with specified parameters."""

    # Prepare test data
    test_data = []
    for i in range(total_requests):
        query = test_queries[i % len(test_queries)]
        test_data.append({"query": query})

    # Create session with connection pooling
    connector = aiohttp.TCPConnector(limit=concurrency, limit_per_host=concurrency)
    timeout = aiohttp.ClientTimeout(total=30)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(concurrency)

        async def bounded_request(data):
            async with semaphore:
                return await make_request(session, f"{base_url}/query?mode=auto", data)

        # Run requests
        start_time = time.time()
        tasks = [bounded_request(data) for data in test_data]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()

        # Process results
        latencies = []
        successful_requests = 0
        failed_requests = 0
        errors = []

        for result in results:
            if isinstance(result, Exception):
                failed_requests += 1
                errors.append(str(result))
            elif result.get("success"):
                latencies.append(result["latency_ms"])
                successful_requests += 1
            else:
                failed_requests += 1
                errors.append(f"HTTP {result.get('status', 'unknown')}")

        # Calculate statistics
        if latencies:
            latencies.sort()
            total_time = end_time - start_time

            return {
                "summary": {
                    "total_requests": total_requests,
                    "successful_requests": successful_requests,
                    "failed_requests": failed_requests,
                    "success_rate": successful_requests / total_requests,
                    "total_time_seconds": total_time,
                    "requests_per_second": total_requests / total_time,
                },
                "latency_ms": {
                    "min": min(latencies),
                    "max": max(latencies),
                    "mean": statistics.mean(latencies),
                    "median": statistics.median(latencies),
                    "p50": latencies[int(len(latencies) * 0.5)],
                    "p90": latencies[int(len(latencies) * 0.9)],
                    "p95": latencies[int(len(latencies) * 0.95)],
                    "p99": latencies[int(len(latencies) * 0.99)],
                    "stddev": statistics.stdev(latencies) if len(latencies) > 1 else 0,
                },
                "errors": errors[:10] if errors else [],  # Limit error list
            }
        else:
            return {
                "summary": {
                    "total_requests": total_requests,
                    "successful_requests": 0,
                    "failed_requests": failed_requests,
                    "success_rate": 0.0,
                    "total_time_seconds": end_time - start_time,
                    "requests_per_second": 0.0,
                },
                "latency_ms": {
                    "min": 0,
                    "max": 0,
                    "mean": 0,
                    "median": 0,
                    "p50": 0,
                    "p90": 0,
                    "p95": 0,
                    "p99": 0,
                    "stddev": 0,
                },
                "errors": errors,
            }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="AE v2 HTTP Performance Harness")
    parser.add_argument(
        "--base", default="http://localhost:8001", help="Base URL for API"
    )
    parser.add_argument(
        "--total", type=int, default=100, help="Total number of requests"
    )
    parser.add_argument(
        "--concurrency", type=int, default=10, help="Concurrent requests"
    )
    parser.add_argument("--json", default="perf_http.json", help="Output JSON file")
    parser.add_argument(
        "--metrics", action="store_true", help="Fetch metrics after test"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Test queries
    test_queries = [
        "what is ospf",
        "define tcp",
        "what is arp",
        "explain bgp",
        "ipv6 overview",
        "icmp protocol",
        "dns explanation",
        "routing protocols",
    ]

    print("Starting performance test...")
    print(f"  Base URL: {args.base}")
    print(f"  Total requests: {args.total}")
    print(f"  Concurrency: {args.concurrency}")
    print(f"  Test queries: {len(test_queries)}")

    # Run test
    start_time = time.time()
    result = asyncio.run(
        run_performance_test(args.base, args.total, args.concurrency, test_queries)
    )
    end_time = time.time()

    # Print results
    summary = result["summary"]
    latency = result["latency_ms"]

    print("\nPerformance Results:")
    print(f"  Total time: {summary['total_time_seconds']:.2f}s")
    print(f"  Requests/sec: {summary['requests_per_second']:.1f}")
    print(f"  Success rate: {summary['success_rate']:.1%}")
    print(f"  Successful: {summary['successful_requests']}/{summary['total_requests']}")

    if summary["successful_requests"] > 0:
        print("\nLatency (ms):")
        print(f"  Min: {latency['min']:.1f}")
        print(f"  Mean: {latency['mean']:.1f}")
        print(f"  Median: {latency['median']:.1f}")
        print(f"  P50: {latency['p50']:.1f}")
        print(f"  P90: {latency['p90']:.1f}")
        print(f"  P95: {latency['p95']:.1f}")
        print(f"  P99: {latency['p99']:.1f}")
        print(f"  Max: {latency['max']:.1f}")
        print(f"  StdDev: {latency['stddev']:.1f}")

    if result.get("errors"):
        print(f"\nErrors ({len(result['errors'])}):")
        for error in result["errors"][:5]:  # Show first 5 errors
            print(f"  - {error}")

    # Fetch metrics if requested
    metrics_data = None
    if args.metrics:
        try:
            import aiohttp

            async def fetch_metrics():
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{args.base}/metrics") as response:
                        if response.status == 200:
                            return await response.text()
                        return None

            metrics_data = asyncio.run(fetch_metrics())
            if metrics_data:
                # Save raw metrics
                with open("perf_metrics.prom", "w") as f:
                    f.write(metrics_data)
                print("Metrics saved to: perf_metrics.prom")

                # Extract key metrics for summary
                metrics_summary = {}
                for line in metrics_data.split("\n"):
                    if line.startswith("ae_http_request_latency_ms_sum"):
                        metrics_summary["latency_sum"] = line.split(" ")[1]
                    elif line.startswith("ae_http_request_latency_ms_count"):
                        metrics_summary["latency_count"] = line.split(" ")[1]
                    elif line.startswith("ae_router_intent_total"):
                        metrics_summary["router_intents"] = line.split(" ")[1]
                    elif line.startswith("ae_cache_hits_total"):
                        metrics_summary["cache_hits"] = line.split(" ")[1]
                    elif line.startswith("ae_cache_misses_total"):
                        metrics_summary["cache_misses"] = line.split(" ")[1]

                # Save metrics summary
                with open("perf_summary.json", "w") as f:
                    json.dump(
                        {
                            "timestamp": time.time(),
                            "test_args": vars(args),
                            "performance": result,
                            "metrics": metrics_summary,
                        },
                        f,
                        indent=2,
                    )
                print("Summary saved to: perf_summary.json")
        except Exception as e:
            print(f"Warning: Failed to fetch metrics: {e}")

    # Save results
    result["metadata"] = {
        "timestamp": time.time(),
        "test_duration_seconds": end_time - start_time,
        "args": vars(args),
    }

    with open(args.json, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\nResults saved to: {args.json}")

    # Exit with error if success rate is too low
    if summary["success_rate"] < 0.8:
        print(f"\nWARNING: Low success rate ({summary['success_rate']:.1%})")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
