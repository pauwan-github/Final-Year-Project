import os
import json
from pathlib import Path
from web3 import Web3

# Try to use eth-tester for in-memory blockchain
try:
    from eth_tester import EthereumTester
    from web3.providers.eth_tester import EthereumTesterProvider
    USE_ETH_TESTER = True
except Exception:
    USE_ETH_TESTER = False
    print("eth-tester not available, falling back to HTTP provider")

# Import `geth_poa_middleware` with compatibility for web3.py v5 and v6.
try:
    # v5 location
    from web3.middleware.geth_poa import geth_poa_middleware  # type: ignore
except Exception:
    # v6+ exposes middleware at package level
    try:
        from web3.middleware import geth_poa_middleware  # type: ignore
    except Exception:
        # Last resort: define a no-op middleware to avoid import errors when not available.
        def geth_poa_middleware(make_request, w3):
            def middleware(method, params):
                return make_request(method, params)
            return middleware

# ABI for AuditLog contract (includes authorization helpers)
ABI = [
    {
        "inputs": [
            {"internalType": "bytes32", "name": "recordHash", "type": "bytes32"}
        ],
        "name": "storeHash",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "string","name": "data","type": "string"}],
        "name": "storeRecord",
        "outputs": [{"internalType": "bytes32","name": "","type": "bytes32"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "bytes32","name": "id","type": "bytes32"}],
        "name": "getRecord",
        "outputs": [{"internalType": "string","name": "","type": "string"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "recordHash", "type": "bytes32"}
        ],
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
    {
        "inputs": [{"internalType": "address", "name": "account", "type": "address"}],
        "name": "addAuthorized",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "address", "name": "account", "type": "address"}],
        "name": "removeAuthorized",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "address", "name": "account", "type": "address"}],
        "name": "isAuthorized",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "patient", "type": "address"},
            {"internalType": "string", "name": "consentType", "type": "string"}
        ],
        "name": "giveConsent",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "patient", "type": "address"},
            {"internalType": "string", "name": "consentType", "type": "string"}
        ],
        "name": "revokeConsent",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "patient", "type": "address"},
            {"internalType": "string", "name": "consentType", "type": "string"}
        ],
        "name": "hasConsent",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Defaults
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _find_deployed_address_file() -> Path | None:
    """Search common locations for a deployed_address.txt file.

    Looks in:
    - server/deployed_address.txt (sibling of this package)
    - workspace top-level `blockchain/deployed_address.txt` (two levels up)
    - current package folder
    Returns Path or None if not found.
    """
    candidates = []
    # sibling to server package (server/deployed_address.txt)
    candidates.append(PROJECT_ROOT / 'deployed_address.txt')
    # workspace-level blockchain/deployed_address.txt (e.g., ../.. /blockchain/deployed_address.txt)
    try:
        ws_root = Path(__file__).resolve().parents[2]
        candidates.append(ws_root / 'blockchain' / 'deployed_address.txt')
    except Exception:
        pass
    # current package dir
    candidates.append(Path(__file__).resolve().parent / 'deployed_address.txt')

    for p in candidates:
        if p.exists():
            return p
    return None


DEPLOYED_ADDRESS_FILE = _find_deployed_address_file()
RPC_URL = os.environ.get('BLOCKCHAIN_RPC_URL', None)
PRIVATE_KEY = os.environ.get('BLOCKCHAIN_PRIVATE_KEY')
IS_PRODUCTION = os.environ.get('ENVIRONMENT', '').lower() == 'production'

