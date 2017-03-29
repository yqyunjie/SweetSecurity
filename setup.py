#!/usr/bin/env python

import argparse, fcntl, getpass, json, os, re, shutil, socket, sqlite3, struct, sys
from time import sleep

#Local Installer Scripts
from install import packages
from install import bro
from install import criticalStack
from install import elasticSearch
from install import logstash
from install import kibana 
from install import sweetSecurity
from install import apache

#Issue: When using OpenDNS, no hostname resolution
#TODO: build kibana searches/visualizations/dashboards
#TODO: build kibana stuff for sweet_security index too
#TODO: Can we implement network isolation?
#TODO: intelligent firewall service in the cloud

class color:
   PURPLE = '\033[95m'
   CYAN = '\033[96m'
   DARKCYAN = '\033[36m'
   BLUE = '\033[94m'
   GREEN = '\033[92m'
   YELLOW = '\033[93m'
   RED = '\033[91m'
   BOLD = '\033[1m'
   UNDERLINE = '\033[4m'
   END = '\033[0m'

def get_user_input(input_string):
	if sys.version_info[0] > 2:
		return input(input_string)
	else:
		return raw_input(input_string)

def getIP(ifname):
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	try:
		return socket.inet_ntoa(fcntl.ioctl(s.fileno(),0x8915,struct.pack('256s', ifname[:15]))[20:24])
	except:
		return ''

def validateIP(ip):
	if re.match(r'^(\d{1,3}\.){3}\d{1,3}$',ip):
		return True
	elif re.match(r'^[a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9](\.[a-zA-Z]{2,})+$',ip):
		return True
	elif re.match(r'^[a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9]$',ip):
		return True
	else:
		return False

