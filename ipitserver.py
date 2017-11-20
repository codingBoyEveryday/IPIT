#!/usr/bin/python
# -*- coding: UTF-8 -*- 
"""Running IPIT WebServer."""

import os
import csv
import xlsxwriter
import re

from datetime import datetime

from flask import Flask
from flask import render_template
from flask import request
from flask import make_response
from flask import redirect
from flask import send_file

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from werkzeug.contrib.fixers import ProxyFix # Added 24-Aug for Gunicorn

from database_setup import Base

from ipit_functions import normalize_db_value
from ipit_functions import allocation_plan
from ipit_functions import query_human_plan
from ipit_functions import query_element_plan
from ipit_functions import update_project
from ipit_functions import update_employee
from ipit_functions import gen_employee_list
from ipit_functions import gen_priority_list
from ipit_functions import gen_department_list
from ipit_functions import gen_project_list
from ipit_functions import gen_domain_list
from ipit_functions import add_project
from ipit_functions import del_project
from ipit_functions import gen_node_list
from ipit_functions import update_element
from ipit_functions import del_element_byid
from ipit_functions import get_element_byid
from ipit_functions import query_element_usages
from ipit_functions import add_element
from ipit_functions import add_employee
from ipit_functions import gen_element_list
from ipit_functions import gen_usages_list
from ipit_functions import is_valid_time_line
from ipit_functions import get_project_name_byid
from ipit_functions import gen_role_list
from ipit_functions import get_dept_name_byid
from ipit_functions import get_role_name_byid
from ipit_functions import is_valid_hour
from ipit_functions import update_project_human_plan
from ipit_functions import get_project_info
from ipit_functions import get_allocation_plan_by_prjid
from ipit_functions import update_human_allocation
from ipit_functions import gen_phu_report
from ipit_functions import gen_peu_report
from ipit_functions import get_employee_byid
from ipit_functions import is_valid_name
from ipit_functions import is_valid_email
from ipit_functions import is_valid_regnum
from ipit_functions import get_test_manager_email
from ipit_functions import is_valid_domain
from ipit_functions import is_valid_new_domain
from ipit_functions import is_valid_node
from ipit_functions import add_node
from ipit_functions import add_domain
from ipit_functions import gen_template_list
from ipit_functions import get_template
from ipit_functions import update_template
from ipit_functions import update_template_content
from ipit_functions import delete_template
from ipit_functions import gen_template_content
from ipit_functions import add_template
from ipit_functions import is_valid_year_week
from ipit_functions import get_tpl_content_by_name
from ipit_functions import get_tpl_content_by_project
from ipit_functions import update_element_plan
from ipit_functions import get_element_id
from ipit_functions import get_usage_id
from ipit_functions import filter_conflicts
from ipit_functions import summary_conflict_msg
from ipit_functions import get_change_request_info
from ipit_functions import gen_impact_list
from ipit_functions import gen_change_request_list
from ipit_functions import add_change_request
from ipit_functions import get_conflicted_elements
from ipit_functions import get_yw_by_date
from ipit_functions import gen_status_list
from ipit_functions import update_change_request
from ipit_functions import del_change_request
from ipit_functions import gen_applicant_list
from ipit_functions import is_valid_applicant
from ipit_functions import add_applicant
from ipit_functions import is_valid_date_time
from ipit_functions import valid_date
from ipit_functions import gen_request_report
from ipit_functions import get_employee_id
from ipit_functions import get_project_id
from ipit_functions import update_human_allocation_per_week
from ipit_functions import temp_phu_data
from ipit_functions import valid_hours_from_list
from ipit_functions import get_request_element_info
from ipit_functions import project_selected
from ipit_functions import impact_selected
from ipit_functions import del_applicant
from ipit_functions import valid_project_input
from ipit_functions import gen_element_id_list
from ipit_functions import convert_date_format
from ipit_functions import convert_dates_for_table
from ipit_functions import add_department
from ipit_functions import is_valid_department
from ipit_functions import del_department
from ipit_functions import update_department
from ipit_functions import del_node
from ipit_functions import get_node_id

from credential import is_valid_username
from credential import is_valid_password
from credential import register_user
from credential import login_user
from credential import verify_pwd
from credential import update_pwd
from credential import get_by_name
from credential import if_logged_in
from compiler.ast import nodes

from ipit_user_manager import show_all_users
from ipit_user_manager import add_new_users
from ipit_user_manager import del_user
from ipit_user_manager import get_user_info
from ipit_user_manager import update_user




# Flask app definition
app = Flask(__name__)
# In order to use python functions in Jinja2, they must be declared here.
app.jinja_env.globals.update(len=len)
app.jinja_env.globals.update(enumerate=enumerate)
app.jinja_env.globals.update(showNone=lambda s: "" if s is None else s)
app.wsgi_app = ProxyFix(app.wsgi_app) # Added 24-Aug for Gunicorn

# SQLALCHEMY Session maker for postgresql.
ENGINE = create_engine('postgresql://dewei:853852@localhost/ipit_db')
Base.metadata.bind = ENGINE
DBSession = sessionmaker(bind=ENGINE)

# Global Policy of user authorities.
GROUPS = ['admin', 'human_admin', 'element_admin', 'testmanager', 'test_manager', 'guest']

GROUPS_CAN_ADD_PROJECT = ['admin', 'human_admin', 'element_admin']
GROUPS_CAN_DEL_PROJECT = ['admin', 'human_admin']
GROUPS_CAN_MOD_PROJECT = ['admin', 'human_admin', 'element_admin']
GROUPS_CAN_ADD_EMPLOYEE = ['admin', 'human_admin']
GROUPS_CAN_MOD_EMPLOYEE = ['admin', 'human_admin']
GROUPS_CAN_ADD_ELEMENT = ['admin', 'element_admin']
GROUPS_CAN_MOD_ELEMENT = ['admin', 'element_admin']
GROUPS_CAN_DEL_ELEMENT = ['admin', 'element_admin']
GROUPS_CAN_MOD_ELEMENT_PLAN = ['admin', 'element_admin']
GROUPS_CAN_MOD_HUMAN_PLAN = ['admin', 'human_admin']
GROUPS_CAN_ALLOCATE_HUMAN = ['admin', 'human_admin']
GROUPS_CAN_ADD_ELEMENT_TEMPLATES = ['admin', 'element_admin']
GROUPS_CAN_MOD_ELEMENT_TEMPLATES = ['admin', 'element_admin']
GROUPS_CAN_DEL_ELEMENT_TEMPLATES = ['admin', 'element_admin']
GROUPS_CAN_ADD_CHANGE_REQUEST = ['admin', 'human_admin', 'element_admin', 'testmanager', 'test_manager']
GROUPS_CAN_DEL_CHANGE_REQUEST = ['admin', 'human_admin', 'element_admin', 'testmanager', 'test_manager']
GROUPS_CAN_MOD_CHANGE_REQUEST = ['admin', 'human_admin', 'element_admin', 'testmanager', 'test_manager']
GROUPS_CAN_ADD_MOD_DEL_HUMAN = ['admin', 'human_admin']
GROUPS_CAN_MOD_DEPARTMENT = ['admin', 'human_admin']
GROUPS_CAN_ADD_DEPARTMENT = ['admin', 'human_admin']
GROUPS_CAN_DEL_DEPARTMENT = ['admin', 'human_admin']
GROUPS_CAN_ADD_USER = ['admin', 'human_admin']
GROUPS_CAN_DEL_USER = ['admin', 'human_admin']
GROUPS_CAN_MOD_USER = ['admin', 'human_admin']

# define important element usages to define coloured rows in csv file
IMPORTANT_ELEMENT_USAGES = set(['Cfg aanp. + Test Uitv.', 'Software update',
    'software update + Testen', 'Training', 'Configuratie aanpassing'])

REQUEST_ELEMENTS = 4 # this number defines the amount of elements that can be added in a change request


# ============================== Page Handlers of pages: main, signup, login, set password ==========================
@app.route('/')
def main_page():
    """The handle for main page."""
    kwargs = {}
    kwargs['loggedin'], kwargs['user'], kwargs['group'] = if_logged_in(request)
    return render_template('main.html', **kwargs)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    # Initialize the page.
    kwargs = dict(username='', email='', name_error='', pwd_error='',
        email_error='')
    if request.method == 'POST':  # User hit the button and send a signup form.
        # Update variable set and verify inputs.
        kwargs['username'] = request.form['username']
        password = request.form['password']
        verify = request.form['verify']
        kwargs['email'] = request.form['email']
        valid_name, kwargs['name_error'] = is_valid_username(kwargs['username'])
        valid_pwd, kwargs['pwd_error'] = is_valid_password(password, verify)
        valid_email, kwargs['email_error'] = is_valid_email(kwargs['email'])

        # If all inputs are valid. Register the user and automatically log in.
        if valid_name and valid_pwd and valid_email:
            group = 'testmanager' if valid_email in get_test_manager_email(
                DBSession, 0) else 'guest'  # 0 means get all emails.
            register_user(valid_name, valid_pwd, valid_email, group=group)
            cookie_val = login_user(valid_name, valid_pwd)  # After signup, automatically login.
            response = make_response(redirect('/', 302))
            response.set_cookie('user_id', cookie_val)
            return response

    return render_template('signup.html',**kwargs)


