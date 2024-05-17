
import hashlib

def hash_block(data):
    # FIX: Use full 256-bit hash for cryptographic security
    return hashlib.sha256(data.encode()).hexdigest()
