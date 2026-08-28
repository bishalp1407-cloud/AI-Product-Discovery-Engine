import json
import time

import httpx
import re

from app.core.config import get_settings
from app.schemas.feedback_analysis import FeedbackAnalysisResult


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

def repair_common_json_issues(
    content: str,
) -> str:
    repaired = content.strip()

    # Remove Markdown JSON fences if the model adds them.
    if repaired.startswith("```"):
        repaired = re.sub(
            r"^```(?:json)?\s*",
            "",
            repaired,
            flags=re.IGNORECASE,
        )
        repaired = re.sub(
            r"\s*```$",
            "",
            repaired,
        )

    # Repair unquoted enum values such as:
    # "sentiment": positive
    # "severity": medium
    # "is_relevant": true is already valid JSON
    enum_values = (
        "positive",
        "neutral",
        "negative",
        "low",
        "medium",
        "high",
    )

    enum_pattern = (
        r'("(?:sentiment|severity)"\s*:\s*)'
        r'('
        + "|".join(enum_values)
        + r')(?=\s*[,}])'
    )

    repaired = re.sub(
        enum_pattern,
        r'\1"\2"',
        repaired,
        flags=re.IGNORECASE,
    )

    return repaired

def request_openrouter_completion(
    *,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.1,
) -> str:
    """
    Send a chat-completion request to OpenRouter and return
    the raw model completion text.

    This function owns provider-level concerns:
    - authentication
    - HTTP requests
    - transient-error retries
    - Retry-After handling
    - embedded provider errors
    - empty completion validation

    Domain-specific parsing belongs to the caller.
    """

    settings = get_settings()

    payload = {
        "model": settings.openrouter_model,
        "messages": [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        "temperature": temperature,
    }

    headers = {
        "Authorization": (
            f"Bearer {settings.openrouter_api_key}"
        ),
        "Content-Type": "application/json",
    }

    max_attempts = 5
    data = None

    with httpx.Client(timeout=60.0) as client:
        for attempt in range(max_attempts):
            try:
                response = client.post(
                    OPENROUTER_URL,
                    headers=headers,
                    json=payload,
                )

                # Normal HTTP-level transient errors.
                if response.status_code in {429, 500, 502, 503, 504, 520}:
                    if attempt == max_attempts - 1:
                        response.raise_for_status()

                    retry_after = response.headers.get(
                        "Retry-After"
                    )

                    if retry_after:
                        try:
                            wait_seconds = float(
                                retry_after
                            )
                        except ValueError:
                            wait_seconds = min(
                                2 ** attempt,
                                20,
                            )
                    else:
                        wait_seconds = min(
                            2 ** attempt,
                            20,
                        )

                    print(
                        "OpenRouter temporary error "
                        f"({response.status_code}). "
                        "Retrying in "
                        f"{wait_seconds}s..."
                    )

                    time.sleep(wait_seconds)
                    continue

                response.raise_for_status()

                # Provider failures can occasionally arrive
                # inside an HTTP 200 response.
                data = response.json()

                embedded_error = data.get("error")

                if embedded_error:
                    error_code = embedded_error.get(
                        "code"
                    )

                    if error_code in {
                        429,
                        500,
                        502,
                        503,
                        504,
                    }:
                        if attempt == max_attempts - 1:
                            raise RuntimeError(
                                "OpenRouter provider error "
                                "after "
                                f"{max_attempts} attempts: "
                                f"{embedded_error}"
                            )

                        wait_seconds = min(
                            2 ** attempt,
                            20,
                        )

                        print(
                            "OpenRouter embedded "
                            "provider error "
                            f"({error_code}). "
                            "Retrying in "
                            f"{wait_seconds}s..."
                        )

                        time.sleep(wait_seconds)
                        continue

                    raise RuntimeError(
                        "OpenRouter provider error: "
                        f"{embedded_error}"
                    )

                break

            except httpx.RequestError:
                if attempt == max_attempts - 1:
                    raise

                wait_seconds = min(
                    2 ** attempt,
                    20,
                )

                print(
                    "OpenRouter network error. "
                    "Retrying in "
                    f"{wait_seconds}s..."
                )

                time.sleep(wait_seconds)

    if data is None:
        raise RuntimeError(
            "OpenRouter returned no response data."
        )

    if "choices" not in data or not data["choices"]:
        error_message = data.get(
            "error",
            data,
        )

        raise RuntimeError(
            "OpenRouter returned no completion: "
            f"{error_message}"
        )

    message = data["choices"][0].get(
        "message",
        {},
    )

    content = message.get("content")

    if not content:
        raise RuntimeError(
            "OpenRouter returned an empty completion."
        )

    return content


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
- pain_point: main user problem
- severity: low | medium | high
- summary: one concise sentence

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

SEVERITY RULES:

Low:

- positive feedback or praise
- general opinions with no meaningful customer harm
- minor inconvenience
- cosmetic or low-impact issues
- irrelevant feedback must always use low severity

Medium:

- meaningful inconvenience or degraded customer experience
- delayed delivery
- incorrect or damaged order that is recoverable
- app usability problems where the customer can still use the service
- repeated inconvenience without significant financial loss
- support or service problems that materially frustrate the customer

High:

- money deducted but transaction/order failed
- refund or reimbursement failure involving customer money
- customer cannot complete a core task such as ordering or payment
- serious safety or hygiene concern
- severe product quality issue that may create a safety risk
- severe repeated failure that prevents normal use of the service

SEVERITY DECISION RULES:

- Choose severity based on customer impact, not emotional wording.
- Words such as "terrible", "worst", or "pathetic" alone do not make an issue high severity.
- Use high only when there is clear evidence of major financial, functional, safety, or repeated customer impact.
- When uncertain between two severity levels, choose the lower level.
- Positive feedback should normally be low severity.
- Irrelevant feedback must always be low severity.

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
- category must use the most appropriate irrelevant category from the taxonomy
- pain_point should describe what the text is actually about
- sentiment should reflect the text itself
- severity must be low
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
        "Authorization": (
            f"Bearer {settings.openrouter_api_key}"
        ),
        "Content-Type": "application/json",
    }

    max_attempts = 5
    data = None

    with httpx.Client(timeout=60.0) as client:
        for attempt in range(max_attempts):
            try:
                response = client.post(
                    OPENROUTER_URL,
                    headers=headers,
                    json=payload,
                )

                # Handle normal HTTP-level transient errors.
                if response.status_code in { 500, 502, 503, 504, 520,521}:
                    if attempt == max_attempts - 1:
                        response.raise_for_status()

                    retry_after = response.headers.get(
                        "Retry-After"
                    )

                    if retry_after:
                        try:
                            wait_seconds = float(
                                retry_after
                            )
                        except ValueError:
                            wait_seconds = min(
                                2 ** attempt,
                                20,
                            )
                    else:
                        wait_seconds = min(
                            2 ** attempt,
                            20,
                        )

                    print(
                        "OpenRouter temporary error "
                        f"({response.status_code}). "
                        "Retrying in "
                        f"{wait_seconds}s..."
                    )

                    time.sleep(wait_seconds)
                    continue

                response.raise_for_status()

                # OpenRouter/provider failures can occasionally
                # arrive inside a successful HTTP response.
                data = response.json()

                embedded_error = data.get("error")

                if embedded_error:
                    error_code = embedded_error.get(
                        "code"
                    )

                    if error_code in {
                        
                        500,
                        502,
                        503,
                        504,
                        520,
                        521
                    }:
                        if attempt == max_attempts - 1:
                            raise RuntimeError(
                                "OpenRouter provider error "
                                "after "
                                f"{max_attempts} attempts: "
                                f"{embedded_error}"
                            )

                        wait_seconds = min(
                            2 ** attempt,
                            20,
                        )

                        print(
                            "OpenRouter embedded "
                            "provider error "
                            f"({error_code}). "
                            "Retrying in "
                            f"{wait_seconds}s..."
                        )

                        time.sleep(wait_seconds)
                        continue

                    raise RuntimeError(
                        "OpenRouter provider error: "
                        f"{embedded_error}"
                    )

                # HTTP request and provider response
                # were both successful.
                break

            except httpx.RequestError:
                if attempt == max_attempts - 1:
                    raise

                wait_seconds = min(
                    2 ** attempt,
                    20,
                )

                print(
                    "OpenRouter network error. "
                    "Retrying in "
                    f"{wait_seconds}s..."
                )

                time.sleep(wait_seconds)

    if data is None:
        raise RuntimeError(
            "OpenRouter returned no response data."
        )

    if "choices" not in data or not data["choices"]:
        error_message = data.get(
            "error",
            data,
        )

        raise RuntimeError(
            "OpenRouter returned no completion: "
            f"{error_message}"
        )

    message = data["choices"][0].get(
        "message",
        {},
    )

    content = message.get("content")

    if not content:
        raise RuntimeError(
            "OpenRouter returned an empty completion."
        )

    try:
        parsed = json.loads(content)

    except json.JSONDecodeError:
        repaired_content = repair_common_json_issues(
            content
        )

        try:
            parsed = json.loads(repaired_content)

        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "OpenRouter returned invalid JSON. "
                f"Raw content: {content!r}. "
                f"Repaired content: {repaired_content!r}. "
                f"Parse error: {exc}"
            ) from exc

    result = FeedbackAnalysisResult.model_validate(
        parsed
    )

    time.sleep(0.5)

    return result