@app.route('/login', methods=['GET', 'POST'])
def login():
    kwargs = dict(username='', name_error='', pwd_error='')
    if request.method == 'POST':
        kwargs['username'] = request.form['username']
        password = request.form['password']
        valid_name, kwargs['name_error'] = is_valid_username(kwargs['username'], check_type='login')
        cookie_val = login_user(valid_name, password)
        if cookie_val:  # login successful
            response = make_response(redirect('/', 302))
            response.set_cookie('user_id', cookie_val)
            return response

    return render_template('login.html',**kwargs)


@app.route('/logout')
def logout():
    response = make_response(redirect('/', 302))
    response.set_cookie('user_id', '')
    return response


@app.route('/set_pwd', methods=['GET', 'POST'])
def set_pwd():
    "Page Handler for setting password."

    kwargs = dict(old_pwd_error='', pwd_error='', up_msg='')
    kwargs['loggedin'], kwargs['user'], ugroup = if_logged_in(request)
    if not kwargs['loggedin']:
        return redirect('/')
    if request.method == 'POST':
        password = request.form['new']
        verify = request.form['verify']
        old_pwd_correct, kwargs['old_pwd_error'] = verify_pwd(kwargs['user'], request.form['old'])
        if old_pwd_correct:
            valid_pwd, kwargs['pwd_error'] = is_valid_password(password, verify)
            if valid_pwd:
                kwargs['up_msg'] = update_pwd(kwargs['user'], password)

    return render_template('set_pwd.html',**kwargs)


# ====================All Page Handlers for Projects =================================================================
@app.route('/projects', methods=['GET', 'POST'])
def projects():
    """The handler for '/projects'."""
    kwargs = {}
    kwargs['loggedin'], uname, ugroup = if_logged_in(request)
    kwargs['block_add'] = False if ugroup in GROUPS_CAN_ADD_PROJECT else True
    kwargs['block_del'] = False if ugroup in GROUPS_CAN_DEL_PROJECT else True
    data_list = get_project_info(DBSession)
    kwargs['data_list'] = convert_dates_for_table(data_list)
    if not kwargs['block_add'] and request.form.get('user_action') == 'new':
        return redirect("/new_project", 302)
    elif not kwargs['block_del'] and request.form.get('user_action') == 'del':
        return redirect("/del_project", 302)
    else:
        return render_template('projects.html', **kwargs)


@app.route('/project_<int:prj_id>', methods=['GET', 'POST'])
def project_single(prj_id):
    kwargs = {}
    kwargs['loggedin'], uname, ugroup = if_logged_in(request)
    kwargs['block_mod'] = False if ugroup in GROUPS_CAN_MOD_PROJECT else True
    # TODO: write function is_owner to link user to test manager.
    if get_by_name(uname, target='email') == get_test_manager_email(DBSession, prj_id):
        kwargs['block_mod'] = False
    kwargs['block_del'] = False if ugroup in GROUPS_CAN_DEL_PROJECT else True
    year, week = datetime.now().isocalendar()[:2] #[year, week]
    kwargs['time_line'] = [year, week, year, week]
    project_info = get_project_info(DBSession, prj_id)
    kwargs['project_info'] = convert_dates_for_table(project_info, one_row = True)
    kwargs['employee_list'] = gen_employee_list(DBSession)
    kwargs['priority_list'] = gen_priority_list(DBSession)
    kwargs['department_list'] = gen_department_list(DBSession)
    kwargs['domain_list'] = gen_domain_list(DBSession)
    kwargs['p_type'] = 'Human'
    kwargs['prj_id'] = prj_id
    kwargs['time_errors'] = [""] * 4
    if request.method == 'POST':
        if request.form.get('project_info'):
            if request.form.get('project_info') == 'Change' and not kwargs['block_mod']:  # User changed Project static information
                update_project(DBSession, prj_id, request.form)
                return redirect("/project_{0}".format(prj_id), 302)
            elif request.form.get('project_info') == 'Delete'and not kwargs['block_del']:  # User delete this project
                del_project(DBSession, kwargs['project_info'][0])
                return redirect("/projects", 302)
            else:
                return "Error: project_info takes invalid value."
        elif request.form.get('plan_info'):
            kwargs['p_type'] = request.form['plan_type']
            kwargs['time_line'] = [request.form['start_year'], request.form['start_week'],
                request.form['end_year'], request.form['end_week']]
            valid_time_line, kwargs['time_errors'] = is_valid_time_line(kwargs['time_line'])
            kwargs['time_filter'] = request.form.get('time_filter')
            if not valid_time_line:  # Jump out when the time line is not valid.
                return render_template('project_single.html', **kwargs)
            if request.form.get('plan_info') == 'Edit':  # User tries to edit project plan.
                if kwargs['p_type'] == "Human Allocation":
                    url_template = "/allocation_plan_edit_{0}_{1}_{2}_{3}_{4}_{5}_{6}"
                else:
                    url_template = "/plan_edit_{0}_{1}_{2}_{3}_{4}_{5}_{6}"
                if request.form.get('time_filter'):  # time_filter will be used in plan_edit
                    url = url_template.format(prj_id, kwargs['p_type'], True, *valid_time_line)
                else:
                    url = url_template.format(prj_id, kwargs['p_type'], False, *valid_time_line)
                return redirect(url, 302)
            elif kwargs['p_type'] == 'Human':  # Human Plan
                kwargs['data'], kwargs['column_names'] = query_human_plan(DBSession, prj_id, valid_time_line)
            elif kwargs['p_type'] == 'Element':  # Element Plan
                if request.form.get('time_filter'):
                    kwargs['data'], kwargs['column_names'] = query_element_plan(DBSession, prj_id, valid_time_line)
                else:
                    kwargs['data'], kwargs['column_names'] = query_element_plan(DBSession, prj_id)
            elif kwargs['p_type'] == 'Human Allocation':  # Human Allocation Plan
                kwargs['data'], kwargs['column_names'] = get_allocation_plan_by_prjid(DBSession, valid_time_line, prj_id)
            else:
                return "Oops, You should not see this page. There must be a bug. Tell Dewei"
        else:
            return "Error, expect plan_info/ project_info, but get neither."
    return render_template('project_single.html', **kwargs)


@app.route('/new_project', methods=['GET', 'POST'])
def new_project():
    kwargs = {}
    kwargs['loggedin'], uname, ugroup = if_logged_in(request)
    if ugroup not in GROUPS_CAN_ADD_PROJECT:
        return redirect("/", 302)
    kwargs['employee_list'] = gen_employee_list(DBSession)
    kwargs['priority_list'] = gen_priority_list(DBSession)
    kwargs['department_list'] = gen_department_list(DBSession)
    kwargs['domain_list'] = gen_domain_list(DBSession)
    kwargs['no_input_error'] = ['','','']
    if request.method=='POST':
        # First collect user inputs.
        kwargs['name'] = name = normalize_db_value(request.form['name'])
        kwargs['management'] = request.form['management']
        kwargs['test_manager'] = request.form['test_manager']
        # kwargs['implementation_manager'] = request.form['implementation_manager']
        kwargs['code'] = request.form['code']
        kwargs['priority'] = request.form['priority']
        kwargs['department'] = request.form['department']
        kwargs['domain'] = request.form['domain']
        kwargs['date_el'] = request.form['date_el']
        kwargs['note'] = request.form['note']
        kwargs['active'] = request.form.get('active')
        # Then verify the inputs
        valid_name, kwargs['result_msg'] = is_valid_name(kwargs['name'],
            name_list=gen_project_list(DBSession), is_project=True)
        valid_input, kwargs['no_input_error'] = valid_project_input(request.form)
        # Update DB if name is valid.
        if valid_name and valid_input:
            kwargs['up_msg'] = add_project(DBSession, request.form)
    return render_template('new_project.html', **kwargs)


# ====================All Page Handlers for Elements =================================================================
@app.route('/elements', methods=['GET', 'POST'])
def elements():
    """ The handle for '/elements'. """
    kwargs = {}
    kwargs['loggedin'], uname, ugroup = if_logged_in(request)
    kwargs['block_add'] = False if ugroup in GROUPS_CAN_ADD_ELEMENT else True
    kwargs['data'] = gen_element_list(DBSession, full=True)
    if request.form.get('user_action') == "new-domain" and not kwargs['block_add']:
        return redirect('/new_domain', 302)
    elif request.form.get('user_action') == "node_info" and not kwargs['block_add']:
        return redirect('/node_info', 302)
    elif request.form.get('user_action') == "new-element" and not kwargs['block_add']:
        return redirect('/new_element', 302)
    else:
        return render_template('elements.html', **kwargs)

