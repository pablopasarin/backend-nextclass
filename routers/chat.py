from fastapi import APIRouter, UploadFile, Form, File, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from routers.students import get_students_by_class  # Asegúrate de que esta ruta sea correcta
from database import get_db  # Tu archivo de configuración de base de datos
from services.google_api_v2 import create_chat_session_with_context, get_gemini_response, get_gemini_audio_response  # Importar funciones de google_api_v2
import re
from routers.students import update_grades  # Importa el endpoint directamente
from schemas import UpdateGradesRequest
from typing import List, Union, Optional
from routers.classes import get_user_classes
from routers.auth import get_current_user
from models import User
router = APIRouter()

# Modelo para la solicitud de chat
class ChatRequest(BaseModel):
    message: str
    state: str  # "in_class" o "in_dashboard"
    class_id: Optional[int]  # Puede ser un único `class_id`

# Diccionario para almacenar sesiones de chat por clase
chat_sessions_in_class = {}
chat_sessions_in_dashboard = {}

@router.post("/chat")
async def chat_with_gemini(request: ChatRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
        is_teacher = user.is_teacher
        try:
            if not is_teacher:
                return {"response": "El usuario no es un profesor."}
            elif is_teacher:
                    if request.state == "in_class":
                        # Obtener los datos de la clase
                        class_data = get_students_by_class(request.class_id, db, user)

                        if (user.id, request.class_id) not in chat_sessions_in_class:
                            chat_sessions_in_class[user.id, request.class_id] = create_chat_session_with_context(request.state,class_data)

                        # Recuperar la sesión existente
                        chat_session = chat_sessions_in_class[user.id, request.class_id]

                        # Enviar el mensaje al modelo Gemini
                        response = await get_gemini_response(chat_session, request.message)
                        print("Respuesta completa:", response)
                        # Intentar analizar si la respuesta es un comando
                        command = parse_response_to_upgrade_command(response)
                        update_required = False

                        if command is not None:
                            print("Comando detectado:", command)
                            try:
                                dummy = execute_upgrade_grades_command(command, request.class_id, db)
                                print("dummy", dummy)
                                update_required = True
                            except HTTPException as http_exc:
                                print("Error al ejecutar el comando:", http_exc.detail)
                                # Continuar devolviendo el `response` al cliente incluso si falla el comando
                            except Exception as e:
                                print("Error inesperado al ejecutar el comando:", str(e))
                                # Continuar devolviendo el `response` al cliente incluso si falla el comando

                        return {"response": response, "update_required": update_required}
                    elif request.state == "in_dashboard":
                            user_data = get_user_classes(user, db)
                            if user.id not in chat_sessions_in_dashboard:
                                chat_sessions_in_dashboard[user.id] = create_chat_session_with_context(request.state, user_data)
                            chat_session = chat_sessions_in_dashboard[user.id]
                            # Enviar el mensaje al modelo Gemini
                            response = await get_gemini_response(chat_session, request.message)
                            print("Respuesta completa en dashboard:", response)
                            return {"response": response}




        except Exception as e:
                print("Error ocurrido:", str(e))
                raise HTTPException(status_code=500, detail="Error interno en el servidor.")

def parse_response_to_upgrade_command(response: str):
    """
    Convierte una respuesta en un comando para upgrade-grades.
    :param response: Respuesta del modelo (e.g., "Ok. Álvaro Morata +10 en Comportamiento").
    :return: Diccionario con el comando estructurado.
    """
    # Patrón para extraer nombre, puntos y categoría
# Patrón para extraer nombres, puntos y categoría
    match = re.match(r"Ok\. ([\w\s,]+(?: y [\w\s]+)?) ([+-]?\d+)(?: puntos?)? en ([\w\s]+)", response)
    if not match:
        return None

    # Extraer los datos
    student_names_raw = match.group(1).strip()  # Todos los nombres juntos
    points = int(match.group(2))  # Puntos
    category = match.group(3).strip()  # Categoría

    # Dividir los nombres: primero separar por comas, luego manejar el "y" al final
    if " y " in student_names_raw:
        *comma_separated, last_name = student_names_raw.split(" y ")
        student_names = [name.strip() for name in ",".join(comma_separated).split(",")] + [last_name.strip()]
    else:
        # Si no hay "y", solo dividir por comas
        student_names = [name.strip() for name in student_names_raw.split(",")]

    return {
        "student_names": student_names,
        "points": points,
        "category_name": category,
    }

def execute_upgrade_grades_command(command: dict, class_id: int, db: Session):
    """
    Llama directamente a la función update_grades con los datos procesados.
    """
    response = update_grades(
        request=UpdateGradesRequest(
            student_names=command["student_names"],
            category_name=command["category_name"],
            points=command["points"],
        ),
        db=db
    )
    return response


@router.post("/chat/audio")
async def chat_with_audio(
    file: UploadFile = File(...),
    state: str = Form(...),
    class_id: Optional[int] = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Endpoint para procesar un archivo de audio con Gemini.
    """
    try:
        is_teacher = user.is_teacher
        if not is_teacher:
                return {"response": "El usuario no es un profesor."}
        elif is_teacher:
            if state == "in_class":
                class_data = get_students_by_class(class_id, db, user)
                # Enviar el archivo de audio a Gemini y obtener la transcripción
                response = await get_gemini_audio_response(state,class_data,file)
                print("Respuesta completa:", response)
                # Intentar analizar si la respuesta es un comando
                command = parse_response_to_upgrade_command(response)
                update_required = False

                if command is not None:
                    print("Comando detectado:", command)
                    try:
                        execute_upgrade_grades_command(command, class_id, db)
                        update_required = True
                    except HTTPException as http_exc:
                        print("Error al ejecutar el comando:", http_exc.detail)
                    except Exception as e:
                        print("Error inesperado al ejecutar el comando:", str(e))

                return {"response": response, "update_required": update_required}
            elif state == "in_dashboard":
                user_data = get_user_classes(user, db)
                # Enviar el archivo de audio a Gemini y obtener la transcripción
                response = await get_gemini_audio_response(state,user_data,file)
                print("Respuesta completa en dashboard:", response)
                return {"response": response}
    except Exception as e:
        print("Error al procesar el archivo de audio:", str(e))
        raise HTTPException(status_code=500, detail="Error interno en el servidor.")
# Compare this snippet from backend/routers/auth.py:   