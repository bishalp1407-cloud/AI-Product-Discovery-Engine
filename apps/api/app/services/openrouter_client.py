import json
import re
import time

import httpx

from app.core.config import get_settings
from app.schemas.feedback_analysis import FeedbackAnalysisResult


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

TRANSIENT_STATUS_CODES = {
    429,
    500,
    502,
    503,
    504,
    520,
    521,
}

MAX_ATTEMPTS = 5


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


def _retry_delay(
    attempt: int,
    retry_after: str | None = None,
) -> float:
    if retry_after:
        try:
            return min(float(retry_after), 20.0)
        except ValueError:
            pass

    return float(min(2 ** attempt, 20))


def request_openrouter_completion(
    *,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.1,
) -> str:
    """
    Send one OpenRouter completion request.

    Owns provider-level concerns:
    - authentication
    - HTTP timeout
    - transient retries
    - Retry-After handling
    - embedded provider errors
    - response validation
    """
    settings = get_settings()

    if not settings.openrouter_api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is required for AI analysis."
        )

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

    timeout = httpx.Timeout(
        connect=10.0,
        read=60.0,
        write=20.0,
        pool=10.0,
    )

    with httpx.Client(timeout=timeout) as client:
        for attempt in range(MAX_ATTEMPTS):
            try:
                response = client.post(
                    OPENROUTER_URL,
                    headers=headers,
                    json=payload,
                )

                if (
                    response.status_code
                    in TRANSIENT_STATUS_CODES
                ):
                    if attempt == MAX_ATTEMPTS - 1:
                        response.raise_for_status()

                    wait_seconds = _retry_delay(
                        attempt,
                        response.headers.get(
                            "Retry-After"
                        ),
                    )

                    print(
                        "OpenRouter temporary error "
                        f"({response.status_code}). "
                        f"Retrying in {wait_seconds}s..."
                    )

                    time.sleep(wait_seconds)
                    continue

                response.raise_for_status()

                data = response.json()

                embedded_error = data.get("error")

                if embedded_error:
                    error_code = embedded_error.get(
                        "code"
                    )

                    try:
                        error_code = int(error_code)
                    except (TypeError, ValueError):
                        pass

                    if (
                        error_code
                        in TRANSIENT_STATUS_CODES
                    ):
                        if (
                            attempt
                            == MAX_ATTEMPTS - 1
                        ):
                            raise RuntimeError(
                                "OpenRouter provider "
                                "error after "
                                f"{MAX_ATTEMPTS} "
                                "attempts: "
                                f"{embedded_error}"
                            )

                        wait_seconds = _retry_delay(
                            attempt
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

                choices = data.get("choices")

                if not choices:
                    raise RuntimeError(
                        "OpenRouter returned "
                        "no completion."
                    )

                message = choices[0].get(
                    "message",
                    {},
                )

                content = message.get("content")

                if not content:
                    raise RuntimeError(
                        "OpenRouter returned "
                        "an empty completion."
                    )

                return content

            except httpx.RequestError:
                if attempt == MAX_ATTEMPTS - 1:
                    raise

                wait_seconds = _retry_delay(
                    attempt
                )

                print(
                    "OpenRouter network error. "
                    "Retrying in "
                    f"{wait_seconds}s..."
                )

                time.sleep(wait_seconds)

    raise RuntimeError(
        "OpenRouter request failed unexpectedly."
    )


def analyze_feedback_with_openrouter(
    feedback_text: str,
    source_type: str | None = None,
) -> FeedbackAnalysisResult:

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

    content = request_openrouter_completion(
        system_prompt=system_prompt,
        user_prompt=(
            f"Source: {source_type or 'unknown'}\n"
            f"Feedback: {feedback_text}"
        ),
        temperature=0.1,
    )

    try:
        parsed = json.loads(content)

    except json.JSONDecodeError:
        repaired_content = repair_common_json_issues(
            content
        )

        try:
            parsed = json.loads(
                repaired_content
            )

        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "OpenRouter returned invalid JSON. "
                f"Raw content: {content!r}. "
                "Repaired content: "
                f"{repaired_content!r}. "
                f"Parse error: {exc}"
            ) from exc

    return FeedbackAnalysisResult.model_validate(
        parsed
    )