@app.route('/element_<int:elmt_id>', methods=['GET', 'POST'])
def element_single(elmt_id):
    """
    Page handler for a single element's page.
    """
    kwargs = {}
    kwargs['loggedin'], uname, ugroup = if_logged_in(request)
    kwargs['block_mod'] = False if ugroup in GROUPS_CAN_MOD_ELEMENT else True
    kwargs['block_del'] = False if ugroup in GROUPS_CAN_DEL_ELEMENT else True
    kwargs['element'] = get_element_byid(DBSession, elmt_id)
    kwargs['node_list'] = gen_node_list(DBSession)
    year, week = datetime.now().isocalendar()[:2]
    kwargs['time_line'] = [year, week, year, week]
    kwargs['project_list'] = gen_project_list(DBSession, elmt_id=elmt_id)
    kwargs['time_errors'] = [''] * 4
    kwargs['up_msg'] = ''
    kwargs['elmt_id'] = elmt_id

    if request.form.get('user_action') == 'Change' and not kwargs['block_mod']:
        # TODO: add input detection. Judge if the input is correct.
        update_element(DBSession, elmt_id, request.form)  # TODO: Add update msg.
        # Refresh after update.
        kwargs['element'] = get_element_byid(DBSession, elmt_id)
    if request.form.get('user_action') == 'Delete' and not kwargs['block_del']:
        kwargs['up_msg'] =  del_element_byid(DBSession, elmt_id)
        if kwargs['up_msg'] == 'redirect':
            return redirect("/elements", 302)

    if request.form.get('plan_info') == "Query":
        kwargs['time_line'] = [request.form['str_y'], request.form['str_w'],
            request.form['end_y'], request.form['end_w']]
        valid_time_line, kwargs['time_errors'] = is_valid_time_line(kwargs['time_line'])
        kwargs['selected_project'] = request.form['project_name']
        kwargs['column_names'], kwargs['data'] = query_element_usages(
            DBSession, elmt_id, request.form) if valid_time_line else ([], [])

    return render_template('element_single.html', **kwargs)

@app.route('/new_domain', methods=['GET', 'POST'])
def new_domain():
    """
    Page handler for add new domain.
    """
    kwargs = {}
    kwargs['loggedin'], uname, ugroup = if_logged_in(request)
    kwargs['block_add'] = False if ugroup in GROUPS_CAN_ADD_ELEMENT else True
    kwargs['domain'] = ''
    if request.form.get('user_action') == 'Add' and not kwargs['block_add']:
        kwargs['domain'] = domain=normalize_db_value(request.form.get('domain'))
        valid_domain, kwargs['domain_error'] = is_valid_new_domain(DBSession, kwargs['domain'])
        if valid_domain:
            kwargs['up_msg'] = add_domain(DBSession, kwargs['domain'])
    return render_template('new_domain.html', **kwargs)

@app.route('/node_info', methods=['GET', 'POST'])
def node_info():
    """
    Page handler for add new node.
    """
    kwargs = {}
    kwargs['loggedin'], uname, ugroup = if_logged_in(request)
    kwargs['block_add'] = False if ugroup in GROUPS_CAN_ADD_ELEMENT else True
    kwargs['domain'] = None
    kwargs['domain_list'] = gen_domain_list(DBSession)
    kwargs['node_list'] = gen_node_list(DBSession)
    kwargs['node'] = ''
    kwargs['note'] = ''
    kwargs['domain_error'] = ''
    kwargs['node_error'] = ''
    kwargs['up_msg'] = ''
    if request.form.get('user_action') == 'Add' and not kwargs['block_add']:
        kwargs['domain'] = request.form.get('domain')
        valid_domain, kwargs['domain_error'] = is_valid_domain(DBSession, kwargs['domain'])
        kwargs['node'] = normalize_db_value(request.form.get('node'))
        valid_node, kwargs['node_error'] = is_valid_node(DBSession, kwargs['node'])
        kwargs['note'] = request.form.get('note')
        if valid_domain and valid_node:
            kwargs['up_msg'] = add_node(DBSession, request.form)
            kwargs['node_list'] = gen_node_list(DBSession)
    if request.form.get('user_action') == 'Delete' and not kwargs['block_add']:
        kwargs['delete_node'] = request.form.get('delete_node')
        node_id = get_node_id(DBSession, kwargs['delete_node'])
        kwargs['up_msg'] = del_node(DBSession, node_id)
        kwargs['node_list'] = gen_node_list(DBSession)
    return render_template('node_info.html', **kwargs)


@app.route('/new_element', methods=['GET', 'POST'])
def new_element():
    """
    Page handler for new elelment.
    """
    kwargs = {}
    kwargs['node_list'] = gen_node_list(DBSession)
    kwargs['loggedin'], uname, ugroup = if_logged_in(request)
    kwargs['block_add'] = False if ugroup in GROUPS_CAN_ADD_ELEMENT else True
    if request.form.get('user_action') == 'Add' and not kwargs['block_add']:
        kwargs['up_msg'] = add_element(DBSession, request.form)
    return render_template('new_element.html', **kwargs)

#======================= Page handler for element templates =========================================================
@app.route('/element_templates', methods=['GET', 'POST'])
def element_templates():
    """Shows list of all defined templates in IPIT"""
    kwargs = {}
    kwargs['loggedin'], uname, ugroup = if_logged_in(request)
    kwargs['block_add'] = False if ugroup in GROUPS_CAN_ADD_ELEMENT_TEMPLATES else True
    kwargs['data'] = gen_template_list(DBSession)
    if request.form.get('user_action') == "new" and not kwargs['block_add']:
        return redirect('/new_element_template')

    return render_template('element_templates.html', **kwargs)


@app.route('/element_template_<int:tpl_id>', methods=['GET', 'POST'])
def element_template_single(tpl_id):
    """Show a specific template. Provide editing and deleting buttons. Show result real time """

    kwargs = {}
    kwargs['loggedin'], uname, ugroup = if_logged_in(request)
    kwargs['block_mod'] = False if ugroup in GROUPS_CAN_MOD_ELEMENT_TEMPLATES else True
    kwargs['block_del'] = False if ugroup in GROUPS_CAN_DEL_ELEMENT_TEMPLATES else True
    kwargs['template_id'] = tpl_id
    kwargs['name_error'] = ''
    kwargs['up_msg'] = ''
    kwargs['selected_element'] = None
    kwargs['selected_usage'] = None
    kwargs['element_error'] = ''
    kwargs['element_list'] = gen_element_list(DBSession)
    kwargs['usages_list'] = gen_usages_list(DBSession)
    kwargs['column_names'] = ['Node', 'Hostname', 'Usage']
    kwargs['name'], kwargs['note'] = get_template(DBSession, tpl_id)
    if not kwargs['name']:
    # The tpl_id doesn't exit.
        return redirect('/element_templates')
    if request.form.get('user_action_sta') == 'Change' and not kwargs['block_mod']:
        # User wants to modify static information.
        kwargs['name'] = normalize_db_value(request.form.get('tpl_name'))
        kwargs['note'] = request.form.get('tpl_note')
        names_inuse = gen_template_list(DBSession, full=False)
        try:
            names_inuse.remove(kwargs['name']) # To allow user keep current template name unchanged.
        except ValueError:
            pass
        if not kwargs['name']:
            kwargs['name_error'] = "New name can't be empty."
        elif kwargs['name'] in names_inuse:
            kwargs['name_error'] = "This name is already in use"
        else:
            kwargs['up_msg'] = update_template(DBSession, tpl_id, kwargs['name'], kwargs['note'])
    elif request.form.get('user_action_sta') == 'Delete' and not kwargs['block_del']:
        #Delete the template
        delete_template(DBSession, tpl_id)
        return redirect('/element_templates')
    elif request.form.get('user_action_dyn') and not kwargs['block_mod']:
        # User wants to update the dynamic data.
        kwargs['selected_element'] = request.form.get('element')
        kwargs['selected_usage'] = request.form.get('usage')
        kwargs['up_msg'] = update_template_content(DBSession, tpl_id, request.form.get('user_action_dyn'),
            kwargs['selected_element'], kwargs['selected_usage'])

    kwargs['data'] = gen_template_content(DBSession, tpl_id)  # [(elmt_1, usg_1), (elmt_1, usg_1)]
    return render_template('template_single.html' ,**kwargs)

@app.route('/new_element_template', methods=['GET', 'POST'])
def new_element_template():
    """
    Page handler for adding a new element template.
    """

    kwargs = {}
    kwargs['loggedin'], uname, ugroup = if_logged_in(request)
    kwargs['block_add'] = False if ugroup in GROUPS_CAN_ADD_ELEMENT_TEMPLATES else True
    kwargs['name'] = ''
    kwargs['name_error'] = ''
    kwargs['note'] = ''
    if not kwargs['loggedin']:
        return redirect('/login')
    if request.method == 'POST':
        kwargs['name'] = normalize_db_value(request.form.get('tpl_name'))
        kwargs['note'] = request.form.get('tpl_note')
        names_inuse = gen_template_list(DBSession, full=False)
        if not kwargs['name']:
            kwargs['name_error'] = "New name can't be empty."
        elif kwargs['name'] in names_inuse:
            kwargs['name_error'] = "This name is already in use"
        else:
            kwargs['up_msg'] = add_template(DBSession, kwargs['name'], kwargs['note'])

    return render_template('new_element_template.html', **kwargs)

# ====================All Page Handlers for Employees =================================================================

@app.route('/employees', methods=['GET', 'POST'])
def employees():
    """The Handler for '/employees'."""
    kwargs = {}
    kwargs['loggedin'], uname, ugroup = if_logged_in(request)
    kwargs['block_add'] = False if ugroup in GROUPS_CAN_ADD_EMPLOYEE else True

    if request.method == "POST" and request.form['user_action'
    ] == "new-employee" and not kwargs['block_add']:
        return redirect('/new_employee', 302)
    else:
        kwargs['data'] = gen_employee_list(DBSession, contain_id=True, full=True,
            hide_sensitive=kwargs['block_add'])
        return render_template('employees.html', **kwargs)

