#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  dmx.py - _dev.py
#
#  Copyright 2019 DMX Systems <https://dmx.systems>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.

__author__ = 'Juergen Neumann <juergen@dmx.systems>'
__copyright__ = 'Copyright 2019, DMX Systems <https://dmx.systems>'
__license__ = 'GPL'
__version__ = '3'
__maintainer__ = 'Juergen Neumann'
__email__ = 'juergen@dmx.systems'
__status__ = 'Development'
__doc__ = """
The aim of the script is to provide a set of python functions to play
with DMX's REST API.

jpn - 20170231

"""

import os, sys, json
import urllib.request, urllib.parse, urllib.error, http.cookiejar, base64
import configparser
import hashlib
import argparse

## define global variables
config = []    # The data required to access and login to dmx


def read_config_file():
    """
    Put this content in your dmx.cfg:

    [Credentials]
    authname = admin
    password =

    [Connection]
    server = localhost
    port = 8080
    workspace = DMX
    """
    global config

    script_dir = os.path.dirname(__file__) #<-- absolute dir the script is in
    config_file_name = 'dmx.cfg'
    config_file=os.path.join(script_dir, config_file_name)
    ## if empty or missing, use these parameters
    config = configparser.SafeConfigParser()
    # config.read(DEFAULT_CONFIG)
    if os.path.isfile(config_file):
        config.read(config_file)
    else:
        print("ERROR! Config file %s not found." % config_file)
        sys.exit(1)


def read_dmx_config(config_properties):
    """
    Reads the configuration data from '/path/to/dmx/config.properties'
    and overwrites the config settings with new values.
    """
    global config
    config = ConfigParser.SafeConfigParser()
    dmx_params={}
    dmx_config_file=str(config_properties)
    if os.access(dmx_config_file, os.R_OK):
        with open(dmx_config_file) as f_in:
            lines = [_f for _f in (line.rstrip() for line in f_in) if _f]
    for ln in lines:
        if not ln[0] in ('', ' ', '#', ';'):
            try:
                key, val = ln.strip().replace(" ", "").split('=', 1)
            except ValueError:
                print("INFO: No value found for %s in %s" % (key, dmx_config_file))
            else:
                dmx_params[key.lower()] = val

    port=dmx_params['org.osgi.service.http.port']
    password=dmx_params['dmx.security.initial_admin_password']
    config.add_section('Credentials')
    config.set('Credentials', 'authname', 'admin') # usualy the admin user
    config.set('Credentials', 'password', password) # usualy the admin password
    config.add_section('Connection')
    config.set('Connection', 'server', 'localhost') # usualy localhost
    config.set('Connection', 'port', port) # usualy 8080
    config.set('Connection', 'workspace', 'DMX') # usualy DMX

    for mandatory in ['org.osgi.service.http.port', 'dmx.security.initial_admin_password']:
        if mandatory not in list(dmx_params.keys()):
            print("ERROR! Could not read config file %s." % dmx_config_file)
            sys.exit(0)


def import_payload(json_filename, default="payload.json"):
    """
    Here we open the file and import the content as json.
    """
    print("Reading file %s" % (json_filename))
    with open(json_filename, 'r') as data_file:
        payload_json = json.load(data_file)

    # Test if the payload is a valid json object and get it sorted.
    try:
        payload = json.loads(json.dumps(payload_json, indent=3, sort_keys=True))
        print("LenPayload: %s" % len(payload))
    except:
        print("ERROR! Could not read Payload. Not JSON?")
        sys.exit(1);

    pretty_print(payload)
    return(payload)