if __name__=="__main__":
	
	#Check if user is root first...
	if os.getuid() != 0:
		sys.exit("Must run as root/sudo")
	
	while True:
		question="\033[1m1 - \033[4mFull Install\033[0m: Bro IDS, Critical Stack, ELK Stack, Apache, Sweet Security\n"
		question+="\033[1m2 - \033[4mSensor Only\033[0m: Bro IDS, Critical Stack, Logstash, Sweet Security\n"
		question+="\033[1m3 - \033[4mWeb Server Only\033[0m: Elasticsearch, Kibana, Apache\n"
		question+="\033[1mChoose an Installation Type (1-3)\033[0m: "
		installType = get_user_input(question)
		if not re.match(r'^[1-3]$', installType ):
			print("Choose 1, 2, or 3.")
		else:
			break
	
	#Install prerequisites
	packages.install(installType)
	
	interfaces=os.listdir('/sys/class/net/')
	userQuestion="Available Interfaces: \n"
	availableInts=[]
	availableIntNames=[]
	availableIntIPs=[]
	d=0
	for interface in interfaces:
		if interface != "lo":
			if len(getIP(interface)) > 0:
				availableInts.append(str(d))
				availableIntNames.append(interface)
				availableIntIPs.append(getIP(interface))
				userQuestion+="  %d: %s (%s)\n" % (d,interface,getIP(interface))
				d=d+1
	userQuestion+="\033[1mWhich Interface Should be Used(web admin and spoofing)\033[0m: "
	if len(availableIntIPs) > 1:
		while True:
			chosenInt=get_user_input(userQuestion)
			if chosenInt not in availableInts:
				print("  Invalid Response.")
			else:
				break
		chosenInterface=availableIntNames[int(chosenInt)]
		chosenInterfaceIP=availableIntIPs[int(chosenInt)]
	elif len(availableIntIPs) == 1:
		chosenInterface=availableIntNames[0]
		chosenInterfaceIP=availableIntIPs[0]
	else:
		sys.exit('No available interfaces')
	
	
	#Create Credentials for apache
	while True:
		httpUser = get_user_input("\033[1mEnter username for web portal (apache/kibana)\033[0m: ")
		if len(httpUser) > 100:
			print("Username must be less than 100 characters")
		if not re.match(r'[0-9a-zA-Z]+', httpUser):
			print("Username must be alphanumeric 0-9, a-z, and A-Z")
		else:
			break
	while True:
		httpPass = getpass.getpass("\033[1mEnter password for web portal\033[0m: ")
		httpPassConfirm = getpass.getpass("\033[1mConfirm password for web portal\033[0m: ")
		if httpPass != httpPassConfirm:
			print ("Passwords do not match")
		elif len(httpPass) > 100:
			print("Password must be less than 100 characters")
		elif '"' in httpPass:
			print("Password cannot contain double quote character")
		else:
			break
	
	#Create Credentials for Elasticsearch
	while True:
		elasticUser = get_user_input("\033[1mEnter username for Elasticsearch\033[0m: ")
		if len(elasticUser) > 100:
			print("Username must be less than 100 characters")
		if not re.match(r'[0-9a-zA-Z]+', elasticUser):
			print("Username must be alphanumeric 0-9, a-z, and A-Z")
		else:
			break
	while True:
		elasticPass = getpass.getpass("\033[1mEnter password for Elasticsearch\033[0m: ")
		elasticPassConfirm = getpass.getpass("\033[1mConfirm password for Elasticsearch\033[0m: ")
		if elasticPass != elasticPassConfirm:
			print ("Passwords do not match")
		elif len(elasticPass) > 100:
			print("Password must be less than 100 characters")
		elif '"' in elasticPass:
			print("Password cannot contain double quote character")
		else:
			break
	
	
	if installType == '1':
		#Bro IDS, Critical Stack, ELK Stack, Apache, Sweet Security
		criticalStackInstalled=False
		if os.path.isfile('/usr/bin/critical-stack-intel'):
			criticalStackInstalled=True
		if criticalStackInstalled == False:
			while True:
				installCriticalStack = get_user_input("\033[1mInstall Critical Stack Threat Intel For Bro IDS (Y/n)\033[0m: ")
				if installCriticalStack.lower() not in ('y', 'n', ''):
					print("Must choose Y or N.")
				else:
					break
			if installCriticalStack.lower()=='y' or len(installCriticalStack) == 0:
				installCriticalStack = 'y'
				while True:
					csKey = get_user_input("    \033[1mEnter Your Critical Stack API Key\033[0m: ")
					if not re.match(r'[0-9a-fA-F]{8}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{12}', csKey):
						print("        Not a valid API key.")
					else:
						break
		bro.install(chosenInterface,'localhost')
		if criticalStackInstalled == False and installCriticalStack.lower()=='y':
			criticalStack.install(csKey)
		else:
			print "Critical Stack already installed"
		apache.install(installType,chosenInterface,chosenInterfaceIP)
		print "  Creating web portal credentials"
		os.popen('sudo htpasswd -cb /etc/apache2/.htpasswd %s "%s"' % (httpUser,httpPass)).read()
		os.popen('sudo htpasswd -cb /etc/apache2/.elasticsearch %s "%s"' % (elasticUser,elasticPass)).read()
		elasticSearch.install()
		kibana.install(chosenInterfaceIP)
		print "  Restarting Apache"
		os.popen('sudo service apache2 restart').read()
		logstash.install('localhost',elasticUser,elasticPass)
		sweetSecurity.install(chosenInterface)
		sweetSecurity.addWebCreds('localhost',httpUser,httpPass)
		print "Starting SweetSecurity"
		os.popen('sudo service sweetsecurity restart').read()
	elif installType == '2':
		#Bro IDS, Critical Stack, Logstash, Sweet Security
		esServer=get_user_input('\033[1mEnter Server IP:\033[0m ')
		criticalStackInstalled=False
		if os.path.isfile('/usr/bin/critical-stack-intel'):
			criticalStackInstalled=True
		if criticalStackInstalled == False:
			while True:
				installCriticalStack = get_user_input("\033[1mInstall Critical Stack Threat Intel For Bro IDS (Y/n)\033[0m: ")
				if installCriticalStack.lower() not in ('y', 'n', ''):
					print("Must choose Y or N.")
				else:
					break
			if installCriticalStack.lower()=='y' or len(installCriticalStack) == 0:
				installCriticalStack = 'y'
				while True:
					csKey = get_user_input("    \033[1mEnter Your Critical Stack API Key\033[0m: ")
					if not re.match(r'[0-9a-fA-F]{8}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{12}', csKey):
						print("        Not a valid API key.")
					else:
						break
		if not validateIP(esServer):
			sys.exit('Not a valid IP Address')
		bro.install(chosenInterface,esServer)
		if criticalStackInstalled == False and installCriticalStack.lower()=='y':
			criticalStack.install(csKey)
		logstash.install(esServer,elasticUser,elasticPass)
		sweetSecurity.install(chosenInterface)
		sweetSecurity.addWebCreds(esServer,httpUser,httpPass)
		print "Starting SweetSecurity"
		os.popen('sudo service sweetsecurity restart').read()
	elif installType == '3':
		#Elasticsearch, Kibana, Apache
		apache.install(installType,chosenInterface,chosenInterfaceIP)
		print "  Creating web portal credentials"
		os.popen('sudo htpasswd -cb /etc/apache2/.htpasswd %s "%s"' % (httpUser,httpPass)).read()
		os.popen('sudo htpasswd -cb /etc/apache2/.elasticsearch %s "%s"' % (elasticUser,elasticPass)).read()
		elasticSearch.install()
		print "  Creating elasticsearch credentials"
		kibana.install(chosenInterfaceIP)
		print "  Restarting Apache"
		os.popen('sudo service apache2 restart').read()