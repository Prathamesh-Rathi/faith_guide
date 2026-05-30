import re
import json
from groq import Groq
from config import Config
from app.grounding import (
    build_scripture_context,
    verify_and_ground_verses,
    search_bible
)

# ── Groq client ───────────────────────────────────────────────────────────────
client = Groq(api_key=Config.GROQ_API_KEY)


# ── Denomination-specific context ─────────────────────────────────────────────
DENOMINATION_CONTEXT = {
    'Catholic': """
You are speaking with a Catholic Christian. Key considerations:
- Reference the Catechism of the Catholic Church when relevant
- Acknowledge the authority of Sacred Tradition alongside Scripture
- Include deuterocanonical books (Tobit, Judith, Maccabees, etc.) when relevant
- Reference papal encyclicals or Church Fathers when appropriate
- Acknowledge the role of Mary and the Saints respectfully
- Use inclusive language about sacraments (7 sacraments)
""",
    'Orthodox': """
You are speaking with an Eastern Orthodox Christian. Key considerations:
- Emphasize the Holy Trinity and theosis (union with God)
- Reference the Church Fathers extensively (Chrysostom, Basil, Gregory)
- Acknowledge the authority of the Seven Ecumenical Councils
- Include the Septuagint perspective on Old Testament passages
- Mention the Divine Liturgy and liturgical tradition when relevant
- Emphasize mystery and apophatic theology
""",
    'Baptist': """
You are speaking with a Baptist Christian. Key considerations:
- Emphasize Sola Scriptura — Scripture alone as final authority
- Highlight believer's baptism by immersion
- Stress personal faith and direct relationship with God
- Emphasize the autonomy of the local church
- Focus on evangelism and the Great Commission
""",
    'Methodist': """
You are speaking with a Methodist Christian. Key considerations:
- Reference the Wesleyan Quadrilateral (Scripture, Tradition, Reason, Experience)
- Emphasize sanctification and growing in holiness
- Highlight social justice and serving the poor (Wesley's emphasis)
- Acknowledge prevenient grace available to all
""",
    'Lutheran': """
You are speaking with a Lutheran Christian. Key considerations:
- Emphasize justification by grace through faith alone (Sola Fide)
- Reference Luther's Small Catechism when relevant
- Highlight Law and Gospel distinction
- Acknowledge the two sacraments: Baptism and the Lord's Supper
""",
    'Pentecostal': """
You are speaking with a Pentecostal Christian. Key considerations:
- Emphasize the gifts of the Holy Spirit (tongues, healing, prophecy)
- Highlight Spirit baptism and personal encounter with the Holy Spirit
- Stress the importance of prayer and worship
- Emphasize divine healing and miraculous works
""",
    'Anglican / Episcopal': """
You are speaking with an Anglican/Episcopal Christian. Key considerations:
- Reference the Book of Common Prayer tradition
- Acknowledge the via media (middle way) between Catholic and Protestant
- Respect both Scripture and Church tradition
- Reference the 39 Articles when relevant
""",
    'Protestant (General)': """
You are speaking with a Protestant Christian. Key considerations:
- Emphasize the five Solas: Scripture alone, Faith alone, Grace alone,
  Christ alone, Glory to God alone
- Focus on personal relationship with Jesus Christ
- Stress the importance of prayer, Bible reading, and community
""",
}


def get_denomination_context(denomination: str) -> str:
    return DENOMINATION_CONTEXT.get(
        denomination,
        DENOMINATION_CONTEXT['Protestant (General)']
    )


