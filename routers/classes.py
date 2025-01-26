from fastapi import status, HTTPException, APIRouter, Depends
from sqlalchemy.orm import Session
from models import Class
from database import get_db
from pydantic import BaseModel
from models import Class, ClassMember, Category, User, Item, Challenge
from database import get_db
from schemas import ClassResponse
from routers.auth import get_current_user
from schemas import ClassSettingsRequest
from sqlalchemy.exc import IntegrityError
import logging



logger = logging.getLogger('uvicorn.error')
logger.debug("routers/classes initialized")


router = APIRouter()



# Modelo de entrada para crear una clase
class CreateClassRequest(BaseModel):
    name: str
    description: str = ""

@router.post("/user/create_class")
def create_class(
    class_request: CreateClassRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Get the authenticated user
):
    """
    Endpoint to create a class and associate the user as a teacher.
    """
       # Check if a class with the same name already exists for the current user
    existing_class = (
        db.query(Class)
        .join(ClassMember)
        .filter(Class.name == class_request.name)
        .filter(ClassMember.user_id == current_user.id)
        .first()
    )

    if existing_class:
        raise HTTPException(
            status_code=400,
            detail="Una clase con este nombre ya existe. Por favor, elige otro nombre."
        )
    # Create the class
    new_class = Class(
        name=class_request.name,
        description=class_request.description
    )
    db.add(new_class)
    db.commit()
    db.refresh(new_class)

    # Associate the user with the class as a teacher
    class_member = ClassMember(
        class_id=new_class.id,
        user_id=current_user.id,
        role="teacher"  # Assign the role as "teacher"
    )
    db.add(class_member)
    db.commit()

    return {
        "id": new_class.id,
        "name": new_class.name,
        "description": new_class.description,
        "created_by": current_user.username
    }
