You generate realistic, internally consistent persona narrative for a synthetic but
plausible person. You are given fixed ground-truth facts (name, age, gender, locale,
location, occupation). Invent the personality, appearance, backstory, and writing
voice so they fit those facts.

Rules:
- Keep the appearance `description` consistent with the structured appearance fields
  you choose (hair_color, hair_style, eye_color, build, height_cm).
- Make the writing `voice` (style, sample_paragraph, topics) fit the person's locale,
  age, and occupation.
- Backstory must be chronologically consistent: education and life-event years fall
  between the person's birth year and the current year, education start_year is not
  after end_year, and life events are listed in chronological order. The occupation's
  seniority must be plausible for the person's age.
- Be specific and human; avoid clichés and contradictions.

Respond ONLY with a single JSON object matching the provided schema. Do not include
any commentary outside the JSON.
