import re
from config import Config

# ── Blocked patterns ──────────────────────────────────────────────────────────
BLOCKED_PATTERNS = [
    # Ideology injection into scripture
    r'rewrite.{0,30}(bible|verse|scripture|gospel).{0,30}(to support|to justify|to promote)',
    r'(bible|scripture|jesus|god).{0,20}(supports|justifies|promotes).{0,20}(nazi|fascis|communis|terrorism)',
    r'change.{0,20}(bible|verse|scripture).{0,20}(say|mean|support)',

    # Hateful content
    r'(christianity|bible|jesus).{0,30}(inferior|fake|stupid|evil|satanic)',
    r'(kill|harm|attack|destroy).{0,20}(muslim|jew|atheist|christian|hindu)',

    # Extremism
    r'(holy war|crusade).{0,20}(kill|attack|destroy|wage)',
    r'religious.{0,20}(cleansing|genocide|extermination)',

    # Manipulation attempts
    r'ignore.{0,20}(previous|above|prior|your).{0,20}(instructions|rules|guidelines|prompt)',
    r'(pretend|act|behave).{0,20}(you are|you\'re|as if).{0,20}(not|without).{0,20}(restriction|rule|guideline)',
    r'jailbreak|dan mode|developer mode|unrestricted mode',
]

# ── Sensitive topics requiring careful handling ───────────────────────────────
SENSITIVE_TOPICS = [
    'suicide', 'self-harm', 'self harm', 'kill myself',
    'abuse', 'sexual abuse', 'domestic violence',
    'cult', 'extremism', 'radicalization',
]

# ── Difficult theological topics (handle with grace, not refusal) ─────────────
DIFFICULT_THEOLOGY = [
    'theodicy', 'problem of evil', 'why does god allow suffering',
    'does god exist', 'is god real', 'contradictions in the bible',
    'bible errors', 'bible contradictions', 'hell', 'eternal damnation',
    'predestination vs free will', 'homosexuality', 'lgbtq',
    'abortion', 'divorce', 'women in ministry',
]


def classify_input(user_message: str) -> dict:
    """
    Classify user input before sending to AI.

    Returns:
    {
        safe:        bool,
        category:    str,   # 'safe' | 'blocked' | 'sensitive' | 'difficult_theology'
        reason:      str,
        modified_message: str   # original or modified prompt
    }
    """
    msg_lower = user_message.lower()

    # Check blocked patterns
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, msg_lower, re.IGNORECASE):
            return {
                "safe":             False,
                "category":         "blocked",
                "reason":           "This request contains content that cannot be processed.",
                "modified_message": user_message
            }

    # Check sensitive topics
    for topic in SENSITIVE_TOPICS:
        if topic in msg_lower:
            return {
                "safe":             True,
                "category":         "sensitive",
                "reason":           f"Message contains sensitive topic: {topic}",
                "modified_message": user_message
            }

    # Check difficult theology
    for topic in DIFFICULT_THEOLOGY:
        if topic in msg_lower:
            return {
                "safe":             True,
                "category":         "difficult_theology",
                "reason":           f"Message involves difficult theological topic: {topic}",
                "modified_message": user_message
            }

    return {
        "safe":             True,
        "category":         "safe",
        "reason":           "Message passed all safety checks",
        "modified_message": user_message
    }


def filter_output(ai_response: str) -> dict:
    """
    Check AI output before sending to user.
    Returns {safe: bool, response: str, reason: str}
    """
    blocked_output_patterns = [
        r'(heil|sieg heil)',
        r'(kill all|destroy all|exterminate all).{0,20}(christian|muslim|jew|atheist)',
        r'(god|jesus|bible).{0,20}(hates|despises|condemns).{0,20}(gay|homosexual|trans)',
    ]

    for pattern in blocked_output_patterns:
        if re.search(pattern, ai_response, re.IGNORECASE):
            return {
                "safe":     False,
                "response": "I'm sorry, I cannot provide that response. Please ask me something else.",
                "reason":   "Output failed safety filter"
            }

    return {
        "safe":     True,
        "response": ai_response,
        "reason":   "Output passed safety checks"
    }


def get_sensitive_preamble(category: str, topic: str = '') -> str:
    """
    Return a compassionate preamble for sensitive topics
    to prepend to the AI's response.
    """
    if category == 'sensitive':
        if any(t in topic.lower() for t in ['suicide', 'self-harm', 'kill myself']):
            return (
                "I hear that you're going through something very difficult. "
                "Your life has value and you are loved. "
                "If you're in crisis, please reach out to a crisis helpline "
                "(like 988 in the US) or a trusted pastor immediately.\n\n"
            )
        return (
            "This is a sensitive topic and I want to approach it with care "
            "and compassion. "
        )

    if category == 'difficult_theology':
        return (
            "This is one of the deep questions Christians have wrestled with "
            "throughout history. I'll share multiple perspectives with humility, "
            "acknowledging that faithful Christians hold different views.\n\n"
        )

    return ''