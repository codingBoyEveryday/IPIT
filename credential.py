#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import sqlite3
import re
import hashlib
import hmac
import random
from string import ascii_letters

USER_RE = re.compile(r"^[a-zA-Z0-9\._-]{3,20}$")
PASS_RE = re.compile(r"^.{3,20}$")
INSERT_SQL = "INSERT INTO USERS (name, pwd_hash, email, user_group) VALUES ('{0}', '{1}', '{2}', '{3}')"
SECRET = "xha8&jsKjM,"

ADMIN_PW = '1234'
HADMIN_PW = '1234'
EADMIN_PW = '1234'


def if_logged_in(request):
    """
    Given a user session. Check the cookie and return (True, uname, ugroup) if logged in.
    If user has not logged in, return (False, None,'guest')
    Input:
    request is a flask request object
    """
    uname = None
    ugroup = 'guest'
    logged_in = False
    cookie_val = request.cookies.get('user_id')
    if cookie_val:
        uid = check_secure_val(cookie_val)  # string
        if uid:
            uname = get_by_id(uid)
            ugroup = get_by_id(uid, target='user_group')
            logged_in = True
    return logged_in, uname, ugroup


def make_conn_c():
    "Generate connection and a cursor for the connection to sqlite3 db."
    connection = sqlite3.connect('credential.db')
    cursor = connection.cursor()
    return connection, cursor


def is_valid_username(username, check_type='signup'):
    """
    Support function for /signup handler
    Input: username: string or None.
    Output: nsername: string or None; msg: string
    """
    name, msg = None, ''
    conn, c = make_conn_c()
    names = [x[0] for x in c.execute("SELECT name from USERS;").fetchall()]
    conn.close()
    if not username:
        msg = "User Name can't be empty."
    elif not USER_RE.match(username):
        msg = "Name must be 3 t 20 letters or digits or - or _ or . "
    elif check_type=='signup' and username in names:
        msg = "This name already exists."
    elif check_type=='login' and username not in names:
        msg = "This username doesn't exists."
    else:
        name = username
    return name, msg


def is_valid_password(pwd, repeat):
    """
    Given two user inputs. Decide if the password is valid.
    Inputs: pwd: string; repeat: string;
    Output: valid_pwd: string; msg: string;
    """
    valid_pwd, msg = None, ""
    if not pwd:
        msg = "Password can't be empty."
    elif not PASS_RE.match(pwd):
        msg = "Password must be 3 to 20 characters long."
    elif pwd != repeat:
        msg = "Password and repeat don't match."
    else:
        valid_pwd = pwd
    return valid_pwd, msg


def make_salt(length = 5):
    return ''.join(random.choice(ascii_letters) for x in xrange(length))


def make_pw_hash(name, pw, salt = None):
    if not salt:
        salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return '%s|%s' % (salt, h)


def valid_pw(name, password, h):
    salt = h.split('|')[0]
    return h == make_pw_hash(name, password, salt)


def register_user(name, pwd, email, group='guest'):
    """
    When called by handler signup, create a record in the sqllite3 credential.db, table USERS
    Inputs:
      name: string
      pwd: string
      email: None or string
      group: string.  ['admin', 'human_admin', 'element_admin', 'test_manager', 'guest']
    """
    conn, c = make_conn_c()
    pwd_hash = make_pw_hash(name, pwd)
    try:
        c.execute(INSERT_SQL.format(name, pwd_hash, email, group))
        conn.commit()
        conn.close()
    except:
        return "ERR: {}".format(sys.exc_info()[0])


def make_secure_val(val):
    """ val is a string."""
    return '%s|%s' % (val, hmac.new(SECRET, val).hexdigest())


def check_secure_val(secure_val):
    val = secure_val.split('|')[0]
    if secure_val == make_secure_val(val):
        return val


def login_user(name, pwd):
    """
    Give a username, a pwd. First verify if it matches.
    set the user's cookie according to the verification.
    Inputs: name, string; pwd, string
    Output: cookie value for name 'user_id' can be ''
    """
    cookie_val = ''
    conn, c = make_conn_c()
    q = c.execute("SELECT id, pwd_hash FROM USERS where name = '{0}';".format(name)).fetchall()
    conn.close()
    if q and valid_pw(name, pwd, q[0][1]):
        cookie_val = make_secure_val(str(q[0][0]))
    return cookie_val


def get_by_id(uid, target = 'name'):
    """
    support page handler function is_logged_in()
    uid: string
    target: name of the column. Can be 'name' 'pwd_hash' 'email' 'user_group'
    """
    if uid:
        conn, c = make_conn_c()
        q = c.execute("SELECT {0} FROM USERS where id = '{1}';".format(target, uid)).fetchall()
        conn.close()
        if q:
            return q[0][0]


def get_by_name(uname, target = 'email'):
    """
    support page handler project_single()
    uname: string
    target: name of the column. Can be 'id' 'pwd_hash' 'email' 'user_group'
    """
    if uname:
        conn, c = make_conn_c()
        q = c.execute("SELECT {0} FROM USERS where name = '{1}';".format(target, uname)).fetchall()
        conn.close()
        if q:
            return q[0][0]


def verify_pwd(name, pwd):
    """
    Given a username and a pwd, return if it is correct.
    And return an error message when not correct.
    """

    if name:
        conn, c = make_conn_c()
        q = c.execute("SELECT pwd_hash FROM USERS where name = '{0}';".format(name)
            ).fetchall()
        conn.close()
        if q:
            result = valid_pw(name, pwd, q[0][0])
            msg = '' if result else "The password and username doesn't match"
        else:
            result, msg = False, "The user dosen't exist."
    else:
        result, msg = False, 'Name is empty.'
    return result, msg

def update_pwd(uname, password):
    """
    Given a username and a password, update the credential db.
    Return a message. When successful, return ''
    """
    msg = 'Password updated successfully.'
    conn, c = make_conn_c()
    try:
        q = c.execute("UPDATE USERS SET pwd_hash = '{0}' WHERE name = '{1}';"
            .format(make_pw_hash(uname, password), uname))
        conn.commit()
    except:
        msg = 'Password Update failed.'
    conn.close()
    return msg

if __name__ == '__main__':
    choice = raw_input('Create credential DB?[y/n/new]: ')
    message = ''
    if choice.lower() in ('y', 'new'):
        connection, cursor = make_conn_c()
        message = 'Credential DB created successfully.'
        if choice.lower() == 'new':
            message = 'Credential DB re-created successfully.'
            cursor.execute('DROP TABLE USERS;')
        try:
            cursor.execute('CREATE TABLE USERS (id integer primary key AUTOINCREMENT, name text UNIQUE, pwd_hash text, email text, user_group text);')
            cursor.execute(INSERT_SQL.format('admin', make_pw_hash('admin', ADMIN_PW), 'dewei.zhai@kpn.com', 'admin'))
            cursor.execute(INSERT_SQL.format('martin.g', make_pw_hash('martin.g', HADMIN_PW), 'martin.groeneveld@kpn.com', 'human_admin'))
            cursor.execute(INSERT_SQL.format('martin.s', make_pw_hash('martin.s', EADMIN_PW), 'martin.swaen@kpn.com','element_admin'))
            connection.commit()
            names = cursor.execute("SELECT name from USERS;").fetchall()
            message += ' Credential contains following users:'
            for n in names:
                message += '\n%s' % n
            connection.close()
        except:
            message = "ERR: {}".format(sys.exc_info()[0])
    print message
