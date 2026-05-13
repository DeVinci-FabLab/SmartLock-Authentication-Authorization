import hashlib


def hash_card_id(card_id: str) -> str:
    return hashlib.sha256(card_id.strip().encode()).hexdigest()
