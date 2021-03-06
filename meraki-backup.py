#!/usr/bin/env python3
#
# Before running this script you need to install these two modules:
# pip install requests
# pip install meraki-sdk
#
# Before you can use these scripts you need an API key.  Following this guide to create an API key.
# https://documentation.meraki.com/zGeneral_Administration/Other_Topics/The_Cisco_Meraki_Dashboard_API#Enable_API_access
#
# Create a ".meraki.env" file in your home directory (special note for Windows users - the filename is dot meraki dot env).
# This is used to store your sensitive information.  If you are a Windows user and you go Windows+R and type in "cmd" and
# hit return you'll have a command prompt with the current directory equal to your home directory.  From here you can
# go "notepad .meraki.env" to create the file.  A sample might look like:
# x_cisco_meraki_api_key=****************************************
# Alternatively (ie only do this if you don't do the above) you can create a .env (note dot env) file in the same
# directory as the backup script witht the same "x_cisco_meraki_api_key" field.
#
# To run a backup go:
# meraki-backup.py "org name"
# This will create a file called meraki-restore.py.  To do a restore you go:
# meraki-restore.py "org name"
# Note that the store will not overwrite existing networks.  You can either rename an existing network you want to restore
# over or edit meraki-restore.py to restore into a different [new] network.  Also you can edit meraki-restore.py to only
# restore the bits you want.
#
import os
from meraki_sdk.meraki_sdk_client import MerakiSdkClient
from meraki_sdk.exceptions.api_exception import APIException
import argparse
import json

def get_org_id(meraki,orgName):
	result = meraki.organizations.get_organizations()
	for row in result:
		if row['name'] == orgName:
			return row['id']

	raise ValueError('The organization name does not exist')

def write_restore_header(file):
	file.write("#!/usr/bin/env python3\n");
	file.write("#\n");
	file.write("# Search for \"#restored\" and edit below that to control what is restored.\n");
	file.write("#\n");
	file.write("import os\n");
	file.write("import argparse\n");
	file.write("import requests\n");
	file.write("\n");
	file.write("\n");
	file.write("from dotenv import load_dotenv\n");
	file.write("load_dotenv()\n");
	file.write("load_dotenv(dotenv_path=os.path.join(os.path.expanduser('~'),'.meraki.env'))\n");
	file.write("\n");
	file.write("parser = argparse.ArgumentParser(description='Restore a Meraki online config from an offline file.')\n");
	file.write("parser.add_argument('orgName', help='The name of a Meraki organisation')\n");
	file.write("args = parser.parse_args()\n");
	file.write("\n");
	file.write("headers = {\n");
	file.write("\t'x-cisco-meraki-api-key': os.getenv('x_cisco_meraki_api_key'),\n");
	file.write("\t'Content-Type': 'application/json'\n");
	file.write("\t}\n");
	file.write("\n");
	file.write("session = requests.Session()\n")
	file.write("\n");
	file.write("def get_org_id(orgName):\n");
	file.write("\ttry:\n")
	file.write("\t\t# https://dashboard.meraki.com/api_docs#list-the-organizations-that-the-user-has-privileges-on\n")
	file.write("\t\tgeturl = 'https://api.meraki.com/api/v0/organizations'\n")
	file.write("\t\tdashboard = session.get(geturl, headers=headers)\n")
	file.write("\t\tdashboard.raise_for_status()\n")
	file.write("\texcept requests.exceptions.HTTPError as err:\n")
	file.write("\t\tprint(err)\n")
	file.write("\n")
	file.write("\tfor row in dashboard.json():\n");
	file.write("\t\tif row['name'] == orgName:\n");
	file.write("\t\t\treturn row['id']\n");
	file.write("\traise ValueError('The organization name does not exist')\n");
	file.write("\n");
	file.write("orgid=get_org_id(args.orgName)\n");
	file.write("\n");
	file.write("\n");

def write_admins(file,meraki, orgid):
	myOrgAdmins=meraki.admins.get_organization_admins(orgid)
	file.write("# Organisation Dashboard Administrators\n")
	file.write("# https://dashboard.meraki.com/api_docs#create-a-new-dashboard-administrator\n")
	file.write("posturl = 'https://api.meraki.com/api/v0/organizations/{0}/admins'.format(str(orgid))\n")
	for row in myOrgAdmins:
		file.write("dashboard = session.post(posturl, json="+repr(row)+", headers=headers)\n")
	file.write("\n")

