name: Code Review and Security Check
description: Use when the user shares code, asks for a review, asks whether code is safe, or asks about a security risk in code.

Procedure:
1. Say in one line what the code is doing.
2. Check these, in this order:
   Input validation - is user input checked before it is used?
   SQL - is the query parameterised, or is user input joined into the string?
   Secrets - is a password, key or token written in the code?
   Errors - does a failure leak internal details to the user?
3. List each problem you find with the risk level: HIGH, MEDIUM or LOW.
4. Give the corrected line or the fix for the highest risk item.
5. If you find nothing serious, say so plainly instead of inventing a problem.

Always end your reply with a line in this form:
RISK: <high / medium / low> | ISSUES FOUND: <number>
