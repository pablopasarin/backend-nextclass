from fastapi import status, APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from models import Student, Class, Grade, Category, GradeHistory, User
from database import get_db
from schemas import AddStudentRequest, GradeInput, UpdateGradesRequest, BulkAddStudentsRequest
from sqlalchemy.sql import text
from routers.auth import get_current_user

router = APIRouter()
@router.post("/students/add")
def add_student(student_data: AddStudentRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """
    Endpoint para añadir un nuevo estudiante a una clase.
    """
    if not user.is_teacher:
        raise HTTPException(status_code=403, detail="Solo los profesores pueden agregar estudiantes.")

    # Verificar si la clase existe
    class_obj = db.query(Class).filter(Class.id == student_data.class_id).first()
    if not class_obj:
        raise HTTPException(status_code=404, detail="Clase no encontrada")

    # Verificar si el estudiante ya existe
    existing_student = db.query(Student).filter(Student.email == student_data.email).first()
    if existing_student:
        raise HTTPException(
            status_code=400, 
            detail="El estudiante ya está registrado"
        )

    # Crear un nuevo estudiante
    new_student = Student(
        name=student_data.name,
        email=student_data.email,
        class_id=student_data.class_id,
        is_active=False
    )
    db.add(new_student)
    db.commit()
    db.refresh(new_student)
    # Enviar email con el enlace de registro
    #send_invitation_email(new_student.email, new_student.class_id)
    # Retornar solo los datos esenciales
    return {
        "message": "Estudiante añadido con éxito y email enviado.",
        "student": {
            "id": new_student.id,
            "name": new_student.name,
            "email": new_student.email,
            "class_id": new_student.class_id,
        },
    }
@router.get("/{class_id}")
def get_students_by_class(class_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Obtiene la lista de estudiantes matriculados en una clase específica con sus notas,
    incluyendo todas las categorías aunque no tengan notas asignadas,
    y el historial de cambios de sus notas ordenado por categoría.
    """
    if not user.is_teacher:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los profesores pueden acceder a esta información."
        )

    # Obtener estudiantes y categorías de la clase
    students = db.query(Student).filter(Student.class_id == class_id).all()
    categories = db.query(Category).filter(Category.class_id == class_id).all()

    if not students or not categories:
        return {"students": []}

    # Crear un mapeo de categorías
    category_mapping = [
        {"category": category.name, "grade": None, "subcategories": []}
        for category in categories
    ]

    # Construir la respuesta con las categorías completas para todos los estudiantes
    student_data = []
    for student in students:
        # Inicializar las notas del estudiante con todas las categorías
        grades = {category["category"]: category.copy() for category in category_mapping}

        # Obtener las calificaciones del estudiante
        student_grades = (
            db.query(Grade, Category)
            .join(Category, Grade.category_id == Category.id)
            .filter(Grade.student_id == student.id)
            .all()
        )

        # Asignar las calificaciones existentes a las categorías
        for grade, category in student_grades:
            grades[category.name]["grade"] = grade.grade

        # Obtener el historial de notas del estudiante
        grade_history = (
            db.query(GradeHistory, Category)
            .join(Grade, GradeHistory.grade_id == Grade.id)
            .join(Category, Grade.category_id == Category.id)
            .filter(Grade.student_id == student.id)
            .order_by(Category.name.asc(), GradeHistory.created_at.desc())
            .all()
        )

        # Formatear el historial para el frontend
        formatted_history = [
            {
                "category": category.name,
                "change_amount": history.change_amount,
                "current_grade": history.current_grade,
                "percentage_change": history.percentage_change,
                "timestamp": history.created_at,
                "description": history.description,
            }
            for history, category in grade_history
        ]

        # Convertir el mapeo de categorías en una lista para el `frontend`
        grades_list = list(grades.values())

        student_data.append(
            {
                "id": student.id,
                "name": student.name,
                "email": student.email,
                "grades": grades_list,
                "grade_history": formatted_history,  # Agregar historial de notas ordenado
            }
        )

    return {"students": student_data}

@router.post("/update_grades")
def update_grades(
    request: UpdateGradesRequest,
    db: Session = Depends(get_db)
):
    """
    Añade o quita puntos a los estudiantes en una categoría o subcategoría específica.
    Prohíbe operaciones en categorías con subcategorías.
    Registra un historial de cambios.
    """
    student_names = request.student_names
    category_name = request.category_name
    points = request.points

    # Verificar si la categoría o subcategoría existe
    category = db.query(Category).filter(Category.name == category_name).first()
    if not category:
        raise HTTPException(
            status_code=404,
            detail=f"Categoría o subcategoría '{category_name}' no encontrada."
        )

    # Verificar si la categoría tiene subcategorías
    subcategories = db.query(Category).filter(Category.parent_id == category.id).all()
    if subcategories:
        subcategory_names = [subcategory.name for subcategory in subcategories]
        raise HTTPException(
            status_code=400,
            detail=(
                f"La categoría '{category_name}' tiene subcategorías. "
                f"Especifique una de las siguientes subcategorías: {', '.join(subcategory_names)}."
            )
        )

    # Verificar que los estudiantes existen
    students = db.query(Student).filter(Student.name.in_(student_names)).all()
    if len(students) != len(student_names):
        found_names = [student.name for student in students]
        missing_names = set(student_names) - set(found_names)
        raise HTTPException(
            status_code=404,
            detail=f"Estudiantes no encontrados: {', '.join(missing_names)}."
        )

    # Añadir o quitar puntos a cada estudiante en la categoría
    for student in students:
        grade = (
            db.query(Grade)
            .filter(Grade.student_id == student.id, Grade.category_id == category.id)
            .first()
        )
        if grade:
            previous_grade = grade.grade
            grade.grade += points
        else:
            # Crear un nuevo registro de calificación si no existe
            previous_grade = 0
            grade = Grade(
                student_id=student.id,
                category_id=category.id,
                grade=points
            )
            db.add(grade)
            db.commit()  # Necesario para generar el `id` del nuevo `Grade`
            db.refresh(grade)  # Asegurarse de obtener el ID generado

        # Calcular el porcentaje de cambio
        percentage_change = (
            (points / previous_grade) * 100 if previous_grade != 0 else 100
        )

        # Registrar el cambio en el historial
        history_entry = GradeHistory(
            grade_id=grade.id,
            change_amount=points,
            current_grade=grade.grade,
            percentage_change=percentage_change,
            description=f"Actualización en la categoría '{category.name}'"
        )
        db.add(history_entry)

# Guardar todos los cambios
    # Guardar los cambios
    db.commit()

    return {
        "message": "Puntos actualizados correctamente.",
        "updated_students": [student.name for student in students],
        "category": category.name,
        "points_added": points
    }
@router.post("/students/bulk_add")
def bulk_add_students(
    bulk_data: BulkAddStudentsRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    if not user.is_teacher:
        raise HTTPException(status_code=403, detail="No tienes permiso para realizar esta acción.")

    added_students = []
    errors = []

    for student_data in bulk_data.students:
        try:
            # Comprueba si el estudiante ya existe en la clase
            existing_student = db.query(Student).filter(
                Student.email == student_data.email,
                Student.class_id == student_data.class_id
            ).first()
            if existing_student:
                errors.append(f"El estudiante con correo {student_data.email} ya está en la clase.")
                continue

            # Crea un nuevo estudiante
            new_student = Student(
                name=student_data.name,
                email=student_data.email,
                class_id=student_data.class_id
            )
            db.add(new_student)
            added_students.append(new_student)
        except Exception as e:
            errors.append(f"Error al añadir {student_data.email}: {str(e)}")

    db.commit()

    return {
        "added_students": [student.email for student in added_students],
        "errors": errors,
    }