@router.get("/user/classes")
def get_user_classes(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get classes for the current user based on their ID.
    """

    user_id = current_user.id
    user_classes = db.query(Class).join(ClassMember).filter(ClassMember.user_id == user_id).all()
    return user_classes

@router.get("/{class_id}")
def get_class_details(class_id: str, db: Session = Depends(get_db), user = Depends(get_current_user)):
    # Fetch class details
    if not user.is_teacher:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los profesores pueden acceder a esta información."
        )
    class_item = db.query(Class).filter(Class.id == int(class_id)).first()

    if not class_item:
        raise HTTPException(status_code=404, detail="Clase no encontrada")

    # Fetch members in a single query
    members = (
        db.query(ClassMember, User.username, ClassMember.role)
        .join(User, User.id == ClassMember.user_id)
        .filter(ClassMember.class_id == class_id)
        .all()
    )
    students = [
        {"id": member.ClassMember.user_id, "name": member.username, "role": member.ClassMember.role}
        for member in members
    ]

# Fetch categories and subcategories
    categories = db.query(Category).filter(Category.class_id == class_id).all()
    category_data = []
    for category in categories:
        if category.parent_id is None:  # Only include top-level categories
            subcategories = db.query(Category).filter(Category.parent_id == category.id).all()
            subcategories_data = [
                {"id": sub.id, "name": sub.name, "weight": sub.weight}
                for sub in subcategories
            ]
            category_data.append({
                "id": category.id,
                "name": category.name,
                "weight": category.weight,
                "subcategories": subcategories_data
            })
    challenges = db.query(Challenge).filter(Challenge.class_id == class_id).all()
    challenges_data = [{"id": challenge.id, "name": challenge.name, "description": challenge.description, "icon_path": challenge.icon_path, "level": challenge.level} for challenge in challenges]

    items = db.query(Item).filter(Item.class_id == class_id).all()
    items_data = [{"id": item.id, "name": item.name, "description": item.description, "price": item.price, "expirationEnabled": item.expirationEnabled, "expirationTime": item.expirationTime, "usesEnabled": item.usesEnabled, "uses": item.uses, "icon": item.icon} for item in items]

    
    return {
        "id": class_item.id,
        "name": class_item.name,
        "description": class_item.description,
        "academic_year": class_item.academic_year,
        "group": class_item.group,
        "subject": class_item.subject,
        "is_invitation_code_enabled": class_item.isInvitationCodeEnabled,
        "invitation_link": class_item.inviteLink,
        "invitation_code": class_item.inviteCode,
        "categories": category_data,
        "challenges": challenges_data,
        "items": items_data,
    } 


@router.delete("/user/delete_class/{class_id}")
def delete_class(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Endpoint to delete a class by its ID.
    """

    # Check if the class exists

    class_to_delete = db.query(Class).filter(Class.id == class_id).first()

    
    if not class_to_delete:
        raise HTTPException(status_code=404, detail="La clase no existe.")

    # Check if the current user is the teacher of the class
    teacher_relation = (
        db.query(ClassMember)
        .filter(ClassMember.class_id == class_id, ClassMember.user_id == current_user.id, ClassMember.role == "teacher")
        .first()
    )
    if not teacher_relation:
        raise HTTPException(
            status_code=403,
            detail="No tienes permiso para eliminar esta clase."
        )

    # Delete the class and associated memberships
    db.query(ClassMember).filter(ClassMember.class_id == class_id).delete()
    db.delete(class_to_delete)
    db.commit()

    return {"message": "Clase eliminada correctamente"}

@router.put("/user/update_class/{class_id}")
def update_class(
    class_id: int,
    class_data: ClassSettingsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Endpoint para actualizar los detalles de una clase y manejar las categorías.
    """
    class_to_update = db.query(Class).filter(Class.id == class_id).first()
    if not class_to_update:
        raise HTTPException(status_code=404, detail="Clase no encontrada.")

    teacher_relation = (
        db.query(ClassMember)
        .filter(ClassMember.class_id == class_id, ClassMember.user_id == current_user.id, ClassMember.role == "teacher")
        .first()
    )
    if not teacher_relation:
        raise HTTPException(status_code=403, detail="No tienes permiso para actualizar esta clase.")

    # Actualizar detalles de la clase
    class_to_update.name = class_data.name
    class_to_update.academic_year = class_data.academic_year
    class_to_update.group = class_data.group
    class_to_update.subject = class_data.subject
    class_to_update.isInvitationCodeEnabled = class_data.is_invitation_code_enabled
    class_to_update.inviteLink = class_data.invitation_link
    class_to_update.inviteCode = class_data.invitation_code

    # Manejar categorías principales
    existing_categories = db.query(Category).filter(
        Category.class_id == class_to_update.id,  # Asegúrate de filtrar por la clase específica
        Category.parent_id == None  # Solo categorías principales
    ).all()
    existing_category_ids = {category.id for category in existing_categories}

    # IDs de las categorías principales que se están actualizando
    updated_category_ids = set()


    for category in class_data.categories:
        if category.id and category.id in existing_category_ids:
            # Actualizar categoría existente
            existing_category = db.query(Category).filter(Category.id == category.id).first()
            if existing_category:
                existing_category.name = category.name
                existing_category.weight = category.weight
                updated_category_ids.add(category.id)

                # Manejar subcategorías
                existing_subcategory_ids = {sub.id for sub in existing_category.subcategories}
                updated_subcategory_ids = set()

                for subcategory in category.subcategories:
                    if subcategory.id:  # Subcategoría existente
                        if subcategory.id in existing_subcategory_ids:
                            # Actualizar subcategoría existente
                            existing_subcategory = db.query(Category).filter(Category.id == subcategory.id).first()
                            if existing_subcategory:
                                existing_subcategory.name = subcategory.name
                                existing_subcategory.weight = subcategory.weight
                                updated_subcategory_ids.add(subcategory.id)
                    else:
                        # Crear nueva subcategoría (id: null)
                        new_subcategory = Category(
                            class_id=class_id,
                            name=subcategory.name,
                            weight=subcategory.weight,
                            parent_id=existing_category.id,
                        )
                        db.add(new_subcategory)
                        db.flush()  # Obtener el ID recién creado
                        updated_subcategory_ids.add(new_subcategory.id)

                # Eliminar subcategorías no incluidas en la actualización
                subcategories_to_delete = existing_subcategory_ids - updated_subcategory_ids
                if subcategories_to_delete:
                    db.query(Category).filter(Category.id.in_(subcategories_to_delete)).delete(synchronize_session=False)
        else:
            # Crear nueva categoría
            new_category = Category(
                class_id=class_id,
                name=category.name,
                weight=category.weight,
            )
            db.add(new_category)
            db.flush()  # Obtener el ID recién creado
            updated_category_ids.add(new_category.id)

            # Manejar subcategorías para la nueva categoría
            for subcategory in category.subcategories or []:
                new_subcategory = Category(
                    class_id=class_id,
                    name=subcategory.name,
                    weight=subcategory.weight,
                    parent_id=new_category.id,
                )
                db.add(new_subcategory)
                db.flush()

    # Eliminar categorías no incluidas en la actualización
    categories_to_delete = existing_category_ids - updated_category_ids
    if categories_to_delete:
        db.query(Category).filter(Category.id.in_(categories_to_delete)).delete(synchronize_session=False)        
# Manejar challenges
    existing_challenges_ids = {challenge.id for challenge in class_to_update.challenges}
    updated_challenges_ids = set()

    for challenge in class_data.challenges:
        if "id" in challenge and challenge["id"] in existing_challenges_ids:
            # Actualizar categoría existente
            existing_challenge = db.query(Challenge).filter(Challenge.id == challenge.id).first()
            if existing_challenge:
                existing_challenge.name = challenge.name
                existing_challenge.description = challenge.description
                existing_challenge.icon_path = challenge.icon_path
                existing_challenge.level = challenge.level
                updated_challenges_ids.add(challenge.id)
        else:
            # Crear nueva categoría
            new_challenge = Challenge(
                class_id=class_id,
                name=challenge.name,
                description=challenge.description,
                icon_path=challenge.icon_path,
                level=challenge.level,
            )
            db.add(new_challenge)
            db.flush()  # Obtener el ID recién creado
            updated_challenges_ids.add(new_challenge.id)

    # Eliminar challenges no incluidas en la actualización
    challenges_to_delete = existing_challenges_ids - updated_challenges_ids
    db.query(Challenge).filter(Challenge.id.in_(challenges_to_delete)).delete(synchronize_session=False)

#manejar items
    existing_items_ids = {item.id for item in class_to_update.items}
    updated_items_ids = set()

    for item in class_data.items:
        if "id" in item and item["id"] in existing_items_ids:
            existing_item = db.query(Item).filter(Item.id == item["id"]).first()
            if existing_item:
                existing_item.name = item.name
                existing_item.description = item.description
                existing_item.price = item.price
                existing_item.expirationEnabled = item.expirationEnabled
                existing_item.expirationTime = item.expirationTime
                existing_item.usesEnabled = item.usesEnabled
                existing_item.uses = item.uses
                existing_item.icon = item.icon
                updated_items_ids.add(item["id"])
        else:
            new_item = Item(
                class_id=class_id,
                name=item.name,
                description=item.description,
                price=item.price,
                expirationEnabled=item.expirationEnabled,
                expirationTime=item.expirationTime,
                usesEnabled=item.usesEnabled,
                uses=item.uses,
                icon=item.icon,
            )
            db.add(new_item)
            db.flush()
            updated_items_ids.add(new_item.id)

    items_to_delete = existing_items_ids - updated_items_ids
    db.query(Item).filter(Item.id.in_(items_to_delete)).delete(synchronize_session=False)

    # Confirmar cambios en la base de datos
    db.commit()

    # Refrescar la clase actualizada
    db.refresh(class_to_update)

    return {
        "message": "Clase actualizada correctamente.",
        "class": {
            "id": class_to_update.id,
            "name": class_to_update.name,
            "academic_year": class_to_update.academic_year,
            "group": class_to_update.group,
            "subject": class_to_update.subject,
            "isInvitationCodeEnabled": class_to_update.isInvitationCodeEnabled,
            "inviteLink": class_to_update.inviteLink,
            "inviteCode": class_to_update.inviteCode,
            "categories": [
                {"id": category.id, "name": category.name, "weight": category.weight}
                for category in class_to_update.categories
            ],
            "challenges": [
                {"id": challenge.id, "name": challenge.name, "description": challenge.description, "icon_path": challenge.icon_path, "level": challenge.level}
                for challenge in class_to_update.challenges
            ],
            "items": [
                {"id": item.id, "name": item.name, "description": item.description, "price": item.price, "expirationEnabled": item.expirationEnabled, "expirationTime": item.expirationTime, "usesEnabled": item.usesEnabled, "uses": item.uses, "icon": item.icon}
                for item in class_to_update.items
            ],
        },
    }
