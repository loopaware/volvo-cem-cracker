# Plan for adding a health check

1.  **DONE** Create `src/health_check.py` to check the health of the `cem-sim` service.
2.  **DONE** Modify `src/sim_cem.py` to include a Flask-based health check endpoint.
3.  **DONE** Update `docker-compose.yml` to use the health check and install `Flask` and `requests`.
4.  **DONE** Restore `src/main.py` file.
5.  **DONE** Update the `docker-compose.yml` file to use `src/main.py` instead of `src/cracker.py` and add the `service_healthy` condition.
6.  **DONE** Remove `Flask` and `requests` from `requirements.txt` as they are only used for the health check in the Docker environment.
7.  **DONE** Create `tests/test_health_check.py` to validate the health check.
8.  **DONE** Add `pytest` to `requirements.txt`.
