# Architecture Generation Workflow

Execute the following steps sequentially. Use your file system tools to read inputs, create directories, and write outputs.

## Step 1: Ingest Inputs
1. Read the overarching architectural constraints and guidelines `architecture_guidance.md` under markdowns folder preset in root.
2. Read the requirements available at `markdowns/REQUIREMENTS.md`
3. Read the project phases and feature breakdown from folders representing each phase under `./artifacts/development_plan/<phasename>/phase_summary.md`.

## Step 2: Prepare Workspace
Go over all folders under development_plan, analyze the `phase_summary.md` for each phase to identify all project phases. Ensure the following directory structure exists (create missing folders):
* `./artifacts/architecture/` (Root architecture folder)
* `./artifacts/architecture/<phase_name>/` (Create a child folder for each phase using the exact naming convention found in the development plan).

## Step 3: Generate Overall Architecture
Read the template at `./templates/c4_architecture.md`. 
Using the ingested inputs, generate the overarching C4 Architecture Document that encompasses **all phases**. Write this file to `./artifacts/architecture/overall_architecture.md`.

## Step 4: Generate Phase-Specific Artifacts
For **each** phase identified in Step 1, you must generate three specific artifacts. Process one phase entirely before moving to the next.

For the current phase:
1. **Phase Architecture:** Read `./templates/c4_architecture.md`. Generate a phase-scoped C4 document. Write to `./artifacts/architecture/<phase_name>/c4_architecture.md`.
2. **Diagrams:** Read `./templates/puml_diagrams.md`. Generate the module dependencies and sequence diagrams for this phase. Write to `./artifacts/architecture/<phase_name>/system_diagrams.md`.
3. **QA Specs:** Read `./templates/archunit_specs.md`. Generate the ArchUnit rules for this phase. Write to `./artifacts/architecture/<phase_name>/archunit_specs.md`.

## Step 5: Create project structre
1. **Phase Architecture:** Depending on the platform and language as defined in the architecture_guidance.md in markdowns folder, create or add package and folder structure that developer and QA can use to build their code
2. **Test Cases:** Depending on the platform and language as defined in the architecture_guidance.md in markdowns folder, implement the Arch unit test case described in `./artifacts/architecture/<phase_name>/archunit_specs.md`. Follow DDD inspired package structure that is supported by the framework. 

## Step 6: Scope Demarcation Enforcement
Before finalizing any phase-specific document, verify that it clearly demarcates its scope. A downstream Developer Agent will read these files; they must easily identify exactly what code to write for this phase, and what interfaces/stubs to leave open for future phases.