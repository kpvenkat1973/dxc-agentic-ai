"""Model names and prices. Prices change often: verify at https://aws.amazon.com/bedrock/pricing and
https://openai.com/api/pricing, and edit here or in the app sidebar. Values are USD per 1M tokens."""

# AWS Bedrock is the main provider for this course (the model id comes from BEDROCK_SMALL_MODEL_ID in .env).
DEFAULT_BEDROCK_MODEL = "amazon.nova-lite-v1:0"
DEFAULT_BEDROCK_EMBED = "amazon.titan-embed-text-v2:0"
BEDROCK_MODEL_OPTIONS = ["amazon.nova-micro-v1:0", "amazon.nova-lite-v1:0"]

# OpenAI is the backup provider.
DEFAULT_CHAT_MODEL = "gpt-5-mini"
DEFAULT_EMBED_MODEL = "text-embedding-3-small"

CHAT_MODEL_OPTIONS = ["gpt-5-mini", "gpt-5-nano", "gpt-4.1-mini", "gpt-4o-mini"]

import re


def price_for(model, default=(0.25, 2.0)):
    """Price tuple for a model id. Bedrock ids may carry a region prefix such as 'us.amazon.nova-micro-v1:0'."""
    return PRICES.get(model) or PRICES.get(re.sub(r"^(us|eu|apac)\.", "", model or ""), default)


PRICES = {
    # Bedrock (check the pricing page; ids may carry a "us." prefix, see price_for())
    "amazon.nova-micro-v1:0": (0.035, 0.14),
    "amazon.nova-lite-v1:0": (0.06, 0.24),
    "amazon.titan-embed-text-v2:0": (0.02, 0.0),
    # model: (input $/1M, output $/1M)  -- edit to match the official pricing page
    "gpt-5-mini": (0.25, 2.00),
    "gpt-5-nano": (0.05, 0.40),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4o-mini": (0.15, 0.60),
    "text-embedding-3-small": (0.02, 0.0),
    "text-embedding-3-large": (0.13, 0.0),
}
