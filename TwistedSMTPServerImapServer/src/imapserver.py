"""
IMAP-SERVER
"""
from zope.interface import implements
from twisted.cred import checkers, portal
from twisted.internet import protocol, reactor, ssl
from twisted.mail import imap4, maildir
from twisted.python import log
from twisted.python.modules import getModule
from twisted.python.usage import Options, UsageError
from StringIO import StringIO
import email
import os
import random
import sys
# $ python imapserver.py -s <mail-storage> -p <port>
# ejemplo: python imapserver.py -s /tmp/mail/ -p 1430

storage = "/tmp/mail/"
port_ = 2500

# Argumentos
class ServerOptions(Options):
    # Interface que trae implementada Twisted para manejo de argumentos
    synopsis = "python smtpserver.py [options]"
    optParameters = [
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
        if self['mail-storage'] is None:
            raise UsageError(
                "Must specify mail-storafe --mail-storage")

class IMAPUserAccount(object):
	# evalua que exista la carpeta del usuario y la cantidad de mensajes que tiene
	implements(imap4.IAccount)

	def __init__(self, userDir):
		self.dir = userDir

	def _getMailbox(self, path):
		fullPath = os.path.join(self.dir, path)
		
		if not os.path.exists(fullPath):
			raise KeyError, "No such mailbox"
		return IMAPMailbox(fullPath)

	def listMailboxes(self, ref, wildcard):
		for box in os.listdir(self.dir):
			yield box, self._getMailbox(box)

	def select(self, path, rw=False):
		return self._getMailbox(path)

class ExtendedMaildir(maildir.MaildirMailbox):
	# Interfaz que implementa twisted que se 
	# deriva de la interface Imailbox
	def __iter__(self):
		return iter(self.list)

	def __len__(self):
		return len(self.list)

	def __getitem__(self, i):
		return self.list[i]

class IMAPMailbox(object):
	# Interface que se implementa twisted para poder abrir el archivo donde estan
	#almacenados los correos, tamb verifica la direccion la cantidad de mensajes que hay
	implements(imap4.IMailbox)

	def __init__(self, path):
		self.maildir = ExtendedMaildir(path)
		self.listeners = []
		self.uniqueValidityIdentifier = random.randint(1000000, 9999999)

	def getHierarchicalDelimiter(self):
		return "."

	def getFlags(self):
		return []

	def getMessageCount(self):
		return len(self.maildir)

	def getRecentCount(self):
		return 0

	def isWriteable(self):
		return False

	def getUIDValidity(self):
		return self.uniqueValidityIdentifier

	def _seqMessageSetToSeqDict(self, messageSet):
		# Cargar todos los mensajes que estan en el archivo de correo
		if not messageSet.last:
			messageSet.last = self.getMessageCount()

		seqMap = {}
		for messageNum in messageSet:
			if messageNum >= 0 and messageNum <= self.getMessageCount():
				seqMap[messageNum] = self.maildir[messageNum - 1]
		return seqMap

	def fetch(self, messages, uid):
		#Revisamos la hibicacion del archivo que tiene los mensajes del remitente o quien este accediendo
		if uid:
			raise NotImplementedError("This server only supports lookup by sequence number ")

		messagesToFetch = self._seqMessageSetToSeqDict(messages)
		for seq, filename in messagesToFetch.items():
			yield seq, MaildirMessage(file(filename).read())

	def addListener(self, listener):
		self.listeners.append(listener)

	def removeListener(self, listener):
		self.listeners.remove(listener)

class MaildirMessage(object):
	# Clase que implementa imessage  para manejo del mensaje
	implements(imap4.IMessage)

	def __init__(self, messageData):
		self.message = email.message_from_string(messageData)
		#Imprimimos el contenido de los mensajes
		for part in self.message.walk():
			print("CONTENT:", part.get_content_type())
			print(part.get_payload(decode=True))

	def getHeaders(self, negate, *names):
		# Obtenemos los encabezados
		if not names:
			names = self.message.keys()
		headers = {}
		if negate:
			for header in self.message.keys():
				if header.upper() not in names:
					headers[header.lower()] = self.message.get(header, '')
		else:
			for name in names:
				headers[name.lower()] = self.message.get(name, '')
		return headers

	def getBodyFile(self):
		#Obtenemos el cuerpo
		return StringIO(self.message.get_payload())

	def isMultipart(self):
		return self.message.is_multipart()
	




class MailUserRealm(object):
	implements(portal.IRealm)
	#Clase que busca la direccion exacta de archivo de correo se tambien implementa dela interfaz irealm de twist
	def __init__(self, baseDir):
		self.baseDir = baseDir

	def requestAvatar(self, avatarId, mind, *interfaces):
		if imap4.IAccount not in interfaces:
			raise NotImplementedError("This realm only supports the imap4.IAccount interface.")

		userDir = os.path.join(self.baseDir, avatarId)
		avatar = IMAPUserAccount(userDir)
		return imap4.IAccount, avatar, lambda: None

class IMAPServerProtocol(imap4.IMAP4Server):
	#Implementamos el protocolo imap para la comunicacion
	def lineReceived(self, line):
		# Linea que recive
		print "CLIENT:", line
		imap4.IMAP4Server.lineReceived(self, line)
	def sendLine(self, line):
		#Linea que envia
		imap4.IMAP4Server.sendLine(self, line)
		print "SERVER:", line

class IMAPFactory(protocol.Factory):
	#Construimos el protocolo imap
	def __init__(self, portal):
		self.portal = portal

	def buildProtocol(self, addr):
		proto = IMAPServerProtocol()
		proto.portal = portal
		return proto

def main(args=None):
	
	global storage
	global port_
	#Evaluamos argumentos
	o = ServerOptions()
	try:
		o.parseOptions(args)
	except UsageError as e:
		raise SystemExit(e)
	port_ =  int(o['port'])
	storage = str(o['mail-storage'])
	#log es un modulo de twisted para imprimir logs en consola sobre lo que esta pasando
	log.startLogging(sys.stdout)

if __name__ == '__main__':
	main()
	portal = portal.Portal(MailUserRealm(storage))
	checker = checkers.FilePasswordDB(os.path.join(storage, 'passwords.txt'))
	portal.registerChecker(checker)
	#Buscamos el contenido del certificado y la llave generada por openssl
	certData = getModule(__name__).filePath.sibling('server.pem').getContent()
	# Agregamos el certificado
	certificate = ssl.PrivateCertificate.loadPEM(certData)
	# Escuchamos por tls o ssl por el puerto dado con el protocolo smtp
	reactor.listenSSL(port_, IMAPFactory(portal), certificate.options())
	reactor.run()