# ── Master system prompt ──────────────────────────────────────────────────────
def build_system_prompt(denomination: str, scripture_context: str = '') -> str:
    denom_ctx = get_denomination_context(denomination)

    system = f"""You are FaithGuide, a knowledgeable, compassionate, and theologically grounded Christian AI assistant.

DENOMINATION CONTEXT:
{denom_ctx}

YOUR CORE RULES — follow these without exception:

1. SCRIPTURE CITATIONS — CRITICAL:
   - ONLY cite Bible verses that are provided in the RELEVANT SCRIPTURE section below
   - NEVER invent, guess, or paraphrase a verse reference you are not sure about
   - If you want to cite a verse not in the provided context, say: "I recall a passage in [Book] that speaks to this, but let me not quote it directly to ensure accuracy"
   - Always format citations as: Book Chapter:Verse — "exact text"
   - NEVER change the wording of a verse — quote exactly or not at all

2. THEOLOGICAL ACCURACY:
   - Acknowledge when topics have multiple valid denominational interpretations
   - Never declare one denomination superior to another
   - For difficult questions (theodicy, suffering, contradictions), respond with
     humility and multiple perspectives — not false certainty
   - Distinguish between core Christian doctrine (Trinity, Resurrection) and
     secondary matters where Christians disagree

3. SAFETY & TONE:
   - Refuse any request to rewrite or reinterpret scripture to support ideologies
   - Never produce content that demeans other religions with contempt
   - Respond to grief, doubt, and spiritual crisis with compassion first
   - If someone seems in distress, prioritize pastoral care over theology
   - Never produce hateful, extremist, or violent religious content

4. HALLUCINATION PREVENTION:
   - If you are unsure of a historical claim, say so explicitly
   - Do not invent church councils, popes, theologians, or events
   - Acknowledge the limits of your knowledge openly

5. CONVERSATION STYLE:
   - Warm, pastoral, and accessible — not academic unless asked
   - Use plain language; explain theological terms when you use them
   - End responses with an invitation to explore further or a short prayer
     when contextually appropriate

{f'RELEVANT SCRIPTURE (use ONLY these verses for citations):{chr(10)}{scripture_context}' if scripture_context else ''}

Remember: You are a trusted spiritual companion, not an infallible oracle.
Accuracy and humility matter more than sounding authoritative."""

    return system


# ── Extract verse references from AI response ─────────────────────────────────
def extract_verse_refs_from_text(text: str) -> list:
    """Pull out any Bible references the AI mentioned so we can verify them."""
    pattern = r'\b((?:1|2|3)?\s?[A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s+(\d+):(\d+)(?:-\d+)?\b'
    matches = re.findall(pattern, text)
    refs = []
    for m in matches:
        ref = f"{m[0].strip()} {m[1]}:{m[2]}"
        refs.append(ref)
    return list(set(refs))


# ── Few-shot examples for prompt grounding ────────────────────────────────────
FEW_SHOT_EXAMPLES = [
    {
        "role": "user",
        "content": "What does the Bible say about anxiety?"
    },
    {
        "role": "assistant",
        "content": """That's such an important question, and one many believers wrestle with.

Scripture speaks directly to anxiety and worry. In Philippians 4:6-7, Paul writes: "Do not be anxious about anything, but in every situation, by prayer and petition, with thanksgiving, present your requests to God. And the peace of God, which transcends all understanding, will guard your hearts and your minds in Christ Jesus."

This passage gives us a practical pattern: instead of worry, bring everything to God in prayer with a thankful heart — and receive His peace in return.

Jesus also addresses this in the Sermon on the Mount, reminding us that God cares deeply for His creation and for us as His children.

A few reflections:
- Anxiety is real and valid — the Bible doesn't shame us for feeling it
- Prayer is the primary response Scripture recommends
- God's peace is described as something that *surpasses understanding* — it's not just positive thinking

Would you like to explore what Scripture says about finding peace, or would a short prayer for peace be helpful right now?"""
    },
]


