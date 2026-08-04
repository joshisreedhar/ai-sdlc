# QA Execution Workflow

Execute these steps sequentially for the provided `phase id`. Use your file system tools to read requirements, analyze code, and write E2E tests.

## Step 1: Context & Tech Stack Ingestion
1. **Read Requirements:** Parse the global requirements in `./markdowns/REQUIREMENTS.md`.
2. **Read Phase Stories:** Parse the specific user stories for this phase in `./artifacts/development_plan/<phase_id>/`.
3. **Determine Tech Stack:** Analyze the project's configuration files (e.g., `package.json`, `pom.xml`, `requirements.txt`) to determine the appropriate E2E framework. 
   * *UI Apps:* Prefer Playwright or Cypress unless otherwise configured.
   * *API Apps:* Prefer Supertest (Node), RestAssured (Java), or Pytest (Python) unless otherwise configured.

## Step 2: Developer Test Audit (Gap Analysis)
1. Read the unit and integration tests written by the Developer Agent for the current phase.
2. Compare the developer's test coverage against the acceptance criteria in the phase stories and the global requirements.
3. Look specifically for missing edge cases, unhandled error states, and missing cross-module integration tests.
4. Read `./templates/gap_analysis_report.md`. Generate the report and write it to `./artifacts/qa/<phase_id>/developer_test_gaps.md`.
5. *Action:* If critical gaps are found, halt and present the report to the user to send back to the Developer Agent. If gaps are minor or none exist, proceed to Step 3.

## Step 3: E2E Test Implementation
1. Map out the critical user journeys (for UI) or API consumer flows (for API) defined in the current phase stories.
2. Write the E2E test files in the project's designated E2E testing directory (e.g., `./tests/e2e/`, `./cypress/e2e/`).
3. Ensure tests include proper setup/teardown mechanics (e.g., database seeding, mock external services) if required by the architecture.
4. Ensure E2E tests strictly respect the phase boundary—do not write tests that attempt to interact with buttons, endpoints, or features planned for future phases.

## Step 4: Execution & Commit
1. *Execution:* Run the newly created E2E test suite using your terminal tools. The application development is containerized, so if needed you can bring the environment up and bring it down on demand.
2. Fix any issues in your test code if they fail due to brittle selectors or incorrect assertions. (If they fail due to actual application bugs, report them to the user).
3. Once the E2E suite passes, commit the QA artifacts and test code using the **Conventional Commits** format (e.g., `test(e2e): implement user registration journey`).