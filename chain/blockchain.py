"""
Blockchain Core - Block and chain management.

BUG INVENTORY:
- BUG-057: Hash calculation doesn't include previous hash (chain breakable)
- BUG-058: No merkle tree - transaction tampering undetectable
- BUG-059: Timestamp manipulation not prevented
- BUG-060: Double-spend not checked in mempool
"""

import hashlib
import json
import time
from datetime import datetime
from typing import List, Dict, Optional


class Transaction:
    def __init__(self, sender: str, receiver: str, amount: float,
                 signature: str = ""):
        self.id = hashlib.sha256(
            f"{sender}{receiver}{amount}{time.time()}".encode()
        ).hexdigest()[:16]
        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        self.signature = signature
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sender": self.sender,
            "receiver": self.receiver,
            "amount": self.amount,
            "timestamp": self.timestamp.isoformat(),
        }


class Block:
    def __init__(self, index: int, transactions: List[Transaction],
                 previous_hash: str, nonce: int = 0):
        self.index = index
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.timestamp = datetime.utcnow()
        self.hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        """
        Calculate block hash.

        BUG-057: previous_hash is NOT included in the hash calculation.
        This means the chain link is weak - modifying a previous block's
        hash won't invalidate subsequent blocks.
        """
        # BUG-057: Missing previous_hash in calculation
        block_data = json.dumps({
            "index": self.index,
            "transactions": [t.to_dict() for t in self.transactions],
            # "previous_hash": self.previous_hash,  # BUG: This is missing!
            "nonce": self.nonce,
            "timestamp": self.timestamp.isoformat(),
        }, sort_keys=True)

        return hashlib.sha256(block_data.encode()).hexdigest()


class Blockchain:
    """Core blockchain implementation."""

    def __init__(self, difficulty: int = 2):
        self.chain: List[Block] = []
        self.pending_transactions: List[Transaction] = []
        self.difficulty = difficulty
        self.mining_reward = 10.0
        self.balances: Dict[str, float] = {}

        # Create genesis block
        self._create_genesis_block()

    def _create_genesis_block(self):
        """Create the first block in the chain."""
        genesis = Block(0, [], "0")
        self.chain.append(genesis)

    def add_transaction(self, txn: Transaction) -> bool:
        """
        Add transaction to mempool.

        BUG-060: No double-spend check - same funds can be spent
        multiple times before a block is mined.
        """
        if txn.amount <= 0:
            return False

        # BUG-060: Only checks mined balance, not pending transactions
        sender_balance = self.balances.get(txn.sender, 0)
        if txn.sender != "SYSTEM" and sender_balance < txn.amount:
            return False

        # BUG-060: Doesn't check if sender has enough after other pending txns
        self.pending_transactions.append(txn)
        return True

    def mine_block(self, miner_address: str) -> Block:
        """Mine a new block with proof-of-work."""
        # Add mining reward transaction
        reward_txn = Transaction("SYSTEM", miner_address, self.mining_reward)
        self.pending_transactions.insert(0, reward_txn)

        # Create new block
        previous_block = self.chain[-1]
        new_block = Block(
            len(self.chain),
            self.pending_transactions[:],
            previous_block.hash,
        )

        # Proof of work
        target = "0" * self.difficulty
        while not new_block.hash.startswith(target):
            new_block.nonce += 1
            new_block.hash = new_block.calculate_hash()

        # Update balances
        for txn in new_block.transactions:
            if txn.sender != "SYSTEM":
                self.balances[txn.sender] = (
                    self.balances.get(txn.sender, 0) - txn.amount
                )
            self.balances[txn.receiver] = (
                self.balances.get(txn.receiver, 0) + txn.amount
            )

        # Add block and clear pending
        self.chain.append(new_block)
        self.pending_transactions.clear()

        return new_block

    def is_chain_valid(self) -> bool:
        """
        Validate the entire blockchain.

        BUG-057: Validation is weak because block hashes don't
        include previous_hash, so chain integrity isn't fully verified.
        """
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]

            # Check hash integrity
            if current.hash != current.calculate_hash():
                return False

            # Check chain linking
            if current.previous_hash != previous.hash:
                return False

        return True

    def get_balance(self, address: str) -> float:
        """Get balance for an address."""
        return self.balances.get(address, 0)

    def get_chain_info(self) -> dict:
        """Get blockchain summary."""
        total_txns = sum(len(b.transactions) for b in self.chain)
        return {
            "chain_length": len(self.chain),
            "total_transactions": total_txns,
            "pending_transactions": len(self.pending_transactions),
            "difficulty": self.difficulty,
            "total_addresses": len(self.balances),
            "latest_hash": self.chain[-1].hash if self.chain else None,
        }