@app.route('/new_employee', methods=['GET', 'POST'])
def new_employee():
    kwargs = {}
    kwargs['loggedin'], uname, ugroup = if_logged_in(request)
    if ugroup not in GROUPS_CAN_ADD_EMPLOYEE:
        return redirect('/', 302)
    kwargs['department_list'] = gen_department_list(DBSession)
    kwargs['contract_list'] = ['EP','AP','SoW','OP','Overig']
    if request.method == 'POST' and request.form['user_action'] == 'Add':
        valid_name, kwargs['name_error'] = is_valid_name(request.form.get('name'), name_list=gen_employee_list(DBSession))  # a name or None.
        valid_hour, kwargs['hour_error'] = is_valid_hour(request.form.get('hours'), h_max=40)
        valid_hours_avl, kwargs['hour_avl_error'] = is_valid_hour(request.form.get('hours_available'), h_max=40)
        valid_email, kwargs['email_error'] = is_valid_email(request.form.get('email'))
        valid_reg_num, kwargs['reg_num_error'] = is_valid_regnum(request.form.get('reg_num'))
        if not valid_name or not valid_hour or not valid_hours_avl or not valid_email or not valid_reg_num:
            form_valid = False
        else:
            form_valid = True
        # If valid, then add record to DB
        if form_valid:
            kwargs['up_msg'] = add_employee(DBSession, request.form)
    # make it possible for the application to remember the inputs if filled in
    input_fields = ['name', 'hours', 'hours_available', 'email', 'reg_num']
    for field in input_fields:
        if request.form.get(field):
            kwargs[field] = request.form.get(field)

    return render_template('new_employee.html', **kwargs)

@app.route('/employee_<int:emp_id>', methods=['GET', 'POST'])
def employee_single(emp_id):
    """ handler for '/employee_x' """
    # Initialization
    kwargs ={}
    kwargs['loggedin'], uname, ugroup = if_logged_in(request)
    kwargs['block_mod'] = False if ugroup in GROUPS_CAN_MOD_EMPLOYEE else True
    kwargs['employee'] = get_employee_byid(DBSession, emp_id, hide_sensitive=kwargs['block_mod'])  # List of all static info about the employee.
    kwargs['emp_id'] = emp_id
    kwargs['department_list'] = gen_department_list(DBSession)
    if "All test departments" in kwargs['department_list']:
        kwargs['department_list'].remove("All test departments")
    kwargs['contract_type_list'] = ['EP','AP','SoW','OP','Overig']
    kwargs['project_list'] = gen_project_list(DBSession, emp_id=emp_id)
    year, week = datetime.now().isocalendar()[:2]
    kwargs['time_line'] = [year, week, year, week]
    kwargs['time_errors'] = [''] * 4
    kwargs['hour_error'] = ''
    kwargs['hour_avl_error'] = ''
    kwargs['name_error'] = ''
    kwargs['email_error'] = ''
    kwargs['reg_num_error'] = ''
    kwargs['update_msg'] = ''
    if request.form.get('user_info') == "Change" and not kwargs['block_mod']:  # left form received.
        # Update kwargs
        kwargs['employee'][0] = normalize_db_value(request.form.get('name'))
        kwargs['employee'][1] = request.form.get('hours')
        kwargs['employee'][2] = request.form.get('hours_available')
        kwargs['employee'][3] = request.form.get('department')
        kwargs['employee'][4] = request.form.get('email')
        kwargs['employee'][5] = request.form.get('contract_type')
        kwargs['employee'][6] = request.form.get('registration_number')
        kwargs['employee'][7] = request.form.get('if_left')  # Add a new field.
        # Verify the input
        # Modification on 8-jan-2017
        # Issue, when modifying a user's attribute, below sentence will pop failure that the name is already in use. 
        # valid_name, kwargs['name_error'] = is_valid_name(kwargs['employee'][0], name_list=gen_employee_list(DBSession))
        # Solution: in the name list, remove the user's current name.
        ##
        name_lst = gen_employee_list(DBSession)
        cur_name = get_employee_byid(DBSession, emp_id)[0]
        try:
            name_lst.remove(cur_name)
        except ValueError:
            pass
        valid_name, kwargs['name_error'] = is_valid_name(kwargs['employee'][0], name_list=name_lst)  # a name or None.
        
        valid_hour, kwargs['hour_error'] = is_valid_hour(kwargs['employee'][1], h_max=40)
        valid_hours_avl, kwargs['hour_avl_error'] = is_valid_hour(kwargs['employee'][2], h_max=40)
        valid_email, kwargs['email_error'] = is_valid_email(kwargs['employee'][4])
        valid_reg_num, kwargs['reg_num_error'] = is_valid_regnum(kwargs['employee'][6])
        if not valid_name or not valid_hour or not valid_hours_avl or not valid_email or not valid_reg_num:
            form_valid = False
        else:
            form_valid = True
        # If valid, then update DB and kwargs
        if form_valid:
            kwargs['update_msg'] = update_employee(DBSession, emp_id, request.form)

    elif request.form.get('plan_info') == "Query": #right form received.
        # Update kwargs
        kwargs['time_line'] = [request.form['str_y'], request.form['str_w'],
            request.form['end_y'], request.form['end_w']]
        kwargs['project_name'] = request.form['project_name']
        # Check the validity
        valid_time_line, kwargs['time_errors'] = is_valid_time_line(kwargs['time_line'])
        if valid_time_line:
            kwargs['data'], kwargs['column_names'] = allocation_plan(emp_id, request.form, DBSession)  # TODO: update the function.
    elif request.form.get('plan_info') == "Edit":  # TODO: Enable Project-Human-Allocation plan edit on the employee page.
        return """<h2>Oops, this part has not been developed yet. If you wants to allocate an employee to project, please go to Project.</h2>"""

    return render_template('employee_single.html', **kwargs)

# ====================All Page Handlers for Departments =================================================================
@app.route('/departments', methods=['GET', 'POST'])
def departments():
    """ hander for /departments """
    kwargs = {}
    kwargs['loggedin'], uname, ugroup = if_logged_in(request)
    kwargs['block_mod'] = False if ugroup in GROUPS_CAN_MOD_DEPARTMENT else True
    kwargs['block_add'] = False if ugroup in GROUPS_CAN_ADD_DEPARTMENT else True
    kwargs['block_del'] = False if ugroup in GROUPS_CAN_DEL_DEPARTMENT else True
    kwargs['department_list'] = gen_department_list(DBSession)

    if request.method == 'POST':
        if request.form['user_action'] == 'Delete' and not kwargs['block_del']:  # possibility to delete department
            kwargs['up_msg'] = del_department(DBSession, request.form.get("delete_department"))
            kwargs['department_list'] = gen_department_list(DBSession)  # update department list

        if request.form['user_action'] == 'Add' and not kwargs['block_add']:  # possibility to add department
            valid_department, kwargs['new_department_error'] = is_valid_department(DBSession, request.form.get("new_department"))
            if valid_department:
                kwargs['up_msg'] = add_department(DBSession, normalize_db_value(request.form.get("new_department")))
                kwargs['department_list'] = gen_department_list(DBSession) # update department list

        if request.form['user_action'] == 'Change' and not kwargs['block_mod']:  # possibility to change name of department
            valid_department, kwargs['change_department_error'] = is_valid_department(DBSession, request.form.get("change_department_input"))
            if valid_department:
                kwargs['up_msg'] = update_department(DBSession, request.form.get("change_department_list"), request.form.get("change_department_input"))
                kwargs['department_list'] = gen_department_list(DBSession)  # update department list

    return render_template('departments.html', **kwargs)


# ====================All Page Handlers for ChangeRequests ============================================================

@app.route('/change_requests', methods=['GET', 'POST'])
def change_requests():
    """The handler for '/change_requests'."""
    kwargs = {}
    kwargs['loggedin'], uname, ugroup = if_logged_in(request)
    kwargs['block_add'] = False if ugroup in GROUPS_CAN_ADD_CHANGE_REQUEST else True
    kwargs['block_del'] = False if ugroup in GROUPS_CAN_DEL_CHANGE_REQUEST else True
    if get_by_name(uname, target='email') in get_test_manager_email(DBSession, 0):
        kwargs['block_add'] = False
    data_list = get_change_request_info(DBSession)
    kwargs['data_list'] = convert_dates_for_table(data_list)
    unique_requests = []
    for data in get_change_request_info(DBSession):
        unique_requests.append(data[0])
    kwargs['unique_requests'] = set(unique_requests)
    if not kwargs['block_add'] and request.form.get('user_action') == 'new':
        return redirect("/new_change_request", 302)
    else:
        return render_template('change_requests.html', **kwargs)

