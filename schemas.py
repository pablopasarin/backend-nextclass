from pydantic import BaseModel, EmailStr, validator
from typing import List, Optional


class ClassResponse(BaseModel):
    id: int
    name: str
    description: str

    class Config:
        from_attributes = True




class ItemRequest(BaseModel):
    name: str
    description: Optional[str]
    price: float
    expirationEnabled: Optional[bool] = False
    expirationTime: Optional[int] = None
    usesEnabled: Optional[bool] = False
    uses: Optional[int] = None
    icon: Optional[str] = None

class SubcategoryRequest(BaseModel):
    id: Optional[int]
    name: str
    weight: float

class CategoryRequest(BaseModel):
    id: Optional[int]
    name: str
    weight: float
    subcategories: Optional[List[SubcategoryRequest]]


class ChallengeRequest(BaseModel):
    id: Optional[int]
    name: str
    description: Optional[str] = None
    level: Optional[int] = 1
    icon_path: Optional[str] = None

class ItemResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    price: float
    expirationEnabled: Optional[bool] = False
    expirationTime: Optional[int] = None
    usesEnabled: Optional[bool] = False
    uses: Optional[int] = None
    icon: Optional[str] = None

class ClassSettingsRequest(BaseModel):
    name: str
    academic_year: Optional[int]
    description: Optional[str]
    group: Optional[str]
    id: int
    subject: Optional[str]
    is_invitation_code_enabled: Optional[bool]
    invitation_link: Optional[str]
    invitation_code: Optional[str]
    categories: Optional[List[CategoryRequest]]
    challenges: Optional[List[ChallengeRequest]]
    items: Optional[List[ItemRequest]]

    @validator("description", "group", "subject", pre=True, always=True)
    def empty_string_to_none(cls, value):
        return None if value == "" else value
class AddStudentRequest(BaseModel):
    name: str
    email: EmailStr
    class_id: int

class GradeInput(BaseModel):
    student_id: int
    category_id: int
    grade: float

class UpdateGradesRequest(BaseModel):
    student_names: List[str]
    category_name: str
    points: float

class BulkAddStudentsRequest(BaseModel):
    students: Optional[List[AddStudentRequest]]