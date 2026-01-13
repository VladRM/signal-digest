## 0 Prime directive (non-negotiable) 
Optimize for the following, in this exact order:

1. **Easy to understand**
2. **Easy to test**
3. **Easy to debug**
4. **Easy to extend**

When there is a tradeoff, choose the option that better satisfies the earlier item(s).

---

## 1 Tech stack  
Current stack:

- Python
- Poetry
- Next.js
- shadcn

Rule: **If we update the stack, update this section immediately** and mention the change.

---

## 2 Breaking changes policy
Because we are early-stage, breaking changes are allowed, but must be explicit.

Whenever you propose or implement a breaking change, you MUST:
1. Add a section titled **" --- BREAKING CHANGE --- "** at the top of your response.
2. State:
   - What is breaking
   - Who/what will be impacted
   - How to migrate (steps, commands, code mods)

---

## 3 Testing rules
- Tests must be **fast, deterministic**, and **readable**.
- Favor:
  - Unit tests for domain logic
  - Integration tests for API boundaries
  - A small number of end-to-end tests for critical flows
