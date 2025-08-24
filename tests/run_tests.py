"""
Test runner script for the GROBID client test suite using pytest.
"""
import sys
import os
import subprocess

# Add the parent directory to the path so we can import the grobid_client module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def run_tests():
    """Run all tests in the test suite."""
    cmd = ["pytest", "tests/", "-v"]
    return subprocess.run(cmd).returncode

def run_unit_tests():
    """Run only unit tests (no integration tests)."""
    cmd = ["pytest", "tests/test_client.py", "tests/test_grobid_client.py", "-v", "-m", "not integration"]
    return subprocess.run(cmd).returncode

def run_integration_tests():
    """Run only integration tests."""
    cmd = ["pytest", "tests/test_integration.py", "-v", "-m", "integration"]
    return subprocess.run(cmd).returncode

def run_with_coverage():
    """Run tests with coverage reporting."""
    cmd = ["pytest", "tests/", "-v", "--cov=grobid_client", "--cov-report=term-missing", "--cov-report=html"]
    return subprocess.run(cmd).returncode

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Run GROBID client tests with pytest')
    parser.add_argument('--unit-only', action='store_true',
                       help='Run only unit tests')
    parser.add_argument('--integration-only', action='store_true',
                       help='Run only integration tests')
    parser.add_argument('--coverage', action='store_true',
                       help='Run tests with coverage reporting')

    args = parser.parse_args()

    if args.unit_only:
        exit_code = run_unit_tests()
    elif args.integration_only:
        exit_code = run_integration_tests()
    elif args.coverage:
        exit_code = run_with_coverage()
    else:
        exit_code = run_tests()

    sys.exit(exit_code)