def write_mx_l3_fw_rules(file,meraki,networkid):
	myRules=meraki.mx_l_3_firewall.get_network_l_3_firewall_rules(networkid)[0:-1]
	file.write("\t# MX L3 Firewall Rules\n")
	file.write("\t# https://api.meraki.com/api_docs#update-the-l3-firewall-rules-of-an-mx-network\n")
	file.write("\tputurl = 'https://api.meraki.com/api/v0/networks/{0}/l3FirewallRules'.format(str(networkid))\n")
	file.write("\tdashboard = session.put(puturl, json="+str({"rules":myRules,"syslogDefaultRule":False})+", headers=headers)\n")
	file.write("\n")

def write_mx_vlans(file,meraki,networkid):
	vlanEnabled=meraki.vlans.get_network_vlans_enabled_state(networkid)

	file.write("\t# MX VLANs\n")
	file.write("\t# https://dashboard.meraki.com/api_docs#enable/disable-vlans-for-the-given-network\n")
	file.write("\tputurl = 'https://api.meraki.com/api/v0/networks/{0}/vlansEnabledState'.format(str(networkid))\n")
	file.write("\tdashboard = session.put(puturl, json="+repr(vlanEnabled)+", headers=headers)\n")

	if vlanEnabled['enabled']:
		# VLANS are enabled
		myVLANS=meraki.vlans.get_network_vlans(networkid)

		file.write("\t# https://dashboard.meraki.com/api_docs#add-a-vlan\n")
		file.write("\tposturl = 'https://api.meraki.com/api/v0/networks/{0}/vlans'.format(str(networkid))\n")
		for row in myVLANS:
			file.write("\tdashboard = session.post(posturl, json="+repr(row)+", headers=headers)\n")
		file.write("\n")
	else:
		print("warning: MX VLANs disabled - wont be able to restore IP addressing");
		
def write_mx_cellular_fw_rules(file,meraki,networkid):
	myRules=meraki.mx_cellular_firewall.get_network_cellular_firewall_rules(networkid)[0:-1]
	file.write("\t# MX cellular firewall\n")
	file.write("\t# https://dashboard.meraki.com/api_docs#mx-cellular-firewall\n")
	file.write("\tputurl = 'https://api.meraki.com/api/v0/networks/{0}/cellularFirewallRules'.format(str(networkid))\n")
	file.write("\tdashboard = session.put(puturl, json="+str({"rules":myRules,"syslogEnabled":False})+", headers=headers)\n")
	file.write("\n")

def write_mx_vpn_fw_rules(file,meraki,orgid):
	myRules=meraki.mx_vpn_firewall.get_organization_vpn_firewall_rules(orgid)[0:-1]
	file.write("# MX VPN firewall\n")
	file.write("# https://dashboard.meraki.com/api_docs#mx-vpn-firewall\n")
	file.write("puturl = 'https://api.meraki.com/api/v0/organizations/{0}/vpnFirewallRules'.format(str(orgid))\n")
	file.write("dashboard = session.put(puturl, json="+str({"rules":myRules,"syslogEnabled":True})+", headers=headers)\n")
	file.write("\n")

def write_vpn_settings(file,meraki,networkid):
	myVPN=meraki.networks.get_network_site_to_site_vpn(networkid)
	file.write("\t# Network - AutoVPN Settings\n")
	file.write("\t# https://dashboard.meraki.com/api_docs#update-the-site-to-site-vpn-settings-of-a-network\n")
	file.write("\tputurl = 'https://api.meraki.com/api/v0/networks/{0}/siteToSiteVpn'.format(str(networkid))\n")
	file.write("\tdashboard = session.put(puturl, json="+str(myVPN)+", headers=headers)\n")
	file.write("\n")

def write_snmp_settings(file,meraki,orgid):
	mySNMP=meraki.snmp_settings.get_organization_snmp(orgid)
	if 'v2CommunityString' in mySNMP:
		del mySNMP['v2CommunityString']
	if 'hostname' in mySNMP:
		del mySNMP['hostname']
	if 'port' in mySNMP:
		del mySNMP['port']
	if mySNMP['v3AuthMode'] is None:
		del mySNMP['v3AuthMode']
	if mySNMP['v3PrivMode'] is None:
		del mySNMP['v3PrivMode']

	file.write("# SNMP Settings\n")
	file.write("# https://dashboard.meraki.com/api_docs#update-the-snmp-settings-for-an-organization\n")
	file.write("puturl = 'https://api.meraki.com/api/v0/organizations/{0}/snmp'.format(str(orgid))\n")
	file.write("try:\n")
	file.write("\tdashboard = session.put(puturl, json="+str(mySNMP)+", headers=headers)\n")
	file.write("\tdashboard.raise_for_status()\n")
	file.write("except requests.exceptions.HTTPError as err:\n")
	file.write("\tprint(err)\n")
	file.write("\n")

