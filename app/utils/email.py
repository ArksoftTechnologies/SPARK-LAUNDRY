from flask_mail import Mail, Message
from flask import current_app, render_template
from threading import Thread
from app import create_app

mail = Mail()

def send_async_email(app, msg):
    with app.app_context():
        try:
            mail.send(msg)
        except Exception as e:
            print(f"Failed to send email: {e}")

def send_email(to, subject, template, **kwargs):
    app = current_app._get_current_object()
    msg = Message(
        subject=current_app.config['MAIL_SUBJECT_PREFIX'] + ' ' + subject,
        sender=current_app.config['MAIL_USERNAME'],
        recipients=[to]
    )
    msg.html = render_template(template, **kwargs)
    
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr
