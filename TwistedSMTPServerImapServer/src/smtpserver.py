'''
SMTP-SERVER
'''

from __future__ import print_function

from twisted.python import log
from twisted.python.modules import getModule
from twisted.python.usage import Options, UsageError

from zope.interface import implementer

from twisted.internet import defer, reactor, ssl

from twisted.mail import smtp, relaymanager, maildir
from twisted.mail.imap4 import LOGINCredentials, PLAINCredentials

from twisted.cred.checkers import InMemoryUsernamePasswordDatabaseDontUse
from twisted.cred.portal import IRealm
from twisted.cred.portal import Portal

from twisted.application import internet
from twisted.application import service    

from email.Header import Header
from zope.interface import implements

import dns.resolver
import sys
import os
'''
SMTP-Server:

El servidor permitira el envio de correos electronicos usando SMTP
El servidor permitira la recepcion de correos electronicos usando SMTP
El servidor permitira la comunicacion utilizando una capa segura como la de SSL (ahora TLS) puede ser usando openssl
El servidor debera de verificar los dominios que acepta 
El servidor debera de recibir los correos electronicos dirigidos a dichos dominios 
El servidor debera de rechazar los correos electronicos dirigidos a dichos dominios
El servidor debera permitir la recepcion de archivos adjuntos utilizando el estandar MIME. 

$ python smtpserver.py -d <domains> -s <mail-storage> -p <port>

Ejemplos de storage pero se pueden crear en cualquier lugar
/root/.thunderbird/1xomfhss.default/ImapMail/localhost
/tmp/mail/
'''

host = "localhost"
domain = ["localhost"]
domain_aux = {}

storage = "/tmp/mail/"
port_ = 2500

# Argumentos
class ServerOptions(Options):
    # Interface que trae implementada Twisted para manejo de argumentos
    synopsis = "python smtpserver.py [options]"
    optParameters = [
        ('domain', 'd',"localhost",'Domains,example adding many domains <domain1,domain2,domain3,i-domain>.'),
        ('mail-storage', 's', "/tmp/mail/",'Mail-Storage'),
        ('port', 'p', 2500,'Port')]


    def postOptions(self):
        """
        Verifica las entradas
        """
        try:
            self['port'] = int(self['port'])
        except ValueError:
            raise UsageError("--port argument must be an integer.")
        if self['domain'] is None:
            raise UsageError(
                "Must specify a domain --domain")
        if self['mail-storage'] is None:
            raise UsageError(
                "Must specify mail-storafe --mail-storage")


# Almacenar correos

class LocalMessageDelivery(object):
    '''
    Clase que gestiona los  encabezados o  headers 
    y es una implementacion de la interface ImessageDelivery 
    '''
    implements(smtp.IMessageDelivery)
    
    def __init__(self, protocol, baseDir):
        self.protocol = protocol
        self.baseDir = baseDir

        
    def receivedHeader(self, helo, origin, recipients):
        #Arma el en cabezado
        clientHostname, clientIP = helo
        myHostname = self.protocol.transport.getHost().host
        headerValue = "from %s by %s with ESMTP ; %s" % (clientHostname, myHostname, smtp.rfc822date())
        return "Received: %s" % Header(headerValue)

    def validateFrom(self, helo, origin):
        #valida que el dominio solo sea el del server de quien envia el mensaje
        if origin.domain in domain_aux:
            return origin
        else:
            log.msg("Invalid domain %s" % origin.domain)
            raise smtp.SMTPBadRcpt(origin.domain)

    def validateTo(self, user):
        # Validar dominios de destinatarios
        return lambda: MaildirMessage(self._getAddressDir(str(user.dest)))


    def _getAddressDir(self, address):
        # Guarda la direccion para crear la carpeta con el nombre del correo
        return os.path.join(self.baseDir, "%s" % address)


class MaildirMessage(object):
    # Esta clase obtiene el mensajes y lo almacena en con una
    #jerarquia establecido por la biblioteca de twsted e implementacion
    # de la interface de IMessage
    implements(smtp.IMessage)
    
    def __init__(self,userDir):
        if not os.path.exists(userDir):
            os.mkdir(userDir)
        inboxDir = os.path.join(userDir, 'Inbox')
        self.mailbox = maildir.MaildirMailbox(inboxDir)
        self.lines = []

    def lineReceived(self, line):
        # EL contenido del mensaje
        self.lines.append(line)

    def eomReceived(self):
        # Aqui es donde se usa todo el mensaje para almacenarlo
        print("New message received: ")
        self.lines.append('')
        messageData = '\n'.join(self.lines)
        print(messageData)
        return self.mailbox.appendMessage(messageData)

    def connectionLost(self):
        #Si hay un error de Coneccion entonces borre el mensaje
        print("Conection lost unexpectedly!\n")
        del(self.lines)

    def getDNSquery(dm):
        #Metodo para obtener los dominios de MX
        a = ''
        dnsq = []
        lowest_value = 1000
        mx = ""
        for x in dns.resolver.query(dm,'MX'):
            a = x.to_text()
            tmp = a.split(" ")
            if int(tmp[0]) <= lowest_value:
                lowest_value = int(tmp[0])
                mx = tmp[1]
        dnsq.append(lowest_value)
        dnsq.append(mx[:-1])
        return dnsq

class LocalSMTPFactory(smtp.SMTPFactory):
    # Aqui se crea EL protocolo SMTP
    def __init__(self, baseDir):
        self.baseDir = baseDir
    def buildProtocol(self, addr):
        protocol = smtp.ESMTP()
        protocol.delivery = LocalMessageDelivery(protocol,self.baseDir)
        return protocol



def main(args=None):
    #Evaluamos argumentos
    o = ServerOptions()
    try:
        o.parseOptions(args)
    except UsageError as e:
        raise SystemExit(e)
    else:
        domain = str(o['domain']).split(",")
        port_ =  int(o['port'])
        storage = str(o['mail-storage'])
        try:
            if not os.path.exists(storage):
                os.mkdir(storage)
        except:
            print("[-] Cannot create file %s" % storage)

    for i in domain:
        if i != '':
            domain_aux[i] = i
    #log es un modulo de twisted para imprimir logs en consola sobre lo que esta pasando
    log.startLogging(sys.stdout)
    
    #Buscamos el contenido del certificado y la llave generada por openssl
    certData = getModule(__name__).filePath.sibling('server.pem').getContent()
    # Agregamos el certificado
    certificate = ssl.PrivateCertificate.loadPEM(certData)
    # Escuchamos por tls o ssl por el puerto dado con el protocolo smtp
    reactor.listenSSL(port_, LocalSMTPFactory(storage), certificate.options())
    #corremos el server
    reactor.run()

    return 0

if __name__ == '__main__':
    main()