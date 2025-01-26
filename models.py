from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Tabla de usuarios
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_email_confirmed = Column(Boolean, default=False)
    confirmation_code = Column(String, nullable=True)
    is_teacher = Column(Boolean, default=True)

    # Relación con `ClassMember`
    class_memberships = relationship("ClassMember", back_populates="user")

# Tabla de clases
class Class(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    academic_year = Column(Integer, nullable=True)
    group = Column(String, nullable=True)
    subject = Column(String, nullable=True)
    isInvitationCodeEnabled = Column(Boolean, default=False)
    inviteLink = Column(String, nullable=True)
    inviteCode = Column(String, nullable=True)
    # Relación con `ClassMember`
    members = relationship("ClassMember", back_populates="class_ref", cascade="all, delete-orphan")

    # Relación con `Category`
    categories = relationship("Category", back_populates="class_ref", cascade="all, delete-orphan")
 # Relación con `Item`
    items = relationship("Item", back_populates="class_ref", cascade="all, delete-orphan")
    challenges = relationship("Challenge", back_populates="class_ref", cascade="all, delete-orphan")
    students = relationship("Student", back_populates="class_ref", cascade="all, delete-orphan")
# Relación entre usuarios y clases
class ClassMember(Base):
    __tablename__ = "class_members"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id", name="fk_items_class_id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", name="fk_class_member_user_id"), nullable=False)
    role = Column(String, nullable=False, default="student")  # Rol en la clase
    created_at = Column(DateTime, default=func.now())

    # Relaciones
    user = relationship("User", back_populates="class_memberships")
    class_ref = relationship("Class", back_populates="members")


# Tabla de categorías de evaluación
class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey('classes.id', name='fk_categories_class_id',ondelete='CASCADE'), nullable=False)
    parent_id = Column(Integer, ForeignKey('categories.id',name='fk_categories_parent_id', ondelete='CASCADE'), nullable=True)    
    name = Column(String, nullable=False)  # Nombre de la categoría (por ejemplo, "Participación")
    is_active = Column(Boolean, default=True)  # Estado de activación para la clase

    weight = Column(Float, default=1.0)  # Peso de la categoría (opcional)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    # Relación con `Class`
    class_ref = relationship("Class", back_populates="categories")
# Relación jerárquica (subcategorías y categoría padre)
    parent_category = relationship("Category", remote_side=[id], back_populates="subcategories")
    subcategories = relationship("Category", back_populates="parent_category", cascade="all, delete-orphan")
    # Relación con `Grade`
    grades = relationship("Grade", back_populates="category_ref", cascade="all, delete-orphan")


# Tabla de notas
class Grade(Base):
    __tablename__ = "grades"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(
        Integer,
        ForeignKey("students.id", name="fk_grades_student_id", ondelete="CASCADE"),
        nullable=False
    )
    category_id = Column(
        Integer,
        ForeignKey("categories.id", name="fk_grades_category_id", ondelete="CASCADE"),
        nullable=False
    )
    grade = Column(Float, nullable=False)  # Nota asignada
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    description = Column(String, nullable=True)
    # Relaciones
    student_ref = relationship("Student", back_populates="grades")
    category_ref = relationship("Category", back_populates="grades")
    history = relationship("GradeHistory", back_populates="grade_ref", cascade="all, delete-orphan")

    @staticmethod
    def add_grade(session, student_id, category_id, grade_value, description=None):
        """
        Agrega una nueva nota para un estudiante y registra el cambio en el historial.
        """
        # Buscar o crear la nota
        grade = session.query(Grade).filter_by(student_id=student_id, category_id=category_id).first()
        if not grade:
            grade = Grade(
                student_id=student_id,
                category_id=category_id,
                grade=0  # Inicialmente en 0, luego se sumarán los puntos
            )
            session.add(grade)
            session.commit()

        # Calcular el nuevo total
        previous_grade = grade.grade
        new_grade = previous_grade + grade_value
        grade.grade = new_grade
        grade.updated_at = func.now()

        # Calcular el porcentaje de cambio
        percentage_change = (
            (grade_value / previous_grade) * 100 if previous_grade != 0 else 100
        )

        # Registrar el cambio en el historial
        history_entry = GradeHistory(
            grade_id=grade.id,
            change_amount=grade_value,
            current_grade=new_grade,
            percentage_change=percentage_change,
            description=description
        )
        session.add(history_entry)

        session.commit()
        return {"student_id": student_id, "category_id": category_id, "total_grade": new_grade, "percentage_change": percentage_change}



# Nueva tabla para ítems
class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id", name="fk_items_class_id"), nullable=False)
    name = Column(String, nullable=False)  # Nombre del ítem
    description = Column(String, nullable=True)  # Descripción del ítem
    price = Column(Float, nullable=True)  # Valor del ítem
    expirationEnabled = Column(Boolean, default=False)
    expirationTime = Column(Integer, nullable=True)
    usesEnabled = Column(Boolean, default=False)
    uses = Column(Integer, nullable=True)
    icon = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relación con `Class`
    class_ref = relationship("Class", back_populates="items")

class Challenge(Base):
    __tablename__ = "challenges"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id", name="fk_challenges_class_id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    icon_path = Column(String, nullable=True)  # Ruta al archivo de icono
    level = Column(Integer, default=1)  # Nivel del desafío

    class_ref = relationship("Class", back_populates="challenges")


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id", name="fk_student_class_id"), nullable=False)
    class_ref = relationship("Class", back_populates="students")
    grades = relationship("Grade", back_populates="student_ref", cascade="all, delete-orphan")
    is_active = Column(Boolean, default=False)  # Marcar si el estudiante completó el registro
    __table_args__ = (UniqueConstraint("name", "class_id", name="unique_name_per_class"),)

class GradeHistory(Base):
    __tablename__ = "grade_histories"

    id = Column(Integer, primary_key=True, index=True)
    grade_id = Column(Integer, ForeignKey("grades.id", name="fk_grade_history_grade_id", ondelete="CASCADE"), nullable=False)
    change_amount = Column(Float, nullable=False)  # Cantidad de puntos añadidos o quitados
    percentage_change = Column(Float, nullable=True)  # Porcentaje de cambio en comparación con la nota anterior
    created_at = Column(DateTime, default=func.now())  # Fecha del cambio
    current_grade = Column(Float, nullable=True)  # Puntuación total en ese momento
    description = Column(String, nullable=True)  # Descripción del cambio

    # Relación con `Grade`
    grade_ref = relationship("Grade", back_populates="history")