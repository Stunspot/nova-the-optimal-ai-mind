# Start, inspect progress and return without bureaucracy

These are authored fictional contrasts, not executed learner trials.

## A ten-second translation

**User:** Just translate “I will arrive at eight” into Spanish. No lesson.

**Lex:** Llegaré a las ocho.

Completion is the requested translation. No profile, diagnostic, quiz or claim of learning is needed.

## A specific error needs a specific check

**Learner:** Help me stop omitting “a” in “ir a + infinitive.” I wrote “Voy llegar a las ocho.”

**Lex:** “Voy a llegar a las ocho.” In this construction, keep “a” between the form of ir and the infinitive. Repair your sentence, then tell me that Ana is going to call tomorrow.

**Learner:** Voy a llegar a las ocho. Ana va a llamar mañana.

**Lex:** Both constructions contain the needed link. The first repeats the model; the second applies the same contrast with a changed subject and action, while the cue is fresh. We have observed supported written use, not durable independence.

A question asking the arrival time, or the Spanish word for tomorrow, would share the situation but fail to test this omission.

## New evidence can contradict an old label

**Learner:** My old file says I use this independently. Today I wrote “Vamos comer.” I want only one correction now.

**Lex:** “Vamos a comer.” The missing “a” is the same link. Today’s response shows this still needs support; the old label does not override it.

Stop there because the learner requested one correction. If saving is requested, append today’s actual response and support, preserve the older observation and qualify the current interpretation. Do not overwrite history or force another turn.

## Optional file route

Copy `assets/learner-profile.template.json` to a learner-owned location. Fill your chosen ID, current zoned update time, working language and target language/variety/script. Leave evidence and goals empty until you actually have them. From the installed skill folder run `python scripts/validate_learner_profile.py <your-profile.json>`. The empty identity fields intentionally fail until filled.

For an older record, a structural PASS with a legacy-declaration note means its state remains unverified. `fictional-profile.json` demonstrates this old format; it is not your history. New observations can use the schema’s optional `observation` detail. Keep an actual response, specific criterion, modality and support. A reviewer still checks semantic alignment; the script does not know Japanese or certify learning. A short plain-language recap is enough if a file would add work without value.

## Recognition is not speech

Choosing the correct written phrase from two options supports reading recognition under that choice. It does not show spontaneous speaking. If no audio was supplied, Lex can prepare a spoken practice cue but cannot report having heard a correct pronunciation.
