import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import settings
from decouple import config

frontend_url = settings.FRONTEND_URL

def format_email(message: str):
    logo_url = settings.LOGO_URL
    # Cuerpo del email en formato HTML
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #f9f9f9;
                margin: 0;
                padding: 0;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100%;
            }}
            .email-container {{
                background-color: #ffffff;
                max-width: 600px;
                margin: 20px auto;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                text-align: center;
            }}
            .email-logo {{
                margin-bottom: 20px;
            }}
            .email-header {{
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 20px;
            }}
            .email-text {{
                font-size: 16px;
                margin-bottom: 20px;
                color: #333333;
            }}
            .verification-code {{
                font-size: 32px;
                font-weight: bold;
                color: #000000;
                margin: 20px 0;
            }}
            .email-footer {{
                font-size: 12px;
                color: #777777;
                margin-top: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="email-container">
            <img src="{logo_url}" alt="Logo" class="email-logo" width="80" height="80">
            {message}
        </div>
    </body>
    </html>
    """

    return html_content




def send_confirmation_email(to_email: str, confirmation_code: str):

    sender_email = config("EMAIL_USER")
    sender_password = config("EMAIL_PASS")
    smtp_server = config("SMTP_SERVER")
    smtp_port = config("SMTP_PORT")

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            message = f"""<div class="email-header">Verifica tu correo electrónico</div>
            <div class="email-text">
                Necesitamos verificar tu dirección de correo electrónico <strong>{to_email}</strong> antes de que puedas acceder a tu cuenta.
                Ingresa el código a continuación en tu ventana del navegador.
            </div>
            <div class="verification-code">{confirmation_code}</div>
            <div class="email-footer">
                Este código expira en 10 minutos.<br>
                Si no te registraste en este servicio, puedes ignorar este correo.
            </div>"""
        
            html_content = format_email(message)

            # Configuración del mensaje
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "Verify your email address"
            msg["From"] = sender_email
            msg["To"] = to_email
            msg.attach(MIMEText(html_content, "html"))

            server.sendmail(sender_email, to_email, msg.as_string())  # Enviar email
        print("Email enviado correctamente.")
        return True
    except Exception as e:
        print(f"Error al enviar el correo: {e}")
        return False 




def send_recovery_email(to_email: str, token: str):
    """
    Send a password recovery email to the user.
    """
    sender_email = config("EMAIL_USER")
    sender_password = config("EMAIL_PASS")
    smtp_server = config("SMTP_SERVER")
    smtp_port = config("SMTP_PORT")

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            message = f"""<div class="email-header">Recuperación de contraseña</div>
            <div class="email-text">
                Para recuperar tu contraseña, haz clic en el enlace a continuación:
            </div>
            <div class="email-text">
                <a href="{frontend_url}/password-recovery?token={token}" style="color: #0066cc; text-decoration: underline;">
                    Haz clic aquí para restablecer tu contraseña
                </a>
            </div>
            <div class="email-footer">
                Este enlace expira en 10 minutos.<br>
                Si no solicitaste recuperar tu contraseña, puedes ignorar este correo.
            </div>"""
        
            html_content = format_email(message)

            # Configuración del mensaje
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "Recovery password"
            msg["From"] = sender_email
            msg["To"] = to_email
            msg.attach(MIMEText(html_content, "html"))

            server.sendmail(sender_email, to_email, msg.as_string())  # Enviar email
        print("Email enviado correctamente.")
        return True
    except Exception as e:
        print(f"Error al enviar el correo: {e}")
        return False

    