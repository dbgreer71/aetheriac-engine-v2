"""
Golden test suite for AE v2.

This module contains golden tests that validate the core functionality
of the Aetheriac Engine v2 system with predefined test cases.
"""

import asyncio
import json
import logging
import os
import time
from typing import Dict

import pytest

from ..assembler.definition_assembler import DefinitionAssembler
from ..contracts.models import Query, QueryType
from ..retriever.hybrid_ranker import HybridRanker
from ..router.definitional_router import DefinitionalRouter
from ..storage.index_builder import IndexBuilder

logger = logging.getLogger(__name__)


class GoldenTestSuite:
    """Golden test suite for validating AE v2 functionality."""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.golden_tests")
        self.router = DefinitionalRouter()

        # Only initialize HybridRanker if dense models are enabled
        self.ranker = None
        if os.getenv("ENABLE_DENSE", "0").lower() in ("1", "true", "yes"):
            try:
                self.ranker = HybridRanker()
            except Exception as e:
                self.logger.warning(f"Failed to initialize HybridRanker: {e}")

        self.assembler = DefinitionAssembler()
        self.index_builder = IndexBuilder()

        # Golden test cases
        self.definition_tests = [
            {
                "query": "What is ARP?",
                "expected_type": QueryType.DEFINITION,
                "expected_confidence_min": 0.6,
                "expected_rfc_numbers": [826],  # ARP RFC
                "description": "ARP definition query",
            },
            {
                "query": "Define OSPF",
                "expected_type": QueryType.DEFINITION,
                "expected_confidence_min": 0.6,
                "expected_rfc_numbers": [2328],  # OSPF RFC
                "description": "OSPF definition query",
            },
            {
                "query": "What is BGP?",
                "expected_type": QueryType.DEFINITION,
                "expected_confidence_min": 0.6,
                "expected_rfc_numbers": [4271],  # BGP RFC
                "description": "BGP definition query",
            },
            {
                "query": "Explain TCP",
                "expected_type": QueryType.DEFINITION,
                "expected_confidence_min": 0.6,
                "expected_rfc_numbers": [793],  # TCP RFC
                "description": "TCP definition query",
            },
        ]

        self.concept_tests = [
            {
                "query": "Compare ARP and DNS",
                "expected_type": QueryType.CONCEPT,
                "expected_confidence_min": 0.5,
                "expected_rfc_numbers": [826, 1034],  # ARP and DNS RFCs
                "description": "ARP vs DNS comparison",
            },
            {
                "query": "Difference between OSPF and BGP",
                "expected_type": QueryType.CONCEPT,
                "expected_confidence_min": 0.5,
                "expected_rfc_numbers": [2328, 4271],  # OSPF and BGP RFCs
                "description": "OSPF vs BGP comparison",
            },
        ]

        self.troubleshooting_tests = [
            {
                "query": "OSPF neighbor down",
                "expected_type": QueryType.TROUBLESHOOTING,
                "expected_confidence_min": 0.4,
                "expected_rfc_numbers": [2328],  # OSPF RFC
                "description": "OSPF troubleshooting query",
            },
            {
                "query": "BGP not working",
                "expected_type": QueryType.TROUBLESHOOTING,
                "expected_confidence_min": 0.4,
                "expected_rfc_numbers": [4271],  # BGP RFC
                "description": "BGP troubleshooting query",
            },
        ]

    async def setup(self) -> bool:
        """Setup the test environment."""
        try:
            # Ensure index exists
            if not self.index_builder.index_exists():
                self.logger.info("Building index for golden tests")
                await self.index_builder.build_index()

            # Load documents into ranker
            documents = self.index_builder.load_documents()
            if not documents:
                self.logger.error("No documents loaded for golden tests")
                return False

            if self.ranker is not None:
                self.ranker.build_index(documents)
                self.logger.info(f"Loaded {len(documents)} documents for golden tests")
            else:
                self.logger.info(
                    "HybridRanker not available, skipping dense index build"
                )
            return True

        except Exception as e:
            self.logger.error(f"Failed to setup golden tests: {e}")
            return False

    def test_router_classification(self) -> Dict[str, any]:
        """Test query classification by the router."""
        results = {"passed": 0, "failed": 0, "total": 0, "details": []}

        all_tests = (
            self.definition_tests + self.concept_tests + self.troubleshooting_tests
        )

        for test_case in all_tests:
            results["total"] += 1

            try:
                query = Query(text=test_case["query"])
                routing_info = self.router.route_query(query)

                # Check query type classification
                if routing_info["query_type"] == test_case["expected_type"]:
                    results["passed"] += 1
                    status = "PASS"
                else:
                    results["failed"] += 1
                    status = "FAIL"

                results["details"].append(
                    {
                        "test": test_case["description"],
                        "query": test_case["query"],
                        "expected_type": test_case["expected_type"],
                        "actual_type": routing_info["query_type"],
                        "confidence": routing_info["confidence"],
                        "status": status,
                    }
                )

            except Exception as e:
                results["failed"] += 1
                results["details"].append(
                    {
                        "test": test_case["description"],
                        "query": test_case["query"],
                        "error": str(e),
                        "status": "ERROR",
                    }
                )

        return results

    def test_definition_queries(self) -> Dict[str, any]:
        """Test definition query processing."""
        results = {"passed": 0, "failed": 0, "total": 0, "details": []}

        for test_case in self.definition_tests:
            results["total"] += 1

            try:
                query = Query(text=test_case["query"])

                # Retrieve sections
                if self.ranker is not None:
                    retrieved_sections = self.ranker.search(query=query.text, top_k=5)
                else:
                    # Skip dense retrieval when HybridRanker is not available
                    retrieved_sections = []

                # Assemble response
                query_id = f"golden_test_{int(time.time() * 1000)}"
                response = self.assembler.assemble_definition(
                    query=query,
                    retrieved_sections=retrieved_sections,
                    query_id=query_id,
                )

                # Validate response
                passed = True
                issues = []

                # Check confidence
                if response.confidence < test_case["expected_confidence_min"]:
                    passed = False
                    issues.append(
                        f"Low confidence: {response.confidence:.2f} < {test_case['expected_confidence_min']}"
                    )

                # Check response type
                if response.response_type != QueryType.DEFINITION:
                    passed = False
                    issues.append(f"Wrong response type: {response.response_type}")

                # Check content
                if not response.content.get("definition"):
                    passed = False
                    issues.append("No definition in response")

                # Check citations
                if not response.citations:
                    passed = False
                    issues.append("No citations in response")

                if passed:
                    results["passed"] += 1
                    status = "PASS"
                else:
                    results["failed"] += 1
                    status = "FAIL"

                results["details"].append(
                    {
                        "test": test_case["description"],
                        "query": test_case["query"],
                        "confidence": response.confidence,
                        "processing_time_ms": response.processing_time_ms,
                        "citations_count": len(response.citations),
                        "issues": issues,
                        "status": status,
                    }
                )

            except Exception as e:
                results["failed"] += 1
                results["details"].append(
                    {
                        "test": test_case["description"],
                        "query": test_case["query"],
                        "error": str(e),
                        "status": "ERROR",
                    }
                )

        return results

    def test_performance_metrics(self) -> Dict[str, any]:
        """Test performance metrics."""
        results = {
            "avg_processing_time_ms": 0.0,
            "max_processing_time_ms": 0.0,
            "min_processing_time_ms": float("inf"),
            "total_queries": 0,
            "performance_threshold_ms": 500,  # 500ms threshold
            "passed": 0,
            "failed": 0,
        }

        all_tests = (
            self.definition_tests + self.concept_tests + self.troubleshooting_tests
        )

        for test_case in all_tests:
            try:
                start_time = time.time() * 1000

                query = Query(text=test_case["query"])
                _ = self.router.route_query(query)  # Route but don't use result

                if self.ranker is not None:
                    retrieved_sections = self.ranker.search(query=query.text, top_k=5)
                else:
                    retrieved_sections = []

                query_id = f"perf_test_{int(time.time() * 1000)}"
                _ = self.assembler.assemble_definition(
                    query=query,
                    retrieved_sections=retrieved_sections,
                    query_id=query_id,
                )

                processing_time = time.time() * 1000 - start_time
                results["total_queries"] += 1
                results["avg_processing_time_ms"] += processing_time
                results["max_processing_time_ms"] = max(
                    results["max_processing_time_ms"], processing_time
                )
                results["min_processing_time_ms"] = min(
                    results["min_processing_time_ms"], processing_time
                )

                if processing_time <= results["performance_threshold_ms"]:
                    results["passed"] += 1
                else:
                    results["failed"] += 1

            except Exception as e:
                self.logger.error(
                    f"Performance test failed for {test_case['query']}: {e}"
                )

        if results["total_queries"] > 0:
            results["avg_processing_time_ms"] /= results["total_queries"]

        if results["min_processing_time_ms"] == float("inf"):
            results["min_processing_time_ms"] = 0.0

        return results

    async def run_all_tests(self) -> Dict[str, any]:
        """Run all golden tests and return comprehensive results."""
        self.logger.info("Starting golden test suite")

        # Setup
        if not await self.setup():
            return {"error": "Failed to setup test environment"}

        # Run tests
        router_results = self.test_router_classification()
        definition_results = self.test_definition_queries()
        performance_results = self.test_performance_metrics()

        # Compile results
        total_tests = router_results["total"] + definition_results["total"]
        total_passed = router_results["passed"] + definition_results["passed"]
        total_failed = router_results["failed"] + definition_results["failed"]

        overall_results = {
            "timestamp": time.time(),
            "summary": {
                "total_tests": total_tests,
                "passed": total_passed,
                "failed": total_failed,
                "success_rate": (
                    (total_passed / total_tests * 100) if total_tests > 0 else 0
                ),
            },
            "router_tests": router_results,
            "definition_tests": definition_results,
            "performance_tests": performance_results,
            "index_stats": (
                self.ranker.get_index_stats() if self.ranker is not None else {}
            ),
        }

        self.logger.info(f"Golden tests completed: {total_passed}/{total_tests} passed")
        return overall_results


