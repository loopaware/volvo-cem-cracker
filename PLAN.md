# Plan: Resume Functionality

## Objective
Implement persistent state saving to allow the cracker to resume after power loss or interruption.

## Requirements
1.  **Persistence**: Save current progress to a file (`session.json`).
2.  **Safety**: Upon resume, "rewind" a safe number of attempts (e.g., 500) to account for potential uncommitted writes or interruption timing.
3.  **Efficiency**: Do not write to disk on every attempt. Write periodically (e.g., every 100 attempts).

## Implementation Details
*   **File**: `session.json` in the application directory.
*   **Class `VolvoCracker`**:
    *   `load_session()`: Reads `session.json`. Returns the configuration (fixed bytes) and the starting index (minus safety margin).
    *   `save_session(index, fixed_bytes)`: Writes current index and configuration to disk.
    *   `brute_force`:
        *   Accept `start_index` (default 0).
        *   Loop `i` from `start_index` to `total`.
        *   Call `save_session` every 100 iterations.
    *   `run`:
        *   Check for existing session.
        *   If exists, prompt/auto-resume.
        *   If resume, skip Timing Attack and go straight to `brute_force` with restored parameters.

## Data Structure (`session.json`)
```json
{
  "fixed_bytes": [1, 2, 3, 0, 0, 0], 
  "index": 15000,
  "timestamp": 1700000000
}
```

## "Rewind" Logic
*   `resume_index = max(0, saved_index - 500)`
*   This ensures we re-try the last few seconds of work.

## Verification
*   Deploy to Pi.
*   Start cracker.
*   Interrupt (Ctrl+C or kill).
*   Restart and verify it picks up near where it left off.
