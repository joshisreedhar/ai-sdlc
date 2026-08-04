# ArchUnit Specifications Template

You must generate clear, logical rules that a QA or Developer agent can easily translate into executable ArchUnit tests (e.g., Java ArchUnit, or equivalent structural testing libraries for other languages).

Structure the output into the following categories:

## 1. Layered Architecture Rules
Define strict layer boundaries (e.g., Controllers cannot access the Database directly; they must go through Services).
*Format as descriptive rules:* "Classes residing in a package '..controller..' should only access classes residing in a package '..service..'"

## 2. Dependency Rules
Specify permitted and forbidden cross-module dependencies to prevent tight coupling.

## 3. Naming and Location Conventions
* Specify suffix rules (e.g., "Classes residing in '..repository..' must have the suffix 'Repository'").
* Specify annotation rules (e.g., "Classes suffixed with 'Controller' must be annotated with @RestController").

## Phase Constraint
Ensure that the rules generated only enforce constraints on code that is expected to be written in the current phase. However, structure the package rules broadly enough that adding a new package in a future phase does not inadvertently break the current ArchUnit tests.