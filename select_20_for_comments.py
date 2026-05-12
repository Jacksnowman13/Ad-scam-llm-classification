import argparse
import csv
import json
from collections import defaultdict

CATEGORIES = ["linkedin_targeted", "linkedin_general", "meta_targeted", "meta_general"]


def load_jsonl(path):
    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line:
                yield json.loads(line)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scores", required=True)
    parser.add_argument("--ads", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--per-category", type=int, default=5)
    parser.add_argument("--threshold", type=int, default=20)
    args = parser.parse_args()

    ads = {row.get("unique_id"): row for row in load_jsonl(args.ads)}
    grouped = defaultdict(list)

    for score in load_jsonl(args.scores):
        category = score.get("category", "")
        score["distance_from_threshold"] = abs(int(score.get("total_score", 0)) - args.threshold)
        grouped[category].append(score)

    selected = []
    for category in CATEGORIES:
        rows = sorted(grouped[category], key=lambda row: (-int(row.get("total_score", 0)), row["distance_from_threshold"]))
        selected.extend(rows[:args.per_category])

    output_rows = []
    for score in selected:
        ad = ads.get(score.get("unique_id"), {})
        output_rows.append({
            "unique_id": score.get("unique_id", ""),
            "category": score.get("category", ""),
            "platform": score.get("platform", ""),
            "search_type": score.get("search_type", ""),
            "advertiser_name": score.get("advertiser_name", ""),
            "search_term": score.get("search_term", ""),
            "total_score": score.get("total_score", ""),
            "classification": score.get("classification", ""),
            "ad_text": ad.get("ad_text", ""),
            "ad_library_url": ad.get("ad_library_url", score.get("ad_library_url", "")),
            "landing_url": ad.get("landing_url", score.get("landing_url", "")),
            "comment": ""
        })

    with open(args.output, "w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(output_rows[0].keys()) if output_rows else [])
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"Saved {len(output_rows)} selected ads to: {args.output}")


# AI assisted
if __name__ == "__main__":
    main()