def write_non_meraki_vpn_peers(file,meraki,orgid):
	myPeers=meraki.organizations.get_organization_third_party_vpn_peers(orgid)
	file.write("# Non Meraki VPN Peers\n")
	file.write("# https://dashboard.meraki.com/api_docs#update-the-third-party-vpn-peers-for-an-organization\n")
	file.write("puturl = 'https://api.meraki.com/api/v0/organizations/{0}/thirdPartyVPNPeers'.format(str(orgid))\n")
	file.write("try:\n")
	file.write("\tdashboard = session.put(puturl, json="+str(myPeers)+", headers=headers)\n")
	file.write("\tdashboard.raise_for_status()\n")
	file.write("except requests.exceptions.HTTPError as err:\n")
	file.write("\tprint(err)\n")
	file.write("\n")

def write_ssid_settings(file,meraki,networkid):
	mySSIDs=meraki.ssids.get_network_ssids(networkid)
	if mySSIDs is None:
		return
	file.write("\t# SSIDs\n")
	file.write("\t# https://dashboard.meraki.com/api_docs#update-the-attributes-of-an-ssid\n")
	for row in mySSIDs:
		file.write("\tputurl = 'https://api.meraki.com/api/v0/networks/{0}/ssids/"+str(row['number'])+"'.format(str(networkid))\n")
		if 'radiusServers' in row:
			print("warning: added dummy radius password for SSID "+row['name'])
			row['radiusServers'][0]['secret']='password'
		file.write("\tdashboard = session.put(puturl, json="+str(row)+", headers=headers)\n")

		myRules=meraki.mr_l_3_firewall.get_network_ssid_l_3_firewall_rules({'network_id':networkid, 'number':row['number']})[0:-2]
		file.write("\t# MR L3 firewall\n")
		file.write("\t# https://dashboard.meraki.com/api_docs#update-the-l3-firewall-rules-of-an-ssid-on-an-mr-network\n")
		file.write("\tputurl = 'https://api.meraki.com/api/v0/networks/{0}/ssids/"+str(row['number'])+"/l3FirewallRules'.format(str(networkid))\n")
		file.write("\tdashboard = session.put(puturl, json="+str({"rules":myRules,"allowLanAccess":True})+", headers=headers)\n")
		file.write("\n")
	

from dotenv import load_dotenv
load_dotenv()
load_dotenv(dotenv_path=os.path.join(os.path.expanduser("~"),".meraki.env"))

parser = argparse.ArgumentParser(description='Backup a Meraki config to an offline file.')
parser.add_argument('orgName', help='The name of a Meraki organisation')
args = parser.parse_args()

meraki = MerakiSdkClient(os.getenv("x_cisco_meraki_api_key"))
orgid=get_org_id(meraki,args.orgName)

with open('meraki-restore.py', 'w') as file:
	write_restore_header(file);

	file.write("# Edit script below this line to control what is #restored.\n");
	file.write("\n");

	file.flush()

	write_admins(file,meraki, orgid);
	write_mx_vpn_fw_rules(file,meraki,orgid)
	write_snmp_settings(file,meraki,orgid)
	write_non_meraki_vpn_peers(file,meraki,orgid)

	file.flush()
		
	myNetworks = meraki.networks.get_organization_networks({"organization_id": orgid})
	for row in myNetworks:
		if row['type'] == 'systems manager':
			continue

		if row['tags'] is None:
			del row['tags']

		status="Processing network "+row['name']
		print(status)
		file.write("# Add Network: "+row['name']+"\n")
		file.write("print('"+status+"')\n")

		file.write("try:\n")
		file.write("\t# https://dashboard.meraki.com/api_docs#create-a-network\n")
		file.write("\tposturl = 'https://api.meraki.com/api/v0/organizations/{0}/networks'.format(str(orgid))\n")
		file.write("\tdashboard = session.post(posturl, json="+repr(row)+", headers=headers)\n")
		file.write("\tdashboard.raise_for_status()\n")

		file.write("\tnetworkid=dashboard.json()['id']\n")
		file.write("\n")
		write_mx_vlans(file,meraki, row['id'])
		write_mx_cellular_fw_rules(file,meraki,row['id'])
		write_mx_l3_fw_rules(file,meraki,row['id'])
		write_vpn_settings(file,meraki,row['id'])
		write_ssid_settings(file,meraki,row['id'])
		file.write("except requests.exceptions.HTTPError as err:\n")
		file.write("\tprint('Can not add network "+row['name']+" - it probably already exists')\n")
		file.write("\n");
		file.flush()