@app.route('/new_change_request', methods=['GET', 'POST'])
def new_change_request():
    kwargs = {}
    kwargs['loggedin'], uname, ugroup = if_logged_in(request)
    if get_by_name(uname, target='email') in get_test_manager_email(DBSession, 0):
        ugroup = 'test_manager'
    if ugroup not in GROUPS_CAN_ADD_CHANGE_REQUEST:
        return redirect("/", 302)
    kwargs['block_add'] = False if ugroup in GROUPS_CAN_ADD_CHANGE_REQUEST else True
    kwargs['project_list'] = gen_project_list(DBSession)
    kwargs['impact_list'] = gen_impact_list(DBSession)
    kwargs['element_list'] = gen_element_list(DBSession)
    kwargs['applicant_list'] = gen_applicant_list(DBSession)
    
    # initialize the input fields
    kwargs['description'] = ""
    kwargs['applicant'] = ""
    kwargs['project'] = ""
    kwargs['impact'] = ""
    kwargs['elements'] = ["","","",""]
    date_now = str(datetime.now())
    kwargs['start_dates'] = [convert_date_format(date_now.split(' ')[0])]*4
    kwargs['end_dates'] = [convert_date_format(date_now.split(' ')[0])]*4
    kwargs['start_times'] = ["","","",""]
    kwargs['end_times'] = ["","","",""]
    kwargs['notes'] = ["","","",""]
    kwargs['new_applicant'] = ""
    kwargs['time_errors'] = ""
    kwargs['date_time_errors'] = ""
    kwargs['project_error'] = ""
    kwargs['impact_error'] = ""
    
    if request.method=='POST':
        kwargs.update(get_request_element_info(REQUEST_ELEMENTS, request.form))
        
        if request.form['user_action'] == 'Add applicant' and not kwargs['block_add']: # possibility to add new applicant
             kwargs['new_applicant'] = new_applicant=normalize_db_value(request.form.get('new_applicant'))
             valid_applicant, kwargs['applicant_error'] = is_valid_applicant(DBSession, kwargs['new_applicant'])
             if valid_applicant:
                 kwargs['up_msg'] = add_applicant(DBSession, kwargs['new_applicant'])
                 kwargs['applicant_list'] = gen_applicant_list(DBSession) # new applicant is visible in applicant list
                 kwargs['applicant'] = request.form['new_applicant'] # select new applicant
                 
        elif request.form['user_action'] == 'Delete applicant' and not kwargs['block_add']: # possibility to delete applicant
            applicant_selected = True if request.form['applicant'] != '' else False
            if applicant_selected:
                kwargs['up_msg'] = del_applicant(DBSession, request.form['applicant'])
                kwargs['applicant'] = '' #empty the applicant field 
                kwargs['applicant_list'] = gen_applicant_list(DBSession) # refresh applicant list
        # First collect user inputs.
        elif request.form['user_action'] == 'Add' and not kwargs['block_add']:
             #validation of date/time depends on element
            valid_date_time, kwargs['date_time_errors'] = is_valid_date_time(kwargs['start_dates'], 
                        kwargs['start_times'], kwargs['end_dates'], kwargs['end_times'], kwargs['elements'])
             
            valid_name, kwargs['result_msg'] = is_valid_name(kwargs['description'],
                            name_list=gen_change_request_list(DBSession), is_project = True)
            selected_project, kwargs['project_error'] = project_selected(request.form)
            selected_impact, kwargs['impact_error'] =  impact_selected(request.form) 
        # Update DB if name and date/time are valid.
            if valid_name and valid_date_time and selected_project and selected_impact:
                element_ids = []
                for i in range(REQUEST_ELEMENTS):
                    if request.form['element_{}'.format(i)] != '':
                # for the time line, get the earliest start date and the latest end date
                        # date is converted to yyyy-mm-dd and back to evaluate its min and max value
                        kwargs['time_line'] =  get_yw_by_date(convert_date_format(min(convert_date_format(date) for date in kwargs['start_dates'] if date != '')), 
                                                              convert_date_format(max(convert_date_format(date) for date in kwargs['end_dates'] if date != ''))) #function returns [str_y, str_w, end_y, end_w]
                        valid_time_line, kwargs['time_errors'] = is_valid_time_line(kwargs['time_line'])
                        
                        element_id = get_element_id(DBSession, request.form['element_{}'.format(i)])
                        element_ids.append(element_id)
                kwargs['up_msg'] = add_change_request(DBSession, request.form)
                kwargs['data'], kwargs['column_names'] = get_conflicted_elements(DBSession, valid_time_line, element_ids)
                
    return render_template('new_change_request.html', **kwargs)

@app.route('/change_request_<int:req_id>', methods=['GET', 'POST'])
def change_request_single(req_id):
  
    kwargs = {}
    kwargs['loggedin'], uname, ugroup = if_logged_in(request)

    if get_by_name(uname, target='email') in get_test_manager_email(DBSession, 0):
        ugroup = 'test_manager'

    kwargs['block_mod'] = False if ugroup in GROUPS_CAN_MOD_CHANGE_REQUEST else True
    kwargs['block_del'] = False if ugroup in GROUPS_CAN_DEL_CHANGE_REQUEST else True
    
    kwargs['change_request_info'] = get_change_request_info(DBSession, req_id)
    kwargs['general_req_info'] = kwargs['change_request_info'][0]
    kwargs['status'] = kwargs['change_request_info'][0][11]
    kwargs['description'] = kwargs['change_request_info'][0][0]
    kwargs['applicant'] = kwargs['change_request_info'][0][1]
    kwargs['project'] = kwargs['change_request_info'][0][2]
    kwargs['impact'] = kwargs['change_request_info'][0][3]
    kwargs['project_list'] = gen_project_list(DBSession)
    kwargs['impact_list'] = gen_impact_list(DBSession)
    kwargs['element_list'] = gen_element_list(DBSession)
    kwargs['status_list'] = gen_status_list(DBSession)
    kwargs['applicant_list'] = gen_applicant_list(DBSession)
    kwargs['date_time_errors'] = ""
    kwargs['req_id'] = req_id
    
    start_dates = []
    end_dates = []
    start_times = []
    end_times = []
    notes = []
    elements = []
    for i in range(len(kwargs['change_request_info'])):
        elements.append('{0}:{1}'.format(kwargs['change_request_info'][i][4],kwargs['change_request_info'][i][5]))
        start_dates.append(convert_date_format(str(kwargs['change_request_info'][i][6])))
        start_times.append(kwargs['change_request_info'][i][7])
        end_dates.append(convert_date_format(str(kwargs['change_request_info'][i][8])))
        end_times.append(kwargs['change_request_info'][i][9])
        notes.append(kwargs['change_request_info'][i][10])

    kwargs['start_times'] = start_times
    kwargs['end_times'] = end_times
    kwargs['start_dates'] = start_dates
    kwargs['end_dates'] = end_dates
    kwargs['notes'] = notes
    kwargs['elements'] = elements
        
    if request.method == 'POST':
        if request.form.get('change_request_info'):
            
            kwargs.update(get_request_element_info(REQUEST_ELEMENTS, request.form))
            kwargs['status'] = request.form.get('status')
            
            # date is converted to yyyy-mm-dd and back to evaluate its min and max value
            kwargs['time_line'] =  get_yw_by_date(convert_date_format(min(convert_date_format(date) for date in kwargs['start_dates'] if date != '')), 
                                                  convert_date_format(max(convert_date_format(date) for date in kwargs['end_dates'] if date != '')))
            # verify the inputs
            valid_time_line, kwargs['time_errors'] = is_valid_time_line(kwargs['time_line'])
            
            valid_date_time, kwargs['date_time_errors'] = is_valid_date_time(kwargs['start_dates'], 
                        kwargs['start_times'], kwargs['end_dates'], kwargs['end_times'], kwargs['elements'])
            
            name_list=gen_change_request_list(DBSession)
            name_list.remove(kwargs['change_request_info'][0][0])
            valid_name, kwargs['result_msg'] = is_valid_name(kwargs['description'],
                           name_list , is_project = True)
            
            if request.form.get('change_request_info') == 'Change' and not kwargs['block_mod']:  # User  Changes this Change Request
                # Update DB if name and date/time are valid.
                if valid_date_time and valid_name:
                    kwargs['up_msg']  = update_change_request(DBSession, req_id, request.form)
            elif request.form.get('change_request_info') == 'Query':
                
                element_ids = []
                for i in range(REQUEST_ELEMENTS):
                    if request.form['element_{}'.format(i)] != '':
                        element_id = get_element_id(DBSession, request.form['element_{}'.format(i)])
                        element_ids.append(element_id)
                kwargs['data'], kwargs['column_names'] = get_conflicted_elements(DBSession, valid_time_line, element_ids)
            elif request.form.get('change_request_info') == 'Delete'and not kwargs['block_del']:  # User delete this Change Request
                del_change_request(DBSession, kwargs['req_id'])
                return redirect("/change_requests", 302)
            else:
                return "Error: change_request_info takes invalid value."
    return render_template('change_request_single.html', **kwargs)

# ====================All Page Handlers for Plan editing ==============================================================

@app.route('/plan_edit_<int:prj_id>_<string:p_type>_<string:time_filter>_<int:str_y>_<int:str_w>_<int:end_y>_<int:end_w>',
    methods = ['GET', 'POST'])
