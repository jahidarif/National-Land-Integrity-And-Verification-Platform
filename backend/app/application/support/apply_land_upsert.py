import re
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Callable
from app.core.value_sets import VALUE_SETS
from app.domain.models import Land, LandOwner, LandTransaction, User
from app.domain.value_objects.role import Role


class ApplyLandUpsert:
    def execute(self, land: Land, payload: dict, officer: User, is_new: bool, find_user: Callable[[str], User | None]) -> Land:
        field_map = {re.sub(r"_([a-z])", lambda match: match.group(1).upper(), column.name): column.name for column in Land.__table__.columns}
        blocked = {"id", "landId", "areaId", "area_id", "area", "createdAt", "updatedAt", "created_at", "updated_at", "created_by", "updated_by", "createdBy", "updatedBy"}
        accepted = set(field_map) | blocked | {"owners", "transactions"}
        unknown = set(payload) - accepted
        if unknown: raise ValueError(f"Unknown land fields: {', '.join(sorted(unknown))}")
        value_fields = {"recordType":"record_type", "landClass":"land_class", "khatianStatus":"khatian_status", "mutationStatus":"mutation_status", "dcrStatus":"dcr_status", "dakhilaStatus":"dakhila_status", "ownershipStatus":"ownership_status", "deathIndicator":"death_indicator", "successionStatus":"succession_status", "successorProcess":"successor_process", "mutationAfterSuccession":"mutation_after_succession", "caseType":"case_type", "caseStatus":"case_status", "mortgageStatus":"mortgage_status", "priceFlag":"price_flag", "overallStatus":"overall_status", "riskLevel":"risk_level", "documentLevelStatus":"document_level_status", "ownershipCheck":"ownership_check", "successionCheck":"succession_check", "caseCheck":"case_check", "mortgageCheck":"mortgage_check", "priceCheck":"price_check", "verificationFlags":"verification_flags"}
        for incoming, set_name in value_fields.items():
            value = payload.get(incoming)
            allowed_values = VALUE_SETS.get(set_name, [])
            if value not in (None, "") and allowed_values and value not in allowed_values:
                raise ValueError(f"Invalid {incoming}; allowed values: {', '.join(allowed_values)}")
        for boolean_field in ("caseExists", "mortgageExists"):
            if boolean_field in payload and not isinstance(payload[boolean_field], bool):
                raise ValueError(f"{boolean_field} must be a boolean")
        for key, value in payload.items():
            column = field_map.get(key)
            if column and column not in {"area_id", "created_by", "updated_by"}:
                if value is not None and column in {"deed_date", "last_sold_date", "reserved_price_date"} and isinstance(value, str): value = date.fromisoformat(value[:10])
                if value is not None and column == "verified_at" and isinstance(value, str): value = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if value is not None and column in {"last_sold_price_bdt", "reserved_price_bdt"}: value = int(value)
                setattr(land, column, value)
        if is_new:
            land.area_id = officer.assigned_area_id
            land.created_by = officer.id
        land.updated_by = officer.id
        if "owners" in payload:
            owners = payload.get("owners") or []
            emails = set(); total = Decimal("0")
            for item in owners:
                unknown_owner_fields = set(item) - {"email", "ownerRef", "sharePercent", "isDeceased"}
                if unknown_owner_fields: raise ValueError(f"Unknown owner fields: {', '.join(sorted(unknown_owner_fields))}")
                if "isDeceased" in item and not isinstance(item["isDeceased"], bool): raise ValueError("Owner isDeceased must be a boolean")
                email = str(item.get("email", "")).strip().lower()
                if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email) or email in emails: raise ValueError("Owner emails must be valid and unique")
                emails.add(email)
                account = find_user(email)
                if account and account.role in {Role.ADMIN, Role.LAND_OFFICER}: raise ValueError("Owners cannot be Admin or Land Officer accounts")
                share = Decimal(str(item.get("sharePercent"))) if item.get("sharePercent") is not None else None
                if share is not None:
                    if share < 0 or share > 100: raise ValueError("Owner share must be between 0 and 100")
                    total += share
            if total > 100: raise ValueError("Ownership shares cannot exceed 100 percent")
            land.owners.clear()
            for item in owners:
                land.owners.append(LandOwner(id=str(uuid.uuid4()), owner_email=str(item["email"]).strip().lower(), owner_ref=item.get("ownerRef"), share_percent=item.get("sharePercent"), is_deceased=bool(item.get("isDeceased", False))))
        if "transactions" in payload:
            land.transactions.clear()
            for item in payload.get("transactions") or []:
                unknown_transaction_fields = set(item) - {"transactionId", "transactionType", "date", "amountBdt", "deedRef", "sellerRef", "buyerRef", "status", "id"}
                if unknown_transaction_fields: raise ValueError(f"Unknown transaction fields: {', '.join(sorted(unknown_transaction_fields))}")
                for incoming, set_name in (("transactionType", "transaction_type"), ("status", "transaction_status")):
                    value = item.get(incoming)
                    allowed_values = VALUE_SETS.get(set_name, [])
                    if value not in (None, "") and allowed_values and value not in allowed_values:
                        raise ValueError(f"Invalid transaction {incoming}; allowed values: {', '.join(allowed_values)}")
                tx_date = date.fromisoformat(item["date"][:10]) if isinstance(item.get("date"), str) and item.get("date") else item.get("date")
                amount = int(item["amountBdt"]) if item.get("amountBdt") not in (None, "") else None
                land.transactions.append(LandTransaction(id=str(uuid.uuid4()), transaction_id=str(item.get("transactionId") or f"TX-{uuid.uuid4().hex[:10].upper()}"), transaction_type=item.get("transactionType"), date=tx_date, amount_bdt=amount, deed_ref=item.get("deedRef"), seller_ref=item.get("sellerRef"), buyer_ref=item.get("buyerRef"), status=item.get("status")))
        return land
