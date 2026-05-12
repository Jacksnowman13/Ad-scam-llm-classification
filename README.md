# LLM Ad Scoring Package - Score Only

This version assumes you already have one combined input file, for example:

`all_clean_ads_for_llm.jsonl`

The local LLM is used only to assign rubric item scores. Python computes `total_score`, applies the threshold, creates the 0/1 classification, and summarizes counts/percentages by category.

## Expected input fields

Each row should include at least:

- unique_id
- category
- platform
- search_type
- advertiser_name
- paid_by
- search_term
- landing_url
- ad_library_url
- ad_text

Valid categories:

- linkedin_targeted
- linkedin_general
- meta_targeted
- meta_general

## Step 1: Score ads with local LLM

Start LM Studio or another OpenAI-compatible local server. Default endpoint:

`http://localhost:1234/v1/chat/completions`

Run:

```bash
python score_ads_local_llm.py --input all_clean_ads_for_llm.jsonl --output rubric_scores_only.jsonl --model local-model
```

For a small test:

```bash
python score_ads_local_llm.py --input all_clean_ads_for_llm.jsonl --output rubric_scores_only_test.jsonl --model local-model --limit 20
```

The output contains rubric item scores and `total_score`, but no classification.

## Step 2: Apply threshold and summarize

```bash
python apply_threshold_and_summarize.py --input rubric_scores_only.jsonl --scored-output rubric_scores_with_classification.jsonl --summary-output classification_summary_by_category.csv --threshold 20
```

This creates:

- `rubric_scores_with_classification.jsonl`
- `classification_summary_by_category.csv`

The summary includes exact counts and percentages for each category.

## Step 3: Select 20 ads for comments

This selects 5 ads per category, prioritizing highest total scores:

```bash
python select_20_for_comments.py --scores rubric_scores_with_classification.jsonl --ads all_clean_ads_for_llm.jsonl --output selected_20_for_comments.csv --per-category 5 --threshold 20
```

Fill the `comment` column manually or run a separate comment-only LLM pass on just these 20 rows.

## Notes

- The LLM does not compute classification.
- The LLM does not compute the threshold decision.
- Python computes total_score as the sum of rubric item scores.
- Python sets classification = 1 when total_score >= 20, else 0.
- The scoring script is resumable: if the output file already contains rows, it skips those unique_id values.
