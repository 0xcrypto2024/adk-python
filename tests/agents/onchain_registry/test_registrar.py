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

import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from google.adk.agents.onchain_registry.registrar import ERC8004Registrar

class TestERC8004Registrar(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.keystore_path = os.path.join(self.test_dir, "test_keystore.json")
        self.env_patcher = patch.dict(os.environ, {
            "AGENT_WALLET_PASSWORD": "test_password",
            "AGENT_KEYSTORE_PATH": self.keystore_path,
            "AGENT_RPC_URL": "http://localhost:8545",
            "AGENT_REGISTRY_ADDRESS": "0x1234567890123456789012345678901234567890"
        })
        self.env_patcher.start()

    def tearDown(self):
        self.env_patcher.stop()
        shutil.rmtree(self.test_dir)

    def test_create_new_wallet(self):
        registrar = ERC8004Registrar()
        address = registrar.load_or_create_wallet()
        self.assertIsNotNone(address)
        self.assertTrue(os.path.exists(self.keystore_path))

    def test_load_existing_wallet(self):
        # Create a wallet first
        registrar1 = ERC8004Registrar()
        address1 = registrar1.load_or_create_wallet()
        
        # Load it back
        registrar2 = ERC8004Registrar()
        address2 = registrar2.load_or_create_wallet()
        
        self.assertEqual(address1, address2)

    def test_mock_registration(self):
        registrar = ERC8004Registrar()
        registrar.load_or_create_wallet()
        tx_hash = registrar.register("http://test.agent", mock=True)
        self.assertEqual(tx_hash, "0x" + "0" * 64)

    @patch("google.adk.agents.onchain_registry.registrar.Web3")
    def test_real_registration_flow(self, mock_web3_cls):
        # Mock Web3 setup
        mock_w3 = MagicMock()
        mock_web3_cls.return_value = mock_w3
        mock_w3.is_connected.return_value = True
        
        # Mock contract
        mock_contract = MagicMock()
        mock_w3.eth.contract.return_value = mock_contract
        
        # Mock transaction build
        mock_tx_func = MagicMock()
        mock_contract.functions.register.return_value = mock_tx_func
        mock_tx_func.build_transaction.return_value = {"to": "0x...", "data": "0x..."}
        
        # Mock transaction count
        mock_w3.eth.get_transaction_count.return_value = 1
        
        # Mock transaction signing
        mock_signed_tx = MagicMock()
        mock_signed_tx.raw_transaction = b"raw_tx"
        mock_w3.eth.account.sign_transaction.return_value = mock_signed_tx
        
        # Mock send transaction
        mock_w3.eth.send_raw_transaction.return_value = b"tx_hash"
        
        # Mock receipt
        mock_w3.eth.wait_for_transaction_receipt.return_value = {"status": 1}

        registrar = ERC8004Registrar()
        registrar.load_or_create_wallet()
        
        tx_hash = registrar.register("http://test.agent", mock=False)
        
        self.assertEqual(tx_hash, "74785f68617368") # hex of b'tx_hash'
        mock_contract.functions.register.assert_called_with("http://test.agent")

if __name__ == "__main__":
    unittest.main()
