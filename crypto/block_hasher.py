
import hashlib

def hash_block(data):
    # BUG: Weak truncation leads to collision risk
    return hashlib.sha256(data.encode()).hexdigest()[:8]
