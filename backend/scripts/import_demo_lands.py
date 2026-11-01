import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
"""Optional import of synthetic demo land records from the supplied one-file bundle."""
import json
import os
import re
import uuid
from datetime import date, datetime
from sqlalchemy import func, select
from app.domain.models import Area, Land, LandOwner, LandTransaction
from app.infrastructure.database import SessionLocal


class ImportDemoLands:
    def __init__(self, session):
        self.session = session

    def execute(self, source_path: str) -> int:
        records = json.loads(Path(source_path).read_text(encoding="utf-8"))
        imported = 0
        for entry in records:
            record = entry.get("authoritative_structured_land_record")
            if not record:
                continue
            parcel = record["parcel"]
            normalized = {key: " ".join(str(parcel[key]).strip().split()) for key in ("mouza", "upazila", "district")}
            area = self.session.scalar(select(Area).where(func.lower(Area.mouza) == normalized["mouza"].lower(), func.lower(Area.upazila) == normalized["upazila"].lower(), func.lower(Area.district) == normalized["district"].lower()))
            if area is None:
                area = Area(id=str(uuid.uuid4()), **normalized)
                self.session.add(area); self.session.flush()
            land_id = record["land_id"]
            land = self.session.get(Land, land_id)
            if land is None:
                land = Land(id=land_id, area_id=area.id, record_type=parcel["record_type"], dag_no=str(parcel["dag_no"]))
                self.session.add(land)
            land.area_id = area.id
            mapping = {"jl_no":"jl_no", "khatian_no":"khatian_no", "area_decimal":"area_decimal", "land_class":"land_class"}
            for source, target in mapping.items(): setattr(land, target, parcel.get(source))
            khatian, deed, mutation, dcr, dakhila = (record.get(key, {}) for key in ("khatian", "registered_deed", "mutation", "dcr", "dakhila"))
            values = {"khatian_ref":khatian.get("document_ref"), "khatian_status":khatian.get("document_status"), "deed_no":deed.get("deed_no"), "deed_date":date.fromisoformat(deed["deed_date"]) if deed.get("deed_date") else None, "deed_registration_office":deed.get("registration_office"), "mutation_ref":mutation.get("document_ref"), "mutation_status":mutation.get("status"), "dcr_ref":dcr.get("document_ref"), "dcr_status":dcr.get("status"), "dakhila_ref":dakhila.get("document_ref"), "dakhila_status":dakhila.get("status")}
            for key, value in values.items(): setattr(land, key, value)
            succession, cases, mortgage, price, verification = (record.get(key, {}) for key in ("succession", "cases", "mortgage", "last_sold_reserved_price", "verification"))
            for key, value in {"ownership_status":record.get("ownership",{}).get("status"), "death_indicator":succession.get("death_indicator"), "successor_process":succession.get("successor_process"), "mutation_after_succession":succession.get("mutation_after_succession"), "succession_status":succession.get("status"), "case_exists":str(cases.get("case_exists",False)).strip().lower() in {"true", "1", "yes"}, "case_ref":cases.get("case_ref") or None, "case_type":cases.get("case_type") or None, "case_status":cases.get("case_status"), "mortgage_exists":str(mortgage.get("mortgage_exists",False)).strip().lower() in {"true", "1", "yes"}, "mortgage_ref":mortgage.get("mortgage_ref") or None, "mortgage_status":mortgage.get("status"), "last_sold_price_bdt":int(price["last_sold_price_bdt"]) if str(price.get("last_sold_price_bdt","")).isdigit() else None, "last_sold_date":date.fromisoformat(price["last_sold_date"]) if price.get("last_sold_date") else None, "last_sold_deed_ref":price.get("last_sold_deed_ref"), "reserved_price_bdt":int(price["reserved_price_bdt"]) if str(price.get("reserved_price_bdt","")).isdigit() else None, "reserved_price_date":date.fromisoformat(price["reserved_price_date"]) if price.get("reserved_price_date") else None, "price_flag":price.get("price_flag") or None, "overall_status":verification.get("overall_status"), "risk_level":verification.get("risk_level"), "verification_flags":verification.get("verification_flags"), "document_level_status":verification.get("document_level_status"), "ownership_check":verification.get("ownership_check"), "succession_check":verification.get("succession_check"), "case_check":verification.get("case_check"), "mortgage_check":verification.get("mortgage_check"), "price_check":verification.get("price_check"), "verified_at":datetime.fromisoformat(verification["verified_at"].replace("Z","+00:00")) if verification.get("verified_at") else None, "verification_version":verification.get("verification_version"), "source_snapshot_version":verification.get("source_snapshot_version")}.items(): setattr(land, key, value)
            land.owners.clear()
            self.session.flush()
            for index, owner in enumerate(record.get("ownership",{}).get("relations",[]), start=1):
                suffix = chr(96 + index) if index <= 26 else str(index)
                land.owners.append(LandOwner(id=str(uuid.uuid4()), owner_email=f"owner-{re.sub(r'[^0-9]','',land_id)}-{suffix}@demo.local", owner_ref=owner.get("owner_ref"), share_percent=owner.get("share_percent"), is_deceased=owner.get("deceased") is True or str(owner.get("deceased")).lower() == "true"))
            land.transactions.clear()
            self.session.flush()
            for tx in record.get("transactions", []):
                land.transactions.append(LandTransaction(id=str(uuid.uuid4()), transaction_id=tx["transaction_id"], transaction_type=tx.get("transaction_type"), date=date.fromisoformat(tx["date"]) if tx.get("date") else None, amount_bdt=int(tx["amount_bdt"]) if str(tx.get("amount_bdt","")).isdigit() else None, deed_ref=tx.get("deed_ref"), seller_ref=tx.get("seller_ref"), buyer_ref=tx.get("buyer_ref"), status=tx.get("status")))
            imported += 1
        self.session.commit()
        return imported


if __name__ == "__main__":
    source = os.getenv("NLI_DEMO_JSON", "../data/National_Land_Integrity_Maira_All_Data_One_JSON_ASCII_UTF8.json")
    db = SessionLocal()
    try: print(f"Imported {ImportDemoLands(db).execute(source)} synthetic demo land records")
    finally: db.close()
