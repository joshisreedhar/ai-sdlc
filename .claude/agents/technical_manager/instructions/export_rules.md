# Artifact Export Rules

Execute these steps strictly upon receiving user approval for the implementation plan:

1. **Directory Validation:** Check for the existence of `artifacts/development_plan/` in the workspace root. Create the directories if they do not exist.
2. **File Generation:** For every phase in the approved plan, create a folder using the phase name as described below.
3. **Naming Convention:** Name the folders sequentially (e.g., `phase_1_mvp`, `phase_2_auth`, `phase_3_analytics`).
4. **Phase Summary:** For each of the phase, create a summary.md using the template defined in `templates/summary.md` 
5. **Story Naming:** For each phase break the tasks into well-defined stories following the INVEST acronym
- Independent: The story should not rely on other stories to be valuable or developed. 
- Negotiable: The story is a flexible invitation for conversation, not a rigid contract. 
- Valuable: Each story must deliver tangible value to the end user or customer. 
- Estimable: The team must have enough information to size the effort required. 
- Small: The story should be small enough to be completed within a single sprint. 
- Testable: There must be clear, precise acceptance criteria to verify completion.
6. **Formatting:** Use the exact structure provided in `templates/story.md` for every exported file.
7. **Confirmation:** Once all files are successfully written to the disk, output a confirmation message listing the created file paths to the user.