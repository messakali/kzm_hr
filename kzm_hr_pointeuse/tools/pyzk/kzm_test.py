# -*- coding: utf-8 -*-
import sys
#sys.path.append("zk")
from signal import signal, SIGPIPE, SIG_DFL
signal(SIGPIPE,SIG_DFL)

from zk import ZK, const

conn = None
zk = ZK('51.210.186.95', port=4370, timeout=20)
try:
    print ('Connecting to device ...')
    conn = zk.connect()
    print ('Disabling device ...')
    print ('Firmware Version: : {}'.format(conn.get_firmware_version()))
    # print '--- Get User ---'
    users = conn.get_users()
    for user in users:
        privilege = 'User'
        if user.privilege == const.USER_ADMIN:
            privilege = 'Admin'
        print ('- UID #{}'.format(user.uid), end = ',  ')
        print ('  Name       : {}'.format(user.name), end = ',  ')
        print ('  Privilege  : {}'.format(privilege), end = ',  ')
        print ('  Password   : {}'.format(user.password), end = ',  ')
        print ('  Group ID   : {}'.format(user.group_id), end = ',  ')
        print ('  Card   : {}'.format(user.card), end = ',  ')
        print ('  User  ID   : {}'.format(user.user_id))

    print ("Voice Test ...")
    print ('Enabling device ...')
except Exception as e:
    print ("Process terminate : {}".format(e))
finally:
    if conn:
        conn.disconnect()
