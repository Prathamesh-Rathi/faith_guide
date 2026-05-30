"""
Run once: python seed_bible.py
Indexes Bible verses into ChromaDB for RAG grounding.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.grounding import seed_core_verses, get_collection

print("=" * 50)
print("FaithGuide — Bible Seeder")
print("=" * 50)

seed_core_verses()

collection = get_collection()
print(f"\nTotal verses in ChromaDB: {collection.count()}")
print("Done! You can now run the app.")