# Debug: Log environment setup
print(f"🔐 PRIVATE_KEY configured: {bool(PRIVATE_KEY)}")
print(f"🌐 RPC_URL: {RPC_URL}")
print(f"📍 Production mode: {IS_PRODUCTION}")
def _init_w3():
    """Initialize Web3 with eth-tester for in-memory blockchain or HTTP provider."""
    if USE_ETH_TESTER:
        try:
            eth_tester = EthereumTester()
            w3 = Web3(EthereumTesterProvider(eth_tester))
            # Auto-mine blocks immediately for eth-tester
            print("Successfully initialized Web3 with eth-tester")
            return w3, True
        except Exception as e:
            print(f"Failed to initialize eth-tester: {e}")
            # Fall through to HTTP provider if eth-tester fails
    
    # Use HTTP provider if RPC URL is configured
    if RPC_URL:
        try:
            provider = Web3.HTTPProvider(RPC_URL, request_kwargs={'timeout': 5})
            w3 = Web3(provider)
            print(f"Initialized Web3 with HTTP provider at {RPC_URL}")
            return w3, False
        except Exception as http_err:
            print(f"Failed to initialize HTTP provider at {RPC_URL}: {http_err}")
            return None, False
    else:
        # Production environment without RPC URL configured
        if IS_PRODUCTION:
            print("❌ ERROR: BLOCKCHAIN_RPC_URL environment variable not set in production!")
            print("Please configure a valid blockchain RPC endpoint (e.g., Infura, Alchemy, or a self-hosted node)")
        else:
            print("⚠️  WARNING: BLOCKCHAIN_RPC_URL not configured. Using fallback to http://127.0.0.1:8545 for development.")
            try:
                provider = Web3.HTTPProvider('http://127.0.0.1:8545', request_kwargs={'timeout': 5})
                w3 = Web3(provider)
                print("Initialized Web3 with development HTTP provider at http://127.0.0.1:8545")
                return w3, False
            except Exception as e:
                print(f"Failed to initialize development HTTP provider: {e}")
        return None, False

_w3_instance = None
_using_eth_tester = False
_eth_tester_account = None

def get_w3():
    """Get or create Web3 instance. Returns None if initialization fails."""
    global _w3_instance, _using_eth_tester, _eth_tester_account
    if _w3_instance is None:
        _w3_instance, _using_eth_tester = _init_w3()
        # If using eth-tester, setup a default account
        if _w3_instance is not None and _using_eth_tester:
            try:
                accounts = _w3_instance.eth.accounts
                if accounts:
                    _eth_tester_account = accounts[0]
                    # Set as default sender
                    _w3_instance.eth.default_account = _eth_tester_account
                    print(f"Set default account: {_eth_tester_account}")
            except Exception as e:
                print(f"Warning: Failed to setup eth-tester account: {e}")
    return _w3_instance

def get_eth_tester_account():
    """Get the default eth-tester account for signing transactions."""
    get_w3()  # Ensure initialized
    return _eth_tester_account


def _load_contract(w3):
    """Load contract - for eth-tester, return None as we use direct storage."""
    if _using_eth_tester:
        return None
    if not DEPLOYED_ADDRESS_FILE or not DEPLOYED_ADDRESS_FILE.exists():
        return None
    addr = DEPLOYED_ADDRESS_FILE.read_text().strip()
    return w3.eth.contract(address=Web3.to_checksum_address(addr), abi=ABI)


def compute_record_hash(hex_prefixed_hash: str) -> bytes:
    # accepts a 0x-prefixed 32-byte hex string and returns bytes
    if hex_prefixed_hash.startswith('0x'):
        return Web3.to_bytes(hexstr=hex_prefixed_hash)
    return Web3.to_bytes(hexstr='0x' + hex_prefixed_hash)


