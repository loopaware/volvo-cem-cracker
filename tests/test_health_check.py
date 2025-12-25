import subprocess
import time
import pytest
import requests

@pytest.fixture(scope="module")
def services():
    """Fixture to bring up and tear down the Docker Compose services."""
    try:
        # Build and start services in detached mode
        subprocess.run(["docker-compose", "up", "--build", "-d"], check=True)
        
        # Wait for the cem-sim service to be healthy
        # This relies on the healthcheck defined in docker-compose.yml
        # A more robust solution might involve polling the health check endpoint directly
        time.sleep(15) # Give it some time to start and become healthy
        
        yield
    finally:
        # Stop and remove containers, networks, and volumes
        subprocess.run(["docker-compose", "down", "--volumes"], check=True)

def test_health_check_endpoint(services):
    """
    Tests if the health check endpoint on the cem-sim service is responsive
    and returns the correct status.
    """
    try:
        response = requests.get("http://localhost:5001/health")
        # Assert that the request was successful
        assert response.status_code == 200
        # Assert that the response body is what we expect
        assert response.json() == {"status": "ok"}
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Health check request failed: {e}")

def test_cracker_starts_after_sim_is_healthy(services):
    """
    Checks if the cracker service starts up, which implies it waited for the 
    cem-sim service to become healthy. We can verify this by checking the logs
    of the cracker service.
    """
    # Let's give the cracker a moment to run and produce logs
    time.sleep(5)
    
    # Get the logs of the cracker service
    result = subprocess.run(
        ["docker-compose", "logs", "cracker"],
        capture_output=True,
        text=True,
        check=True
    )
    
    # A simple check to see if the cracker's "main" function started
    # This is a basic way to infer it started correctly.
    # A more robust test would be to have the cracker produce a specific output
    # or status that we can check.
    assert "Checking CAN connection..." in result.stdout
