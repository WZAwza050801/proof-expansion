# Package Drop Zone

Place immutable versioned problem packages here, one YAML file per package.

Start from `../problem-package.template.yml`. A valid package must:

1. keep writer-visible and judge-only material separate;
2. cite and status-label its source;
3. state its selected variant ground truth;
4. carry human approval before being moved from `candidate` to `ready` in `../queue.yml`.

This directory is intentionally empty apart from this instruction. The harness can be completed and validated before Terra starts producing packages.