def send_hash_transaction(record_hash_hex: str):
    """Send the given 0x-prefixed SHA-256 hex (32 bytes) to the blockchain.

    Returns transaction hash string on success or None if not configured.
    """
    if not PRIVATE_KEY and not USE_ETH_TESTER:
        # Not configured to send transactions
        return None

    w3 = get_w3()
    
    # For eth-tester, simulate a transaction
    if USE_ETH_TESTER:
        try:
            acct_addr = get_eth_tester_account()
            if not acct_addr:
                return None
            # Send a simple value transfer to simulate a blockchain transaction
            # Build transaction with explicit gas limit to avoid estimation
            tx = {
                'from': acct_addr,
                'to': acct_addr,  # Send to self
                'value': 0,
                'gas': 21000,  # Standard transaction gas
                'gasPrice': w3.eth.gas_price,
                'nonce': w3.eth.get_transaction_count(acct_addr),
                'data': '0x' + record_hash_hex[2:] if record_hash_hex.startswith('0x') else record_hash_hex,
            }
            tx_hash = w3.eth.send_transaction(tx)
            return w3.to_hex(tx_hash)
        except Exception as e:
            print(f"Error sending transaction to eth-tester: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    # For HTTP provider, use contract
    try:
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    except Exception:
        pass

    contract = _load_contract(w3)
    if contract is None:
        return None

    acct = w3.eth.account.from_key(PRIVATE_KEY)
    acct_addr = acct.address
    nonce = w3.eth.get_transaction_count(acct_addr)

    record_bytes = compute_record_hash(record_hash_hex)

    tx = contract.functions.storeHash(record_bytes).build_transaction({
        'from': acct_addr,
        'nonce': nonce,
        'gas': 200000,
        'gasPrice': w3.eth.gas_price,
    })

    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    return w3.to_hex(tx_hash)


def send_record_transaction(record_data: str):
    """Send the given UTF-8 record string to the on-chain contract.

    Returns transaction hash string on success or None if not configured.
    """
    if not PRIVATE_KEY and not USE_ETH_TESTER:
        return None

    w3 = get_w3()
    try:
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    except Exception:
        pass

    contract = _load_contract(w3)
    if contract is None:
        return None

    acct = w3.eth.account.from_key(PRIVATE_KEY)
    nonce = w3.eth.get_transaction_count(acct.address)

    tx = contract.functions.storeRecord(record_data).build_transaction({
        'from': acct.address,
        'nonce': nonce,
        'gas': 800000,
        'gasPrice': w3.eth.gas_price,
    })

    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    return w3.to_hex(tx_hash)


def get_record_by_id(record_id_hex: str) -> str:
    """Fetch a stored record string by its 0x-prefixed bytes32 id. Returns empty string if missing."""
    w3 = get_w3()
    contract = _load_contract(w3)
    if contract is None:
        return ""

    # normalize to 0x-prefixed bytes32 hex
    if not record_id_hex.startswith('0x'):
        record_id_hex = '0x' + record_id_hex
    try:
        return contract.functions.getRecord(Web3.to_bytes(hexstr=record_id_hex)).call()
    except Exception:
        return ""


def send_record_and_get_id(record_data: str, wait_for_receipt: bool = True, timeout: int = 120):
    """Send the given string (interpreted as a CID/reference) to the on-chain contract,
    wait for the transaction receipt and return (tx_hash_hex, record_id_hex) when available.

    If `wait_for_receipt` is False the function returns (tx_hash_hex, None) immediately.
    """
    if not PRIVATE_KEY and not USE_ETH_TESTER:
        return None, None

    w3 = get_w3()
    try:
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    except Exception:
        pass

    contract = _load_contract(w3)
    if contract is None:
        return None, None

    acct = w3.eth.account.from_key(PRIVATE_KEY)
    nonce = w3.eth.get_transaction_count(acct.address)

    tx = contract.functions.storeRecord(record_data).build_transaction({
        'from': acct.address,
        'nonce': nonce,
        'gas': 300000,
        'gasPrice': w3.eth.gas_price,
    })
    signed = acct.sign_transaction(tx)
    raw_tx = signed.rawTransaction
    tx_hash = w3.eth.send_raw_transaction(raw_tx)
    tx_hash_hex = w3.to_hex(tx_hash)

    if not wait_for_receipt:
        return tx_hash_hex, None

    try:
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)
    except Exception:
        return tx_hash_hex, None

    try:
        events = contract.events.RecordStored().processReceipt(receipt)
        if events and len(events) > 0:
            record_id = events[0]['args']['recordId']
            # record_id is bytes32; convert to hex string
            try:
                record_id_hex = Web3.to_hex(record_id)
            except Exception:
                # fallback if already hex-like
                record_id_hex = str(record_id)
            return tx_hash_hex, record_id_hex
    except Exception:
        pass

    return tx_hash_hex, None


