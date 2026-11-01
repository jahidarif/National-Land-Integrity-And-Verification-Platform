from tests.conftest import csrf, register_and_login


def test_admin_role_cannot_self_register(client):
    response = client.post("/api/auth/register", json={"full_name":"Forbidden Admin", "email":"admin-attempt@example.com", "password":"SafePass123!", "role":"Admin"}, headers=csrf(client))
    assert response.status_code == 422


def test_unassigned_officer_reads_empty_and_cannot_write(client):
    client.post("/api/auth/register", json={"full_name":"Area Officer", "email":"officer@example.com", "password":"SafePass123!", "role":"LandOfficer"}, headers=csrf(client))
    login = client.post("/api/auth/login", json={"email":"officer@example.com", "password":"SafePass123!"}, headers=csrf(client))
    assert login.status_code == 200
    assert login.json()["role"] == "LandOfficer"
    listing = client.get("/api/officer/lands")
    assert listing.status_code == 200
    assert listing.json()["items"] == []
    create = client.post("/api/officer/lands", json={"recordType":"RS", "dagNo":"D-100"}, headers=csrf(client))
    assert create.status_code == 403


def test_user_documents_are_user_only_and_paginated(client):
    register_and_login(client)
    response = client.get("/api/user/documents")
    assert response.status_code == 200
    assert response.json() == {"page":1,"pageSize":10,"totalCount":0,"totalPages":0,"hasPrevious":False,"hasNext":False,"items":[]}
    assert client.get("/api/admin/officers").status_code == 403
    assert client.get("/api/officer/lands").status_code == 403


def test_officer_cannot_attach_stored_documents(client):
    client.post("/api/auth/register", json={"full_name":"Area Officer", "email":"officer@example.com", "password":"SafePass123!", "role":"LandOfficer"}, headers=csrf(client))
    client.post("/api/auth/login", json={"email":"officer@example.com", "password":"SafePass123!"}, headers=csrf(client))
    response = client.post("/api/v1/chat/messages-with-files", data={"query":"check this", "document_ids":"fake-id"}, headers=csrf(client))
    assert response.status_code == 403


def _seed_admin_for_client(client):
    from app.domain.models import User, Role
    from app.infrastructure.adapters.password_hasher import BcryptPasswordHasher
    from app.infrastructure.database import get_db
    db_gen = client.app.dependency_overrides[get_db]()
    db = next(db_gen)
    db.add(User(id="admin-platform", full_name="System Admin", email="platform-admin@example.com", password_hash=BcryptPasswordHasher().hash("SafePass123!"), role=Role.ADMIN, is_active=True))
    db.commit(); db_gen.close()
    client.post("/api/auth/login", json={"email":"platform-admin@example.com", "password":"SafePass123!"}, headers=csrf(client))


def test_officer_land_draft_and_owner_scoping(client):
    _seed_admin_for_client(client)
    area = client.post("/api/admin/areas", json={"mouza":"Demo Mouza 01","upazila":"Demo Upazila","district":"Dhaka"}, headers=csrf(client)).json()
    officer = client.post("/api/admin/officers", json={"fullName":"Area Officer","email":"area-officer@example.com","password":"SafePass123!","assignedAreaId":area["id"]}, headers=csrf(client))
    assert officer.status_code == 201, officer.text
    client.post("/api/auth/logout", json={}, headers=csrf(client))
    assert client.post("/api/auth/login", json={"email":"area-officer@example.com","password":"SafePass123!"}, headers=csrf(client)).status_code == 200
    land = client.post("/api/officer/lands", json={"recordType":"RS","dagNo":"D-1001","khatianNo":"K-1001","areaDecimal":12,"landClass":"Residential","owners":[{"email":"owner-a@example.com","sharePercent":60},{"email":"owner-b@example.com","sharePercent":40}],"transactions":[]}, headers=csrf(client))
    assert land.status_code == 201, land.text
    land_id = land.json()["landId"]
    assert client.get("/api/officer/lands").json()["totalCount"] == 1
    draft = client.put(f"/api/officer/drafts/updates/{land_id}", json={"recordType":"RS","dagNo":"D-1001","overallStatus":"VERIFIED"}, headers=csrf(client))
    assert draft.status_code == 200, draft.text
    assert client.get("/api/officer/drafts/summary").json()["updates"] == 1
    published = client.post(f"/api/officer/drafts/updates/{land_id}/publish", json={}, headers=csrf(client))
    assert published.status_code == 200, published.text
    client.post("/api/auth/logout", json={}, headers=csrf(client))
    assert client.post("/api/auth/register", json={"full_name":"Owner A","email":"owner-a@example.com","password":"SafePass123!","role":"User"}, headers=csrf(client)).status_code == 201
    assert client.post("/api/auth/login", json={"email":"owner-a@example.com","password":"SafePass123!"}, headers=csrf(client)).status_code == 200
    owned = client.get("/api/user/lands")
    assert owned.status_code == 200 and owned.json()["totalCount"] == 1
    assert owned.json()["items"][0]["overallStatus"] == "VERIFIED"
    assert owned.json()["items"][0]["owners"][0]["ownerEmail"] == "owner-a@example.com"
    assert land_id in client.get("/api/auth/me").json()["ownedLandIds"]
    assert client.get(f"/api/user/lands/{land_id}").status_code == 200


