import chromadb
import json
import os
import re
from sentence_transformers import SentenceTransformer
from config import Config


# ── Singleton loader ─────────────────────────────────────────────────────────
_chroma_client     = None
_collection        = None
_embedding_model   = None


def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        print("Loading embedding model (first time only)...")
        _embedding_model = SentenceTransformer(Config.EMBEDDING_MODEL)
    return _embedding_model


def get_collection():
    global _chroma_client, _collection
    if _collection is None:
        _chroma_client = chromadb.PersistentClient(path=Config.CHROMA_DB_PATH)
        _collection    = _chroma_client.get_or_create_collection(
            name=Config.CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"}
        )
    return _collection


# ── Core Bible data — key verses hardcoded as reliable seed ──────────────────
# This ensures the system works even before full Bible indexing
CORE_VERSES = {
    "John 3:16": "For God so loved the world that he gave his one and only Son, that whoever believes in him shall not perish but have eternal life.",
    "Romans 8:28": "And we know that in all things God works for the good of those who love him, who have been called according to his purpose.",
    "Psalm 23:1": "The Lord is my shepherd, I lack nothing.",
    "Psalm 23:4": "Even though I walk through the darkest valley, I will fear no evil, for you are with me; your rod and your staff, they comfort me.",
    "Proverbs 3:5": "Trust in the Lord with all your heart and lean not on your own understanding.",
    "Proverbs 3:6": "in all your ways submit to him, and he will make your paths straight.",
    "Isaiah 40:31": "but those who hope in the Lord will renew their strength. They will soar on wings like eagles; they will run and not grow weary, they will walk and not be faint.",
    "Jeremiah 29:11": "For I know the plans I have for you, declares the Lord, plans to prosper you and not to harm you, plans to give you hope and a future.",
    "Matthew 5:3": "Blessed are the poor in spirit, for theirs is the kingdom of heaven.",
    "Matthew 5:4": "Blessed are those who mourn, for they will be comforted.",
    "Matthew 6:9": "Our Father in heaven, hallowed be your name,",
    "Matthew 6:33": "But seek first his kingdom and his righteousness, and all these things will be given to you as well.",
    "Matthew 28:19": "Therefore go and make disciples of all nations, baptizing them in the name of the Father and of the Son and of the Holy Spirit,",
    "John 1:1": "In the beginning was the Word, and the Word was with God, and the Word was God.",
    "John 1:14": "The Word became flesh and made his dwelling among us.",
    "John 11:25": "Jesus said to her, I am the resurrection and the life. The one who believes in me will live, even though they die;",
    "John 14:6": "Jesus answered, I am the way and the truth and the life. No one comes to the Father except through me.",
    "Romans 3:23": "for all have sinned and fall short of the glory of God,",
    "Romans 6:23": "For the wages of sin is death, but the gift of God is eternal life in Christ Jesus our Lord.",
    "Romans 10:9": "If you declare with your mouth, Jesus is Lord, and believe in your heart that God raised him from the dead, you will be saved.",
    "1 Corinthians 13:4": "Love is patient, love is kind. It does not envy, it does not boast, it is not proud.",
    "1 Corinthians 13:13": "And now these three remain: faith, hope and love. But the greatest of these is love.",
    "Galatians 5:22": "But the fruit of the Spirit is love, joy, peace, forbearance, kindness, goodness, faithfulness,",
    "Ephesians 2:8": "For it is by grace you have been saved, through faith and this is not from yourselves, it is the gift of God",
    "Philippians 4:6": "Do not be anxious about anything, but in every situation, by prayer and petition, with thanksgiving, present your requests to God.",
    "Philippians 4:7": "And the peace of God, which transcends all understanding, will guard your hearts and your minds in Christ Jesus.",
    "Philippians 4:13": "I can do all this through him who gives me strength.",
    "2 Timothy 3:16": "All Scripture is God-breathed and is useful for teaching, rebuking, correcting and training in righteousness,",
    "Hebrews 11:1": "Now faith is confidence in what we hope for and assurance about what we do not see.",
    "James 1:5": "If any of you lacks wisdom, you should ask God, who gives generously to all without finding fault, and it will be given to you.",
    "1 John 4:8": "Whoever does not love does not know God, because God is love.",
    "Revelation 21:4": "He will wipe every tear from their eyes. There will be no more death or mourning or crying or pain, for the old order of things has passed away.",
    "Genesis 1:1": "In the beginning God created the heavens and the earth.",
    "Exodus 20:3": "You shall have no other gods before me.",
    "Deuteronomy 6:4": "Hear, O Israel: The Lord our God, the Lord is one.",
    "Joshua 1:9": "Have I not commanded you? Be strong and courageous. Do not be afraid; do not be discouraged, for the Lord your God will be with you wherever you go.",
    "Psalm 119:105": "Your word is a lamp for my feet, a light on my path.",
    "Psalm 46:1": "God is our refuge and strength, an ever-present help in trouble.",
    "Isaiah 53:5": "But he was pierced for our transgressions, he was crushed for our iniquities; the punishment that brought us peace was on him, and by his wounds we are healed.",
    "Micah 6:8": "He has shown you, O mortal, what is good. And what does the Lord require of you? To act justly and to love mercy and to walk humbly with your God.",
    "Luke 1:37": "For no word from God will ever fail.",
    "Acts 1:8": "But you will receive power when the Holy Spirit comes on you; and you will be my witnesses in Jerusalem, and in all Judea and Samaria, and to the ends of the earth.",
    "Acts 2:38": "Peter replied, Repent and be baptized, every one of you, in the name of Jesus Christ for the forgiveness of your sins. And you will receive the gift of the Holy Spirit.",
}