def check_hash_on_chain(record_hash_hex: str) -> bool:
    w3 = get_w3()
    contract = _load_contract(w3)
    if contract is None:
        return False
    record_bytes = compute_record_hash(record_hash_hex)
    return contract.functions.checkHash(record_bytes).call()


def get_owner_address():
    w3 = get_w3()
    contract = _load_contract(w3)
    if contract is None:
        return None
    return contract.functions.owner().call()


def add_authorized_address(account_address: str):
    """Call contract.addAuthorized(account_address). Returns tx hash or None if not configured."""
    if not PRIVATE_KEY:
        return None
    w3 = get_w3()
    try:
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    except Exception:
        pass
    contract = _load_contract(w3)
    if contract is None:
        return None
    acct = w3.eth.account.from_key(PRIVATE_KEY)
    nonce = w3.eth.get_transaction_count(acct.address)
    addr = Web3.to_checksum_address(account_address)
    tx = contract.functions.addAuthorized(addr).build_transaction({
        'from': acct.address,
        'nonce': nonce,
        'gas': 100000,
        'gasPrice': w3.eth.gas_price,
    })
    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    return w3.to_hex(tx_hash)


def remove_authorized_address(account_address: str):
    if not PRIVATE_KEY:
        return None
    w3 = get_w3()
    try:
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    except Exception:
        pass
    contract = _load_contract(w3)
    if contract is None:
        return None
    acct = w3.eth.account.from_key(PRIVATE_KEY)
    nonce = w3.eth.get_transaction_count(acct.address)
    addr = Web3.to_checksum_address(account_address)
    tx = contract.functions.removeAuthorized(addr).build_transaction({
        'from': acct.address,
        'nonce': nonce,
        'gas': 100000,
        'gasPrice': w3.eth.gas_price,
    })
    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    return w3.to_hex(tx_hash)


def is_authorized_address(account_address: str) -> bool:
    w3 = get_w3()
    contract = _load_contract(w3)
    if contract is None:
        return False
    addr = Web3.to_checksum_address(account_address)
    return contract.functions.isAuthorized(addr).call()


# Consent management functions
def give_patient_consent(patient_address: str, consent_type: str):
    """Give consent for a patient and consent type. Returns tx hash or None."""
    if not PRIVATE_KEY:
        return None
    w3 = get_w3()
    try:
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    except Exception:
        pass
    contract = _load_contract(w3)
    if contract is None:
        return None
    acct = w3.eth.account.from_key(PRIVATE_KEY)
    nonce = w3.eth.get_transaction_count(acct.address)
    addr = Web3.to_checksum_address(patient_address)
    tx = contract.functions.giveConsent(addr, consent_type).build_transaction({
        'from': acct.address,
        'nonce': nonce,
        'gas': 100000,
        'gasPrice': w3.eth.gas_price,
    })
    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    return w3.to_hex(tx_hash)

def revoke_patient_consent(patient_address: str, consent_type: str):
    """Revoke consent for a patient and consent type. Returns tx hash or None."""
    if not PRIVATE_KEY:
        return None
    w3 = get_w3()
    try:
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    except Exception:
        pass
    contract = _load_contract(w3)
    if contract is None:
        return None
    acct = w3.eth.account.from_key(PRIVATE_KEY)
    nonce = w3.eth.get_transaction_count(acct.address)
    addr = Web3.to_checksum_address(patient_address)
    tx = contract.functions.revokeConsent(addr, consent_type).build_transaction({
        'from': acct.address,
        'nonce': nonce,
        'gas': 100000,
        'gasPrice': w3.eth.gas_price,
    })
    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    return w3.to_hex(tx_hash)

def has_patient_consent(patient_address: str, consent_type: str) -> bool:
    """Check if a patient has given consent for a consent type."""
    w3 = get_w3()
    contract = _load_contract(w3)
    if contract is None:
        return False
    addr = Web3.to_checksum_address(patient_address)
    return contract.functions.hasConsent(addr, consent_type).call()
