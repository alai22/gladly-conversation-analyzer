# Interview participant guidelines

Share this document with marketing, legal, or compliance when they ask how AI text interviews behave. This is informational — not an approval gate.

## Purpose

Halo Insight **Text Interviews** run lightweight, adaptive 1:1 research chats. The product team defines a topic and audience; an AI agent conducts the conversation and produces structured insights for prioritization (e.g. Shape Up pitches).

This is **research**, not customer support. Participants join via a unique link without a Halo account.

## What the agent will do

- Introduce itself as an AI research assistant
- Explain approximate duration and high-level data handling
- Ask for **explicit consent** before substantive questions
- Ask **one question at a time**, adapting follow-ups to answers
- Clarify vague terms, ask for examples, and quantify impact when useful
- Periodically reflect back (“I heard X — did I get that right?”)
- End with an open “anything else we should have asked?” question
- Stop and offer support handoff if the participant raises urgent account or safety issues

## What the agent will not do

- Pitch products or features
- Use leading language (“Wouldn't you love if…”)
- Request personal identifiers (full name, email, phone, address, account numbers)
- Provide medical, legal, or financial advice
- Pressure participants who refuse to answer
- Continue interviewing after consent is declined or after a safety handoff

## Tone

Friendly, neutral, concise. Not robotic, not salesy.

## Consent and data

- Consent is required before exploration questions
- Declining consent ends the session immediately with a polite exit
- Transcripts are stored for internal research analysis
- Insights are generated for the product team, not shared back to the participant automatically

## Safety and handoff

If a participant mentions account lockouts, urgent support needs, harassment, or safety risks, the agent:

1. Responds empathetically
2. Stops interview questions
3. Points them to Halo support (support@halocollar.com / in-app support)
4. Marks the session with a support handoff flag

## AI disclosure

If asked “Are you a human?”, the agent clearly states it is an AI research assistant.

## What researchers configure

| Researcher sets | Agent decides |
|-----------------|---------------|
| Topic / decision | Follow-up wording |
| Audience description | Which template to use next |
| Time limit & max questions | Depth based on signal & budget |
| Banned topics | Synthesis checkbacks |
| Hypothesis (optional) | Wrap-up phrasing |
| Follow-up recruitment allowed | When to move phases |

## Plug-in points for production

- **Storage:** sessions default to in-memory + local JSON; swap to S3 via `StorageService`
- **LLM:** Anthropic via existing `ClaudeService`; set `INTERVIEW_MOCK_LLM=true` for offline/tests
- **Auth:** researchers use Halo Insight login; participants use opaque URL tokens
