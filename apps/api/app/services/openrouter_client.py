import json
import time

import httpx

from app.core.config import get_settings
from app.schemas.feedback_analysis import FeedbackAnalysisResult


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def analyze_feedback_with_openrouter(
    feedback_text: str,
    source_type: str | None = None,
) -> FeedbackAnalysisResult:
    settings = get_settings()

    system_prompt = """
You are a product feedback analyst analyzing customer feedback for a consumer product.

Analyze the supplied text and return ONLY valid JSON.

Required fields:
- is_relevant: boolean
- sentiment: positive | neutral | negative
- category: exactly one category from the controlled taxonomy below

CONTROLLED CATEGORY TAXONOMY:

For relevant customer feedback:
- ordering: placing, modifying, cancelling, or completing an order
- delivery: delivery speed, delays, rider behavior, order handling, delivery hygiene, or missing delivery
- payments_refunds: payments, failed payments, money deducted, refunds, returns, or reimbursement
- product_quality: damaged, defective, spoiled, incorrect, or poor-quality products
- pricing_fees: prices, charges, delivery fees, platform fees, or affordability
- availability: products being unavailable, out of stock, or inventory-related issues
- customer_support: support agents, complaint resolution, help, or customer service
- app_usability: app performance, crashes, navigation, search, UI, or technical usability
- account: login, authentication, profile, account access, or account-related problems
- promotions: coupons, discounts, offers, rewards, or promotional benefits
- packaging: bags, packaging quality, leakage, wrapping, or packaging-related experience
- general_experience: relevant praise or criticism about the overall product/service when no more specific category applies

For irrelevant feedback:
- employment: jobs, hiring, salaries, wages, shifts, workload, or workplace conditions
- video_discussion: comments primarily about the creator, video, channel, or video content
- market_opinion: general opinions about the company, industry, competitors, or market that do not describe a customer experience
- unrelated: anything else unrelated to customer product/service experience

CATEGORY RULES:
- Return exactly one of the category values listed above.
- Use the most specific applicable category.
- Do not create new category names.
- Do not change capitalization or wording.
- Use general_experience only when no more specific relevant category applies.
- Use unrelated only when none of the more specific irrelevant categories apply.
- pain_point: main user problem
- severity: low | medium | high
- summary: one concise sentence

RELEVANCE RULES:

Mark is_relevant=true only when the text describes or evaluates a customer's
experience with the product or service, including:
- ordering
- delivery
- payments or refunds
- product quality
- pricing or fees
- product availability
- customer support
- application usability
- account experience
- promotions or offers
- delivery handling and hygiene
- packaging or physical handling of the customer's order
- delivery-partner or rider behavior when it directly affects the customer's
  order, delivery experience, safety, hygiene, or service experience

Mark is_relevant=false when the text is primarily about:
- jobs or job applications
- salaries or wages
- employee shifts
- employee breaks
- hiring
- picker/packer work
- delivery-worker employment
- workplace conditions
- creator/video discussion
- unrelated conversation

Do not infer a customer problem that is not explicitly present in the text.

For irrelevant feedback:
- is_relevant must be false
- category should describe the irrelevant topic briefly
- pain_point should describe what the text is actually about
- sentiment should reflect the text itself
- severity should be low
- summary should summarize the actual text

Mentioning a delivery worker does NOT automatically make feedback employment-related.

If the text describes how a delivery worker handled, transported, delivered,
damaged, placed, or treated a customer's order, classify it as relevant
customer experience.

Only classify delivery-worker content as irrelevant when it is primarily
about employment topics such as jobs, salary, hiring, shifts, workload,
benefits, or workplace conditions.

Do not include markdown.
Do not include explanations outside the JSON.
""".strip()

    payload = {
    "model": settings.openrouter_model,
    "messages": [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": (
                f"Source: {source_type or 'unknown'}\n"
                f"Feedback: {feedback_text}"
            ),
        },
    ],
    "temperature": 0.1,
}

    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
    }

    max_attempts = 5

    with httpx.Client(timeout=60.0) as client:
        for attempt in range(1, max_attempts + 1):
            try:
                response = client.post(
                    OPENROUTER_URL,
                    headers=headers,
                    json=payload,
                )

                if response.status_code in {429, 500, 502, 503, 504}:
                    if attempt == max_attempts:
                        response.raise_for_status()

                    wait_seconds = min(2 ** attempt, 8)

                    print(
                        f"OpenRouter temporary error "
                        f"({response.status_code}). "
                        f"Retrying in {wait_seconds}s..."
                    )

                    time.sleep(wait_seconds)
                    continue

                response.raise_for_status()
                break

            except httpx.RequestError:
                if attempt == max_attempts:
                    raise

                wait_seconds = 2 ** attempt

                print(
                    "OpenRouter network error. "
                    f"Retrying in {wait_seconds}s..."
                )

                time.sleep(wait_seconds)

    data = response.json()

    if "choices" not in data or not data["choices"]:
        error_message = data.get("error", data)

        raise RuntimeError(
            f"OpenRouter returned no completion: {error_message}"
        )

    message = data["choices"][0].get("message", {})
    content = message.get("content")

    if not content:
        raise RuntimeError(
            "OpenRouter returned an empty completion."
        )

    parsed = json.loads(content)

    return FeedbackAnalysisResult.model_validate(parsed)