# Pytest fixtures and tests
@pytest.fixture
async def golden_test_suite():
    """Fixture for golden test suite."""
    suite = GoldenTestSuite()
    await suite.setup()
    return suite


@pytest.mark.golden
@pytest.mark.asyncio
async def test_router_classification(golden_test_suite):
    """Test query classification."""
    results = golden_test_suite.test_router_classification()
    assert results["failed"] == 0, f"Router classification failed: {results['details']}"


@pytest.mark.golden
@pytest.mark.asyncio
async def test_definition_queries(golden_test_suite):
    """Test definition query processing."""
    results = golden_test_suite.test_definition_queries()
    assert results["failed"] == 0, f"Definition queries failed: {results['details']}"


@pytest.mark.golden
@pytest.mark.asyncio
async def test_performance_metrics(golden_test_suite):
    """Test performance metrics."""
    results = golden_test_suite.test_performance_metrics()
    assert results["failed"] == 0, f"Performance tests failed: {results}"


@pytest.mark.golden
@pytest.mark.asyncio
async def test_full_golden_suite():
    """Run the complete golden test suite."""
    suite = GoldenTestSuite()
    results = await suite.run_all_tests()

    assert "error" not in results, f"Golden test suite failed: {results}"
    assert (
        results["summary"]["success_rate"] >= 90
    ), f"Success rate too low: {results['summary']['success_rate']}%"


if __name__ == "__main__":

    async def main():
        suite = GoldenTestSuite()
        results = await suite.run_all_tests()
        print(json.dumps(results, indent=2))

    asyncio.run(main())
