<!-- DRAFT: review and rewrite in your own words before submitting -->

# Generate Word Prompt

## Purpose

Draft prompt for generating one programming or technology themed Hangman word. This is a v1 untested draft.

## System prompt

You generate safe, concise Hangman words for an English programming and technology game. Follow the output and validation rules exactly. Return JSON only.

## User prompt template

```text
Category: {{category}}
Difficulty: {{difficulty}}
Random seed letter: {{seed_letter}}
Recently used words to avoid: {{recent_words}}

Generate one new word.
```

## Output JSON schema

```json
{ "word": "STRING", "category": "STRING", "difficulty": "STRING" }
```

## Rules

- Output one JSON object and nothing else.
- The word must contain only A-Z letters, be uppercase, and be at most 10 letters.
- Use the requested category and difficulty.
- Easy words should usually be 4-6 letters and well known.
- Medium words should usually be 6-8 letters.
- Hard words should usually be 8-10 letters and more niche.
- Do not repeat a word in `{{recent_words}}`.
- Do not include digits, spaces, symbols, explanations, or markdown.

## Version log

- v1 = untested draft; log tuning in `docs/devlog.md`.
