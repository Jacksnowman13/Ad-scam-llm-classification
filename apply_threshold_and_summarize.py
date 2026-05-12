import json
import csv
from collections import defaultdict


INPUT_FILE = "rubric_scores_only.jsonl"
OUTPUT_SCORED_FILE = "rubric_scores_with_classification.jsonl"
OUTPUT_SUMMARY_FILE = "classification_summary_by_category.csv"

THRESHOLD = 20

RUBRIC_FIELDS = [
    "advertiser_credibility",
    "return_outcome_claims",
    "urgency_fear_tactics",
    "capitalization_frequency",
    "emojis",
    "incorrect_spelling",
    "information_inconsistency",
    "link_legitimacy_issue",
    "casual_tone",
    "selling_course"
]

EXPECTED_CATEGORIES = [
    "linkedin_targeted",
    "linkedin_general",
    "meta_targeted",
    "meta_general"
]


def load_jsonl(path):
    rows = []

    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    return rows


def safe_number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def main():
    rows = load_jsonl(INPUT_FILE)

    summary = defaultdict(lambda: {
        "total_ads": 0,
        "classified_1": 0,
        "classified_0": 0,
        "score_sum": 0.0
    })

    scored_rows = []

    for row in rows:
        total_score = sum(safe_number(row.get(field)) for field in RUBRIC_FIELDS)
        classification = 1 if total_score >= THRESHOLD else 0

        row["total_score"] = total_score
        row["classification"] = classification

        scored_rows.append(row)

        category = row.get("category", "missing_category")

        summary[category]["total_ads"] += 1
        summary[category]["score_sum"] += total_score

        if classification == 1:
            summary[category]["classified_1"] += 1
        else:
            summary[category]["classified_0"] += 1

    with open(OUTPUT_SCORED_FILE, "w", encoding="utf-8") as file:
        for row in scored_rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary_rows = []

    for category in EXPECTED_CATEGORIES:
        total_ads = summary[category]["total_ads"]
        classified_1 = summary[category]["classified_1"]
        classified_0 = summary[category]["classified_0"]
        score_sum = summary[category]["score_sum"]

        classified_1_percent = (classified_1 / total_ads * 100) if total_ads else 0
        classified_0_percent = (classified_0 / total_ads * 100) if total_ads else 0
        average_score = (score_sum / total_ads) if total_ads else 0

        summary_rows.append({
            "category": category,
            "total_ads": total_ads,
            "classified_1_count": classified_1,
            "classified_1_percent": round(classified_1_percent, 2),
            "classified_0_count": classified_0,
            "classified_0_percent": round(classified_0_percent, 2),
            "average_score": round(average_score, 2),
            "threshold": THRESHOLD
        })

    with open(OUTPUT_SUMMARY_FILE, "w", encoding="utf-8-sig", newline="") as file:
        fieldnames = [
            "category",
            "total_ads",
            "classified_1_count",
            "classified_1_percent",
            "classified_0_count",
            "classified_0_percent",
            "average_score",
            "threshold"
        ]

        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)

    print("Classification summary by category")
    print("----------------------------------")

    for row in summary_rows:
        print(
            f"{row['category']}: "
            f"{row['classified_1_count']}/{row['total_ads']} classified as 1 "
            f"({row['classified_1_percent']}%), "
            f"average score = {row['average_score']}"
        )

    print()
    print(f"Saved scored file to: {OUTPUT_SCORED_FILE}")
    print(f"Saved summary to: {OUTPUT_SUMMARY_FILE}")


# AI assisted
if __name__ == "__main__":
    main()