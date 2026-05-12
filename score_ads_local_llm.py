import argparse
import json
import re
import time
import urllib.request
import urllib.error

SCORE_KEYS = [
    "advertiser_credibility",
    "return_outcome_claims",
    "urgency_fear_tactics",
    "capitalization_frequency",
    "emojis",
    "incorrect_spelling",
    "information_inconsistency",
    "link_legitimacy_issue",
    "casual_tone",
    "selling_course",
]

MAX_VALUES = {
    "advertiser_credibility": 10,
    "return_outcome_claims": 10,
    "urgency_fear_tactics": 10,
    "capitalization_frequency": 5,
    "emojis": 5,
    "incorrect_spelling": 10,
    "information_inconsistency": 10,
    "link_legitimacy_issue": 10,
    "casual_tone": 7,
    "selling_course": 3,
}

BINARY_VALUES = {
    "incorrect_spelling": [0, 10],
    "information_inconsistency": [0, 10],
    "link_legitimacy_issue": [0, 10],
    "casual_tone": [0, 7],
    "selling_course": [0, 3],
}

SYSTEM_PROMPT = """You are scoring financial advertisements for scam-risk research.
Return valid JSON only. Do not include markdown, explanations, classification, or total score.
Use only the ad content and metadata provided.
Score suspicion/risk, not quality.
For numeric ranges, higher means more suspicious.
For binary items, use exactly the allowed values.

Rubric:
1. advertiser_credibility: 0-10. Higher if advertiser is vague, unverifiable, academy/coach/guru-like, impersonates celebrities, or lacks credible institutional identity. Lower for banks, insurers, credit unions, regulators, established institutions.
2. return_outcome_claims: 0-10. Higher for guaranteed returns/outcomes, high percentage returns, specific price targets, passive income/low-effort claims, "double your money", "earn while you sleep".
3. urgency_fear_tactics: 0-10. Higher for fearmongering, limited spots/time pressure, pain-point framing such as "tired of...", "don't miss out", "act now".
4. capitalization_frequency: 0-5. Higher for excessive ALL CAPS, repeated exclamation, promotional shouting.
5. emojis: 0-5. Higher for frequent/varied hype emojis, money/fire/rocket/100 emojis. Lower for minimal or professional check/cross usage.
6. incorrect_spelling: 0 or 10. Use 10 for clear misspellings/grammar errors that reduce trust; otherwise 0.
7. information_inconsistency: 0 or 10. Use 10 if advertiser/company name appears inconsistent with the landing domain or ad identity; otherwise 0.
8. link_legitimacy_issue: 0 or 10. Use 10 if landing URL/domain looks suspicious, impersonates a reputable company, uses strange misspelling, or does not match claimed entity; otherwise 0.
9. casual_tone: 0 or 7. Use 7 for overly casual/informal hype tone; otherwise 0.
10. selling_course: 0 or 3. Use 3 if the ad sells/promotes a course, masterclass, training, webinar, coaching program, trading group, strategy call, or similar; otherwise 0.
"""

USER_TEMPLATE = """Score this ad.

unique_id: {unique_id}
category: {category}
platform: {platform}
search_type: {search_type}
advertiser_name: {advertiser_name}
paid_by: {paid_by}
search_term: {search_term}
landing_url: {landing_url}
ad_library_url: {ad_library_url}

ad_text:
{ad_text}

Return exactly this JSON object with integer values only:
{{
  "advertiser_credibility": 0,
  "return_outcome_claims": 0,
  "urgency_fear_tactics": 0,
  "capitalization_frequency": 0,
  "emojis": 0,
  "incorrect_spelling": 0,
  "information_inconsistency": 0,
  "link_legitimacy_issue": 0,
  "casual_tone": 0,
  "selling_course": 0
}}
"""


def load_jsonl(path):
    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line:
                yield json.loads(line)


def append_jsonl(path, row):
    with open(path, "a", encoding="utf-8") as file:
        file.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_completed_ids(path):
    ids = set()
    try:
        for row in load_jsonl(path):
            unique_id = row.get("unique_id")
            if unique_id:
                ids.add(unique_id)
    except FileNotFoundError:
        pass
    return ids


def post_chat_completion(endpoint, model, messages, temperature, max_tokens, timeout):
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        result = json.loads(response.read().decode("utf-8"))
    return result["choices"][0]["message"]["content"]


def extract_json_object(text):
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in model response")
    return json.loads(match.group(0))


def clamp_score(key, value):
    try:
        value = int(round(float(value)))
    except (TypeError, ValueError):
        value = 0
    if key in BINARY_VALUES:
        allowed = BINARY_VALUES[key]
        return min(allowed, key=lambda x: abs(x - value))
    return max(0, min(MAX_VALUES[key], value))


def score_row(row, endpoint, model, temperature, max_tokens, timeout, retries):
    user_prompt = USER_TEMPLATE.format(
        unique_id=row.get("unique_id", ""),
        category=row.get("category", ""),
        platform=row.get("platform", ""),
        search_type=row.get("search_type", ""),
        advertiser_name=row.get("advertiser_name", ""),
        paid_by=row.get("paid_by", ""),
        search_term=row.get("search_term", ""),
        landing_url=row.get("landing_url", ""),
        ad_library_url=row.get("ad_library_url", ""),
        ad_text=row.get("ad_text", ""),
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    last_error = None
    for attempt in range(retries + 1):
        try:
            content = post_chat_completion(endpoint, model, messages, temperature, max_tokens, timeout)
            raw_scores = extract_json_object(content)
            scores = {key: clamp_score(key, raw_scores.get(key, 0)) for key in SCORE_KEYS}
            total_score = sum(scores.values())
            output = {
                "unique_id": row.get("unique_id", ""),
                "category": row.get("category", ""),
                "platform": row.get("platform", ""),
                "search_type": row.get("search_type", ""),
                "original_ad_id": row.get("original_ad_id", ""),
                "advertiser_name": row.get("advertiser_name", ""),
                "search_term": row.get("search_term", ""),
                "landing_url": row.get("landing_url", ""),
                "ad_library_url": row.get("ad_library_url", ""),
                **scores,
                "total_score": total_score,
            }
            return output
        except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError, KeyError) as error:
            last_error = error
            time.sleep(1 + attempt)
    raise RuntimeError(f"Failed after retries: {last_error}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--endpoint", default="http://localhost:1234/v1/chat/completions")
    parser.add_argument("--model", default="local-model")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=300)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    completed_ids = load_completed_ids(args.output)
    processed = 0
    skipped = 0

    for row in load_jsonl(args.input):
        unique_id = row.get("unique_id", "")
        if not unique_id or unique_id in completed_ids:
            skipped += 1
            continue
        if not row.get("ad_text", "").strip():
            skipped += 1
            continue
        result = score_row(row, args.endpoint, args.model, args.temperature, args.max_tokens, args.timeout, args.retries)
        append_jsonl(args.output, result)
        processed += 1
        completed_ids.add(unique_id)
        print(f"scored {processed}: {unique_id} total={result['total_score']}")
        if args.limit and processed >= args.limit:
            break

    print(f"Done. New scored rows: {processed}. Skipped/resumed rows: {skipped}.")


# AI assisted
if __name__ == "__main__":
    main()