def query_yes_no(question, default="no"):
    """
    Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
    It must be "yes" (the default), "no" or None (meaning
    an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")


def get_base64():
    """
    This function returns the authentication string for the user against DM
    """
    authname = config.get('Credentials', 'authname') # usualy the admin user
    password = config.get('Credentials', 'password') # usualy the admin password
    authstring = bytes((str(authname + ':' + password)), 'UTF-8')
    base64string = (base64.b64encode(authstring)).decode('UTF-8')
    return(base64string)


def get_session_id():
    """
    Creates an initial session and returns the session id.
    """
    server = config.get('Connection', 'server')
    port = config.get('Connection', 'port')
    url = 'http://%s:%s/core/topic/0' % (server, port)
    req = urllib.request.Request(url)
    req.add_header("Authorization", "Basic %s" % get_base64())
    req.add_header("Content-Type", "application/json")
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    try:
        test_url = opener.open(req)
    except urllib.request.HTTPError as e:
        print('Get Session ID Error: '+str(e))
    else:
        for c in cj:
            if c.name == "JSESSIONID":
                jsessionid = c.value
        return(jsessionid)


def read_request(url):
    """
    Reads the data from a given URL.
    """
    server = config.get('Connection', 'server')
    port = config.get('Connection', 'port')
    url = 'http://%s:%s/%s' % (server, port, url)
    jsessionid = get_session_id()
    print("Read Data %s" % url)
    req = urllib.request.Request(url)
    req.add_header("Cookie", "JSESSIONID=%s" % jsessionid)
    req.add_header("Content-Type", "application/json")
    try:
        response = (json.loads(urllib.request.urlopen(req).read().decode('UTF-8')))
    except urllib.error.HTTPError as e:
        print('Read Data Error: '+str(e))
    except ValueError:
        print('WARNING! No JSON Object found.')
        try:
            response = urllib.request.urlopen(req).read()
        except urllib.error.HTTPError as e:
            print('Read Data Error: '+str(e))
        else:
            return(response)
    else:
        return(response)


def write_request(url, payload=None, workspace='DMX', method='POST'):
    """
    Writes the data to a given URL.
    """
    ### The wsid is used for the Cockie here!
    ### Not for the payload - this might be confusing
    server = config.get('Connection', 'server')
    port = config.get('Connection', 'port')
    url = 'http://%s:%s/%s' % (server, port, url)
    jsessionid = get_session_id()
    print("Write Data %s" % url, payload)
    wsid = get_ws_id(workspace)
    req = urllib.request.Request(url)
    req.add_header("Cookie", "JSESSIONID=%s; dmx_workspace_id=%s" % (jsessionid, wsid))
    req.add_header("Content-Type", "application/json")
    req.get_method = lambda: method
    if payload:
        try:
            response = (json.loads(urllib.request.urlopen(req,
                    (json.dumps(payload)).encode('UTF-8')).read().decode('UTF-8')))
        except urllib.error.HTTPError as e:
            print('Write Data Error: '+str(e))
        else:
            return(response)
    else:
        try:
            # response = (json.loads(urllib.request.urlopen(req).read()))
            response = (urllib.request.urlopen(req).read())
        except urllib.error.HTTPError as e:
            print('Write Data Error: '+str(e))
        else:
            return(response)


def create_user(dm_user='testuser', dm_pass='testpass'):
    """
    This function creates a new user on the server.
    """
    # check if username exits
    users = list(get_items('dmx.accesscontrol.username').values())
    print(users)
    if dm_user in users:
        print("ERROR! User '%s' exists." % dm_user)
        sys.exit(1)
    else:
        # create user
        url = 'accesscontrol/user_account'
        hash_object = hashlib.sha256(dm_pass.encode('UTF-8'))
        dm_pass = '-SHA256-'+hash_object.hexdigest()
        payload = {'username' : dm_user, 'password' : dm_pass}
        topic_id = write_request(url, payload)["id"]
        print("New user '%s' was created with topic_id %s." % (dm_user, topic_id))
        return


def change_password(dm_user, dm_old_pass, dm_new_pass):
    """
    This function changes a user's password
    """
    ###
    ### Needs testing and might need adopting to DMX
    ###
    base64string = base64.encodestring("%s:%s" %
                    (dm_user, dm_old_pass)).replace("\n", "")

    # get id of user_account (not user_name!)
    url = 'core/topic/by_type/dmx.accesscontrol.user_account?children=false'
    topic_id = read_request(url)
    print("change Password - Topic ID of user: %s" % topic_id)

    # get id of private workspace
    url = 'core/topic?type_uri=dmx.workspaces.workspace_name&query=Private%%20Workspace'
    # wsnameid = read_request(url)[0]["id"]
    wsnameid = json.dumps(read_request(url))[0]
    print("WSNAMEID: %s" % wsnameid)


    url = ('core/topic/%s/related_topics'
           '?assoc_type_uri=dmx.core.composition&my_role_type_uri='
           'dmx.core.child&others_role_type_uri=dmx.core.parent&'
           'others_topic_type_uri=dmx.workspaces.workspace' % str(wsnameid)
          )
    wsid = read_request(url)
    print("Change Password WS ID = %s" % response)

    # change password
    server = config.get('Connection', 'server')
    port = config.get('Connection', 'port')
    jsessionid = get_session_id()
    url = 'http://%s:%s/core/topic/%s' % (server, port, topic_id)
    req = urllib.request.Request(url)
    req.add_header("Cookie", "JSESSIONID=%s" % jsessionid)
    req.add_header("Content-Type", "application/json")
    req.get_method = lambda: 'PUT'
    # encrypt the new password
    hash_object = hashlib.sha256(dm_new_pass)
    dm_new_pass = '-SHA256-'+hash_object.hexdigest()
    payload = {
        'children': {
            'dmx.accesscontrol.password': dm_new_pass
        }
    }
    try:
        response = (json.loads(urllib.request.urlopen(req,
                    (json.dumps(payload))).read()))
    except urllib.error.HTTPError as e:
        print('Change Password Error: '+str(e))
    else:
        print(response)


def get_ws_id(workspace):
    """
    This function gets the workspace ID for a workspace by its name.
    It's much faster to get it by its uri, if present.
    """
    print("Searching Workspace ID for %s" % workspace)
    url = ('core/topic?type_uri=dmx.workspaces.workspace_name&query="%s"' % workspace.replace(' ', '%20'))
    # wsnameid = read_request(url)[0]["id"]
    wsnameid = read_request(url)["topics"][0]["id"]
    # print("WSNAME: %s" % wsnameid )
    url = ('core/topic/%s/related_topics'
           '?assoc_type_uri=dmx.core.composition&my_role_type_uri='
           'dmx.core.child&others_role_type_uri=dmx.core.parent&'
           'others_topic_type_uri=dmx.workspaces.workspace' %
           str(wsnameid))
    ws_id = read_request(url)[0]["id"]
    print("WS ID = %s" % ws_id)
    return(ws_id)


def create_ws(workspace, ws_type):
    """
    This function creates a workspace with workspace uri
    (needed for id) on the server.
    """
    ### The create-workspace request changed:
    ###
    ### POST /workspace?name=...&uri=...&sharing_mode_uri=...
    ### Instead of path params query params are used now.
    ### `uri` is optional.
    uri = workspace.lower()+'.uri'
    url = ('workspace?name=%s&uri=%s&sharing_mode_uri=dmx.workspaces.%s' %
            (workspace, uri, ws_type))
    topic_id = write_request(url)["id"]


def create_member(workspace='DMX', dm_user='testuser'):
    """
    This function creates a user memebrship association for
    the workspace on the server.
    """
    print("Creating Workspace membership for user %s in %s" % (dm_user, workspace))
    wsid = get_ws_id(workspace)
    url = ('accesscontrol/user/%s/workspace/%s' %
            (dm_user, wsid))
    # topic_id = write_request(url)["id"]
    topic_id = write_request(url)


def send_data(payload, workspace='DMX'):
    """
    This function sends the topics according to payload to
    the workspace name on the server.
    """
    url = 'core/topic/'
    topic_id = write_request(url, payload, workspace)["id"]
    return(topic_id)


def get_topic(topic_id):
    """
    This function fetches the data according to datapath from
    the server and returns the data.
    """
    url = ('core/topic/%s?children=true' % topic_id)
    return(read_request(url))


def get_data(datapath):
    """
    This function fetches the data according to datapath from
    the server and returns the data.
    """
    url = ('core/%s?children=true' % datapath)
    return(read_request(url))


def get_items(topictype):
    """
    This function searches for topics of the specified topictype and
    returns the items, if exists
    """
    dm_items = {} # for dictionary
    data = get_data('topic/by_type/%s' % topictype)
    try:
        total = len(data)
    except:
        print("Error while trying to get items.")
        total = 0
        pass
    if total > 0:
        for i in range(total):
            dm_items.update(
                {(data[i]["id"]): (data[i]["value"])}
            )
    return(dm_items)


def get_related(topic_id):
    """
    This function fetches related topics according to topic_id from
    the server and returns the data.
    """
    url = ('core/topic/%s/related_topics?' % topic_id)
    return(read_request(url))


def get_creator(topic_id):
    """
    This function fetches related topics according to topic_id from
    the server and returns the data.
    """
    url = ('accesscontrol/object/%s/creator' % topic_id)
    return(read_request(url))


def get_modifier(topic_id):
    """
    This function fetches related topics according to topic_id from
    the server and returns the data.
    """
    url = ('accesscontrol/object/%s/modifier' % topic_id)
    return(read_request(url))


def get_topic_ws(topic_id):
    """
    This function fetches the topic's workspace id according to topic_id from
    the server and returns the data.
    """
    url = ('workspace/object/%s' % topic_id)
    return(read_request(url))


def get_ws_owner(workspace_id):
    """
    This function fetches the owner of a workspace id from
    the server and returns the data.
    """
    url = ('accesscontrol/workspace/%s/owner' % workspace_id)
    return(read_request(url))


def delete_topic(topic_id):
    """
    This function deletes a topic by its id from the server.
    """
    ###
    ### Still needs to be adopted to make use of write_request
    ###
    server = config.get('Connection', 'server')
    port = config.get('Connection', 'port')
    jsessionid = get_session_id()
    url = ('http://%s:%s/core/topic/%s' %
            (server, port, topic_id))
    req = urllib.request.Request(url)
    req.add_header("Cookie", "JSESSIONID=%s" % jsessionid)
    req.add_header("Content-Type", "application/json")
    req.get_method = lambda: 'DELETE'
    try:
        response = (json.loads(urllib.request.urlopen(req).read()))
    except urllib.error.HTTPError as e:
        print('Delete Topic Error: '+str(e))
    else:
        return(response)


def pretty_print(data):
    """
    This function just prints the json data in a pretty way. :)
    """
    # print("Data: %s" % type(data))
    print(json.dumps(data, indent=3, sort_keys=True))
    return


def main(args):
    """
    ToDo:
    # change_password(user, password, 'new_pass')
    """
    parser = argparse.ArgumentParser(description = 'This is a Python script \
             for DMX by Juergen Neumann <juergen@junes.eu>. It is free \
             software licensed under the GNU General Public License Version 3 \
             and comes with ABSOLUTELY NO WARRANTY.')
    parser.add_argument('-b','--by_type', type=str, help='Get all items of a TopicType by its topic.type.uri.', required=False)
    parser.add_argument('-C','--create_user', help='Create a user with -u username and -p password.', action='store_true', required=False, default=None)
    parser.add_argument('-d','--delete_topic', type=int, help='Detele a topic by id.', required=False)
    parser.add_argument('-f','--file', type=str, help='Creates a new topic from json file in a specified workspace with -f file name and -w workspace name.', required=False)
    parser.add_argument('-c','--config_properties', type=str, help='Reads config data from dmx config properties file.', required=False)
    parser.add_argument('-l','--login', help='Login as -u user with password -p instead of admin.', action='store_true', required=False, default=None)
    parser.add_argument('-m','--membership', help='Create a new workspace membership with -w workspace name and -n username of new member.', action='store_true', required=False, default=None)
    parser.add_argument('-n','--new_member', type=str, help='Provide the username of new member.', required=False)
    parser.add_argument('-p','--password', type=str, help='Provide a password.', required=False)
    parser.add_argument('-r','--get_related', type=int, help='Get all related items of a topic id.', required=False)
    parser.add_argument('-s','--get_session_id', help='Get a valid session id.', action='store_true', required=False, default=None)
    parser.add_argument('-t','--get_topic', type=int, help='Get all data of a topic id.', required=False)
    parser.add_argument('-u','--user', type=str, help='Provide a username.', required=False)
    parser.add_argument('-w','--workspace', type=str, help='Create a new workspace by name with -T type.', required=False)
    parser.add_argument('-T','--ws_type', type=str, help='Define Type of the new workspace.', required=False)
    args = parser.parse_args()
    argsdict = vars(args)

    ## action on arguments ##

    # instance must be first, cause it overwrites the default setting from config
    if argsdict['config_properties']:
        data = read_dmx_config(argsdict['config_properties'])
    else:
        read_config_file()

    if argsdict['file']:
        print("Importing json data from file %s" % (argsdict['file']))
        payload = import_payload(str(argsdict['file']))
        payload_len = len(payload)
        if argsdict['workspace']:
            workspace = argsdict['workspace']
            if payload_len > 0:
                dm_action_id = (send_data(payload, workspace))
                print("CREATED: %s" % dm_action_id)
            else:
                print("ERROR! Missing data in file %s" % (argsdict['file']))
        else:
            print("ERROR! Missing workspace declaration.")

    if argsdict['create_user']:
        if (argsdict['user'] != None) and (argsdict['password'] != None):
            data = create_user(argsdict['user'], argsdict['password'])
        else:
            print("ERROR! Missing username or password.")

    if argsdict['by_type']:
        data = get_items(argsdict['by_type'])
        pretty_print(data)

    if argsdict['get_related']:
        data = get_related(argsdict['get_related'])
        pretty_print(data)

    if argsdict['get_topic']:
        data = get_topic(argsdict['get_topic'])
        pretty_print(data)

    if argsdict['workspace'] and (argsdict['ws_type'] != None) and not argsdict['membership']:
        # Does not work with 'private' for now!
        if argsdict['ws_type'] in ["confidential", "collaborative", "public", "common"]:
            print("Creating new %s workspace %s" % (argsdict['ws_type'],argsdict['workspace']))
            data = create_ws(argsdict['workspace'], argsdict['ws_type'])
        elif argsdict['ws_type'] == "private":
            print("Sorry! %s is not working yet via scripting." % argsdict['ws_type'])
        else:
            print("ERROR! %s is not a valid workshop type." % argsdict['ws_type'])

    if argsdict['login']:
        if (argsdict['user'] != None) and (argsdict['password'] != None):
            config.set('Credentials', 'authname', argsdict['user']) # usualy the admin password
            config.set('Credentials', 'password', argsdict['password']) # usualy the admin password
        else:
            print("ERROR! Missing username or password.")

    if argsdict['get_session_id']:
        data = get_session_id()
        print(data)

    if argsdict['membership']:
        if (argsdict['workspace'] != None) and (argsdict['new_member'] != None):
            data = create_member(argsdict['workspace'], argsdict['new_member'])
        else:
            print("ERROR! Missing username of new member or missing workspace name.")

    if argsdict['delete_topic']:
        data = get_topic(argsdict['delete_topic'])
        if query_yes_no("Are you sure you want to delete topic id %s with value \"%s\"" % (argsdict['delete_topic'], data['value'])):
            print('yes')
            data = delete_topic(argsdict['delete_topic'])
            pretty_print(data)
        else:
            print('no')

    if len(sys.argv) < 2:
        parser.print_usage()
        print("Use -h or --help for more information.")
        parser.exit(1)


if __name__ == '__main__':
    # import sys
    if (sys.version_info < (3, 0)):
        print('ERROR! This program requires python version 3 or highter.')
        sys.exit(1)
    else:
        sys.exit(main(sys.argv))

# END.