# Books and chapter counts for validation
BIBLE_BOOKS = {
    # Old Testament
    "Genesis": 50, "Exodus": 40, "Leviticus": 27, "Numbers": 36,
    "Deuteronomy": 34, "Joshua": 24, "Judges": 21, "Ruth": 4,
    "1 Samuel": 31, "2 Samuel": 24, "1 Kings": 22, "2 Kings": 25,
    "1 Chronicles": 29, "2 Chronicles": 36, "Ezra": 10, "Nehemiah": 13,
    "Esther": 10, "Job": 42, "Psalm": 150, "Psalms": 150,
    "Proverbs": 31, "Ecclesiastes": 12, "Song of Solomon": 8,
    "Isaiah": 66, "Jeremiah": 52, "Lamentations": 5, "Ezekiel": 48,
    "Daniel": 12, "Hosea": 14, "Joel": 3, "Amos": 9, "Obadiah": 1,
    "Jonah": 4, "Micah": 7, "Nahum": 3, "Habakkuk": 3, "Zephaniah": 3,
    "Haggai": 2, "Zechariah": 14, "Malachi": 4,
    # New Testament
    "Matthew": 28, "Mark": 16, "Luke": 24, "John": 21, "Acts": 28,
    "Romans": 16, "1 Corinthians": 16, "2 Corinthians": 13,
    "Galatians": 6, "Ephesians": 6, "Philippians": 4, "Colossians": 4,
    "1 Thessalonians": 5, "2 Thessalonians": 3, "1 Timothy": 6,
    "2 Timothy": 4, "Titus": 3, "Philemon": 1, "Hebrews": 13,
    "James": 5, "1 Peter": 5, "2 Peter": 3, "1 John": 5,
    "2 John": 1, "3 John": 1, "Jude": 1, "Revelation": 22,
}


def seed_core_verses():
    """Index the core hardcoded verses into ChromaDB."""
    collection = get_collection()
    model      = get_embedding_model()

    existing = collection.count()
    if existing >= len(CORE_VERSES):
        print(f"ChromaDB already has {existing} verses. Skipping seed.")
        return

    print(f"Seeding {len(CORE_VERSES)} core verses into ChromaDB...")
    ids        = []
    documents  = []
    embeddings = []
    metadatas  = []

    for ref, text in CORE_VERSES.items():
        full_text  = f"{ref}: {text}"
        embedding  = model.encode(full_text).tolist()
        safe_id    = ref.replace(" ", "_").replace(":", "_")

        ids.append(safe_id)
        documents.append(full_text)
        embeddings.append(embedding)
        metadatas.append({"reference": ref, "text": text})

    collection.upsert(
        ids        = ids,
        documents  = documents,
        embeddings = embeddings,
        metadatas  = metadatas
    )
    print(f"Seeded {len(CORE_VERSES)} verses successfully.")


