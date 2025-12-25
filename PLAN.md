2025-12-25 11:35:00
## Objective: Create a high-fidelity local hardware simulation and testing suite using a Proxmox LXC container (Debian 13).

## Strategy
Instead of battling Proxmox API token permissions with OpenTofu, we will utilize direct host access via SSH to provision the LXC container using `pct`. This ensures maximum compatibility and speed.

## Tasks:
* [x] Initialize pytest-based testing framework.
* [x] Create 'src/sim_cem.py' - A standalone Volvo CEM simulator.
* [in_progress] Provision a Debian 13 (Trixie) LXC on Proxmox (10.32.2.11).
    * [x] Verify host connectivity and template availability.
    * [ ] Create LXC using `pct` over SSH.
    * [ ] Configure LXC for `vcan` networking and Python dependencies.
* [ ] Deploy code to LXC via Ansible/Rsync.
* [ ] Run hardware simulation tests (Timing Attack & Brute Force) inside the LXC.
* [ ] Document the "Remote-Sim" workflow.