def plan_edit(prj_id, p_type, time_filter, str_y, str_w, end_y, end_w):
    """
    Description:
        Given a project ID, a time line, and a plan type (human or element)
        render a page allowing user to edit a element allocation plan.
        With that plan, update ipit DB, table "ProjectElementUsages"
        The edit result will be shown in the same page.
        5-Sept: Also enables the user to change project in the same page.
    Input:
        prj_id: Integer
        time_filter: True or False 
        str_y, str_w, end_y, end_w,
        p_type: Human or Element
    """
    # Common initialization
    kwargs = {}
    kwargs['loggedin'], uname, ugroup = if_logged_in(request)
    kwargs['prj_id'] = prj_id
    kwargs['time_line'] = [str_y, str_w, end_y, end_w] # default time line
    kwargs['project_name'] = get_project_name_byid(DBSession, prj_id)
    kwargs['project_list'] = gen_project_list(DBSession, contain_id=True)
    kwargs['time_errors'] = [''] * 4
    kwargs['p_type'] = p_type
    kwargs['update_msg'] = ""

    if p_type == "Element":
        # initialize special fields for element plan edit
        kwargs['block_mod'] = False if ugroup in GROUPS_CAN_MOD_ELEMENT_PLAN else True
        if get_by_name(uname, target='email') == get_test_manager_email(DBSession, prj_id):
            kwargs['block_mod'] = False
        # TODO, make ownership check, if a guest owns a project, he can edit plan.
        # if not kwargs['block_mod'] and is_owner(DBSession, prj_id, uname):
        #  kwargs['block_mod'] = False
        # This is_owner() function checks if the uname in credential.db mapped to an employee_id in ipit_db
        # If it maps, check if the employee is the test_manager of that project. Return True if both are true.
        kwargs['time_filter'] = request.form.get('time_filter')
        kwargs['element_list'] = gen_element_list(DBSession)
        kwargs['usages_list'] = gen_usages_list(DBSession)
        kwargs['template_list'] = gen_template_list(DBSession, full = False)

        kwargs['cp_time'] = ['','']
        kwargs['selected_project'] = None
        kwargs['cp_errors'] = ['', '']
        change = False

        if request.method == 'POST' and not kwargs['block_mod']:
            # Update the kwargs with user choices.
            kwargs['time_line'] = [request.form['str_y'], request.form['str_w'],
                request.form['end_y'], request.form['end_w']]
                # Note, all string val
            kwargs['cp_time'] = [request.form['cp_year'], request.form['cp_week']]  # All string val
            valid_time_line, kwargs['time_errors'] = is_valid_time_line(kwargs['time_line'])
            kwargs['selected_element'] = request.form['element']
            kwargs['selected_usage'] = request.form['usage']
            kwargs['selected_template'] = request.form['template']
            kwargs['selected_project'] = [request.form['copy_project'],
                get_project_name_byid(DBSession, request.form['copy_project'])]  # [Prj_id, prj_name]

            if valid_time_line:
                delete = False
                if request.form['user_action'] == 'Change':
                    # First way of updating Project Element Plan: specify one element and its usage.
                    # We form a fake tamplate.
                    target_tpl = [
                        (get_element_id(DBSession, kwargs['selected_element']),
                         get_usage_id(DBSession, kwargs['selected_usage'])
                        )]
                    change = True
                elif request.form['user_action'] == 'Change all':
                    # Second way: specify a predefined element template
                    target_tpl = get_tpl_content_by_name(
                        DBSession, kwargs['selected_template'])
                
                elif request.form['user_action'] == 'Copy':
                    # Third way: by copying a project's certain week.

                    # check if the copy year and week is valid.
                    valid_cp_time, kwargs['cp_errors'] = is_valid_year_week(*kwargs['cp_time'])
                    if valid_cp_time:
                        # Copy from another project.
                        target_tpl = get_tpl_content_by_project(DBSession, kwargs['selected_project'][0], valid_cp_time)
                    else:
                        target_tpl = []
                    
                    if len(target_tpl) == 0:
                        kwargs['no_records_error'] = "No records to copy"
                        
                elif request.form['user_action'] == 'Delete':
                    # delete existing usages from selected fields
                        target_tpl = [
                        (get_element_id(DBSession, kwargs['selected_element']),
                         get_usage_id(DBSession, kwargs['selected_usage'])
                        )]
                        delete = True

                elif request.form['user_action'] == 'Delete all':
                    # delete all from a specified element template
                    target_tpl = get_tpl_content_by_name(
                        DBSession, kwargs['selected_template'])
                    delete = True
                    
                # Allow user to just query the plan.
                if request.form['user_action'] != 'Query':
                    kwargs['update_msg'] = update_element_plan(
                            DBSession, kwargs['prj_id'], valid_time_line, target_tpl, delete = delete)
                else:
                    kwargs['update_msg'] = "SUCCESSFUL query."

        if kwargs['update_msg'].startswith('SUCCESSFUL query'): # execute this statement when user action is query
            kwargs['data'], kwargs['column_names'] = query_element_plan(
                        DBSession, kwargs['prj_id'], valid_time_line)
        elif kwargs['update_msg'].startswith('SUCCESSFULL'): # execute this statement after an update
            kwargs['data'], kwargs['column_names'] = query_element_plan(
                        DBSession, kwargs['prj_id'])
        
        # execute this statements when no query or update is executed yet (update_msg = "")    
        elif time_filter == "True": 
            kwargs['data'], kwargs['column_names'] = query_element_plan(
                DBSession, prj_id, kwargs['time_line'])
        else:
            kwargs['data'], kwargs['column_names'] = query_element_plan(DBSession, prj_id)
        
        if change == True:
            kwargs['element_ids'] = gen_element_id_list(DBSession, kwargs['data'])
            kwargs['selected_element_id'] = str(get_element_id(DBSession, request.form['element']))
        else:
            kwargs['element_ids'] = ['']*len(kwargs['data'])
            kwargs['selected_element_id'] = 0
            
        return render_template('element_plan_edit.html', **kwargs)
    else:  # Human Plan
        # Initialize special kwargs for Human Plan edit.
        kwargs['block_mod'] = False if ugroup in GROUPS_CAN_MOD_HUMAN_PLAN else True
        if get_by_name(uname, target='email') == get_test_manager_email(DBSession, prj_id):
            kwargs['block_mod'] = False
        # TODO, make ownership check, if a guest owns a project, he can edit plan.
        # if if not kwargs['block_mod'] and is_owner(DBSession, prj_id, uname):
        #     kwargs['block_mod'] = False
        # This is_owner() function checks if the uname in credential.db mapped to an employee_id in ipit_db
        # If it maps, check if the employee is the test_manager of that project. Return True if both are true.
        kwargs['hour_error'] = ''
        kwargs['department_list'] = gen_department_list(DBSession, contain_id=True)
        kwargs['role_list'] = gen_role_list(DBSession, contain_id=True)
        kwargs['data'], kwargs['column_names'] = query_human_plan(DBSession, kwargs['prj_id'], kwargs['time_line'])

        # If POST, process user request then update kwargs
        if request.method == 'POST':
            # read user input, updates the kwargs.
            fm = request.form
            kwargs['prj_id'] = fm['project']
            kwargs['time_line'] = [fm['str_y'], fm['str_w'], fm['end_y'], fm['end_w']]
            valid_time_line, kwargs['time_errors']  = is_valid_time_line(kwargs['time_line'])
            kwargs['hour'] = fm['hour']
            valid_hour, kwargs['hour_error'] = is_valid_hour(kwargs['hour']) #None or float\
            kwargs['project_name'] = get_project_name_byid(DBSession, kwargs['prj_id'])
            kwargs['selected_dept_id'] = fm['department']
            kwargs['selected_dept'] = get_dept_name_byid(DBSession, kwargs['selected_dept_id'])
            kwargs['selected_role_id'] = fm['role']
            kwargs['selected_role'] = get_role_name_byid(DBSession, kwargs['selected_role_id'])
            # If the user chosen time line and hours are valid, update the DB
            if valid_time_line and valid_hour is not None:
                sub_kwargs = {}
                sub_kwargs['project_id'] = kwargs['prj_id']
                sub_kwargs['role_id'] = kwargs['selected_role_id']
                sub_kwargs['department_id'] = kwargs['selected_dept_id']
                sub_kwargs['time_line'] = valid_time_line
                sub_kwargs['hours'] = valid_hour
                kwargs['update_msg'] = update_project_human_plan(DBSession, **sub_kwargs)
                # After update DB, if successful, refresh the table to show.
                if kwargs['update_msg'].startswith("SUC"):
                    kwargs['data'], kwargs['column_names'] = query_human_plan(
                        DBSession, kwargs['prj_id'], valid_time_line)

        #Return an HTML page.
        return render_template("human_plan_edit.html", **kwargs)

@app.route('/allocation_plan_edit_<int:prj_id>_<string:p_type>_<int:str_y>_<int:str_w>_<int:end_y>_<int:end_w>',
    methods = ['GET', 'POST'])