def test_create_draft_publish_generates_land_id_and_removes_draft(client):
    _seed_admin_for_client(client)
    area = client.post("/api/admin/areas", json={"mouza":"Create Draft Mouza","upazila":"Demo Upazila","district":"Dhaka"}, headers=csrf(client)).json()
    officer = client.post("/api/admin/officers", json={"fullName":"Draft Officer","email":"draft-officer@example.com","password":"SafePass123!","assignedAreaId":area["id"]}, headers=csrf(client))
    assert officer.status_code == 201
    client.post("/api/auth/logout", json={}, headers=csrf(client))
    client.post("/api/auth/login", json={"email":"draft-officer@example.com","password":"SafePass123!"}, headers=csrf(client))
    draft = client.post("/api/officer/drafts/creates", json={"recordType":"RS","dagNo":"NEW-01","khatianNo":"K-NEW"}, headers=csrf(client))
    assert draft.status_code == 201, draft.text
    draft_id = draft.json()["id"]
    saved = client.put(f"/api/officer/drafts/creates/{draft_id}", json={"recordType":"RS","dagNo":"NEW-01","khatianNo":"K-NEW","overallStatus":"VERIFIED","owners":[{"email":"owner-b@example.com","sharePercent":100}],"transactions":[{"transactionId":"TX-NEW-01","transactionType":"SALE","date":"2026-01-15","amountBdt":125000,"deedRef":"DEED-NEW-01","sellerRef":"SYN-SELLER","buyerRef":"SYN-BUYER","status":"AUTHORITATIVE"}]}, headers=csrf(client))
    assert saved.status_code == 200
    published = client.post(f"/api/officer/drafts/creates/{draft_id}/publish", json={}, headers=csrf(client))
    assert published.status_code == 201, published.text
    assert published.json()["landId"].startswith("LAND-BD-DHAKA-")
    assert client.get("/api/officer/drafts/creates").json()["totalCount"] == 0
    final_land = client.get(f"/api/officer/lands/{published.json()['landId']}").json()
    assert [owner["ownerEmail"] for owner in final_land["owners"]] == ["owner-b@example.com"]
    assert final_land["transactions"][0]["transactionId"] == "TX-NEW-01"
    assert client.get("/api/officer/lands").json()["totalCount"] == 1


def test_stale_update_draft_returns_409(client):
    _seed_admin_for_client(client)
    area = client.post("/api/admin/areas", json={"mouza":"Stale Draft Mouza","upazila":"Demo Upazila","district":"Dhaka"}, headers=csrf(client)).json()
    officer = client.post("/api/admin/officers", json={"fullName":"Stale Officer","email":"stale-officer@example.com","password":"SafePass123!","assignedAreaId":area["id"]}, headers=csrf(client))
    client.post("/api/auth/logout", json={}, headers=csrf(client))
    client.post("/api/auth/login", json={"email":"stale-officer@example.com","password":"SafePass123!"}, headers=csrf(client))
    land = client.post("/api/officer/lands", json={"recordType":"RS","dagNo":"STALE-01"}, headers=csrf(client)).json()
    land_id = land["landId"]
    draft = client.put(f"/api/officer/drafts/updates/{land_id}", json={"recordType":"RS","dagNo":"STALE-01","overallStatus":"VERIFIED"}, headers=csrf(client))
    assert draft.status_code == 200
    changed = client.put(f"/api/officer/lands/{land_id}", json={"recordType":"RS","dagNo":"STALE-01","overallStatus":"REVIEW_REQUIRED"}, headers=csrf(client))
    assert changed.status_code == 200
    published = client.post(f"/api/officer/drafts/updates/{land_id}/publish", json={}, headers=csrf(client))
    assert published.status_code == 409


def test_email_is_unique_across_roles(client):
    assert client.post("/api/auth/register", json={"full_name":"Citizen","email":"same-role@example.com","password":"SafePass123!","role":"User"}, headers=csrf(client)).status_code == 201
    duplicate = client.post("/api/auth/register", json={"full_name":"Officer","email":"same-role@example.com","password":"SafePass123!","role":"LandOfficer"}, headers=csrf(client))
    assert duplicate.status_code == 409


