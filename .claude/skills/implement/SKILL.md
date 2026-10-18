---
name: implement
description: Implement one approved phase from a PRD and plan using feedback loops.
argument-hint: "@prd/<feature>.md @plans/<feature>.md implement phase <N>"
disable-model-invocation: true
---

# Implement

## 1. Understand the Phase

Read the referenced PRD and plan. Explore the codebase to understand the relevant files,
patterns, and conventions. If the request does not identify a phase, ask which one.

Implement only that phase. Do not begin the next one.

## 2. Implement the Phase

First, run the `/tdd` skill to select and test up to three key behaviors for this phase. Next, implement the remaining requirements using the project's normal development process to ensure full feature completion. Keep your changes focused entirely on the requested phase.

## 3. Run Feedback Loops

Run the complete automated testing suite, linter, and code formatter to ensure code quality and stability. Verify that all automated feedback loops pass without errors before proceeding. If any checks fail, fix the issues immediately and rerun the tools.

## 4. Manual Verification

Answer the question: "How do I verify this phase or feature manually in the browser?" Stop and wait for the user to manually verify the phase in their browser, as the phase is not finished until they confirm it passed.

## 5. Finish the Phase

Update the PROMPTS.md file using the format specified in that file. Then, provide the commands to commit the completed phase and push the commit to GitHub.