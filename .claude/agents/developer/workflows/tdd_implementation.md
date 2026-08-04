# TDD Implementation Workflow

Execute these steps sequentially for the provided `phase id`. Use your shell/terminal and file system tools to run tests, linters, and git commands.

## Step 1: Context Ingestion
Before writing any code, load the rules and boundaries for this specific phase:
1. **Guidelines:** Read `./markdowns/developer_notes.md`. You must strictly adhere to these coding standards.
2. **Architecture:** Read the artifacts located at `./artifacts/architecture/<phase_id>/`. Pay special attention to the scope demarcations (`<!-- PHASE: [Phase Name] START -->`) and the `archunit_specs.md`.
3. **Stories:** Read the user stories for this phase located in `./artifacts/development_plan/<phase_id>/`. 

## Step 2: The Story Execution Loop
You must treat a single "story" as your unit of development. For *each* story in the current phase, execute the following TDD loop:

### A. Test (Red)
1. Analyze the current story and the corresponding architectural constraints.
2. Write the unit and integration tests for this specific story. 
3. *Execution:* Run the test suite. **Verify that the tests fail.** If they do not fail, your tests are invalid or testing existing behavior. 

### B. Implement (Green)
1. Write the minimal production code required to make the failing tests pass.
2. Ensure you are implementing the stubs/interfaces defined in the architecture document for future-proofing, but do *not* implement the actual logic for future phases.
3. *Execution:* Run the test suite again. **Verify that the tests pass.**

### C. Refactor & Validate
1. Clean up the code. Ensure naming conventions match the `archunit_specs.md` and `developer_notes.md`.
2. *Execution:* Run the lint checks defined in the root `lint` configuration file (e.g., `npm run lint`, `flake8`, `golangci-lint`, depending on the project).
3. Fix any linting errors. 
4. *Execution:* Run the entire test suite one last time to ensure no regressions were introduced.

### D. Commit
Once linting and all tests pass for the story, create a git commit. 
* You must use the **Conventional Commits** format (e.g., `feat(scope): description`, `fix(scope): description`, `test(scope): description`).
* Stage the changes and execute the commit via your terminal tools.

## Step 3: Loop or Complete
Move to the next story in `./artifacts/development_plan/<phase_id>/` and repeat Step 2. If all stories for the current phase are complete, report success to the user and stop. Do not proceed to the next phase.