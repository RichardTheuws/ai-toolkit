# Contributing

Thanks for looking. This repo exists so that people who work with Claude Code
(and similar tools) can learn from each other's mistakes instead of repeating
them. Every kind of contribution helps, the small ones too.

## Ways to help

- **Tell us how you do it.** A [discussion](https://github.com/RichardTheuws/ai-toolkit/discussions)
  about your own setup is as useful as code. "We tried this and it didn't work" counts.
- **Report what's broken or unclear.** An issue with what you ran, what you
  expected and what happened.
- **Send a fix.** For a hook or script, include a test case that fails before
  your change and passes after. Every tool has a small test file; add to it.
- **Translate.** Playbooks exist in English and Dutch. Corrections to either are welcome.

## Before you open a pull request

1. Run the tests of the tool you touched (see its README).
2. Run the leak gate on the repo:
   `python3 scripts/leak-gate/leak-gate.py .`
   It blocks home paths, private IPs, email addresses and secrets. Use `/Users/you/`,
   `example.com` and fake keys in examples.
3. Keep it small. One tool or one fix per pull request.

## Tone

Write the way you'd explain it to a colleague: what happened, what you do now,
why. No marketing, no hype words. Be kind in reviews and discussions. We are all
figuring this out as we go.

## Language

Code, READMEs and issues in English. Discussions in Dutch are fine too.
