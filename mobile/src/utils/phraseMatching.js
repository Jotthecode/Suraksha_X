// Matching spoken transcripts against the user's code phrases and the built-in distress words.

// Multi-word / unambiguous distress phrases trigger on their own.
export const STRONG_DISTRESS_WORDS = ['bachao', 'help me', 'save me', 'madad karo', 'bachao mujhe', 'please help'];
// Everyday words: only count when repeated within REPEAT_WINDOW_MS ("help… help!").
export const WEAK_DISTRESS_WORDS = ['help', 'emergency', 'madad'];
export const REPEAT_WINDOW_MS = 6000;

export const MIN_PHRASE_WORDS = 2;
export const MAX_PHRASES = 5;

export const normalizeSpeech = (text) =>
  String(text || '')
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^\p{L}\p{N}\s]/gu, ' ')
    .replace(/\s+/g, ' ')
    .trim();

const containsWords = (haystack, needle) => {
  if (!needle) return false;
  return ` ${haystack} `.includes(` ${needle} `);
};

/** Problems with a code phrase the user typed, or null if it is usable. */
export const validateCodePhrase = (phrase, existing = []) => {
  const n = normalizeSpeech(phrase);
  if (!n) return 'Type a phrase';
  if (n.split(' ').length < MIN_PHRASE_WORDS) return `Use at least ${MIN_PHRASE_WORDS} words so it isn't said by accident`;
  if (n.length > 60) return 'Keep it under 60 characters';
  if (existing.some((p) => normalizeSpeech(p) === n)) return 'You already added this phrase';
  return null;
};

/**
 * Checks one transcript.
 * Returns { type: 'code', phrase } | { type: 'distress', word } | null.
 * `weakHits` is a mutable { word: timestamp } map used to require repetition of everyday words.
 * Interim (not final) transcripts repeat the same words as the speaker goes on, so they are only
 * checked for code phrases and strong words; everyday words are counted on final results only.
 */
export const matchTranscript = (
  transcript,
  { codePhrases = [], useDistressWords = true, weakHits = {}, now = Date.now(), isFinal = true } = {}
) => {
  const text = normalizeSpeech(transcript);
  if (!text) return null;

  for (const phrase of codePhrases) {
    if (containsWords(text, normalizeSpeech(phrase))) return { type: 'code', phrase };
  }
  if (!useDistressWords) return null;

  for (const word of STRONG_DISTRESS_WORDS) {
    if (containsWords(text, word)) return { type: 'distress', word };
  }
  if (!isFinal) return null;
  for (const word of WEAK_DISTRESS_WORDS) {
    if (!containsWords(text, word)) continue;
    const count = text.split(' ').filter((w) => w === word).length;
    if (count >= 2) return { type: 'distress', word };
    const last = weakHits[word];
    weakHits[word] = now;
    if (last && now - last <= REPEAT_WINDOW_MS) return { type: 'distress', word };
  }
  return null;
};
