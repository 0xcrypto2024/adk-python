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

import logging
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("mock_rpc")

app = FastAPI()

MOCK_CHAIN_ID = 1337  # Standard local dev chain ID
MOCK_TX_HASH = "0x" + "a" * 64
MOCK_BLOCK_HASH = "0x" + "b" * 64

@app.post("/")
async def handle_rpc(request: Request):
    """Handles JSON-RPC requests."""
    try:
        data = await request.json()
        method = data.get("method")
        params = data.get("params", [])
        req_id = data.get("id")
        
        logger.info(f"RPC Request: {method} params={params}")

        result = None

        if method == "eth_chainId":
            result = hex(MOCK_CHAIN_ID)
        elif method == "net_version":
            result = str(MOCK_CHAIN_ID)
        elif method == "eth_getTransactionCount":
            result = "0x0"
        elif method == "eth_gasPrice":
            result = "0x3b9aca00"  # 1 Gwei
        elif method == "eth_estimateGas":
            result = "0x5208"  # 21000
        elif method == "eth_maxPriorityFeePerGas":
            result = "0x3b9aca00"  # 1 Gwei
        elif method == "eth_getBlockByNumber":
            # Minimal block with baseFeePerGas for EIP-1559 simulation
            result = {
                "number": "0x1",
                "hash": MOCK_BLOCK_HASH,
                "parentHash": "0x" + "0"*64,
                "nonce": "0x0000000000000000",
                "sha3Uncles": "0x" + "0"*64,
                "logsBloom": "0x" + "0"*512,
                "transactionsRoot": "0x" + "0"*64,
                "stateRoot": "0x" + "0"*64,
                "receiptsRoot": "0x" + "0"*64,
                "miner": "0x" + "0"*40,
                "difficulty": "0x0",
                "totalDifficulty": "0x0",
                "extraData": "0x",
                "size": "0x3e8",
                "gasLimit": "0x1c9c380", # 30M
                "gasUsed": "0x0",
                "timestamp": "0x64fc9d77",
                "transactions": [],
                "uncles": [],
                "baseFeePerGas": "0x3b9aca00" # 1 Gwei
            }
        elif method == "eth_sendRawTransaction":
            result = MOCK_TX_HASH
        elif method == "eth_getTransactionReceipt":
            # Return a valid receipt for the mock tx hash
            if params and params[0] == MOCK_TX_HASH:
                result = {
                    "transactionHash": MOCK_TX_HASH,
                    "transactionIndex": "0x1",
                    "blockHash": MOCK_BLOCK_HASH,
                    "blockNumber": "0x1",
                    "from": "0x" + "1" * 40,
                    "to": "0x" + "2" * 40,
                    "cumulativeGasUsed": "0x5208",
                    "gasUsed": "0x5208",
                    "contractAddress": None,
                    "logs": [],
                    "logsBloom": "0x0",
                    "status": "0x1",  # Success
                }
            else:
                result = None
        else:
            # Default fallback for unhandled read methods like eth_call
            logger.warning(f"Unhandled RPC Method: {method}")
            result = "0x0"

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": result
        }

    except Exception as e:
        logger.error(f"RPC Error: {e}")
        return JSONResponse(
            status_code=500,
            content={"jsonrpc": "2.0", "id": None, "error": {"code": -32000, "message": str(e)}}
        )

def run_mock_rpc(host="127.0.0.1", port=8545):
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    run_mock_rpc()
