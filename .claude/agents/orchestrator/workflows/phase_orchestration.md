# Phase Orchestration Workflow

Execute these steps sequentially. Use the `Agent` tool to delegate tasks to the other sub-agents.

## Step 0: Development Plan 
1. Invoke the technical-manager agent and create the development plan for all phases and **WAIT FOR USER TO APPROVE THE DEVELOPMENT PLAN**


## Step 1: Ingest the Plan
1. Read subfolders in `./artifacts/development_plan`.
2. Extract the ordered list of all `phase id`s.

## Step 2: The Phase Loop
For each `phase id` in order, execute the following hand-offs synchronously. Do not start a new phase until the current phase is fully QA-approved.

### A. Architecture Phase
1. Explicitly invoke the Architect agent: 
   `Use the architect agent to generate architecture artifacts for phase: <phase_id>.`
2. Wait for the `architect` to report completion. Verify the generated artifacts exist in `./artifacts/architecture/<phase_id>/`.

### B. Development Phase
1. Explicitly invoke the Developer agent: 
   `Use the developer agent to implement the stories and write unit tests for phase: <phase_id>.`
2. Wait for the `developer` to report completion and verify that a git commit was made.

### C. QA Phase & Feedback Loop
1. Explicitly invoke the QA agent: 
   `Use the quality-agent to audit tests and write E2E tests for phase: <phase_id>.`
2. **Handling Rejections:** If the `quality-agent` generates a `developer_test_gaps.md` report and fails the phase, you must invoke the `developer` agent again. Pass the gap report to the developer and instruct it to fix the missing test coverage.
3. Once the `quality-agent` reports success and the E2E test suite passes, the phase is considered complete.

## Step 3: Next Phase
Proceed to the next `phase id` in the loop. When all phases in the development plan are complete, print a final project summary to the user detailing what was built across all phases.