def test_worked_example_area_scope_owner_reads_and_admin_denials(client):
    from uuid import uuid4
    from decimal import Decimal
    from app.domain.models import Area, Land, LandOwner
    _seed_admin_for_client(client)
    area_one = client.post("/api/admin/areas", json={"mouza":"Demo Mouza 01","upazila":"Demo Upazila A","district":"Dhaka"}, headers=csrf(client)).json()
    area_two = client.post("/api/admin/areas", json={"mouza":"Other Mouza","upazila":"Demo Upazila B","district":"Dhaka"}, headers=csrf(client)).json()
    for name,email,assigned in [("Officer One","scope-one@example.com",area_one["id"]),("Officer Two","scope-two@example.com",area_two["id"]),("Unassigned Officer","scope-none@example.com",None)]:
        created=client.post("/api/admin/officers",json={"fullName":name,"email":email,"password":"SafePass123!","assignedAreaId":assigned},headers=csrf(client));assert created.status_code==201
    db_gen=client.app.dependency_overrides[__import__("app.infrastructure.database",fromlist=["get_db"]).get_db]()
    db=next(db_gen)
    db.add(Land(id="LAND-BD-DEMO-0001",area_id=area_one["id"],record_type="RS",dag_no="D-1001",khatian_no="K-1001",area_decimal=Decimal("12.00")))
    db.flush()
    db.add_all([LandOwner(id=str(uuid4()),land_id="LAND-BD-DEMO-0001",owner_email="owner-a@example.com",share_percent=Decimal("60.00")),LandOwner(id=str(uuid4()),land_id="LAND-BD-DEMO-0001",owner_email="owner-b@example.com",share_percent=Decimal("40.00"))])
    db.commit();db_gen.close()
    # Admin cannot access land endpoints or chat.
    assert client.get("/api/officer/lands").status_code==403
    assert client.get("/api/user/lands").status_code==403
    assert client.get("/api/user/documents").status_code==403
    assert client.get("/api/v1/chat/conversations").status_code==403
    client.post("/api/auth/logout",json={},headers=csrf(client))
    client.post("/api/auth/login",json={"email":"scope-one@example.com","password":"SafePass123!"},headers=csrf(client))
    assert client.get("/api/officer/lands").json()["totalCount"]==1
    assert client.get("/api/officer/lands/LAND-BD-DEMO-0001").status_code==200
    assert client.get("/api/user/documents").status_code==403
    client.post("/api/auth/logout",json={},headers=csrf(client))
    client.post("/api/auth/login",json={"email":"scope-two@example.com","password":"SafePass123!"},headers=csrf(client))
    assert client.get("/api/officer/lands").json()["totalCount"]==0
    assert client.get("/api/officer/lands/LAND-BD-DEMO-0001").status_code==404
    assert client.put("/api/officer/lands/LAND-BD-DEMO-0001",json={"recordType":"RS","dagNo":"D-1001"},headers=csrf(client)).status_code==404
    client.post("/api/auth/logout",json={},headers=csrf(client))
    client.post("/api/auth/login",json={"email":"scope-none@example.com","password":"SafePass123!"},headers=csrf(client))
    assert client.get("/api/officer/lands").json()["totalCount"]==0
    assert client.post("/api/officer/lands",json={"recordType":"RS","dagNo":"NO-AREA"},headers=csrf(client)).status_code==403
    for email in ("owner-a@example.com","owner-b@example.com"):
        client.post("/api/auth/logout",json={},headers=csrf(client))
        client.post("/api/auth/register",json={"full_name":email.split('@')[0],"email":email,"password":"SafePass123!","role":"User"},headers=csrf(client))
        client.post("/api/auth/login",json={"email":email,"password":"SafePass123!"},headers=csrf(client))
        owned=client.get("/api/user/lands")
        assert owned.status_code==200 and owned.json()["totalCount"]==1
        assert owned.json()["items"][0]["landId"]=="LAND-BD-DEMO-0001"
        assert client.put("/api/officer/lands/LAND-BD-DEMO-0001",json={"recordType":"RS","dagNo":"D-1001"},headers=csrf(client)).status_code==403
    client.post("/api/auth/logout",json={},headers=csrf(client))
    client.post("/api/auth/register",json={"full_name":"Another citizen","email":"not-owner@example.com","password":"SafePass123!","role":"User"},headers=csrf(client))
    client.post("/api/auth/login",json={"email":"not-owner@example.com","password":"SafePass123!"},headers=csrf(client))
    assert client.get("/api/user/lands").json()["totalCount"]==0


def test_area_uniqueness_update_unchanged_and_other_upazila(client):
    _seed_admin_for_client(client)
    first=client.post("/api/admin/areas",json={"mouza":"Demo  Mouza","upazila":"Upazila A","district":"Dhaka"},headers=csrf(client))
    assert first.status_code==201
    area=first.json()
    unchanged=client.put(f"/api/admin/areas/{area['id']}",json={"mouza":"Demo Mouza","upazila":"Upazila A","district":"Dhaka"},headers=csrf(client))
    assert unchanged.status_code==200
    other_upazila=client.post("/api/admin/areas",json={"mouza":"Demo Mouza","upazila":"Upazila B","district":"Dhaka"},headers=csrf(client))
    assert other_upazila.status_code==201
    duplicate=client.post("/api/admin/areas",json={"mouza":" demo   mouza ","upazila":"UPAZILA A","district":"DHAKA"},headers=csrf(client))
    assert duplicate.status_code==409
    second=client.post("/api/admin/areas",json={"mouza":"Other Mouza","upazila":"Upazila A","district":"Dhaka"},headers=csrf(client)).json()
    duplicate_update=client.put(f"/api/admin/areas/{second['id']}",json={"mouza":"Demo Mouza","upazila":"Upazila A","district":"Dhaka"},headers=csrf(client))
    assert duplicate_update.status_code==409
