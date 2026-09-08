import sys
import time

def main():
    print("=" * 60)
    print("  SUPERJOIN FACT KNOWLEDGE LAYER - FULL TEST SUITE")
    print("=" * 60)

    start_time = time.time()

    # 1. Environment & Datasets
    print("\n>>> RUNNING TEST 1/4: Environment & Dataset Check")
    from verify_setup import verify
    assert verify() is True, "Environment verification failed"

    # 2. Storage & Pydantic Data Contracts
    print("\n>>> RUNNING TEST 2/4: Storage Engine & Model Contracts")
    from test_storage import test_storage
    test_storage()

    # 3. Cross-Document Reconciliation Logic (The 4 Cases)
    print("\n>>> RUNNING TEST 3/4: Four Required Evaluation Cases")
    from test_reconciler import test_four_cases
    test_four_cases()

    # 4. FastAPI REST Endpoints
    print("\n>>> RUNNING TEST 4/4: FastAPI Route Handlers & Integration")
    from test_api import test_fastapi_endpoints
    test_fastapi_endpoints()

    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"  ALL TESTS PASSED SUCCESSFULLY in {elapsed:.2f}s!")
    print("=" * 60)

if __name__ == "__main__":
    main()