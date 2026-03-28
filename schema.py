from pydantic import BaseModel, Field, EmailStr, field_validator
import re

class User(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str
    role_id: str

    @field_validator("password")
    def validate_password(cls, v):
        if len(v) < 8 or len(v) > 16:
            raise ValueError("Password must be 8-16 characters")
        if not re.search(r"[a-z]", v):
            raise ValueError("Must contain lowercase")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Must contain uppercase")
        if not re.search(r"[^\w\s]", v):
            raise ValueError("Must contain special character")
        return v

class Login(BaseModel):
    name: str
    password: str
    role_id: str

    @field_validator("password")
    def validate_password(cls, v):
        if len(v) < 8 or len(v) > 16:
            raise ValueError("Password must be 8-16 characters")
        if not re.search(r"[a-z]", v):
            raise ValueError("Must contain lowercase")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Must contain uppercase")
        if not re.search(r"[^\w\s]", v):
            raise ValueError("Must contain special character")
        return v