# ── Main chat function ────────────────────────────────────────────────────────
def chat_with_faithguide(
    user_message:    str,
    conversation_history: list,
    denomination:    str = 'Protestant (General)',
    ) -> dict:
    """
    Main entry point for AI responses.

    Args:
        user_message: The user's current message
        conversation_history: List of {role, content} dicts
        denomination: User's Christian denomination

    Returns:
        {
            response: str,
            verses_used: list,
            rejected_verses: list,
            scripture_context: str,
            error: str or None
        }
    """
    try:
        # Step 1 — Retrieve relevant scripture via RAG
        scripture_context = build_scripture_context(user_message)

        # Step 2 — Build system prompt with denomination + scripture
        system_prompt = build_system_prompt(denomination, scripture_context)

        # Step 3 — Build message history (keep last N messages)
        max_history = Config.MAX_CONVERSATION_HISTORY
        recent_history = conversation_history[-max_history:] \
                         if len(conversation_history) > max_history \
                         else conversation_history

        messages = (
            FEW_SHOT_EXAMPLES
            + recent_history
            + [{"role": "user", "content": user_message}]
        )

        # Step 4 — Call Groq API
        response = client.chat.completions.create(
            model      = Config.GROQ_MODEL,
            messages   = [{"role": "system", "content": system_prompt}] + messages,
            temperature= 0.7,
            max_tokens = 1024,
        )

        ai_response = response.choices[0].message.content

        # Step 5 — Extract and verify any verse references in the response
        cited_refs     = extract_verse_refs_from_text(ai_response)
        verification   = verify_and_ground_verses(cited_refs)
        verified       = verification["verified"]
        rejected       = verification["rejected"]

        # Step 6 — If any rejected verses found, append a note
        if rejected:
            rejected_refs = [r["reference"] for r in rejected]
            note = (
                f"\n\n*Note: I mentioned {', '.join(rejected_refs)} — "
                f"please verify these references independently as I cannot "
                f"confirm their exact wording from my verified database.*"
            )
            ai_response += note

        return {
            "response":         ai_response,
            "verses_used":      verified,
            "rejected_verses":  rejected,
            "scripture_context": scripture_context,
            "error":            None
        }

    except Exception as e:
        return {
            "response":         "I'm sorry, I encountered an issue processing your request. Please try again.",
            "verses_used":      [],
            "rejected_verses":  [],
            "scripture_context": "",
            "error":            str(e)
        }


# ── Content generation (devotionals, prayers, etc.) ──────────────────────────
def generate_christian_content(
    content_type: str,
    topic:        str,
    denomination: str = 'Protestant (General)'
) -> dict:
    """
    Generate Christian content: devotional, prayer, sermon outline, etc.

    content_type options:
        'devotional', 'prayer', 'sermon_outline',
        'bible_study', 'reflection'
    """
    scripture_context = build_scripture_context(topic)

    content_prompts = {
        'devotional': f"Write a short daily devotional (200-250 words) on the topic of '{topic}'. Include one Scripture reference from the provided verses, a brief reflection, and a closing prayer.",
        'prayer':     f"Write a heartfelt prayer on the topic of '{topic}' in the style appropriate for the user's denomination. Make it personal, sincere, and scripturally grounded.",
        'sermon_outline': f"Create a sermon outline on '{topic}' with: Title, Key Scripture, Introduction, 3 main points each with a sub-verse, Application, and Conclusion.",
        'bible_study': f"Create a Bible study guide on '{topic}' with: Overview, Key Questions (5), Scripture passages to read, Discussion questions, and Personal application.",
        'reflection': f"Write a spiritual reflection on '{topic}' that is contemplative, warm, and draws from Scripture.",
    }

    prompt = content_prompts.get(content_type, content_prompts['reflection'])
    system = build_system_prompt(denomination, scripture_context)

    try:
        response = client.chat.completions.create(
            model    = Config.GROQ_MODEL,
            messages = [
                {"role": "system",  "content": system},
                {"role": "user",    "content": prompt}
            ],
            temperature = 0.8,
            max_tokens  = 1500,
        )
        content = response.choices[0].message.content

        cited_refs   = extract_verse_refs_from_text(content)
        verification = verify_and_ground_verses(cited_refs)

        return {
            "content":       content,
            "content_type":  content_type,
            "topic":         topic,
            "verses_used":   verification["verified"],
            "error":         None
        }

    except Exception as e:
        return {
            "content":      "Unable to generate content at this time.",
            "content_type": content_type,
            "topic":        topic,
            "verses_used":  [],
            "error":        str(e)
        }