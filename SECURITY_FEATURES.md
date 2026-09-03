# 🔒 Security Features - CSR Project Management

## Overview

This document describes the security features implemented for document integrity, tamper detection, and audit compliance.

## Features Implemented

### 1. **SHA256 Hash Chain** ⛓️

A blockchain-inspired hash chain that creates an immutable audit trail for all documents.

**How it works:**
- Each document gets a SHA256 hash
- Each entry includes the hash of the previous entry
- Creates an unbreakable chain - any tampering is immediately detected
- Genesis block starts with `0000...0000` (64 zeros)

**Benefits:**
- ✅ Tamper-proof audit trail
- ✅ Verifiable document integrity
- ✅ Chronological order guaranteed
- ✅ Detect any modifications to history

**API Endpoints:**
```
POST /security/hash-chain/add          - Add document to chain
GET  /security/hash-chain/verify       - Verify entire chain integrity
GET  /security/hash-chain/document/{id} - Get chain history for document
GET  /security/hash-chain/stats        - Get chain statistics
```

### 2. **Document Integrity Verification** ✓

Cryptographic verification that documents haven't been tampered with.

**How it works:**
- Calculate SHA256 hash on upload
- Store hash in hash chain
- Re-calculate hash on access/verification
- Compare current vs stored hash

**Benefits:**
- ✅ Detect file modifications
- ✅ Prevent document tampering
- ✅ Ensure data authenticity
- ✅ Compliance with legal requirements

**API Endpoints:**
```
POST /security/integrity/verify        - Verify document integrity
```

### 3. **Comprehensive Audit Logging** 📋

Complete audit trail of all user actions for compliance and security.

**Tracked Actions:**
- `upload` - Document uploaded
- `view` - Document viewed
- `download` - Document downloaded
- `update` - Document updated
- `delete` - Document deleted
- `verify` - Document verified
- `approve` - Document/project approved
- `reject` - Document/project rejected
- `share` - Document shared
- `comment` - Comment added

**Logged Information:**
- ✅ Who (user_id)
- ✅ What (action)
- ✅ When (timestamp)
- ✅ Where (IP address)
- ✅ How (user agent)
- ✅ Result (success/failure)
- ✅ Additional metadata

**API Endpoints:**
```
POST /security/audit/log               - Log audit action
POST /security/audit/query             - Query audit logs
GET  /security/audit/document/{id}     - Get document history
GET  /security/audit/user/{id}         - Get user activity
GET  /security/audit/stats             - Get audit statistics
```

## Usage Examples

### Adding Document to Hash Chain

```python
import requests

# Upload document and add to chain
response = requests.post("http://localhost:8000/security/hash-chain/add", json={
    "document_id": "doc_123",
    "document_type": "project_proposal",
    "file_hash": "a1b2c3d4...",  # SHA256 hash of file
    "user_id": "user_456",
    "metadata": {
        "filename": "proposal.pdf",
        "size_bytes": 1024000
    }
})

print(response.json())
# Output:
# {
#     "success": true,
#     "message": "Document added to hash chain",
#     "chain_entry": {
#         "index": 5,
#         "timestamp": "2026-09-02T10:30:00Z",
#         "document_id": "doc_123",
#         "file_hash": "a1b2c3d4...",
#         "previous_hash": "f9e8d7c6...",
#         "hash": "b5a4c3d2..."
#     }
# }
```

### Verifying Chain Integrity

```python
response = requests.get("http://localhost:8000/security/hash-chain/verify")

print(response.json())
# Output:
# {
#     "valid": true,
#     "message": "Hash chain is valid and unbroken",
#     "total_entries": 142
# }
```

### Checking Document Integrity

```python
response = requests.post("http://localhost:8000/security/integrity/verify", json={
    "document_id": "doc_123",
    "current_hash": "a1b2c3d4..."  # Current file hash
})

print(response.json())
# Output:
# {
#     "document_id": "doc_123",
#     "valid": true,
#     "current_hash": "a1b2c3d4...",
#     "stored_hash": "a1b2c3d4...",
#     "message": "Document integrity verified"
# }
```

### Querying Audit Logs

```python
response = requests.post("http://localhost:8000/security/audit/query", json={
    "user_id": "user_456",
    "action": "upload",
    "start_date": "2026-09-01T00:00:00Z",
    "limit": 50
})

print(response.json())
# Output:
# {
#     "total": 12,
#     "logs": [
#         {
#             "timestamp": "2026-09-02T10:30:00Z",
#             "action": "upload",
#             "user_id": "user_456",
#             "document_id": "doc_123",
#             "success": true,
#             "ip_address": "192.168.1.100"
#         },
#         ...
#     ]
# }
```

## Integration with Document Upload

The security features are automatically integrated into the document upload flow:

1. **User uploads document**
2. **Calculate SHA256 hash** of file content
3. **Add to hash chain** with metadata
4. **Log audit action** (upload)
5. **Store hash** for future verification
6. **Return upload confirmation** with hash chain index

## Compliance Benefits

### For CSR Projects:

✅ **Transparency** - Complete audit trail of all project documents
✅ **Accountability** - Track who did what and when
✅ **Data Integrity** - Cryptographic proof documents haven't been altered
✅ **Non-repudiation** - Users cannot deny their actions
✅ **Regulatory Compliance** - Meet audit and compliance requirements
✅ **Fraud Prevention** - Detect tampered or fraudulent documents

## Technical Details

### Hash Chain Structure

```json
{
  "index": 0,
  "timestamp": "2026-09-02T10:00:00Z",
  "document_id": "doc_001",
  "document_type": "project_proposal",
  "file_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "user_id": "user_123",
  "previous_hash": "0000000000000000000000000000000000000000000000000000000000000000",
  "metadata": { "filename": "proposal.pdf" },
  "hash": "5feceb66ffc86f38d952786c6d696c79c2dbc239dd4e91b46729d73a27fb57e9"
}
```

### Storage

- **Hash Chain**: `./data/hash_chain.json` (JSON format)
- **Audit Logs**: `./data/audit_log.jsonl` (JSONL format - one entry per line)

### Security Guarantees

1. **Immutability** - Once added, entries cannot be modified without detection
2. **Verifiability** - Anyone can verify the chain integrity
3. **Tamper Evidence** - Any modification breaks the chain
4. **Chronological Order** - Timestamp and index ensure proper ordering

## Frontend Integration (To Do)

Create UI components for:

1. **Security Dashboard**
   - Show hash chain status
   - Display integrity verification results
   - View recent audit logs

2. **Document Detail Page**
   - Show document hash
   - Display chain position
   - Show audit history for document
   - Button to verify integrity

3. **Admin Audit Panel**
   - Search and filter audit logs
   - Export audit reports
   - View user activity
   - Monitor security events

## Testing

Test the security features:

```bash
# Start backend
cd back-end
python -m uvicorn main:app --reload --port 8000

# Test endpoints
curl http://localhost:8000/security/hash-chain/stats
curl http://localhost:8000/security/audit/stats
```

## Future Enhancements

- [ ] Digital signatures for documents
- [ ] Multi-factor authentication
- [ ] Role-based access control (RBAC)
- [ ] Encryption at rest
- [ ] Real-time security alerts
- [ ] Blockchain integration (public chain)
- [ ] Zero-knowledge proofs for privacy

## Questions?

See `/docs` endpoint for interactive API documentation with all security endpoints.