# ── Verse reference validator ────────────────────────────────────────────────
def validate_verse_reference(reference: str) -> dict:
    """
    Check if a Bible verse reference is structurally valid.
    Returns {valid: bool, reason: str}

    Catches hallucinated refs like 'Exodus 45:12' (only 40 chapters)
    or 'John 25:3' (John only has 21 chapters).
    """
    reference = reference.strip()

    # Pattern: Book Chapter:Verse  or  Book Chapter:Verse-Verse
    pattern = r'^(.+?)\s+(\d+):(\d+)(?:-(\d+))?$'
    match   = re.match(pattern, reference)

    if not match:
        return {"valid": False, "reason": f"Cannot parse reference format: '{reference}'"}

    book    = match.group(1).strip()
    chapter = int(match.group(2))
    verse   = int(match.group(3))

    # Check book exists
    book_key = None
    for b in BIBLE_BOOKS:
        if b.lower() == book.lower():
            book_key = b
            break

    if not book_key:
        return {"valid": False, "reason": f"'{book}' is not a recognized Bible book"}

    # Check chapter range
    max_chapters = BIBLE_BOOKS[book_key]
    if chapter < 1 or chapter > max_chapters:
        return {
            "valid":  False,
            "reason": f"{book_key} only has {max_chapters} chapters (got chapter {chapter})"
        }

    return {"valid": True, "reason": "Reference is structurally valid"}


# ── Semantic Bible search ─────────────────────────────────────────────────────
def search_bible(query: str, top_k: int = None) -> list:
    """
    Search ChromaDB for Bible verses semantically relevant to a query.
    Returns list of {reference, text, score} dicts.
    """
    if top_k is None:
        top_k = Config.TOP_K_VERSES

    collection = get_collection()
    model      = get_embedding_model()

    if collection.count() == 0:
        seed_core_verses()

    query_embedding = model.encode(query).tolist()

    results = collection.query(
        query_embeddings = [query_embedding],
        n_results        = min(top_k, collection.count()),
        include          = ["documents", "metadatas", "distances"]
    )

    verses = []
    if results and results["metadatas"]:
        for i, meta in enumerate(results["metadatas"][0]):
            distance = results["distances"][0][i]
            score    = round(1 - distance, 4)   # cosine similarity
            verses.append({
                "reference": meta.get("reference", ""),
                "text":      meta.get("text", ""),
                "score":     score,
            })

    return verses


# ── Verse text lookup ─────────────────────────────────────────────────────────
def get_verse_text(reference: str) -> dict:
    """
    Look up exact verse text from ChromaDB.
    Returns {found: bool, text: str, reference: str}
    """
    # First check hardcoded core verses (most reliable)
    for ref, text in CORE_VERSES.items():
        if ref.lower() == reference.lower():
            return {"found": True, "text": text, "reference": ref}

    # Then search ChromaDB
    collection = get_collection()
    model      = get_embedding_model()

    query_embedding = model.encode(reference).tolist()
    results = collection.query(
        query_embeddings = [query_embedding],
        n_results        = 1,
        include          = ["metadatas", "distances"]
    )

    if results and results["metadatas"] and results["metadatas"][0]:
        meta     = results["metadatas"][0][0]
        distance = results["distances"][0][0]
        if distance < 0.15:   # Very close match
            return {
                "found":     True,
                "text":      meta.get("text", ""),
                "reference": meta.get("reference", reference)
            }

    return {"found": False, "text": "", "reference": reference}


# ── Full hallucination guard ──────────────────────────────────────────────────
def verify_and_ground_verses(verse_refs: list) -> dict:
    """
    Given a list of verse references the AI wants to cite:
    1. Validate structural correctness (book/chapter exists)
    2. Look up actual text from our database
    3. Return only verified verses

    Returns {
        verified: [{reference, text}],
        rejected: [{reference, reason}]
    }
    """
    verified = []
    rejected = []

    for ref in verse_refs:
        # Step 1 — structural validation
        validation = validate_verse_reference(ref)
        if not validation["valid"]:
            rejected.append({"reference": ref, "reason": validation["reason"]})
            continue

        # Step 2 — text lookup
        lookup = get_verse_text(ref)
        if lookup["found"]:
            verified.append({
                "reference": lookup["reference"],
                "text":      lookup["text"]
            })
        else:
            # Valid structure but not in our DB — mark as unverified
            rejected.append({
                "reference": ref,
                "reason":    "Verse not found in verified database — may be hallucinated"
            })

    return {"verified": verified, "rejected": rejected}


# ── Context builder for prompt injection ─────────────────────────────────────
def build_scripture_context(query: str) -> str:
    """
    Retrieve relevant Bible verses for a query and format them
    as a context block to inject into the AI prompt.
    """
    verses = search_bible(query, top_k=Config.TOP_K_VERSES)
    if not verses:
        return ""

    lines = ["RELEVANT SCRIPTURE (verified from database):"]
    for v in verses:
        lines.append(f'  • {v["reference"]}: "{v["text"]}"')

    return "\n".join(lines)