#!/usr/bin/env python3
"""
BFF Service Setup Verification Script

This script verifies that the BFF service is properly set up and can communicate
with the backend service. It's designed to be run as part of Story 8.1 acceptance testing.
"""

import asyncio
import httpx
import json
import sys
import time
from typing import Dict, Any


class BFFSetupVerifier:
    """Verifies BFF service setup and integration."""
    
    def __init__(self, bff_url: str = "http://127.0.0.1:8001", backend_url: str = "http://127.0.0.1:8000"):
        self.bff_url = bff_url
        self.backend_url = backend_url
        self.results = []
    
    def log_result(self, test_name: str, success: bool, message: str, details: Dict[str, Any] = None):
        """Log test result."""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "details": details or {},
            "timestamp": time.time()
        }
        self.results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        
        if details and not success:
            print(f"   Details: {json.dumps(details, indent=2)}")
    
    async def test_backend_availability(self) -> bool:
        """Test that backend service is available."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.backend_url}/healthz", timeout=5.0)
                
                if response.status_code == 200:
                    data = response.json()
                    self.log_result(
                        "Backend Availability",
                        True,
                        f"Backend service is running and healthy",
                        {"status_code": response.status_code, "response": data}
                    )
                    return True
                else:
                    self.log_result(
                        "Backend Availability",
                        False,
                        f"Backend returned status {response.status_code}",
                        {"status_code": response.status_code}
                    )
                    return False
        
        except Exception as e:
            self.log_result(
                "Backend Availability",
                False,
                f"Cannot connect to backend: {str(e)}",
                {"error": str(e), "backend_url": self.backend_url}
            )
            return False
    
    async def test_bff_health_endpoint(self) -> bool:
        """Test BFF health endpoint."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.bff_url}/api/v1/health", timeout=10.0)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Verify required fields
                    required_fields = ["status", "service", "version", "timestamp", "dependencies", "build_info"]
                    missing_fields = [field for field in required_fields if field not in data]
                    
                    if missing_fields:
                        self.log_result(
                            "BFF Health Endpoint",
                            False,
                            f"Missing required fields: {missing_fields}",
                            {"response": data}
                        )
                        return False
                    
                    # Verify service identification
                    if data["service"] != "hewston-bff":
                        self.log_result(
                            "BFF Health Endpoint",
                            False,
                            f"Incorrect service name: {data['service']}",
                            {"response": data}
                        )
                        return False
                    
                    # Verify backend dependency check
                    if "backend_api" not in data["dependencies"]:
                        self.log_result(
                            "BFF Health Endpoint",
                            False,
                            "Backend API dependency not checked",
                            {"dependencies": data["dependencies"]}
                        )
                        return False
                    
                    self.log_result(
                        "BFF Health Endpoint",
                        True,
                        f"Health endpoint working correctly (status: {data['status']})",
                        {"response": data}
                    )
                    return True
                
                else:
                    self.log_result(
                        "BFF Health Endpoint",
                        False,
                        f"Health endpoint returned status {response.status_code}",
                        {"status_code": response.status_code}
                    )
                    return False
        
        except Exception as e:
            self.log_result(
                "BFF Health Endpoint",
                False,
                f"Cannot connect to BFF health endpoint: {str(e)}",
                {"error": str(e), "bff_url": self.bff_url}
            )
            return False
    
    async def test_bff_readiness_endpoint(self) -> bool:
        """Test BFF readiness endpoint."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.bff_url}/api/v1/health/ready", timeout=5.0)
                
                if response.status_code == 200:
                    data = response.json()
                    self.log_result(
                        "BFF Readiness Endpoint",
                        True,
                        "Readiness endpoint indicates service is ready",
                        {"response": data}
                    )
                    return True
                elif response.status_code == 503:
                    data = response.json()
                    self.log_result(
                        "BFF Readiness Endpoint",
                        False,
                        "Service not ready (503 status)",
                        {"response": data}
                    )
                    return False
                else:
                    self.log_result(
                        "BFF Readiness Endpoint",
                        False,
                        f"Unexpected status code: {response.status_code}",
                        {"status_code": response.status_code}
                    )
                    return False
        
        except Exception as e:
            self.log_result(
                "BFF Readiness Endpoint",
                False,
                f"Cannot connect to BFF readiness endpoint: {str(e)}",
                {"error": str(e)}
            )
            return False
    
    async def test_bff_liveness_endpoint(self) -> bool:
        """Test BFF liveness endpoint."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.bff_url}/api/v1/health/live", timeout=5.0)
                
                if response.status_code == 200:
                    data = response.json()
                    self.log_result(
                        "BFF Liveness Endpoint",
                        True,
                        "Liveness endpoint indicates service is alive",
                        {"response": data}
                    )
                    return True
                else:
                    self.log_result(
                        "BFF Liveness Endpoint",
                        False,
                        f"Liveness check failed with status {response.status_code}",
                        {"status_code": response.status_code}
                    )
                    return False
        
        except Exception as e:
            self.log_result(
                "BFF Liveness Endpoint",
                False,
                f"Cannot connect to BFF liveness endpoint: {str(e)}",
                {"error": str(e)}
            )
            return False
    
    async def test_correlation_id_header(self) -> bool:
        """Test that correlation ID is added to responses."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.bff_url}/api/v1/health/live", timeout=5.0)

                if "X-Correlation-ID" in response.headers:
                    correlation_id = response.headers["X-Correlation-ID"]

                    if len(correlation_id) == 32 and correlation_id.isalnum():
                        self.log_result(
                            "Correlation ID Header",
                            True,
                            "Correlation ID header is present and valid",
                            {"correlation_id": correlation_id}
                        )
                        return True
                    else:
                        self.log_result(
                            "Correlation ID Header",
                            False,
                            "Correlation ID header has invalid format",
                            {"correlation_id": correlation_id}
                        )
                        return False
                else:
                    self.log_result(
                        "Correlation ID Header",
                        False,
                        "Correlation ID header is missing",
                        {"headers": dict(response.headers)}
                    )
                    return False

        except Exception as e:
            self.log_result(
                "Correlation ID Header",
                False,
                f"Error testing correlation ID: {str(e)}",
                {"error": str(e)}
            )
            return False

    async def test_proxy_functionality(self) -> bool:
        """Test basic proxy functionality."""
        try:
            async with httpx.AsyncClient() as client:
                # Test backtests list proxy
                response = await client.get(f"{self.bff_url}/api/v1/backtests", timeout=10.0)

                if response.status_code in [200, 404]:  # 404 is OK if no data
                    self.log_result(
                        "Proxy Functionality",
                        True,
                        f"Backtests proxy working (status: {response.status_code})",
                        {"status_code": response.status_code, "has_correlation_id": "X-Correlation-ID" in response.headers}
                    )
                    return True
                else:
                    self.log_result(
                        "Proxy Functionality",
                        False,
                        f"Unexpected proxy response status: {response.status_code}",
                        {"status_code": response.status_code}
                    )
                    return False

        except Exception as e:
            self.log_result(
                "Proxy Functionality",
                False,
                f"Error testing proxy: {str(e)}",
                {"error": str(e)}
            )
            return False
    
    async def run_all_tests(self) -> bool:
        """Run all verification tests."""
        print("🚀 Starting BFF Service Setup Verification")
        print(f"   BFF URL: {self.bff_url}")
        print(f"   Backend URL: {self.backend_url}")
        print()
        
        tests = [
            self.test_backend_availability,
            self.test_bff_health_endpoint,
            self.test_bff_readiness_endpoint,
            self.test_bff_liveness_endpoint,
            self.test_correlation_id_header,
            self.test_proxy_functionality,
        ]
        
        results = []
        for test in tests:
            result = await test()
            results.append(result)
        
        print()
        print("📊 Test Summary:")
        passed = sum(results)
        total = len(results)
        print(f"   Passed: {passed}/{total}")
        
        if passed == total:
            print("🎉 All tests passed! BFF service is properly set up.")
            return True
        else:
            print("⚠️  Some tests failed. Check the output above for details.")
            return False


async def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Verify BFF service setup")
    parser.add_argument("--bff-url", default="http://127.0.0.1:8001", help="BFF service URL")
    parser.add_argument("--backend-url", default="http://127.0.0.1:8000", help="Backend service URL")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    
    args = parser.parse_args()
    
    verifier = BFFSetupVerifier(args.bff_url, args.backend_url)
    success = await verifier.run_all_tests()
    
    if args.json:
        print(json.dumps(verifier.results, indent=2))
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
