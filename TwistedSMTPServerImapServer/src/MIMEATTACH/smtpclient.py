'''
SMTP-CLIENT => in our case domain is localhost and mailFrom domain is @izthero.com
'''

from twisted.python import log
from twisted.python.modules import getModule
from twisted.python.usage import Options, UsageError
from twisted.internet import defer, reactor
from twisted.application import internet
from twisted.application import service    
from string import Template
from email.mime.text import MIMEText
from email.Header import Header
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email import encoders
from os.path import basename

import sys
import os
import csv
import smtplib
import dns.resolver


'''
Example:
$ python smtpclient.py -c mailTo.csv -e jeffmy@izthero.com -n 'Jeffrey Ricardo Alfaro Fonseca' -h localhost -p 2500 -s "Message Test" -m bodymessage -a bodymessage
'''
host = "localhost"
destfile = ""
port_ = 2500
subject = ""
msgfile = ""
mailfromname = ""
mailfromemail = ""
attach_f = ""
# OPciones
class ServerOptions(Options):
	# Interface que trae implementada Twisted para manejo de argumentos
    synopsis = "python smtpclient.py [options]"
    optParameters = [
        ('mail-server', 'h','mail-server example <localhost>'),
        ('csv-file', 'c','csv file containing emailTo addrs <name1,name1_emailaddr1,.....> example <Name LastN, username@example.com>'),
        ('message-file', 'm', 'File attachment <filename>, this is optional.'),
        ('port','p','port number'),
        ('subject','s',"Subject of the message"),
        ('mailFromN','n',"Sender name, example: 'Name LastName'"),
        ('mailFromE','e',"Sender email, example: example@domain.com"),
        ('file-attach','a',"attach a file, example: example.txt")]


    def postOptions(self):
        """
        Verifica las entradas
        """
        try:
            self['port'] = int(self['port'])
        except ValueError:
            raise UsageError("--port argument must be an integer.")
        if self['mail-server'] is None:
            raise UsageError(
                "Must specify a --mail-server ")
        if self['csv-file'] is None:
            raise UsageError(
                "Must specify mail-storafe --csv-file")
        if self['subject'] is None:
            raise UsageError(
                "Must specify mail-storafe --subject")
        if self['mailFromN'] is None:
            raise UsageError(
                "Must specify name from sender --mailFromN")
        if self['mailFromE'] is None:
            raise UsageError(
                "Must specify email from sender --mailFromE")


def getCSVContent():
	#Lee el csv y retorna una lista con nombre y correo
	content = []
	with open(destfile, 'rt') as f:
		csv_reader = csv.reader(f)
		for line in csv_reader:
			content.append(line)
	return content

def setBodyMsg(content):
	# $NAME
	#Reemplaza $NAME en el cuerpo del mensaje por los nombres de los destinatarios
	message = getModule(__name__).filePath.sibling(msgfile).getContent()
	
	s = Template(message)
	
	pos_name = 0
	names = ""

	if len(content) > 1:
		for name in content:
			names = names + name[pos_name] + ", "
		names = names[:-2]
	else:
		names = names + content[pos_name][pos_name]

	return s.substitute(NAME=names)

def main(args=None):
	global host
	global destfile
	global port_
	global subject
	global msgfile
	global mailfromname
	global mailfromemail
	global attach_f
	#Evaluamos los argumentos
	o = ServerOptions()
	try:
		o.parseOptions(args)
	except UsageError as e:
		raise SystemExit(e)
	else:
		host = str(o['mail-server'])
		destfile = str(o['csv-file'])
		port_ = int(o['port'])
		subject = str(o['subject'])
		msgfile = str(o['message-file'])
		mailfromemail = str(o['mailFromE'])
		mailfromname = str(o['mailFromN'])
		attach_f = str(o['file-attach'])

	csvcontent = getCSVContent()

	#log es un modulo de twisted para imprimir logs en consola sobre lo que esta pasando
	log.startLogging(sys.stdout)
	# Agregamos los parametros del mensaje Subject Body To From
	msg = MIMEMultipart()
	msg["Subject"] = subject
	msg["From"] = '"%s <%s>"' % (mailfromname,mailfromemail)
	msg.attach(MIMEText(setBodyMsg(csvcontent)))
	files = attach_f
	with open (files,"rb") as fil:
		part = MIMEApplication(fil.read(),Name=basename(files))
	part['Content-Disposition'] = 'attachment; filename=%s' % basename(files)
	msg.attach(part)


	recipients = []
	e = 1
	for email in csvcontent:
		recipients.append(email[e])


	msg["To"] = ", ".join(recipients)
	# Nos conectamos por ssl/tls
	s = smtplib.SMTP_SSL('%s:%d' % (host,port_))
	# lo enviamos
	s.sendmail(mailfromemail, recipients, msg.as_string())
	s.quit()

if __name__ == '__main__':
	main()