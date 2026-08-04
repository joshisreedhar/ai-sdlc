# PlantUML Diagrams Template

When generating Module Dependency and Sequence diagrams, adhere to the following rules. Use standard PlantUML formatting embedded in markdown blocks.

## Module Dependency Diagrams
* Use PlantUML package and component syntax (`package "Module A" { ... }`).
* Clearly show unidirectional dependencies to prevent circular dependency issues.
* **Evolution Rule:** If a module will require integration with a future module in a later phase, depict the interface/port that must be established in the current phase to allow that future connection seamlessly. 

## Sequence Diagrams
* Map out the critical user journeys and internal system communications for the current phase scope.
* Clearly define synchronous vs. asynchronous calls.
* **Evolution Rule:** Include notes in the sequence diagram (`note right of...`) indicating where a process will be intercepted or expanded in future phases.