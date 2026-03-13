"""
Blockchain hashing service for medical records.
Provides utilities to compute and store blockchain hashes for records.
"""

import hashlib
import json
from typing import Optional, Dict, Any
from .models import OnChainAudit


def serialize_record_data(data: Dict[str, Any], exclude_fields: list = None) -> str:
    """
    Serialize record data to a stable JSON string for hashing.
    
    Args:
        data: Dictionary of record data
        exclude_fields: List of field names to exclude from hashing
        
    Returns:
        Sorted JSON string for deterministic hashing
    """
    exclude_fields = exclude_fields or ['blockchain_hash', 'blockchain_tx_hash', 'id']
    
    cleaned_data = {}
    for key, value in data.items():
        if key not in exclude_fields:
            # Ensure JSON serializable
            try:
                json.dumps(value)
                cleaned_data[key] = value
            except (TypeError, ValueError):
                # Fallback to string representation for non-serializable objects
                cleaned_data[key] = str(value)
    
    # Sort keys for deterministic hashing
    return json.dumps(cleaned_data, sort_keys=True, default=str)


def compute_hash(data: Dict[str, Any], exclude_fields: list = None) -> str:
    """
    Compute SHA-256 hash of record data.
    
    Args:
        data: Dictionary of record data
        exclude_fields: List of field names to exclude from hashing
        
    Returns:
        0x-prefixed SHA-256 hash string (66 characters)
    """
    serialized = serialize_record_data(data, exclude_fields)
    hash_bytes = hashlib.sha256(serialized.encode('utf-8')).hexdigest()
    return '0x' + hash_bytes


def create_blockchain_record(
    record_type: str,
    object_id: int,
    record_hash: str,
    record_cid: Optional[str] = None,
    tx_hash: Optional[str] = None
) -> OnChainAudit:
    """
    Create an on-chain audit record.
    
    Args:
        record_type: Type of record (e.g., 'Patient', 'Diagnosis', 'LabResults')
        object_id: ID of the record
        record_hash: SHA-256 hash (0x-prefixed)
        record_cid: Optional IPFS CID for off-chain storage
        tx_hash: Optional blockchain transaction hash
        
    Returns:
        OnChainAudit instance
    """
    audit = OnChainAudit.objects.create(
        record_type=record_type,
        object_id=object_id,
        record_hash=record_hash,
        record_cid=record_cid,
        tx_hash=tx_hash,
    )
    return audit


def send_hash_to_blockchain(record_hash: str) -> Optional[str]:
    """
    Send hash to blockchain via web3 client.
    
    Args:
        record_hash: 0x-prefixed SHA-256 hash
        
    Returns:
        Transaction hash if successful, None otherwise
    """
    try:
        from blockchain.web3_client import send_hash_transaction
        return send_hash_transaction(record_hash)
    except Exception as e:
        # Blockchain not configured or unavailable
        print(f"Blockchain send_hash_transaction error: {e}")
        return None


def hash_model_instance(instance, exclude_fields: list = None) -> str:
    """
    Compute hash for a Django model instance.
    
    Args:
        instance: Django model instance
        exclude_fields: List of field names to exclude
        
    Returns:
        0x-prefixed SHA-256 hash string
    """
    data = {}
    exclude_fields = exclude_fields or ['blockchain_hash', 'blockchain_tx_hash', 'id']
    
    for field in instance._meta.concrete_fields:
        name = field.name
        if field.auto_created or name in exclude_fields:
            continue
        
        value = getattr(instance, name)
        
        # Handle foreign keys
        if hasattr(field, 'many_to_one') and field.many_to_one:
            # Store the ID for ForeignKey
            data[name] = value.id if value else None
        else:
            # Ensure JSON serializable
            try:
                json.dumps(value)
                data[name] = value
            except (TypeError, ValueError):
                data[name] = str(value)
    
    # Sort keys for deterministic hashing
    serialized = json.dumps(data, sort_keys=True, default=str)
    hash_hex = hashlib.sha256(serialized.encode('utf-8')).hexdigest()
    return '0x' + hash_hex


def store_record_hash(instance, update_instance: bool = True) -> tuple:
    """
    Compute hash for a record and store it.
    Optionally send to blockchain.
    
    Args:
        instance: Django model instance
        update_instance: Whether to update the instance with hash values
        
    Returns:
        Tuple of (record_hash, tx_hash, OnChainAudit instance)
    """
    record_hash = hash_model_instance(instance)
    tx_hash = send_hash_to_blockchain(record_hash)
    
    audit = create_blockchain_record(
        record_type=instance.__class__.__name__,
        object_id=instance.pk,
        record_hash=record_hash,
        tx_hash=tx_hash
    )
    
    # Update the instance with hash values
    if update_instance:
        instance.blockchain_hash = record_hash
        instance.blockchain_tx_hash = tx_hash
        instance.save(update_fields=['blockchain_hash', 'blockchain_tx_hash'])
    
    return record_hash, tx_hash, audit
