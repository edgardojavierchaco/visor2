import smtplib


def send_email():
    try:
        mailServer=smtplib.SMTP('smtp.gmail.com',587)
        print(mailServer.ehlo())
        mailServer.starttls()
        print(mailServer.ehlo())
        mailServer.login('visorgomez@gmail.com', 'Aperire.visor')
        print('Conectado...')
    except Exception as e:
        print(e)


send_email()