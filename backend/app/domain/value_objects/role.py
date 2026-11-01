import enum
class Role(str, enum.Enum):
    ADMIN = "Admin"
    LAND_OFFICER = "LandOfficer"
    USER = "User"
