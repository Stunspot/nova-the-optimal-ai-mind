# TypeScript with Vitest or Jest

Detect the repository's actual package manager, module mode, TypeScript config, test config, setup files, path aliases, DOM/runtime environment, fixture style, and scripts before authoring.

Prefer the existing framework and imports. Common commands, subject to repository scripts:

```text
npm test -- <pattern>
npm run test -- --run <path>          # common Vitest shape
npx vitest run <path>                 # only when locally installed
npx jest <path> --runInBand           # only when locally installed
npm run typecheck
```

Do not invoke `npx` if it would fetch from the network. Preserve fake timer cleanup, mock restoration, module isolation, and async completion. Assert state and side effects beyond call counts. For API behavior, keep authorization, transaction, serialization, and adapter boundaries real at the layer being claimed.
