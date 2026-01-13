import multiprocessing
import os
import time
import uvicorn
from google.adk.agents.onchain_registry.mock_rpc import app
from google.adk.agents.onchain_registry.registrar import ERC8004Registrar

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8545, log_level="warning")

def verify_registration():
    # Set env vars to point to our mock server
    os.environ["AGENT_RPC_URL"] = "http://127.0.0.1:8545"
    os.environ["AGENT_REGISTRY_ADDRESS"] = "0x" + "1"*40
    os.environ["AGENT_WALLET_PASSWORD"] = "testpass"
    os.environ["AGENT_KEYSTORE_PATH"] = "test_keystore.json"
    
    # Ensure no old keystore
    if os.path.exists("test_keystore.json"):
        os.remove("test_keystore.json")

    print(">>> Starting Mock RPC Server...")
    server_process = multiprocessing.Process(target=run_server)
    server_process.start()
    
    try:
        # Give server time to start
        time.sleep(2)
        
        print(">>> Initializing Registrar...")
        registrar = ERC8004Registrar()
        
        print(">>> Creating Wallet...")
        addr = registrar.load_or_create_wallet()
        print(f"   Wallet created: {addr}")
        
        print(">>> Attempting Registration (mock=False, forcing real network call)...")
        # internal register logic will call web3 -> mock rpc
        tx_hash = registrar.register("http://test.url", mock=False)
        
        print(f">>> Result Tx Hash: {tx_hash}")
        
        expected_hash = "0x" + "a"*64
        if tx_hash == expected_hash:
            print(">>> SUCCESS: Registration confirmed via Mock RPC!")
        else:
            print(f">>> FAILURE: Tx hash mismatch. Got {tx_hash}, expected {expected_hash}")
            raise Exception("Tx hash mismatch")
            
    finally:
        print(">>> Stopping Server...")
        server_process.terminate()
        server_process.join()
        if os.path.exists("test_keystore.json"):
            os.remove("test_keystore.json")

if __name__ == "__main__":
    verify_registration()
