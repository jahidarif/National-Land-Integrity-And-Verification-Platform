export const VALUE_SETS = {
  "record_type": [
    "BS",
    "RS"
  ],
  "land_class": [
    "Agricultural",
    "Commercial",
    "Residential"
  ],
  "khatian_status": [
    "AUTHENTIC_BUT_CONTEXT_CONFLICT",
    "CONFLICT",
    "MATCHED",
    "MISMATCH",
    "NOT_FOUND"
  ],
  "mutation_status": [
    "COMPLETED",
    "PENDING"
  ],
  "dcr_status": [
    "MATCHED"
  ],
  "dakhila_status": [
    "MATCHED"
  ],
  "ownership_status": [
    "CONFLICTING_RECORDS",
    "HISTORICAL_CONFLICT",
    "JOINT",
    "JOINT_PENDING_SUCCESSION",
    "MULTIPLE_CLAIMS",
    "RECENT_CHANGE_FLAGGED",
    "RECORD_CONFLICT",
    "SINGLE_OWNER",
    "SUCCESSION_DISPUTED",
    "SUCCESSION_UPDATED",
    "TRANSFER_PENDING"
  ],
  "succession_status": [
    "DISPUTED",
    "NOT_APPLICABLE",
    "RESOLVED",
    "REVIEW",
    "UNRESOLVED"
  ],
  "death_indicator": [
    "MAY_APPLY",
    "NO",
    "YES"
  ],
  "successor_process": [
    "COMPLETED",
    "DISPUTED",
    "INCOMPLETE",
    "NOT_APPLICABLE"
  ],
  "mutation_after_succession": [
    "COMPLETED",
    "NOT_APPLICABLE",
    "PENDING"
  ],
  "case_status": [
    "ACTIVE",
    "NONE"
  ],
  "case_type": [
    "LAND_OWNERSHIP_DISPUTE"
  ],
  "mortgage_status": [
    "ACTIVE",
    "NONE"
  ],
  "price_flag": [
    "PRICE_ANOMALY"
  ],
  "overall_status": [
    "CANNOT_VERIFY",
    "DOCUMENT_INCONSISTENCY",
    "HIGH_RISK",
    "REVIEW_REQUIRED",
    "VERIFIED",
    "VERIFIED_RECORD_BUT_CLAIM_MISMATCH",
    "VERIFIED_WITH_HISTORY",
    "VERIFIED_WITH_SHARED_OWNERSHIP"
  ],
  "risk_level": [
    "HIGH",
    "LOW",
    "MEDIUM"
  ],
  "verification_flags": [
    "ACTIVE_LAND_CASE",
    "ACTIVE_MORTGAGE",
    "CLAIMANT_MISMATCH",
    "DAG_MISMATCH;MOUZA_MISMATCH",
    "DECEASED_OWNER;SUCCESSION_INCOMPLETE;MUTATION_PENDING",
    "DECEASED_OWNER_HISTORY;SUCCESSION_COMPLETED",
    "DEED_OWNER_MISMATCH;MUTATION_PENDING;OWNERSHIP_CHAIN_GAP",
    "DOCUMENT_AUTHENTIC;TAX_OWNER_MISMATCH;AREA_HISTORY_MISMATCH",
    "DOCUMENT_REFERENCE_NOT_FOUND;DOCUMENT_SIGNATURE_MISMATCH",
    "KHATIAN_AREA_MISMATCH",
    "MULTIPLE_OWNERS;MULTIPLE_CLAIMS;SUCCESSION_DISPUTE;ACTIVE_LAND_CASE;MUTATION_PENDING",
    "MUTATION_PENDING;RECENT_TRANSFER",
    "PRICE_ANOMALY",
    "SHARED_OWNERSHIP",
    "SHARED_OWNERSHIP;SUCCESSION_DISPUTE;MUTATION_PENDING;ACTIVE_LAND_CASE",
    "TRANSACTION_CHAIN_CONTRADICTION",
    "UNEXPECTED_RECENT_CHANGE;RAPID_RECORD_SEQUENCE"
  ],
  "document_level_status": [
    "CANNOT_VERIFY",
    "INCONSISTENT",
    "MATCHED"
  ],
  "ownership_check": [
    "CONFLICT",
    "MULTIPLE",
    "SINGLE"
  ],
  "succession_check": [
    "COMPLETED",
    "DISPUTED",
    "INCOMPLETE",
    "NOT_APPLICABLE"
  ],
  "case_check": [
    "EXISTS",
    "NONE"
  ],
  "mortgage_check": [
    "EXISTS",
    "NONE"
  ],
  "price_check": [
    "ANOMALY",
    "NORMAL"
  ],
  "transaction_type": [
    "SALE"
  ],
  "transaction_status": [
    "AUTHORITATIVE"
  ]
} as const;
