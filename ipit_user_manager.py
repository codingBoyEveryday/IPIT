#!/usr/bin/python
import sqlite3
import credential as crd

conn = sqlite3.connect('credential.db')
c = conn.cursor()

def show_all_users():
    """
    Used to print out all IPIT web users.
    """
    conn, c = crd.make_conn_c()
    user_list = c.execute('SELECT id, name, email, user_group FROM USERS').fetchall()
    conn.close()

    return user_list

    # Get the longest name and email
    # l_name = 4 # Title name is 4 letters
    # l_email = 5 # Title email is 5 letters
    # l_usergroup = 9



    # for row in user_list:
    #     l_name = len(row[0]) if len(row[0]) > l_name else l_name
    #     l_email = len(row[1]) if len(row[1]) > l_email else l_email
    #     l_usergroup = len(row[2]) if len(row[2]) > l_usergroup else l_usergroup

        # print row[0] + "*****" + row[1] + "*****" + row[2]

    # result = ""
    # result += "Name"+" "*(l_name-4) + " | Email" + " "*(l_email-5) + " | Usergroup"
    # result +=  "\n" + "_"*l_name + "_|_" + "_"*l_email + "_|_" + "_" * l_usergroup
    #
    # for row in user_list:
    #     result += "\n" + row[0]+ " "*(l_name-len(row[0])) + " | " + row[1] +" "*(l_email-len(row[1])) + " | " + row[2]
    #
    # return result


def get_user_info(user_id):

    """
    Get user info with user_id
    """
    conn, c = crd.make_conn_c()
    user_list = c.execute("SELECT name, email, user_group FROM USERS WHERE id = '{}';".format(user_id)).fetchall()
    conn.close()

    return user_list


def add_new_users(u_name, u_pwd, u_email, u_group):

    """
    Used to add a new user
    """
    try:
        crd.register_user(u_name, u_pwd, u_email, group= u_group)
        return "New user {0} added successfully.".format(u_name)
    except:
        return "Registering failed. Make sure the user name doesn't exist. "\
        "User group can only be: 'admin', 'human_admin', 'element_admin', 'test_manager', 'guest'"

def update_user(user_id, form):
    """
    Supporting function for page handler /user_<int:user_id>
    Used for updating a certain project.
    Inputs:
        user_id: int
        form: dictionary. Get from page request. It contains all info of the user.
    Outputs:
    """
    conn, c = crd.make_conn_c()
    c.execute("UPDATE USERS SET name = '{}', email = '{}', user_group = '{}' WHERE id = '{}';".format(form['name'], form['email'], form['group'], user_id))

    conn.commit()
    conn.close()


def del_user(u_name):
    """
    Used to delete a user.
    """
    conn, c = crd.make_conn_c()
    # Check if the user exists.
    user = c.execute("SELECT * FROM USERS WHERE name = '{}';".format(u_name)).fetchall()
    if not user:
        return "User {0} doesn't exist. Deleting failed.".format(u_name)
    c.execute("DELETE FROM USERS WHERE name = '{}';".format(u_name))
    try:
        conn.commit()
        conn.close()
        return "Deleting Successfully."
    except:
        conn.close()
        return "Deleting failed."

# if __name__ == '__main__':
#     working = True
#     print "Welcome to IPIT User manager. Here you can manage all account for IPIT 2.0"
#     while working:
#         msg =  "\n============================\n"
#         msg +=  "Please choose your action:\n"
#         msg += "1: Show all users\n"
#         msg += "2: Add a new user.\n"
#         msg += "3: Delete a user.\n"
#         msg += "4: Set a user's password.\n"
#         msg += "5: exit.\n"
#         msg += "============================"
#         print msg
#         choice = raw_input("> ")
#         if choice == '1':
#             print show_all_users()
#         elif choice == '2':
#             u_name = raw_input('User Name: ')
#             u_pwd = raw_input('Password: ')
#             u_email = raw_input('Email: ')
#             print "Valid gourps: admin, human_admin, element_admin, test_manager, guest"
#             u_group = raw_input('Group: ')
#             while u_group not in ['admin', 'human_admin', 'element_admin', 'test_manager', 'guest']:
#                 print "Usergroup name invalid."
#                 print "Please choose from: admin, human_admin, element_admin, test_manager, guest"
#                 u_group = raw_input('Group: ')
#             print add_new_users(u_name, u_pwd, u_email, u_group)
#         elif choice == '3':
#             u_name = raw_input('User Name: ')
#             print del_user(u_name)
#         elif choice == '4':
#             u_name = raw_input('User Name: ')
#             u_pwd = raw_input('Password: ')
#             print crd.update_pwd(u_name, u_pwd)
#         elif choice == '5':
#             working = False
#         else:
#             pass
#     a = get_user_info(32)
#     print a
#     print a[0][0]
#     print a[1]
#     print a[2]
