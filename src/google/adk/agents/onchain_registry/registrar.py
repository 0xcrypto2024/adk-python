# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import logging
import os
from pathlib import Path
from typing import Optional, Union

from eth_account import Account
from web3 import Web3
from web3.exceptions import ContractLogicError

logger = logging.getLogger("google_adk.agents.onchain_registry")

DEFAULT_KEYSTORE_PATH = "agent_keystore.json"

class ERC8004Registrar:
    """Handles ERC8004 registration operations."""

    def __init__(self):
        self._w3: Optional[Web3] = None
        self._account = None
        self._contract = None
        self._registry_address = os.getenv("AGENT_REGISTRY_ADDRESS")
        
        # Initialize Web3 if RPC URL is present
        rpc_url = os.getenv("AGENT_RPC_URL")
        if rpc_url:
            self._w3 = Web3(Web3.HTTPProvider(rpc_url))
            if self._w3.is_connected():
                logger.info(f"Connected to blockchain RPC: {rpc_url}")
            else:
                logger.warning(f"Failed to connect to blockchain RPC: {rpc_url}")

    def load_or_create_wallet(self) -> Optional[str]:
        """Loads existing wallet or creates a new one. Returns the address."""
        password = os.getenv("AGENT_WALLET_PASSWORD")
        if not password:
            logger.warning("AGENT_WALLET_PASSWORD not set. Cannot manage wallet.")
            return None

        # Priority 1: Private Key from Env
        private_key = os.getenv("AGENT_PRIVATE_KEY")
        if private_key:
            try:
                self._account = Account.from_key(private_key)
                logger.info(f"Loaded wallet from private key: {self._account.address}")
                return self._account.address
            except Exception as e:
                logger.error(f"Failed to load wallet from private key: {e}")
                return None

        # Priority 2: Keystore File
        keystore_path = os.getenv("AGENT_KEYSTORE_PATH", DEFAULT_KEYSTORE_PATH)
        keystore_file = Path(keystore_path)

        if keystore_file.exists():
            try:
                with open(keystore_file, "r") as f:
                    encrypted_key = f.read()
                    self._account = Account.from_key(
                        Account.decrypt(encrypted_key, password)
                    )
                logger.info(f"Loaded wallet from keystore: {self._account.address}")
                return self._account.address
            except Exception as e:
                logger.error(f"Failed to decrypt keystore at {keystore_path}: {e}")
                return None

        # Priority 3: Create New Wallet
        try:
            logger.info("No existing wallet found. Creating new wallet...")
            self._account = Account.create()
            encrypted_key = Account.encrypt(self._account.key, password)
            
            with open(keystore_file, "w") as f:
                json.dump(encrypted_key, f)
            
            logger.info(f"Created new wallet: {self._account.address}")
            logger.info(f"Keystore saved to: {keystore_path}")
            return self._account.address
        except Exception as e:
            logger.error(f"Failed to create new wallet: {e}")
            return None

    def _get_default_abi(self):
        # Minimal ERC8004-like ABI for registration
        # Assuming function signature: register(string url)
        return [
            {
                "inputs": [{"internalType": "string", "name": "url", "type": "string"}],
                "name": "register",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function",
            }
        ]

    def register(self, agent_url: str, mock: bool = False) -> Optional[str]:
        """Registers the agent URL on-chain.
        
        Args:
            agent_url: The external URL of the agent.
            mock: If True, simulate the transaction.
            
        Returns:
            Transaction hash if successful, None otherwise.
        """
        if mock:
            logger.info(f"[MOCK] Registering agent URL: {agent_url}")
            logger.info(f"[MOCK] Wallet Address: {self._account.address if self._account else 'N/A'}")
            return "0x" + "0" * 64

        if not self._w3 or not self._w3.is_connected():
            logger.error("Cannot register: Web3 not connected.")
            return None

        if not self._account:
            logger.error("Cannot register: No wallet loaded.")
            return None
            
        if not self._registry_address:
             logger.error("Cannot register: AGENT_REGISTRY_ADDRESS not set.")
             return None

        try:
            # Checksum address
            registry_address = Web3.to_checksum_address(self._registry_address)
            contract = self._w3.eth.contract(
                address=registry_address, 
                abi=self._get_default_abi()
            )

            # Build transaction
            # Note: We are assuming a gasless RPC or funded account.
            # We do NOT check balance here as per requirements.
            
            tx = contract.functions.register(agent_url).build_transaction({
                'from': self._account.address,
                'nonce': self._w3.eth.get_transaction_count(self._account.address),
            })
            
            # Estimate gas if needed, or rely on RPC default. 
            # For robustness, let's try to estimate gas but fallback safe.
            try:
                 gas_estimate = self._w3.eth.estimate_gas(tx)
                 tx['gas'] = int(gas_estimate * 1.2) # Buffer
            except Exception as e:
                logger.warning(f"Gas estimation failed (might be expected for gasless): {e}. Proceeding with default.")

            # Sign transaction
            signed_tx = self._w3.eth.account.sign_transaction(tx, self._account.key)
            
            # Send transaction
            logger.info(f"Sending registration transaction for {agent_url}...")
            tx_hash = self._w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            # Wait for receipt
            receipt = self._w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt['status'] == 1:
                logger.info(f"Successfully registered agent URL on-chain. Tx: {self._w3.to_hex(tx_hash)}")
                return self._w3.to_hex(tx_hash)
            else:
                logger.error(f"Registration transaction failed. Tx: {self._w3.to_hex(tx_hash)}")
                return None

        except ContractLogicError as e:
             logger.error(f"Contract logic error during registration: {e}")
             return None
        except Exception as e:
            logger.error(f"Unexpected error during registration: {e}")
            return None