def allocation_plan_edit(prj_id, p_type, str_y, str_w, end_y, end_w):
    # Initializa kwargs.
    kwargs = {}
    kwargs['loggedin'], uname, ugroup = if_logged_in(request)
    kwargs['block_mod'] = False if ugroup in GROUPS_CAN_ALLOCATE_HUMAN else True
    kwargs['p_type'] = p_type
    kwargs['time_line'] = [str_y, str_w, end_y, end_w]
    kwargs['time_errors'] = ""
    kwargs['hour_error'] = ""
    kwargs['selected_project'] = (prj_id, get_project_name_byid(DBSession, prj_id))
    kwargs['project_list'] = gen_project_list(DBSession, contain_id=True)
    kwargs['employee_list'] = gen_employee_list(DBSession, contain_id=True)
    kwargs['selected_role'] = (3, 'Tester')
    kwargs['role_list'] = gen_role_list(DBSession, contain_id=True)
    kwargs['note'] = ""
    kwargs['update_msg'] = ""
    kwargs['data'], kwargs['column_names'] = get_allocation_plan_by_prjid(DBSession, kwargs['time_line'], prj_id)

    if request.method == 'POST':
        fm = request.form
        kwargs['time_line'] = [fm['str_y'], fm['str_w'], fm['end_y'], fm['end_w']]
        kwargs['selected_project'] = eval(fm['project'])  # fm['project'] is pure string like u"(97, u'Mobile Voice Recording')".
        kwargs['selected_role'] = eval(fm['role'])
        kwargs['selected_employee'] = eval(fm['employee'])
        kwargs['hour'] = fm['hour']
        kwargs['note'] = fm['note']
        valid_time_line, kwargs['time_errors'] = is_valid_time_line(kwargs['time_line'])
        valid_hour, kwargs['hour_error'] = is_valid_hour(kwargs['hour'], h_max=40)
        if valid_time_line and (valid_hour is not None):
            kwargs['update_msg'] = update_human_allocation(DBSession, valid_time_line, valid_hour,
                kwargs['selected_project'][0], kwargs['selected_role'][0],
                kwargs['selected_employee'][0], fm['note'])
            if kwargs['update_msg'].startswith('SUC'):
                kwargs['data'], kwargs['column_names'] = get_allocation_plan_by_prjid(
                    DBSession, valid_time_line, kwargs['selected_project'][0])

    return render_template('allocation_plan_edit.html', **kwargs)

# ====================All Page Handlers for Reports =================================================================

@app.route('/reports', methods=['GET', 'POST'])
def reports():
    """Handeler for '/reports'"""
    kwargs={}
    kwargs['loggedin'], uname, ugroup = if_logged_in(request)
    kwargs['project_list'] = gen_project_list(DBSession, contain_id=True)
    year, week = datetime.now().isocalendar()[:2]
    kwargs['time_line'] = [year, week, year, week]
    kwargs['report_type'] = 'peu'  # Default report type
    kwargs['selected_project'] = (0, 'All Projects')
    kwargs['time_errors'] = [''] * 4
    kwargs['employee_list'] = gen_employee_list(DBSession)
    kwargs['edit'] = False
    kwargs['editable'] = False
    kwargs['calculate'] = False
    kwargs['block_mod'] = False if ugroup in GROUPS_CAN_ADD_MOD_DEL_HUMAN else True
    if request.method == 'POST':
        kwargs['selected_project'] = eval(request.form['selected_project'])
        kwargs['time_line'] = [request.form['str_y'], request.form['str_w'],
                request.form['end_y'], request.form['end_w']]
        kwargs['report_type'] = request.form['report_type']
        if kwargs['report_type'] == 'phru':
            kwargs['employee'] = request.form['employee']
        valid_time_line, kwargs['time_errors'] = is_valid_time_line(kwargs['time_line'])
        if valid_time_line:
            kwargs['rep'] = str(kwargs['selected_project'][0]
                ) + '_' +'_'.join(map(str,valid_time_line))  # /p[e|h]u_<int:prj_id>_<int:str_y>_<int:str_w>_<int:end_y>_<int:end_w>
            if kwargs['report_type'] == 'peu' and request.form['user_action'] == 'Query':  # project element usage
                kwargs['rep'] = '/peu_' + kwargs['rep']
                kwargs['data'], kwargs['column_names'], kwargs['update_msg'
                    ] = gen_peu_report(DBSession, kwargs['rep'])
            elif kwargs['report_type'] == 'phu' and request.form['user_action'] == 'Query':  # Project human usage
                kwargs['rep'] = '/phu_' + kwargs['rep']
                kwargs['data'], kwargs['column_names'], kwargs['update_msg'
                    ] = gen_phu_report(DBSession, kwargs['rep'])
            elif kwargs['report_type'] == 'pcu' and request.form['user_action'] == 'Query': # project element usage conflicts
                kwargs['rep'] = '/pcu_' + kwargs['rep']
                kwargs['data'], kwargs['column_names'], kwargs['update_msg'
                    ] = gen_peu_report(DBSession, '/peu_' + kwargs['rep'][5:])
                kwargs['data'] = filter_conflicts(kwargs['data'], report_type = 'pcu')  # pcu vs peu, the difference is that pcu apply an extra filter.
                kwargs['update_msg'] = summary_conflict_msg(kwargs['update_msg'], kwargs['data'], contain_id=True)  # Update the message.
            elif kwargs['report_type'] == 'pwu' and request.form['user_action'] == 'Query': # (Project) weekly element report
                kwargs['rep'] = '/pwu_' + kwargs['rep']
                kwargs['data'], kwargs['column_names'], kwargs['update_msg'
                    ] = gen_peu_report(DBSession, '/peu_' + kwargs['rep'][5:])
                kwargs['data'] = filter_conflicts(kwargs['data'], report_type = 'pwu')  # pcu vs pwu, the difference is that pwu contains all possible conflict usages (even if there isn's a conflict).
                kwargs['update_msg'] = summary_conflict_msg(kwargs['update_msg'], kwargs['data'], contain_id=True)  # Update the message.
            elif kwargs['report_type'] == 'pru' and request.form['user_action'] == 'Query': # Change Request Report
                kwargs['rep'] = '/pru_' + kwargs['rep']
                kwargs['data'], kwargs['column_names'], kwargs['update_msg'
                    ] = gen_request_report(DBSession, kwargs['rep'])
            elif kwargs['report_type'] == 'phru':  # Human Resources
                if not request.form['employee']:
                    kwargs['employee_error'] = "Please select an employee"
                    kwargs['rep'] = None
                elif request.form['user_action'] == "Edit":
                    kwargs['editable'] = True
                    kwargs['calculate'] = True if kwargs['selected_project'][0] == 0 else False
                    kwargs['rep'] = '/phru_' + kwargs['rep']
                    kwargs['employee'] = request.form['employee']
                    empl_id = get_employee_id(DBSession, kwargs['employee'])
                    kwargs['data'], kwargs['column_names'], kwargs['update_msg'
                        ] = gen_phu_report(DBSession, kwargs['rep'], employee_id = empl_id)
                    if not kwargs['data']:
                        kwargs['edit_error'] = "No data to edit"
                        kwargs['editable'] = False
                        kwargs['edit'] = True
                    return render_template('reports.html', **kwargs)
                
                elif request.form['user_action'] == "Save":
                    kwargs['edit'] = True
                    kwargs['rep'] = '/phru_' + kwargs['rep']
                    kwargs['employee'] = request.form['employee']
                    empl_id = get_employee_id(DBSession, kwargs['employee'])
                    valid_hours, hour_errors = valid_hours_from_list(request.form)    
                    if not None in valid_hours: #only write to db when hours are valid
                        kwargs['update_msg'] = update_human_allocation_per_week(DBSession, valid_hours, 
                                                                            empl_id, kwargs['selected_project'], valid_time_line )
                        kwargs['data'], kwargs['column_names'], kwargs['msg']  = gen_phu_report(DBSession, kwargs['rep'], employee_id = empl_id)
                        return render_template('reports.html', **kwargs)
                    else: # invalid hours are detected 
                        kwargs['edit'] = False
                        kwargs['calculate'] = True if kwargs['selected_project'][0] == 0 else False
                        kwargs['editable'] = True
                        kwargs['hour_error'] = next((error for error in hour_errors if error is not ''), '')
                        kwargs['data'], kwargs['column_names'], kwargs['msg']  = gen_phu_report(DBSession, kwargs['rep'], employee_id = empl_id)
                        kwargs['data'] = temp_phu_data(DBSession, kwargs['data'], request.form.getlist('hour_input'), valid_time_line, kwargs['selected_project'])
                        return render_template('reports.html', **kwargs)
                    
                elif request.form['user_action'] == 'Calculate':
                    kwargs['editable'] = True
                    kwargs['calculate'] = True if kwargs['selected_project'][0] == 0 else False
                    kwargs['rep'] = '/phru_' + kwargs['rep']
                    kwargs['employee'] = request.form['employee']
                    empl_id = get_employee_id(DBSession, kwargs['employee'])
                    valid_hours, hour_errors = valid_hours_from_list(request.form) 
                    if not None in valid_hours: #only only calculate hours when they are valid
                        kwargs['data'], kwargs['column_names'], kwargs['msg']  = gen_phu_report(DBSession, kwargs['rep'], employee_id = empl_id)
                        kwargs['data'] = temp_phu_data(DBSession, kwargs['data'], request.form.getlist('hour_input'), valid_time_line, kwargs['selected_project'], calculate_diff = True)
                        return render_template('reports.html', **kwargs)
                    else: #invalid hours detected
                        kwargs['hour_error'] = next((error for error in hour_errors if error is not ''), '')
                        kwargs['data'], kwargs['column_names'], kwargs['msg']  = gen_phu_report(DBSession, kwargs['rep'], employee_id = empl_id)
                        kwargs['data'] = temp_phu_data(DBSession, kwargs['data'], request.form.getlist('hour_input'), valid_time_line, kwargs['selected_project'])
                        return render_template('reports.html', **kwargs)
                    
                elif request.form['user_action'] == 'Query':
                    kwargs['edit'] = True
                    kwargs['rep'] = '/phru_' + kwargs['rep']
                    kwargs['employee'] = request.form['employee']
                    empl_id = get_employee_id(DBSession, kwargs['employee'])
                    kwargs['data'], kwargs['column_names'], kwargs['update_msg'
                        ] = gen_phu_report(DBSession, kwargs['rep'], employee_id = empl_id)
                    return render_template('reports.html', **kwargs)

    return render_template('reports.html', **kwargs)

