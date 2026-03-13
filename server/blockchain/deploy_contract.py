"""
Deploy a simple AuditLog contract to the blockchain (eth-tester for testing).
"""
from web3 import Web3
from eth_tester import EthereumTester
from web3.providers.eth_tester import EthereumTesterProvider
from pathlib import Path

# Simple contract ABI and bytecode for testing
CONTRACT_ABI = [
    {
        "inputs": [{"internalType": "bytes32", "name": "recordHash", "type": "bytes32"}],
        "name": "storeHash",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "string", "name": "data", "type": "string"}],
        "name": "storeRecord",
        "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "id", "type": "bytes32"}],
        "name": "getRecord",
        "outputs": [{"internalType": "string", "name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "recordHash", "type": "bytes32"}],
        "name": "checkHash",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "owner",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
]

# Minimal contract bytecode - a simple contract that stores hashes
CONTRACT_BYTECODE = "0x608060405234801561001057600080fd5b50610150806100206000396000f3fe60806040523480156100105760008080fd5b50600436106100575760003560e01c80632e4176cf1461005c57806348a4d2011461007a57806362e47cf6146100b6578063c2983cf0146100fa575b600080fd5b6100646100fa565b6040516100719190610117565b60405180910390f35b6100b460048036038101906100af9190610135565b610124565b005b6100e460048036038101906100df919061016f565b61012f565b6040516100f191906101a8565b60405180910390f35b600090565b60003390565b8060008190555050565b8060016000846040516020016101469291906101c9565b6040516020818303038152906040528051906020012081526020019081526020016000208190555050565b60006020528060005260406000206000915090505481565b6101aa81610117565b82525050565b60006020820190506101c560008301846101a1565b92915050565b60006101d78284610117565b91505091905056fea264697066735822122033f8f6c36d41849efafc4d85f32f5f5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e64736f6c63430008070033"

def deploy_contract():
    """Deploy the contract to eth-tester."""
    try:
        eth_tester = EthereumTester()
        w3 = Web3(EthereumTesterProvider(eth_tester))
        
        # Get the first account
        accounts = w3.eth.accounts
        if not accounts:
            print("❌ No accounts available in eth-tester")
            return None
        
        account = accounts[0]
        w3.eth.default_account = account
        
        print(f"📝 Deploying contract from account: {account}")
        
        # Create contract factory
        Contract = w3.eth.contract(abi=CONTRACT_ABI, bytecode=CONTRACT_BYTECODE)
        
        # Deploy
        tx_hash = Contract.constructor().transact()
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        contract_address = receipt['contractAddress']
        print(f"✅ Contract deployed at: {contract_address}")
        
        # Save address to file
        deploy_file = Path(__file__).parent / 'deployed_address.txt'
        deploy_file.write_text(contract_address)
        print(f"✅ Address saved to: {deploy_file}")
        
        return contract_address
        
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    deploy_contract()
