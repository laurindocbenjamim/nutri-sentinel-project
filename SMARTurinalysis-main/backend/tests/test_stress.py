"""
Stress tests for verifying high-load resilience of the analysis endpoint.
"""

import io
import time
import concurrent.futures
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def run_single_upload(image_bytes: bytes) -> tuple:
    """
    Runs a single analysis upload request and returns the status code and duration.
    """
    file_payload = {
        "file": ("mock_photo.png", io.BytesIO(image_bytes), "image/png")
    }
    start_time = time.time()
    try:
        response = client.post("/api/analysis/upload", files=file_payload)
        duration = time.time() - start_time
        return response.status_code, duration
    except Exception as e:
        duration = time.time() - start_time
        return 500, duration

def test_endpoint_stress_concurrency():
    """
    Simulates peak concurrent traffic on the /api/analysis/upload endpoint.
    Sends 10 concurrent requests and checks that all complete successfully
    with latency and status code assertions.
    """
    # 1. Get mock photo bytes
    gen_response = client.post("/api/synthetic/generate", json={"selections": {}})
    assert gen_response.status_code == 200
    mock_url = gen_response.json()["mock_image_url"]
    
    mock_img_response = client.get(mock_url)
    assert mock_img_response.status_code == 200
    image_bytes = mock_img_response.content

    # Number of concurrent requests to simulate
    num_requests = 10
    
    print(f"Starting stress test with {num_requests} concurrent requests...")
    
    # 2. Run concurrent requests using ThreadPoolExecutor
    start_total = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_requests) as executor:
        futures = [executor.submit(run_single_upload, image_bytes) for _ in range(num_requests)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    total_duration = time.time() - start_total
    
    # 3. Assert and analyze results
    success_count = 0
    durations = []
    
    for status_code, duration in results:
        durations.append(duration)
        if status_code == 200:
            success_count += 1
            
    avg_duration = sum(durations) / len(durations)
    print(f"Stress test completed. Success rate: {success_count}/{num_requests}")
    print(f"Total time: {total_duration:.2f}s, Avg request time: {avg_duration:.2f}s")
    
    assert success_count == num_requests, f"Only {success_count}/{num_requests} requests succeeded."
    # Ensure average response time is under 2.5 seconds per request (ORB matching can take up to 0.5s per image)
    assert avg_duration < 2.5, f"Average request latency {avg_duration:.2f}s is too high."