@app.route('/p<string:ehcwr>u_<string:prj_id>_<string:str_y>_<string:str_w>_<string:end_y>_<string:end_w>')
def down_pehu_report(ehcwr, prj_id, str_y, str_w, end_y, end_w):
    """
    The handler for downloading a Project Element/Human Usages report.
    Inputs:
        -ehcwr: string, value is e, h or c. e means peu, h means phu, c means pcu, w means pwu
        -prj_id the project ID in table Projects.
        -str_y, str_w, end_y, end_w: starting and ending year and weeks.
    Returns:
        A XLSX file, utf-8 without BOM coded.
    """

    # Get the query info.
    if ehcwr == "e":
        rep = '/peu_' + '_'.join([prj_id, str_y, str_w, end_y, end_w])
        data, csv_header, msg = gen_peu_report(DBSession, rep, contain_id=False)
    elif ehcwr=='h':
        rep = '/phu_' + '_'.join([prj_id, str_y, str_w, end_y, end_w])
        data, csv_header, msg = gen_phu_report(DBSession, rep, contain_id=False)
    elif ehcwr == 'c':
        rep = '/peu_' + '_'.join([prj_id, str_y, str_w, end_y, end_w])
        data, csv_header, msg = gen_peu_report(DBSession, rep, contain_id=False)
        data = filter_conflicts(data, contain_id=False)
    elif ehcwr == 'w':
        rep = '/pwu_' + '_'.join([prj_id, str_y, str_w, end_y, end_w])
        data, csv_header, msg = gen_peu_report(DBSession, rep, contain_id=False)
        data = filter_conflicts(data, contain_id=False, report_type = 'pwu')
        cr_data, cr_csv_header, cr_msg = gen_request_report(DBSession, '/pru_' + rep[5:], contain_id=False)
    elif ehcwr == 'r':
        rep = '/pru_' + '_'.join([prj_id, str_y, str_w, end_y, end_w])
        data, csv_header, msg = gen_request_report(DBSession, rep, contain_id=False)

    # Generate the file
    project_name = get_project_name_byid(DBSession, prj_id, zero_name='AllProject')
    if ehcwr == 'e':
        filename = '_'.join(
            ['ProjectElementUsages', project_name, str_y, str_w, end_y, end_w])
    elif ehcwr == 'h':
         filename = '_'.join(
            ['ProjectHumanUsages', project_name, str_y, str_w, end_y, end_w])
    elif ehcwr == 'c':
        filename = '_'.join(
           ['ProjectElementConflicts', project_name, str_y, str_w, end_y, end_w])
    elif ehcwr == 'w':
        filename = '_'.join(
           ['WeeklyElementReport', project_name, str_y, str_w, end_y, end_w])
        cr_filename = '_'.join(
            ['ChangeRequests', project_name, str_y, str_w, end_y, end_w])
        cr_title = "{0} / {1} ({2}-{3} - {4}-{5})".format(cr_filename.split('_')[0], project_name,
                                                          str_w, str_y, end_w, end_y)
    elif ehcwr == 'r':
        filename = '_'.join(
           ['ChangeRequests', project_name, str_y, str_w, end_y, end_w])
        
    title = "{0} / {1} ({2}-{3} - {4}-{5})".format(filename.split('_')[0], project_name, 
            str_w,  str_y, end_w, end_y)
    filename = re.sub('[~!@#$%^&*()/?:;{}.<>=+]', '', filename) #remove signs from filename (they may cause a crash of the application)
    filename = filename.replace(' ', '') #remove spaces in the filename
    filename += '.xlsx'
    absfilename = os.path.abspath('static\\user_reports\\'+ filename)

    # Open a xlsx workbook with one worksheet
    workbook = xlsxwriter.Workbook(absfilename)
    worksheet = workbook.add_worksheet()
    
     #  first write the title
    format = workbook.add_format()
    format.set_font_size(15)
    worksheet.write(0,0, title, format)
    
    #write the header line bold
    format = workbook.add_format()
    format.set_bold()
    worksheet.write_row(1, 0, csv_header, format)  
    
    if ehcwr == 'w':  # for weekly element report, write blank line between two different hostnames
        count = 0
        for a_row in data:
            if count < 1:
                pre_row = a_row[2]
            cur_row = a_row[2]  # compares hostname with previous hostname
            if cur_row != pre_row:
                count += 1 # no row is written
            pre_row = cur_row
            row_coloured = False
            for cel in a_row:
                if cel in IMPORTANT_ELEMENT_USAGES: # colour the background of important element usages 
                    format = workbook.add_format()
                    format.set_bg_color('FAB958')
                    worksheet.write_row(count+2, 0, a_row, format)
                    row_coloured = True
            if row_coloured == False:
                worksheet.write_row(count+2, 0, a_row)
            count += 1

        # make an extra worksheet with CR report for WeeklyElementReport
        worksheet2 = workbook.add_worksheet()

        #  first write the title
        format = workbook.add_format()
        format.set_font_size(15)
        worksheet2.write(0, 0, cr_title, format)

        # write the header line bold
        format = workbook.add_format()
        format.set_bold()
        worksheet2.write_row(1, 0, cr_csv_header, format)

        # now add change request report to second worksheet (with a white line after a new description)
        count = 0
        for row in cr_data:
            if count < 1:
                pre_row = row[0]
            cur_row = row[0]  # compares Change request description with previous CR description
            if cur_row != pre_row:
                count += 1 # no row is written
            pre_row = cur_row
            worksheet2.write_row(count + 2, 0, row)
            count += 1

    elif ehcwr == 'r': #Change request report also with a withline between different descriptions
        count = 0
        for row in data:
            if count < 1:
                pre_row = row[0]
            cur_row = row[0]  # compares Change request description with previous CR description
            if cur_row != pre_row:
                count += 1  # no row is written
            pre_row = cur_row
            worksheet.write_row(count + 2, 0, row)
            count += 1

    elif ehcwr == 'h': #human usage report with colored cells
        count = 0
        format_red = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
        format_green = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'})
        for a_row in data:
            worksheet.write_row(count + 2, 0, a_row)
            if a_row[6] == 'Difference':
                worksheet.conditional_format(count + 2, 7, count + 2, 7, {'type': 'cell', 'criteria': '<', 'value': 0, 'format': format_red})
                worksheet.conditional_format(count + 2, 7, count + 2, 7, {'type': 'cell', 'criteria': '>', 'value': 0, 'format': format_green})
            count += 1

    else: # all other report types
        count = 0
        for a_row in data:
            worksheet.write_row(count+2, 0, a_row)
            count += 1

    
    workbook.close()

    # Return the file.
    return send_file(
        absfilename, as_attachment=True, attachment_filename=filename)

# ====================All Page Handlers for Users ============================================================


@app.route('/users', methods=['GET', 'POST'])
def users():
    """The handler for '/users'."""
    kwargs = {}
    kwargs['loggedin'], uname, ugroup = if_logged_in(request)
    kwargs['block_add'] = False if ugroup in GROUPS_CAN_ADD_USER else True
    kwargs['all_users'] = show_all_users()

    if not kwargs['block_add'] and request.form.get('user_action') == 'new':
        return redirect("/new_user", 302)
    else:
        return render_template('users.html', **kwargs)


@app.route('/user_<int:user_id>', methods=['GET', 'POST'])
def user_single(user_id):
    kwargs = {}
    kwargs['loggedin'], uname, ugroup = if_logged_in(request)
    kwargs['block_mod'] = False if ugroup in GROUPS_CAN_MOD_USER else True
    kwargs['block_del'] = False if ugroup in GROUPS_CAN_DEL_USER else True
    kwargs['user_id'] = user_id
    user_info = get_user_info(user_id)
    # kwargs['name'] = user_info[0][0]
    # kwargs['email'] = user_info[0][1]
    kwargs['group'] = GROUPS
    kwargs['user_info'] = user_info

    if request.method == 'POST':
        if request.form.get('user_info'):
            if request.form.get('user_info') == 'Change' and not kwargs['block_mod']:  # User changed Project static information
                update_user(user_id, request.form)
                # update_user(user_id)
                return redirect("/user_{0}".format(user_id), 302)
            if request.form.get('user_info') == 'Delete' and not kwargs['block_del']:  # User delete this project
                del_user(kwargs['user_info'][0][0])
                return redirect("/users", 302)
            else:
                return "Error: user_info takes invalid value."
        else:
            return "Error, expect user_info, but get neither."
    return render_template('user_single.html', **kwargs)


@app.route('/new_user', methods=['GET', 'POST'])
def new_user():
    kwargs = {}
    kwargs['loggedin'], uname, ugroup = if_logged_in(request)
    kwargs['group'] = GROUPS
    if ugroup not in GROUPS_CAN_ADD_USER:
        return redirect("/", 302)
    if request.method=='POST':
    # First collect user inputs.
        kwargs['name'] = request.form['name']
        kwargs['email'] = request.form['email']
        kwargs['up_msg'] = add_new_users(request.form['name'], request.form['pwd'], request.form['email'], request.form['group'])
    return render_template('new_user.html', **kwargs)


if __name__ == '__main__':
    app.debug = False
    app.run(host='0.0.0.0', port=8070)
