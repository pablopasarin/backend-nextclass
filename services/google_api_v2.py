from decouple import config
import google.generativeai as genai

# Configuración del modelo Gemini
genai.configure(api_key=config("GOOGLE_API_KEY"))

generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 100,  # Limitar tokens en la salida
    "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
    model_name="gemini-2.0-flash-exp",
    generation_config=generation_config,
)
def prepare_prompt(state:str,class_data: dict):
    """
    Prepara el prompt inicial para una sesión de chat con el modelo Gemini.
    """
    prompt1 = f"""
    Eres un asistente que puede interpretar comandos y 
    decidir si tiene la información para ejecutarlos. Puedes completar la 
    información basándote en la lista de datos que tienes.

    Base de datos: {class_data}.

    Ejemplo de comandos, (los nombres que apercen aquí son ficticios no tienen
     por que estar en la base de datos):
    1. "Añade 10 puntos a Juan y Maria en comportamiento."
       Respuesta: ""Ok. Juan Pérez y María Gómez +10 puntos en Comportamiento""
    2. "Quita 5 puntos a María en participación."
       En el caso de que se repita el nombre, tienes que preguntar cuál de los posibles nombres es. Si el nombre no se repite en la base
       de datos no preguntes.
    3. Comprueba antes de responder si los nombres que te doy están repetidos en la base de datos. 
    Si sólo hay una persona en la base de datos con ese nombre no preguntes a quién me refiero.
    4. Si ya sabes que puedes llevar a cabo el comando, entonces tienes
    que responder así: Ok. Nombre del estudiante + o - los puntos en categoría. 
    5. Si te doy más de un nombre debes responder así: 
    Ok. Nombre del estudiante, Nombre del estudiante y Nombre del estudiante + o - los puntos en categor
    Por ejemplo: Ok. Pedro Perez +10 puntos en Participación
    Otro ejemplo: Ok. Pedro Perez y Alvaro Morata -10 puntos en Tareas. 
  
    """
    promp2 = f"""
    Eres un asistente que conoce la base de datos de un usuario, profesor, que tiene varias clases.
    Base de datos {class_data}
    """
    if state == "in_dashboard":
        return promp2
    elif state == "in_class":
        return prompt1
    else:
        return "Error: State not found"

# Contexto inicial
def create_chat_session_with_context(state:str,class_data: dict):
    
    # Crear la sesión de chat con el contexto inicial
    return model.start_chat(
        history=[
            {
                "role": "user", 
                "parts": [
                    {
                        "text": prepare_prompt(state,class_data)
                    }
                ] 
            }
        ]
    )

async def get_gemini_response(chat_session, message: str) -> str:
    """
    Envía un mensaje al modelo Gemini dentro de una sesión de chat.
    """
    response = chat_session.send_message(message)
    return response.text

async def get_gemini_audio_response(state: str, class_data: dict, file) -> bytes:
    """
    Envía un mensaje al modelo Gemini dentro de una sesión de chat y obtiene la respuesta en formato de audio.
    """

    file_data = await file.read()

    response = model.generate_content([
    prepare_prompt(state,class_data),
    {
        "mime_type": "audio/mp3",
        "data": file_data,
    }
])

    return response.text