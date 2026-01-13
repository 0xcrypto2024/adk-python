# Proposal: ERC8004 Agent Auto-Registration

## 1. Overview
This proposal introduces an automatic on-chain registration mechanism for agents using the ERC8004 standard. This feature allows agents to automatically register their external service URL on a target blockchain upon initialization, making them discoverable and verifiable in a decentralized registry.

## 2. Implementation Details

### Core Components
*   **`onchain_registry` Module**: A new module at `src/google/adk/agents/onchain_registry` containing the `ERC8004Registrar` class. This class handles:
    *   Wallet management (loading/creating/encrypting).
    *   Blockchain interaction (Web3 connection, contract calls).
    *   Registration logic (checking status, sending transactions).
*   **Mock RPC Server**: `src/google/adk/agents/onchain_registry/mock_rpc.py` implementing a lightweight JSON-RPC server (FastAPI) to simulate Ethereum endpoints (`eth_chainId`, `eth_sendRawTransaction`, etc.). This enables full end-to-end testing without a real network connection.
*   **`BaseAgent` Integration**: The `BaseAgent` class now includes a hook in `model_post_init` to trigger registration if enabled.
*   **Configuration**: Prioritized `enable_erc8004_registration` flag in `BaseAgentConfig` and environment variables.

### Dependencies
*   Added `web3` and `eth-account` to `pyproject.toml`.

## 3. Key Design Decisions

### Wallet Management Strategy
To balance usability and security, the agent follows this priority order for wallet resolution:
1.  **`AGENT_PRIVATE_KEY` (Env)**: Highest priority. Use provided key directly.
2.  **`AGENT_KEYSTORE_PATH` (File)**: If exists, load and decrypt using `AGENT_WALLET_PASSWORD`.
3.  **Auto-Generation**: If neither exists, generate a new wallet, encrypt it with `AGENT_WALLET_PASSWORD`, and save it to `AGENT_KEYSTORE_PATH` (default: `./agent_keystore.json`).

### URL Discovery
The agent cannot reliably inspect its own public URL during startup (especially in containerized/cloud environments). Therefore, we mandate the use of the **`AGENT_EXTERNAL_URL`** environment variable.

### Non-Blocking Execution
Registration involves network calls to the blockchain. To prevent stalling agent startup:
*   In standard async contexts (e.g., `adk run`), registration runs in the background via `loop.run_in_executor`.
*   Exceptions are logged as errors/warnings but do **not** crash the agent.

## 4. Developer Tools
We included a **Mock RPC Server** (`mock_rpc.py`) that developers can use to verify the registration flow locally.
- Run it: `uvicorn google.adk.agents.onchain_registry.mock_rpc:app --port 8545`
- Point your agent to it: `export AGENT_RPC_URL="http://localhost:8545"`

---

# Tutorial: Using ERC8004 Auto-Registration

## Prerequisites
Before starting your agent, ensure you have the following information:
1.  **RPC URL**: A WebSocket or HTTP endpoint for your target blockchain (e.g., `https://mainnet.infura.io/v3/...` or a local Anvil node).
2.  **Registry Address**: The contract address of the ERC8004 registry.
3.  **External URL**: The public URL where your agent is hosted.

## Step 1: Configuration

### Environment Variables
Create a `.env` file or export the following variables:

```bash
# Required
export AGENT_EXTERNAL_URL="https://my-awesome-agent.com"
export AGENT_RPC_URL="https://your-blockchain-rpc.com"
export AGENT_REGISTRY_ADDRESS="0xYourRegistryContractAddress"
export AGENT_WALLET_PASSWORD="your-secure-password"

# Optional
# export AGENT_PRIVATE_KEY="0x..."  # Only if you want to bring your own key
# export AGENT_KEYSTORE_PATH="./custom_keystore.json" # Default is ./agent_keystore.json
```

### Code Configuration
Enable the feature in your agent's configuration:

```python
from google.adk.agents import BaseAgent, BaseAgentConfig

class MyAgent(BaseAgent):
    # ... your agent logic ...
    pass

# When instantiating (or via YAML config):
agent = MyAgent(
    name="my_agent",
    enable_erc8004_registration=True, 
    # mock_registration=True # Use this to test without spending gas!
)
```

## Step 2: First Run (Wallet Creation)
When you run your agent for the first time without a private key:
```bash
adk run agent.py
```

**What happens:**
1.  The agent sees no existing wallet.
2.  It generates a new Ethereum account.
3.  It encrypts the private key with your `AGENT_WALLET_PASSWORD` and saves it to `agent_keystore.json`.
4.  It attempts to register against the `AGENT_RPC_URL`.

## Step 3: Registration Verification
Check your agent's logs. You should see messages like:

```text
INFO:google_adk.agents.onchain_registry.registrar:Loaded wallet from keystore: 0x123...
INFO:google_adk.agents.onchain_registry.registrar:Sending registration transaction for https://my-awesome-agent.com...
INFO:google_adk.agents.onchain_registry.registrar:Successfully registered agent URL on-chain. Tx: 0xabc...
```
