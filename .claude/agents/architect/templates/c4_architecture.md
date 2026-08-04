# C4 Architecture Template

When generating C4 architecture documents, you must adhere to this structure. All diagrams must be written using standard PlantUML (`@startuml` ... `@enduml`) embedded within markdown code blocks.

## 1. Context 
Describe how the system interacts with users and external systems. 
*Include a C4 System Context PlantUML diagram.*

## 2. Containers
Describe the high-level applications, databases, and microservices that make up the system.
*Include a C4 Container PlantUML diagram.*

## 3. Components
Detail the internal structure of the containers being built or modified in this scope.
*Include a C4 Component PlantUML diagram.*

## Strict Constraints for Phase-Specific Documents:
If you are generating this document for a specific phase (not the overall architecture):
1. **Scope Boundary:** You MUST wrap the phase-specific requirements in explicit markdown tags like this:
   `<!-- PHASE: [Phase Name] START -->`
   `...details...`
   `<!-- PHASE: [Phase Name] END -->`
2. **Future-Proofing:** Explicitly document which interfaces, abstract classes, or database columns must be implemented *now* as stubs or nullable fields to support the next phase without breaking.