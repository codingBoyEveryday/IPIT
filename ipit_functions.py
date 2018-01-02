#!/usr/bin/python
# -*- coding: UTF-8 -*-
""" Supporting functions for IPIT Web Server. """

import sys
import re

from datetime import date, datetime, timedelta

from sqlalchemy import distinct
from sqlalchemy import or_
from sqlalchemy import and_
from sqlalchemy.sql import label
from sqlalchemy.sql import func

from database_setup import Employees
from database_setup import Managers
from database_setup import Projects
from database_setup import ProjectHumanUsages
from database_setup import ProjectPlans
from database_setup import Departments
from database_setup import Roles
from database_setup import Domains
from database_setup import ProjectElementUsages
from database_setup import ElementUsages
from database_setup import Elements
from database_setup import Nodes
from database_setup import Priorities
from database_setup import ElementTemplates
from database_setup import ElementTemplateContents
from database_setup import ChangeRequests
from database_setup import Impact
from database_setup import Status
from database_setup import Applicants
from database_setup import ChangeRequestsElements
from popdata import float_or_none

from sqlalchemy.exc import IntegrityError

# Global constants.
VALID_YEARS = range(2014, 2020)  # Global parameter to control valid year range.
VALID_HOUR = re.compile(r'^-?\d*\.?\d*$')
VALID_NAME = re.compile(r'^\D{3,30}$')
VALID_NAME_PRJ = re.compile(r'^[ \S]+$')  # space and any non-white characters.
VALID_EMAIL = re.compile(r"^[\S]+@[\S]+\.[\S]+$")
VALID_REG_NUM = re.compile(r'^[a-zA-Z0-9]{6}$')
# This set is used for project element usage detection.
# All usage in set means they can cause impact on other usages.
CONFLICT_USAGES = set(['Cfg aanp. + Test Uitv.', 'Software update',
    'software update + Testen', 'Switched off', 'Configuratie aanpassing'])
# All usage in set means they are important for the weekly element report.
IMPORTANT_ELEMENT_USAGES = set(['Cfg aanp. + Test Uitv.', 'Software update',
    'software update + Testen', 'Training', 'Configuratie aanpassing'])
REQUEST_ELEMENTS = 4 # this number defines the amount of elements that can be added in a change request

class ErrorInvalidTime(Exception):
    "Local defined Exception for gen_yw_list()."
    pass

class ErrorWrongForm(Exception):
    """
    Used by gen_report_sql_1.Indicating when the user
    handed in a different form type."""
    pass

def normalize_db_value(value):
    """
    Removes all strange values in the string `value`. """
    value = " ".join(value.split()) #remove double spaces
    return value 
    
def is_valid_name(name, name_list=[], is_project=False):
    """
    Verify if a user given name is valid name.
    Not empty, length between 3 characters and 30 characters. Doesn't contain digits.
    Return valid name + error message.
    When not valid, valid_name is None.
    ===Update 15-Sep===
    Add name_list and is_project two parameters.
    Rules changes:
    1 All names in the name_list is taken. So not valid to add again.
    2 when is_project is True, the name can use digits and punctuations.
    3
    """
    valid_name, msg = None, ""
    if not name:
        msg = "Name can't be empty."
    elif name in name_list:
        msg = "This name is already in use."
    elif VALID_NAME.match(name):
        valid_name = name
    elif is_project and VALID_NAME_PRJ.match(name):
        valid_name = name
    else:
        msg = 'The name is not valid.'
    return valid_name, msg

def is_valid_hour(hour, h_max=None):
    """
    Verify if user input hour is valid.
    Not empty, positive digits.
    """
    valid_hour, msg = None, ''
    if hour is None or hour == "":
        msg = "This field can't be empty"
    elif VALID_HOUR.match(str(hour)):
        if float(hour) < 0:
            msg = "Hour can't be negative."
        elif h_max and float(hour) > h_max:
            msg = "Hour should be lower than {}.".format(h_max)
        else:
            valid_hour = float(hour)
    else:
        msg = "Please only type digit and (maximum) one dot."
    return valid_hour, msg

def valid_hours_from_list(form):
    """
    Description:
    validates from a list of hours (retrieved from form) if they are valid
    """
    valid_hours = []
    hour_errors = []
    for hour in form.getlist('hour_input'): # validate hour input
        if hour != '':
            kwargs = {}
            valid_hour, kwargs['hour_error'] = is_valid_hour(hour, h_max=40)
            valid_hours.append(valid_hour)
            hour_errors.append(kwargs['hour_error'])
        else:
            valid_hours.append(hour)
    return valid_hours, hour_errors


def is_valid_email(email):
    """Verify if the input is a valid email string."""

    valid_email, msg = None, ''
    if not email:
        msg = "This field can't be empty"
    elif VALID_EMAIL.match(str(email)):
        valid_email = str(email)
    else:
        msg = "This is not an valid email"
    return valid_email, msg


def is_valid_regnum(reg_num):
    "Check if user's registration number is valid. Return None if not valid."

    valid_reg_num, msg = None, ''
    if not reg_num:
        msg = "This field can't be empty."
    elif VALID_REG_NUM.match(str(reg_num)):
        valid_reg_num = str(reg_num)
    else:
        msg = "This is not a valid registration number."
    return valid_reg_num, msg

def valid_project_input(form):
    """for page /new_project
    Check whether input is given on the fields where it is mandatory
    output: boolean, error message
    """
    
    is_valid = True
    input_errors = ['','','']
    if form['priority'] == '':
        input_errors[0] = 'Please select a priority'
        is_valid = False
    if form['department'] == '':
        input_errors[1] = 'Please select a department'
        is_valid = False
    if form['domain'] == '':
        input_errors[2] = 'Please select a domain'
        is_valid = False
    
    return is_valid, input_errors

def project_selected(form):
    """for page /change_requests
    Evaluates whether a project is selected"""
    if form['project'] != '':
        return True, '' 
    else: 
        return False, 'please select a project'
    
def impact_selected(form):
    """for page /change_requests
    Evaluates whether an impact value is selected"""
    if form['impact'] != '':
        return True, '' 
    else: 
        return False, 'please select an impact value'

def float_or_zero(x):
    return float(x) if x else 0.0

def the_last_week(year):
    """
    IPIT often needs to know a year has 52 or 53 weeks in total.
    Same as the out-look, we use ISO week date here.
    I firstly used date(start_year, 12, 31).isocalendar()[1] to get the last week number.
    But some years, this 31-Dec falls to 1st week of next year.
    For example:
        date(2014, 12, 31).isocalendar() == (2015, 1, 3)
    This is because:
    1 ISO week always starts a week from Monday
    2 In that week of date(2014, 12, 31), there are 4 days from 2015, so that
      week becomes 1st week 2015.
    Simple judgement is to check the Thursday of a week.
    It decides which year that week belongs.
    Input:
        year, int
    Output:
        weeknum, int.
    """
    weeknum = date(year, 12, 31).isocalendar()[1]
    if weeknum == 1:
        return date(year, 12, 24).isocalendar()[1]
    else:
        return weeknum
    

def get_yw_by_date(start_date, end_date):
    """
    Description: converts mm/dd/yyyy 00:00:00 format to start year, 
    start week, end year, end week for the page /new_change_request
    
    input:
    start_date (dd-mm-yyyy format)
    end_date (dd-mm-yyyy format)
    
    output:
    start year, start week, end_year, end_week"""
    
    # extract start and end year from datetime format

    str_y = int(start_date.split('-')[2]) 
    str_m = int(start_date.split('-')[1])
    str_d = int(start_date.split('-')[0])
    end_y = int(end_date.split('-')[2])
    end_m = int(end_date.split('-')[1])
    end_d = int(end_date.split('-')[0])
    
    str_w = int(date(str_y, str_m, str_d).isocalendar()[1])
    if str_m == 1 and str_d == 1 and str_w >= 52:
        str_w = int(date(str_y, 1, 8).isocalendar()[1])
    if str_m == 12 and str_d == 31 and str_w == 1:
        str_w = int(date(str_y, 12, 24).isocalendar()[1])
    end_w = int(date(end_y, end_m, end_d).isocalendar()[1])
    if end_m == 1 and end_d == 1 and end_w >= 52:
        end_w = int(date(end_y, 1, 8).isocalendar()[1])
    if end_m == 12 and end_d == 31 and end_w == 1:
        end_w = int(date(end_y, 12, 24).isocalendar()[1])
        
    return [str_y, str_w, end_y, end_w]

def is_valid_time(start_year, start_week, end_year, end_week):
    """
    Detect if the start/end time makes sense.
    Rules:
        1 Week number use ISO week Number.
        2 The earliest week is 2014, 1 because IPIT DB doesn't contain data
          earlier.
        3 Inputs can be int or float.
    Input:
        4 int/ float
    Output:
        Bool
    Unit test:
        TestIsValidTime
    """
    try:
        start_week = int(start_week)
        start_year = int(start_year)
        end_week = int(end_week)
        end_year = int(end_year)
    except (ValueError, TypeError):
        return False
    if end_year < start_year:
        return False
    if end_year == start_year and end_week < start_week:
        return False
    if start_week < 1 or end_week < 1 or start_year < 2014 or end_year < 2014:
        return False
    if (start_week > the_last_week(start_year)  or
            end_week > the_last_week(end_year)):
        return False
    return True

def gen_yw_list(start_year, start_week, end_year, end_week):
    """
    Supporting function for gen_year_week_columns().
    input:
        start_year, int
        start_week, int
        end_year, int
        end_week, int
    Output:
        yw_list: list of tuples of ints. (year, week)

    Example:
        gen_yw_list(2016, 11, 2016, 14)
        ==> [(2016, 11), (2016, 12), (2016, 13), (2016, 14)]
    Unittest:
        TestGenYwList
    """
    start_year, start_week, end_year, end_week = map(int, [start_year, start_week, end_year, end_week])
    if is_valid_time(start_year, start_week, end_year, end_week):
        if start_year == end_year:
            yw_list = [(start_year, w) for w in range(start_week, end_week + 1)]
        else:
            yw_list = []
            for year in range(start_year, end_year + 1):
                if year == start_year:
                    new = [(year, w) for w in range(start_week, the_last_week(year) + 1)]
                elif year == end_year:
                    new = [(year, w) for w in range(1, end_week + 1)]
                else:
                    new = [(year, w)  for w in range(1, the_last_week(year) + 1)]
                yw_list.extend(new)
        return yw_list
    else:
        raise ErrorInvalidTime

# TODO:
def gen_year_week_columns(start_year, start_week, end_year, end_week):
    """
    Supporting function for generating SQL statement.
    Inputs:
        start_year: int
        start_week: int
        end_year: int
        end_week: int
    Outputs:
        yw_columns: string
        yw_columns_definition: string
        x_series: string

    Example:
        gen_year_week_columns(2016, 11, 2016, 14)
        yw_columns: "yw_2016_11, yw_2016_12, yw_2016_13, yw_2016_14"
        yw_columns_definition: "yw_2016_11 text, yw_2016_12 text, yw_2016_13 text, yw_2016_14 text"
        x_series: "(2016, 11), (2016, 12), (2016, 13), (2016, 14)"
    Unit Test:
        TestGenYearWeekColumns
    """

    year_week = gen_yw_list(start_year, start_week, end_year, end_week)
    yw_list = ['yw_' + '_'.join((str(x), str(y))) for (x, y) in year_week]
    # yw_list = ['_W'.join((str(x), str(y))) for (x, y) in year_week]
    yw_columns = ', '.join(yw_list)
    yw_columns_definition = ' text, '.join(yw_list) + ' text'
    x_series = repr(year_week)[1:-1]

    return yw_columns, yw_columns_definition, x_series

def gen_employee_hours(DBSession, name, time_line):
    """
    A supporting function for add_rows_phu_report().
    Given an employee, and a time period, generates a list of available hours.
    Input:
        DBSession: session maker
        name: string. The name of the Employee. Must be same as stroed in DB.
        time_line: list of 4 ints.
    Output:
        employee_hours, list of strings.
    Example:
        hours = gen_employee_hours("Dewei Zhai", 2016, 10, 2016, 12)
        hours
        [40, 40, 40]
    TODO: Change the logic to allow different hours in different weeks.
    """

    session = DBSession()
    hour = float(session.query(Employees.hours_available).filter(Employees.name
        == name).first()[0])
    session.close()
    return [hour] * len(gen_yw_list(*time_line))

def pre_4_cross_tab(raw):
    """
    This function is to process the raw query result, convert it to
    format that cross_tab() could handle.
    1 Change the last column to float.
    2 combine -2 and -3 column to one tuple column.
    Input:
        raw: list of tuples.
    Output:
        target: list of tuples.
    Example:
        raw_data =
        [(u'SBC Swap', 2016, 4, Decimal('2.5')),
         (u'SBC Swap', 2016, 3, Decimal('2.5')),
         (u'SBC Swap', 2016, 2, Decimal('2.5')),
         (u'SBC Swap', 2016, 1, Decimal('2.5'))]
        good_data =
        [(u'SBC Swap', (2016, 4), 2.5),
         (u'SBC Swap', (2016, 3), 2.5),
         (u'SBC Swap', (2016, 2), 2.5),
         (u'SBC Swap', (2016, 1), 2.5)]
    """
    target = []
    for a_row in raw:
        new_row = a_row[:-3] + ((a_row[-3], a_row[-2]),)
        try:
            new_row += (float(a_row[-1]),)
        except TypeError:
            new_row += (None,)
        target.append(new_row)
    return target

def cross_tab(in_data, x_series, unique_len=1):
    """
    Many of the IPIT reports needs to pivot the query result.
    If you consider the raw_table's column is (Y,X,V).
    Then here we convert the columns to (Y,X1,X2,X3,...) and V is
    no more column. But values in the table.
    Postgresql has build-in function crosstab to do this.
    But in order to use that, we can't use ORM modle but via direct sql
    statement.
    This function aims to achieve the same function in python so that we
    can stay in using ORM.
    Note:
    1 Col-1 is used to distinguish different Y.
    3 In output, each row is a list, not a tuple.

    Input:
        in_data: list of tuples
        x_series: list of X values.
        unique_len: int, indicating how to distinguish one "Y" point. By default, ul = 1
                    Only check the first column from data matrix.
    Output:
        out_data: list of tuples.
    Example:
        Input:
        in_data =
        [
        ('CS2 (Circuit Switch Core Swap)', (2015, 50), 12.0),
        ('CS2 (Circuit Switch Core Swap)', (2015, 51), 12.0),
        ('CS2 (Circuit Switch Core Swap)', (2015, 52), 12.0),
        ('SBC Swap', (2016, 1), 2.5),
        ('SBC Swap', (2016, 2), 2.5),
        ('SBC Swap', (2016, 3), 2.5)]
        x_series =
        [(2015,50),(2015,51),(2015,52),(2015,53),(2016,1),(2016,2),(2016,3)]

        Output:
        out_data =
        [['CS2 (Circuit Switch Core Swap)', 12.0, 12.0, 12.0, None, None, None, None],
        [''SBC Swap'', None, None, None, None, 2.5, 2.5, 2.5]
    """
    # First scan in_data, get all different Y's.
    # A Y here means a unique value in the first column of in_data.
    # For each unique Y, form a row and save to out_data
    # Save the position of each Y in out_data to dict_y
    out_data = []
    dict_y = {}
    for record in in_data:
        key_y = tuple(record[:unique_len])
        if dict_y.get(key_y) is None:  # first time see an Y instance.
            out_data.append(list(record[:-2]) + [None] * len(x_series))
            dict_y[key_y] = len(out_data) - 1  # The position of this Y in out_data.
        else:
            pass  # Skip any seen Y instance.
    # Convert x_series into a dictionary for mapping X to a position. dict_x
    dict_x = dict(zip(x_series, range(len(x_series))))
    # Scan in_data again, use dict_y to get row number in out_data and use dict_x to get
    # position number inside the row and update that element v.
    for record in in_data:
        row_ind = dict_y[tuple(record[:unique_len])]
        col_ind = dict_x[record[-2]] + len(record) - 2
        out_data[row_ind][col_ind] = record[-1]

    # Return out_data.
    return out_data

def allocation_plan(emp_id, form, DBSession):
    """
    Supporting handler function 'employee_single' in ipitserver.py
    Given employee id and start end date
    Return a table of employee allocation hours for each project.
    Inputs:
        emp_id: Int, the employee_id value.
        form: dictionary.
            -'project_name': Name of the queried project or 'All Projects'
            -'start_year':
            -'start_week':
            -'end_year':
            -'end_week':
        DBSession: Sql alchemy session maker
    Outputs:
        data: List of tuples. Each row represents a project. Each column represents a week.
        column_names: List of strings.
    Example:
        emp_id = 1
        form = {'project_name':'All Projects',
        'start_year':'2016', 'start_week':'5', 'start_year':'2016', 'start_week':'9'}
        data ==>
        [('Packed Switched Core naar PS11', 8.0, None, None, None, None),
        ('Datagroei MVNO en Roaming (cap. Uitbreiding)', 5.0, 5.0, 5.0, 5.0, None),
        ('LTE TX Cap-uitbreiding', None, None, None, None, 2.0)
        ]
        column_names ==>
        ['Projects', 'yw_2016_5, 'yw_2016_6', 'yw_2016_7', 'yw_2016_8', 'yw_2016_9']

    """
    start_year = int(form['str_y'])
    start_week = int(form['str_w'])
    end_year = int(form['end_y'])
    end_week = int(form['end_w'])
    project_name = form['project_name']
    session = DBSession()

    # TODO: Distinguish the query whether it is one project of all.
    if start_year == end_year:
        raw_data = (
            session.query(
                Projects.name,
                ProjectHumanUsages.year,
                ProjectHumanUsages.week,
                ProjectHumanUsages.hours
                         )
            .filter(ProjectHumanUsages.employee_id == emp_id)
            .filter(ProjectHumanUsages.year == start_year)
            .filter(start_week <= ProjectHumanUsages.week)
            .filter(ProjectHumanUsages.week <= end_week)
            .filter(ProjectHumanUsages.project_id == Projects.project_id)
            .all()
                   )
    else:
        raw_data = []
        for year in range(start_year, end_year + 1):
            if year == start_year:  # start year
                raw_data += (
                session.query(
                    Projects.name,
                    ProjectHumanUsages.year,
                    ProjectHumanUsages.week,
                    ProjectHumanUsages.hours
                             )
                .filter(ProjectHumanUsages.employee_id == emp_id)
                .filter(ProjectHumanUsages.year == year)
                .filter(ProjectHumanUsages.week >= start_week)
                .filter(ProjectHumanUsages.project_id == Projects.project_id)
                .all()
                       )
            elif year < end_year:  # Middle years.
                raw_data += (
                session.query(
                    Projects.name,
                    ProjectHumanUsages.year,
                    ProjectHumanUsages.week,
                    ProjectHumanUsages.hours
                             )
                .filter(ProjectHumanUsages.employee_id == emp_id)
                .filter(ProjectHumanUsages.year == year)
                .filter(ProjectHumanUsages.project_id == Projects.project_id)
                .all()
                       )
            else:
                raw_data += (
                session.query(
                    Projects.name,
                    ProjectHumanUsages.year,
                    ProjectHumanUsages.week,
                    ProjectHumanUsages.hours
                             )
                .filter(ProjectHumanUsages.employee_id == emp_id)
                .filter(ProjectHumanUsages.year == year)
                .filter(ProjectHumanUsages.week <= end_week)
                .filter(ProjectHumanUsages.project_id == Projects.project_id)
                .all()
                       )
    session.close()

    raw_data = pre_4_cross_tab(raw_data)
    yw_columns = gen_year_week_columns(start_year, start_week, end_year, end_week)[0]
    x_series = gen_yw_list(start_year, start_week, end_year, end_week)
    data = cross_tab(raw_data, x_series)
    column_names = ["Projects"] + yw_columns.split(', ')
    return data, column_names

def query_human_plan(DBSession, project_id, time_line):
    """
       Support function for page '/project_x'.
       Given project_id, the time_line.
       Return data for a displaying table to show the project human resource planning.
    Inputs:
        DBSession: sqlalchemy session maker
        project_id: int. Used to refer to a project in SQL DB.
        time_line: tuple of 4 int. (start_year, start_week, end_year, end_week).
            Used to define query window.
    Outputs:
        human_plan: List of list. With columns:
         -department: strings.
         -Resource type: strings.
         -Dynamically generated columns: float values or none.
        column_names: list of strings, column names.
    Example:
        project_id = 1
        time_line = (2015, 2, 2015, 3)

        human_plan is:
        [(u'Innovation Test Voice', u'Tester', 3.0, 3.0),
        (u'Innovation Test Data', u'Tester', 4.0, 4.0),
        (u'Innovation Test Radio', u'Tester', 3.0, 3.0)
        ]
        column_names is:
        ['Departments', 'Resource Type', '2015-2', '2015-3']
    Unit Test:
        TestQueryHumanPlan
    """
    if not is_valid_time(*time_line):
        raise ErrorInvalidTime('query_human_plan received invalid time_line {0}'
            .format(time_line))
    raw_data = []
    session = DBSession()
    if time_line[0] == time_line[2]:
        raw_data = (session.query(Departments.department,
                Roles.role, ProjectPlans.year, ProjectPlans.week, ProjectPlans.hours)
            .filter(ProjectPlans.project_id == project_id)
            .filter(ProjectPlans.department_id == Departments.department_id)
            .filter(ProjectPlans.role_id == Roles.role_id)
            .filter(ProjectPlans.year == time_line[0])
            .filter(ProjectPlans.week >= time_line[1])
            .filter(ProjectPlans.week <= time_line[3])
            .all()
            )
    else:
        for year in range(time_line[0], time_line[2] + 1):
            if year == time_line[0]:
                raw_data += (session.query(Departments.department,
                    Roles.role, ProjectPlans.year, ProjectPlans.week, ProjectPlans.hours)
                    .filter(ProjectPlans.project_id == project_id)
                    .filter(ProjectPlans.department_id == Departments.department_id)
                    .filter(ProjectPlans.role_id == Roles.role_id)
                    .filter(ProjectPlans.year == year)
                    .filter(ProjectPlans.week >= time_line[1])
                    .all()
                    )
            elif year == time_line[2]:
                raw_data += (session.query(Departments.department,
                    Roles.role, ProjectPlans.year, ProjectPlans.week, ProjectPlans.hours)
                    .filter(ProjectPlans.project_id == project_id)
                    .filter(ProjectPlans.department_id == Departments.department_id)
                    .filter(ProjectPlans.role_id == Roles.role_id)
                    .filter(ProjectPlans.year == year)
                    .filter(ProjectPlans.week <= time_line[3])
                    .all()
                    )
            else:
                raw_data += (session.query(Departments.department,
                    Roles.role, ProjectPlans.year, ProjectPlans.week, ProjectPlans.hours)
                    .filter(ProjectPlans.project_id == project_id)
                    .filter(ProjectPlans.department_id == Departments.department_id)
                    .filter(ProjectPlans.role_id == Roles.role_id)
                    .filter(ProjectPlans.year == year)
                    .all()
                    )
    session.close()
    formatted_data = []
    for a_row in raw_data:
        temp = list(a_row[:2])  # [dept, role]
        temp.append(tuple(a_row[2:4]))  # [dept, role, (year, week)]
        try:
            temp += map(float, a_row[4:])  # [dept, role, (year, week), hour1, hour2, ....]
        except TypeError:
            hours = []
            for h in a_row[4:]:
                try:
                    hours.append(float(h))
                except TypeError:
                    hours.append(None)
            temp += hours  # [dept, role, (year, week), hour1, hour2, ....]
        formatted_data.append(temp)

    x_series = gen_yw_list(*time_line)  # [(year, week1), (year, week2), (year, week3)...]
    human_plan = cross_tab(formatted_data, x_series, 2)
    column_names = ['Departments', 'Resource Type']
    column_names += map(lambda x: str(x[0]) + '-' + str(x[1]), x_series)
    return human_plan, column_names

def query_element_plan(DBSession, project_id, time_line=None):
    """
    Description:
       Support function for page '/project_x'.
       Given project_id and time_line (optional).
       Return data and column names list to be showed in the page for prject element usage.
       When time_line is not set, makes no filter on time and show all plans.
    Inputs:
        DBSession: sqlalchemy session maker
        project_id: int. Used to refer to a project in IPIT DB.
        time_line: tuple of 4 int. (start_year, start_week, end_year, end_week).
            Used to define query window.
            When not present, don't filter on the time.
    Outputs:
        element_plan: List of list. With columns:
         -domain: strings.
         -node: strings.
         -hostname: strings.
         -Dynamically generated columns: strings.
        column_names: list of strings, column names.
    Example:
        project_id = 8
        time_line = (2016, 1, 2016, 1)

        Element_plan is:
        [('Data', 'PCRF', 'GVTEPP2', 'Impliciet Test'),
         ('Data', 'PCRF', 'GVTEPP3', 'Impliciet Test'),
         ('Data', 'SeGw', 'GVTEEF1', 'Impliciet Test'),
         ('Data', 'SeGw', 'GVTEEF2', 'Impliciet Test'),
         ('Data', 'UGW (PGW /SGW)', 'GVTEPG5', 'Impliciet Test'),
         ('Data', 'UGW (PGW /SGW)', 'GVTEPG6', 'Cfg aanp. + Test Uitv.'),
         ('Data', 'USN (MME / SGSN)', 'GVTEEM1', 'Impliciet Test'),
         ('Data', 'USN (MME / SGSN)', 'GVTEEM2', 'Cfg aanp. + Test Uitv.'),
         ('Radio', 'eNodeB - 6201', 'RBS7', 'Impliciet Test'),
         ('Radio', 'NodeB', 'rbs099039 (RBS3)', 'Impliciet Test'),
         ('Voice', 'DRA - HPc7000', 'GVDRS1', 'Cfg aanp. + Test Uitv.'),
         ('Voice', 'MGW', 'EXT-GVTEMW1', 'Impliciet Test'),
         ('Voice', 'MGW', 'EXT-GVTEMW2', 'Impliciet Test'),
         ('Voice', 'MSC-S - ATCA', 'GVTMSS1', 'Impliciet Test'),
         ('Voice', 'MSC-S - ATCA', 'GVTMSS2', 'Impliciet Test'),
         ('Voice', 'MSTP - Eagle 5 SAS (Tekelec)', 'GVTEGX1', 'Impliciet Test'),
         ('Voice', 'MSTP - Eagle 5 SAS (Tekelec)', 'GVTEGX2', 'Impliciet Test')
        ]
        column_names is:
        ['Domain', 'Node', 'Hostname', '2016-1']
    Unit Test:
        TestQueryElementPlan
    """
    # Initialize
    if time_line:
        valid_time_line = is_valid_time_line(time_line)[0]
    session = DBSession()
    # Query
    q = session.query(
        Domains.domain, Nodes.node, Elements.hostname, ProjectElementUsages.year,
        ProjectElementUsages.week, ElementUsages.element_usage)
    # Join
    q = q.filter(
            (ProjectElementUsages.element_id == Elements.element_id) & 
            (ProjectElementUsages.element_usage_id == ElementUsages.element_usage_id) & 
            (Elements.node_id == Nodes.node_id) & 
            (Nodes.domain_id == Domains.domain_id))
    # Filter
    q = q.filter(ProjectElementUsages.project_id == project_id)
    if time_line:
        q = add_time_filter(q, ProjectElementUsages, valid_time_line)
    # Order
    if not time_line:
        q = q.order_by(ProjectElementUsages.year, ProjectElementUsages.week)
    # Get data
    d = q.all()
    session.close()
    d = [x[:3] + ((x[3], x[4]), x[5]) for x in d]  # Combine year, week to a tuple.
    # Make column_names and x_series
    column_names = ['Domain', 'Node', 'Hostname']
    if time_line:
        x_series = gen_yw_list(*valid_time_line)
    elif len(d):  # When not filter on time, get the actual time from data.
        valid_time_line = d[0][3] + d[-1][3]
        x_series = gen_yw_list(*valid_time_line)
    else:
        x_series = []
    column_names += map(lambda x: str(x[0]) + '-' + str(x[1]), x_series)
    # Pivote data
    data = cross_tab(d, x_series, 3)
    
    return data, column_names

def update_employee(DBSession, emp_id, form):
    """
    Supporting function for page handler /employee_<int:emp_id>
    Used to update the IPIT DB table employee.
    Input:
        DBSession: sqlalchemy session maker
        emp_id: int. Specify the employee.
        form: dictionary, get from HTTP request form.
    Output:
        msg: A description about
    """
    session = DBSession()
    person = session.query(Employees).filter_by(employee_id=emp_id).first()
    person.name = normalize_db_value(form['name'])
    person.hours = float(form['hours'])  # This form is validated before send to this func.
    person.hours_available = float(form['hours_available'])
    person.department_id = session.query(Departments.department_id
        ).filter_by(department=form['department']).one()[0]
    person.email = form['email']
    person.contract_type = form['contract_type']
    person.registration_number = form['registration_number']
    person.if_left = form['if_left'] == 'True'
    try:
        session.commit()
        update_msg = u"Database Update on {} successfully.".format(normalize_db_value(form['name']))
    except:  # Protect "Hours" & "Hours Available" these must be only numeric.
        session.rollback()
        update_msg = "ERROR:" + sys.exc_info()[0]
    session.close()
    return update_msg

def update_project(DBSession, prj_id, form):
    """
    Supporting function for page handler /project_<int:prj_id>
    Used for updating a certain project.
    Inputs:
        DBSession: sqlalchemy session maker.
        prj_id: int
        form: dictionary. Get from page request. It contains all info of the project.
    Outputs:
        bool
    """
    session = DBSession()
    project = session.query(Projects).filter_by(project_id=prj_id).first()
    project.name = normalize_db_value(form['name'])
    project.management = form['management']
    project.active = (form['active'] == 'active')
    project.note = form['note']
    print repr(form['note'])
    if form['department']:  # Consider None
        project.department_id = (session.query(Departments.department_id).
        filter(Departments.department == form['department'])
        .first()[0])
    if form['test_manager']:
        project.test_manager_id = (session.query(Employees.employee_id).
            filter(Employees.name == form['test_manager']).first()[0]
            )
    else:
        project.test_manager_id = None

    if form['implementation_manager']:
        project.implementation_manager_id = (session.query(Managers.manager_id).
            filter(Managers.name == form['implementation_manager']).first()[0]
            )
    else:
        project.implementation_manager_id = None

    if form['domain']:
        project.domain_id = (session.query(Domains.domain_id).
            filter(Domains.domain == form['domain']).first()[0]
            )
    project.priority_id = (session.query(Priorities.priority_id).
        filter(Priorities.priority == form['priority']).first()[0]
        )
    project.code = form['code']

    if form['date_el']:
        project.date_EL = convert_date_format(form['date_el'])

    try:
        session.commit()
        succ = True
    except:
        session.rollback()
        succ = False
    session.close()
    return succ

def update_change_request(DBSession, req_id, form):
    """
    Supporting function for page handler /change_request_<int:req_id>
    Used for updating a certain Change Request.
    Inputs:
        DBSession: sqlalchemy session maker.
        prj_id: int
        form: dictionary. Get from page request. It contains all info of the project.
    Outputs:
        bool
    """
    session = DBSession()
    change_request = session.query(ChangeRequests).filter_by(change_request_id=req_id).first()
   
    if form['description']:
        change_request.description = description=normalize_db_value(form['description'])
        
    if form['applicant']:
        change_request.applicant_id = session.query(Applicants.applicant_id).filter(
            Applicants.applicant == form['applicant']).first()[0]
            
    if form['project']:
        change_request.project_id = session.query(Projects.project_id).filter(
            Projects.name == form['project']).first()[0]
            
    if form['impact']:
        change_request.impact_id = session.query(Impact.impact_id).filter(
            Impact.impact == form['impact']).first()[0]

    if form['status']:
        change_request.status_id = session.query(Status.status_id).filter(
            Status.status == form['status']).first()[0]

    #first, change existing request elements
    change_request_elements = session.query(ChangeRequestsElements).filter_by(
        change_request_id=req_id).order_by(ChangeRequestsElements.request_element_id).all()
    for i in range(len(change_request_elements)):
        if form['element_{}'.format(i)]:
            element_id = get_element_id(DBSession, form['element_{}'.format(i)])
            change_request_elements[i].element_id = session.query(Elements.element_id).filter(
              Elements.element_id == element_id).first()[0]
        if form['note_{}'.format(i)]:
                change_request_elements[i].note = form['note_{}'.format(i)]
        if form['start_date_{}'.format(i)]:
                change_request_elements[i].start_date = convert_date_format(form['start_date_{}'.format(i)])
        if form['start_time_{}'.format(i)]:
                change_request_elements[i].start_time = form['start_time_{}'.format(i)]
                
        if form['end_date_{}'.format(i)]:
                change_request_elements[i].end_date = convert_date_format(form['end_date_{}'.format(i)])
        if form['end_time_{}'.format(i)]:
                change_request_elements[i].end_time = form['end_time_{}'.format(i)] 

    #then, update possible new request elements
    for i in range(len(change_request_elements), REQUEST_ELEMENTS):
        if form.get('element_{}'.format(i)):
            new_el = new_request_element(DBSession, session, form, i)
            session.add(new_el)

    try:
        session.commit()
        succ = True
        msg = u"Successfully updated change request {}.".format(form['description'])
    except:
        session.rollback()
        succ = False
        session.close()
    return msg

def gen_employee_list(DBSession, contain_id=False, full=False, hide_sensitive=True):
    """
    Return a list of employee names.
    If hide_sensitive is True, don't show hours and hours_available info.
    if full is False, we are only interested in name list, (maybe also id)
    Hide left employees.
    """
    # Construct query targets:
    nkw = [Employees.name]
    if contain_id:
        nkw.insert(0, Employees.employee_id)
    if full:
        if hide_sensitive:
            nkw.extend([Departments.department, Employees.email, Employees.contract_type,
                Employees.registration_number])
        else:
            nkw.extend([Employees.hours, Employees.hours_available, Departments.department,
                Employees.email, Employees.contract_type, Employees.registration_number])

    session = DBSession()
    q = session.query(*nkw)
    # Filter left ones
    q = q.filter(
        (Employees.if_left == None) | (Employees.if_left == False)
           )
    if full:
        q = q.outerjoin(Departments, Employees.department_id == Departments.department_id)
    q = q.order_by(Employees.name)

    result = q.all()
    if not contain_id and not full:
        result = [x[0] for x in result]  # Avoid getting list of tuples with single element.
    session.close()

    return result


def gen_manager_list(DBSession):
    """
    Return a list of manager names.
    """
    # Construct query targets:
    nkw = [Managers.name]
    session = DBSession()
    q = session.query(*nkw)
    result = q.all()
    result = [x[0] for x in result]  # Avoid getting list of tuples with single element.
    session.close()

    return result


def gen_element_id_list(DBSession, data):
    """
    for page /element_plan_edit
    returns a list with the elements_ids of the queried element plan 
    """
    element_ids = []
    for row in data:
        element = row[1]+":"+ row[2] #node + hostname 
        element_id = str(get_element_id(DBSession, element))
        element_ids.append(element_id)
    
    return element_ids
        
def gen_priority_list(DBSession):
    """
    Return a list of priorities names.

    Inputs
        DBSession: SQLAlchemy session maker for querying IPIT DB.
    Outputs
        result: List of priorities names.
    """
    session = DBSession()
    result = [item[0] for item in session.query(distinct(Priorities.priority))
        .order_by(Priorities.priority).all()]
    session.close()

    return result

def gen_impact_list(DBSession):
    """
    Return a list of impact names.

    Inputs
        DBSession: SQLAlchemy session maker for querying IPIT DB.
    Outputs
        result: List of impact names.
    """
    session = DBSession()
    q = session.query(Impact.impact_id, Impact.impact
        ).order_by(Impact.impact_id)
        
    result = [x[1] for x in q.all()]
    
    session.close()

    return result

def gen_status_list(DBSession):
    """
    Return a list of status names.

    Inputs
        DBSession: SQLAlchemy session maker for querying IPIT DB.
    Outputs
        result: List of status names.
    """
    session = DBSession()
    result = [item[0] for item in session.query(distinct(Status.status))
        .order_by(Status.status).all()]
    session.close()

    return result
def gen_change_request_list(DBSession):
    """
    Return a list of change request names.

    Inputs
        DBSession: SQLAlchemy session maker for querying IPIT DB.
    Outputs
        result: List of change request names.
    """
    session = DBSession()
    result = [item[0] for item in session.query(distinct(ChangeRequests.description))
        .order_by(ChangeRequests.description).all()]
    session.close()

    return result

def gen_project_list(DBSession, emp_id=0, elmt_id=0, contain_id=False):
    """
    Supporting function to make a list of project names.
    When emp_id or elmt_id appears, use them to filter on the project list.
    Only pass projects that has ProjectElementUsages data or ProjectHumanUsages
    data.
    When contain_id is True, give list of (prj_id, prj_name) tuple instead of list of prj_name.
    Inputs:
        DBSession: Used to make a session accessing SQL DB.
        emp_id: int, employee id, might be used to filter the project list.
        elmt_id: int, element_id, used to filter the project list.
        contain_project_id: syntax controller.
    Outputs:
        result: list of project names.(or List of tuples, each tuple is (id, name))
    """
    session = DBSession()
    q = session.query(Projects.project_id, Projects.name).distinct().order_by(
        Projects.name)
    if elmt_id:
        q = q.filter(
            (Projects.project_id == ProjectElementUsages.project_id) & 
            (ProjectElementUsages.element_id == elmt_id)
            )
    if emp_id:
        q = q.filter(
            (Projects.project_id == ProjectHumanUsages.project_id) & 
            (ProjectHumanUsages.employee_id == emp_id)
            )
    if contain_id:
        result = q.all()
    else:
        result = [x[1] for x in q.all()]
    session.close()

    return result

def gen_department_list(DBSession, contain_id=False):
    """
    Return a list of department names.

    Inputs
        DBSession: SQLAlchemy session maker for querying IPIT DB.
        contain_id: Used to control wether or not take department_id field at the
        output.
    Outputs
        result: List of tuple or priorities names.
    """

    session = DBSession()
    q = session.query(Departments.department_id, Departments.department
        ).order_by(Departments.department)

    q = q.filter((Departments.hide_department == None) | (Departments.hide_department == False))

    if contain_id:
        result = q.all()
    else:
        result = [x[1] for x in q.all()]
    session.close()
    return result

def gen_role_list(DBSession, contain_id=False):
    """
    Return a list of roles.
    """
    session = DBSession()
    q = session.query(Roles.role_id, Roles.role).order_by(Roles.role.desc())
    if contain_id:
        result = q.all()
    else:
        result = [x[1] for x in q.all()]
    session.close()
    return result

def gen_domain_list(DBSession):
    """
    Return a list of Domain names.

    Inputs
        DBSession: SQLAlchemy session maker for querying IPIT DB.
    Outputs
        result: List of domain names.
    """
    session = DBSession()
    result = [item[0] for item in session.query(Domains.domain).
        order_by(Domains.domain).all()]

    session.close()

    return result

def gen_applicant_list(DBSession):
    """
    Return a list of Applicant names.
    
    Inputs: 
        DBSession: SQLAlchemy session maker for querying IPIT DB.
    Outputs:
        result: List of applicant names.
    """
    session = DBSession()
    q = session.query(Applicants.applicant).order_by(Applicants.applicant)

    #only show applicants when they hiding is None or False
    q = q.filter(
        (Applicants.hide_applicant == None) | (Applicants.hide_applicant == False)
    ).all()

    result = [item[0] for item in q]
    
    session.close()
    
    return result
    

def gen_node_list(DBSession):
    """
    Return a list of Nodes.

    Inputs
        DBSession: SQLAlchemy session maker for querying IPIT DB.
    Outputs
        result: List of node names.
    """
    session = DBSession()
    result = [item[0] for item in session.query(Nodes.node).
        order_by(Nodes.node).all()]
    session.close()

    return result

def add_change_request(DBSession, form):
    """
    Description:
        Supporting function for page handler /new_change_request
        Used for creating a new change request.
    Inputs:
        DBSession: session maker.
        form: dictionary. Originally collected from "new_change_request.html"
        The form have following keys:
        description, demand_manager, project, impact, element, start_date, end_date, note
        All value type is string. Empty value is "".
    Outputs:
        message.
    """
    if not form.get('description'):
        return "ERROR: Change Request Description can't be empty."

    session = DBSession()
    new_req = ChangeRequests(description= normalize_db_value(form['description']), status_id=3)
    if form.get('applicant'):
        new_req.applicant_id = session.query(Applicants.applicant_id).filter(
            Applicants.applicant == form['applicant']).first()[0]
    if form.get('project'):
        new_req.project_id = session.query(Projects.project_id).filter(
            Projects.name == form['project']).first()[0]
    if form.get('impact'):
        new_req.impact_id = session.query(Impact.impact_id).filter(
            Impact.impact == form['impact']).first()[0]

    session.add(new_req)

    for i in range(REQUEST_ELEMENTS):
        if form.get('element_{}'.format(i)):
            new_el = new_request_element(DBSession, session, form, i)
            session.add(new_el)
    
    try:
        session.commit()
        msg = u"Successfully added change request {}.".format(form['description']) 
    except:
        msg = "ERR: {}".format(sys.exc_info()[0])
        session.rollback()

    session.close()
    return msg

def new_request_element(DBSession, session, form, i):
    """ 
    Description:
        Supporting function for page handler /new_change_request. 
        Makes one column with elements, date/time and note to send to the database
        ChangeRequestsElements"""
    
    new_el = ChangeRequestsElements()
    new_el.change_request_id = session.query(ChangeRequests.change_request_id).filter(
                ChangeRequests.description == normalize_db_value(form['description'])).first()[0]
    if form.get('element_{}'.format(i)):
        element_id = get_element_id(DBSession, form['element_{}'.format(i)])
        new_el.element_id = session.query(Elements.element_id).filter(
              Elements.element_id == element_id).first()[0]
    if form['start_date_{}'.format(i)]:
        new_el.start_date = convert_date_format(form['start_date_{}'.format(i)])
                
    if form['end_date_{}'.format(i)]:
        new_el.end_date = convert_date_format(form['end_date_{}'.format(i)])
               
    if form['start_time_{}'.format(i)]:
        new_el.start_time = form['start_time_{}'.format(i)]
                
    if form['end_time_{}'.format(i)]:
        new_el.end_time = form['end_time_{}'.format(i)]
            
    new_el.note = form['note_{}'.format(i)]
    
    return new_el
    

def is_valid_applicant(DBSession, applicant):
    """
    Support function for page handler /new_change_request
    Verify if the applicant name given by user is valid.
    Input:
        DBSession: SQLAlchemy session maker.
        applicant: name of applicant
    Output:
        valid_applicant: string or None when not valid.
        msg: string, describe reason why not valid.
    """
    valid_applicant, msg = None, ''
    if not applicant:
        msg = "Applicant name can't be empty."
    elif applicant in gen_applicant_list(DBSession):
        msg = "The applicant name already exists"
    else:
        valid_applicant = applicant
    return valid_applicant, msg

def add_applicant(DBSession, applicant):
    """
    To add a new applicant to table Applicants. 
    This is part of the page /new_change_request
    DBSession: sqlalchemy session maker.
    If the applicant already exists in the DB, then change hide_applicant to False.
    Inputs:
          -'applicant'
    Outputs:
        msg: A string describing successful or not and why.
    """
    session = DBSession()

    new_apl = Applicants(applicant=normalize_db_value(applicant), hide_applicant = False)
    applicant_list = [item[0] for item in session.query(Applicants.applicant).all()]
    if applicant in applicant_list: #When a name is deleted and added again, only set hide_applicant to False
        upd_apl = session.query(Applicants).filter_by(applicant=applicant).first()
        upd_apl.hide_applicant = False
    else:
        session.add(new_apl)

    try:
        session.commit()
        msg = u"Applicant {0} added successfully.".format(applicant)
    except:
        session.rollback()
        msg = u"Applicant {0} added failed.".format(applicant)
    session.close()
    return msg

def is_valid_department(DBSession, department):
    """
    Support function for page handler /departments
    Verify if the department name given by user is valid.
    Input:
        DBSession: SQLAlchemy session maker.
        applicant: name of department
    Output:
        valid_department: string or None when not valid.
        msg: string, describe reason why not valid.
    """
    session = DBSession()
    valid_department, msg = None, ''
    if not department:
        msg = u"Department field can't be empty."
    elif department in gen_department_list(DBSession):
        msg = u"Department \"{0}\" already exists".format(department)
    else:
        valid_department = department
    session.close()
    return valid_department, msg

def add_department(DBSession, new_department):
    """
    To add a new department that can be used in table Projects and Employees.
    This is part of the page /Departments
    DBSession: sqlalchemy session maker.
    Inputs:
          -'new_department'
    Outputs:
        msg: A string describing successful or not and why.
    """
    session = DBSession()
    new_dep = Departments(department=normalize_db_value(new_department), hide_department = False)
    department_list = [item[0] for item in session.query(Departments.department).all()]
    if new_department in department_list: #When a name is deleted and added again, only set hide_department to False
        upd_dep = session.query(Departments).filter_by(department=new_department).first()
        upd_dep.hide_department = False
    else:
        session.add(new_dep)

    try:
        session.commit()
        msg = u"Deparment {0} added successfully.".format(new_department)
    except:
        session.rollback()
        msg = u"Department {0} added failed.".format(new_department)
    session.close()
    return msg

def update_department(DBSession, selected_department, input_department):
    """This is part of the page /Departments
    Enables the user to change the name of a Department
    DBSession: sqlalchemy session maker.
    Inputs:
          -'selected_department'
          -'input_departmant"
    Outputs:
        msg: A string describing successful or not and why.
    """
    session = DBSession()
    with session.no_autoflush:
        department_list = [item[0] for item in session.query(Departments.department).all()]
        upd_dep = session.query(Departments).filter_by(department=selected_department).first()
        upd_dep.department = input_department

        try:
            session.commit()
            msg = u" Changed Department \"{0}\" successfully in \"{1}\".".format(selected_department, input_department)
        except:
            session.rollback()
            if input_department in department_list:
                msg = u"Failed: Department \"{0}\" already exists in database.".format(input_department)
            else:
                msg = u"Failed to change Department \"{0}\" in \"{1}\".".format(selected_department, input_department)
        session.close()
    return msg


def add_project(DBSession, form):
    """
    Description:
        Supporting function for page handler /new_project
        Used for creating a new project.
    Inputs:
        DBSession: session maker.
        form: dictionary. Originally collected from "new_project.html"
        The form have following keys:
        name, management, test_manager, code, priority, department, domain, date_el, note, active
        All value type is string. Empty value is "".
    Outputs:
        message.
    """
    if not form.get('name'):
        return "ERROR: Project Name can't be empty."

    session = DBSession()
    new_prj = Projects(name= normalize_db_value(form['name']), active=(form.get('active') == 'active'))
    new_prj.management = form['management']
    new_prj.note = form['note']
    new_prj.code = form['code']
    if form['date_el']:
        new_prj.date_EL = convert_date_format(form['date_el'])

    if form.get('department'):
        new_prj.department_id = session.query(Departments.department_id).filter(
            Departments.department == form['department']).first()[0]
    if form.get('test_manager'):
        new_prj.test_manager_id = session.query(Employees.employee_id).filter(
            Employees.name == form['test_manager']).first()[0]
    if form.get('domain'):
        new_prj.domain_id = session.query(Domains.domain_id).filter(
            Domains.domain == form['domain']).first()[0]
    if form.get('priority'):
        new_prj.priority_id = session.query(Priorities.priority_id).filter(
            Priorities.priority == form['priority']).first()[0]
    try:
        session.add(new_prj)
        session.commit()
        msg = u"Successfully added project {}.".format(normalize_db_value(form['name']))
    except:
        session.rollback()
        msg = "ERR: {}".format(sys.exc_info()[0])
    session.close()
    return msg

def del_project(DBSession, name):
    """
    Supporting function for page /del_project
    Given a project name, delete it from IPIT DB
    Input:
        DBSession: session maker.
        name: string
    Output:
        Bool, True/ False
    """
    session = DBSession()
    project = session.query(Projects).filter(Projects.name == name).first()
    prj_id = project.project_id
    # Del from ProjectElementUsages
    peu = session.query(ProjectElementUsages).filter(ProjectElementUsages.project_id == prj_id).all()
    # Del from ProjectHumanUsages
    phu = session.query(ProjectHumanUsages).filter(ProjectHumanUsages.project_id == prj_id).all()
    # Del from ProjectPlans
    pp = session.query(ProjectPlans).filter(ProjectPlans.project_id == prj_id).all()
    # TODO: using delete/delete-orphan Cascade so that I only need to delete a project.
    # All records from peu, phu and pp will automatically get removed.
    # See http://docs.sqlalchemy.org/en/latest/orm/tutorial.html#deleting
    for p in peu:
        session.delete(p)
    for p in phu:
        session.delete(p)
    for p in pp:
        session.delete(p)
    session.delete(project)
    try:
        session.commit()
        succ = True
    except:
        session.rollback()
        succ = False
    session.close()
    return succ

def del_change_request(DBSession, req_id):
    """
    Supporting function for page /del_change_request
    Given a change request name, delete it from IPIT DB
    Input:
        DBSession: session maker.
        name: string
    Output:
        Bool, True/ False
    """
    session = DBSession()
    request = session.query(ChangeRequests).filter(ChangeRequests.change_request_id == req_id).first()
    requestelements = session.query(ChangeRequestsElements).filter(ChangeRequestsElements.change_request_id == req_id).all()
    for e in requestelements:
        session.delete(e)
    session.delete(request)

    try:
        session.commit()
        succ = 1
    except:
        session.rollback()
        succ = 0
    session.close()
    return succ == 1

def del_applicant(DBSession, applicant):
    """
    Supporting function for page /new_change_request
    Given a applicant name, hide it from the list of applicants
    Input:
        DBSession: session maker.
        name: string
    Output:
        message string 
    """
    session = DBSession()
    appl = session.query(Applicants).filter(Applicants.applicant == applicant).first()
    appl.hide_applicant = True

    try:
        session.commit()
        message = u"Successfully removed {0} from applicant list.".format(applicant)
    except:
        session.rollback()
        message = "Deleting failed."
        
    session.close()
    
    return message


def del_department(DBSession, department):
    """
    Supporting function for page /departments
    Given a department name, hide it from the list of departments
    Input:
        DBSession: session maker.
        name: string
    Output:
        message string
    """
    session = DBSession()
    dep = session.query(Departments).filter(Departments.department == department).first()
    dep.hide_department = True

    try:
        session.commit()
        message = u"Successfully removed {0} from department list.".format(department)
    except:
        session.rollback()
        message = "Deleting failed."

    session.close()

    return message
    
def add_element(DBSession, form):
    """
    Used to add a new element to table Elements
    DBSession: sqlalchemy session maker.
    Inputs:
        form: HTTP request form from '/new_element'
          -'node'
          -'hostname'
          -'cur_ver'
          -'cur_date'
          -'pre_ver'
          -'pre_date'
          -'pre2_ver'
          -'pre2_date'
          -'note'
    Outputs:
        A string describing successful or not and why.
    """
    if not form['hostname']:
        return "Adding failed, must type a hostname."
    session = DBSession()
    elmt = Elements(node_id=session.query(Nodes.node_id).filter_by(
        node=form['node']).first()[0], hostname= normalize_db_value(form['hostname']),
        note=form['note'], current_version=form['cur_ver'],
        current_version_date=convert_date_format(form['cur_date']) if form['cur_date'] else None,
        previous_version=form['pre_ver'],
        previous_version_date=convert_date_format(form['pre_date']) if form['pre_date'] else None,
        previous2_version=form['pre2_ver'],
        previous2_version_date=convert_date_format(form['pre2_date']) if form['pre2_date'] else None
        )
    session.add(elmt)
    try:
        session.commit()
        succ = u"{0} added successfully.".format(normalize_db_value(form['hostname']))
    except:
        session.rollback()
        succ = "Adding failed."
    session.close()
    return succ

def update_element(DBSession, elmt_id, form):
    """
    Used to change an element in table Elements when a
    user trigger a change from '/element_x'
    Inputs:
        DBSession: Used to make a session for accessing SQL DB.
        elmt_id: int. The element_id value in SQL DB.
        form: HTTP request form generated from element_single.html. Like a dict.
            -'node'
            -'hostname'
            -'cur_ver'
            -'cur_date'
            -'pre_ver'
            -'pre_date'
            -'pre2_ver'
            -'pre2_date'
            -'note'
    Outputs:
        Bool value representing if successfully changed.
    """
    session = DBSession()
    elmt = session.query(Elements).filter_by(element_id=elmt_id).first()

    elmt.node_id = session.query(Nodes.node_id).filter_by(node=form['node']).first()[0]
    elmt.hostname = normalize_db_value(form['hostname'])
    elmt.current_version = form['cur_ver']
    elmt.current_version_date = convert_date_format(form['cur_date']) if form['cur_date'] else None
    elmt.previous_version = form['pre_ver']
    elmt.previous_version_date = convert_date_format(form['pre_date']) if form['pre_date'] else None
    elmt.previous2_version = form['pre2_ver']
    elmt.previous2_version_date = convert_date_format(form['pre2_date']) if form['pre2_date'] else None
    elmt.note = form['note']

    try:
        session.commit()
        succ = 1
    except:
        session.rollback()
        succ = 0
    session.close()
    return succ == 1

def del_element_byid(DBSession, elmt_id):
    """
    Used to delete one element from SQL DB.
    First introduced to handle the '/element_x' URL user triggered deletion.
    Different from delete project, only allow when there is no project Element usage data.
    Inputs:
        DBSession: Used to make a session for accessing SQL DB.
        elmt_id: int. The element_id value in SQL DB.
    Outputs:
        No name, a bool value to indicate if the deletion is successful or not.
    """
    session = DBSession()
    elmt = session.query(Elements).filter_by(element_id=elmt_id).first()

    #Check which projects uses this elements (cause that deleting doesn't work)
    elmt_usages = session.query(ProjectElementUsages).filter_by(element_id=elmt_id).all()
    projects =[]
    for usage in elmt_usages:
        project_id = usage.project_id
        project = get_project_name_byid(DBSession, project_id)
        projects.append(project)
    projects = list(set(projects)) #remove double values

    # Check which Templates uses this elements (cause that deleting doesn't work)
    elmt_templs = session.query(ElementTemplateContents).filter_by(element_id=elmt_id).all()
    templates = []
    for template in elmt_templs:
        template_id = template.template_id
        template = get_template(DBSession, template_id)[0]
        templates.append(template)

    # Check which ChangeRequests uses this elements (cause that deleting doesn't work)
    elmt_reqs = session.query(ChangeRequestsElements).filter_by(element_id=elmt_id).all()
    requests = []
    for request in elmt_reqs:
        request_id = request.change_request_id
        request = get_change_request_by_id(DBSession, request_id)
        requests.append(request)

    if len(projects) == 0 and len(templates) == 0 and len(requests) == 0: #only delete when record exists on no other place
        session.delete(elmt)
        try:
            session.commit()
            msg = u'redirect'
        except:
            session.rollback()
            msg = u'Oops! Something went wrong..'
    else:
        msg = u"This element can't be deleted, because there are records depending on it. " \
              u"Projects: {0}. Templates: {1}. Change Requests: {2}.".format(', '.join(map(str, projects, )),
                                                                            ', '.join(map(str, templates, )),
                                                                            ', '.join(map(str, requests, )))
    session.close()
    return msg

def query_element_usages(DBSession, elmt_id, form):
    """
    Used to query ProjectElementUsages table for a given Element.
    Inputs:
        DBSession: SQLAlchemy session maker.
        elmt_id: int. the element_id in IPIT DB.
        form: dictionary, containing filter conditions for the query.
          -'project_name'
          -'start_year'
          -'start_week'
          -'end_year'
          -'end_week'
    Outputs:
        column_names: list of column names.
        data: List of tuples.
    """
    session = DBSession()
    # Using time line filter
    time_line = map(int, [form['str_y'], form['str_w'], form['end_y'],
        form['end_w']])

    query_obj = (session.query(Projects.name, ProjectElementUsages.year,
        ProjectElementUsages.week, ElementUsages.element_usage)
        .filter(ProjectElementUsages.element_id == elmt_id)
        .filter(ProjectElementUsages.project_id == Projects.project_id)
        .filter(ProjectElementUsages.element_usage_id == ElementUsages.element_usage_id)
        )
    if form['project_name'] != "All Projects":
        query_obj = query_obj.filter(Projects.name == form['project_name'])

    if time_line[0] == time_line[2]:
        query_obj = (query_obj
            .filter(ProjectElementUsages.year == time_line[0])
            .filter(ProjectElementUsages.week >= time_line[1])
            .filter(ProjectElementUsages.week <= time_line[3])
            )
        query_result = query_obj.all()
    else:
        query_result = []
        for year in range(time_line[0], time_line[2] + 1):
            if year == time_line[0]:
                query_result += (query_obj
                    .filter(ProjectElementUsages.year == year)
                    .filter(ProjectElementUsages.week >= time_line[1])
                    ).all()
            elif year == time_line[2]:
                query_result += (query_obj
                    .filter(ProjectElementUsages.year == year)
                    .filter(ProjectElementUsages.week <= time_line[3])
                    ).all()
            elif time_line[0] < year < time_line[2]:
                query_result += query_obj.filter(ProjectElementUsages.year == year).all()

    session.close()
    data_before_pivot = [
        x[:1] + (tuple(x[1:3]),) + x[3:] for x in query_result
        ]
    x_series = gen_yw_list(*time_line)

    data = cross_tab(data_before_pivot, x_series)
    column_names = ['Project Name'] + [str(y) + '_' + str(w) for y, w in x_series]
    return column_names, data

def get_element_byid(DBSession, elmt_id):
    """
    Used in "/element_x" page handler to get a dictionary which stores
    the element information.
    Inputs:
        DBSession: SQLAlchemy DB session maker.
        elmt_id: int, the element id.
    Outputs:
        element_dict: dictionary with following keys.
        -'node'
        -'hostname'
        -'cur_ver'
        -'cur_date'
        -'pre_ver'
        -'pre_date'
        -'pre2_ver'
        -'pre2_date'
        -'note'
        If the element id doesn't exists, return None.
    """
    session = DBSession()
    element = (session.query(Nodes.node, Elements.hostname,
        Elements.current_version, Elements.current_version_date,
        Elements.previous_version, Elements.previous_version_date,
        Elements.previous2_version, Elements.previous2_version_date,
        Elements.note)
        .filter(Elements.node_id == Nodes.node_id)
        .filter(Elements.element_id == elmt_id)
        .first()
        )  # Result like (u'CG', u'GVTEEC1', None, None, None, None, None, None, u'Data')
    session.close()
    element = replace_date(list(element))

    if element:
        return dict(zip(['node', 'hostname', 'cur_ver', 'cur_date',
            'pre_ver', 'pre_date', 'pre2_ver', 'pre2_date', 'note'], element)
            )
    else:
        return None

def add_employee(DBSession, form):
    """
    Used to add a new element to table Elements
    DBSession: sqlalchemy session maker.
    Inputs:
        form: HTTP request form from '/new_employee'
          -'name'
          -'hours'
          -'hours_available'
          -'department'
          -'email'
          -'contract_type'
          -'reg_num'
    Outputs:
        A string describing successful or not and why.
    """
    # Added 27-Nov --  Start
    valid_name, msg = is_valid_name(normalize_db_value(form['name']), name_list=gen_employee_list(DBSession))
    if not valid_name:
        return msg
    # Added 27-Nov -- finish
    session = DBSession()
    employee = Employees(
        name=valid_name,
        hours=form['hours'] if form['hours'] else None,
        hours_available=form['hours_available'] if form['hours_available'] else None,
        department_id=session.query(Departments.department_id).filter_by(
        department=form['department']).first()[0], email=form['email'],
        contract_type=form['contract_type'], registration_number=form['reg_num'],
        if_left=False  # Modified on 27_nov. This field was missing so adding a new employee with empty field.
        )
    session.add(employee)
    try:
        session.commit()
        msg = u"{0} added successfully.".format(valid_name)
    except IntegrityError:
        msg = u"Adding failed, This name or registration number already exists."
        session.rollback()
    session.close()
    return msg

def add_time_filter(in_query, table, time_line):
    """
    This function is used to update a SQLAlchemy query object by adding filter
    conditions about year and week.
    Inputs:
        in_query: an object of type "sqlalchemy.orm.query.Query"
        table: class name of a ORM table.
           1 This table must contain column year and week.
           2 It should be already a part of the in_query so that we can filter
           the result.
        time_line: a list to define start week and finish week.
        [start_year, start_week, end_year, end_week].
           The time_line values are assumed to be valid, so this function puts
           no checks on.
    Outputs:
        An updated query object.

    Example:
        We want to query table ProjectPlans all records between 2015
        week 50 to 2016 week 3. Codes below:
        ...
        t = [2015, 50, 2016, 3]
        raw_query = session.query(ProjectPlans)
        updated_query = add_time_filter(raw_query, ProjectPlans, t)
        ...
    """
    sy, sw, ey, ew = time_line  # s: start, e: end, y: year, w: week
    if sy == ey:
        return in_query.filter((table.year == sy) & 
            (table.week >= sw) & (table.week <= ew)
            )
    if sy < ey:
        return in_query.filter(
            ((table.year == sy) & (table.week >= sw)) | 
            ((table.year > sy) & (table.year < ey)) | 
            ((table.year == ey) & (table.week <= ew))
            )

def gen_weekyear_list(startdate, enddate):
    """
    Description:
        This functions returns a  list with the weeknumbers and years 
        between two dates that are given as input.
    Input:
        - startdate
        - enddate
    Output:
        - list with corresponding weeknumbers and years
    """

    dates = []
    next_day = startdate
    
    while True:
        if next_day > enddate:
            break
        dates.append(next_day)
        next_day += timedelta(days=7) # jump per week
    weekyears = []
    
    for date in dates:
        pair = []
        year = date.isocalendar()[0]
        week = date.isocalendar()[1]
        pair.append(year)
        pair.append(week)
        weekyears.append(pair)
        
    # make sure the last week is also printed
    if weekyears[-1][1] < enddate.isocalendar()[1]: 
        endpair = []
        year = enddate.isocalendar()[0]
        week = enddate.isocalendar()[1]
        endpair.append(year)
        endpair.append(week)
        weekyears.append(endpair)

    return weekyears
    

def add_date_filter(in_query, time_line, ids = 3):
    """
    Description:
        This function is made to convert a query with two date time objects, in multiple
        queries with a row for each week. 
    Input:
        - query, with date displayed in datetime objects 
        - time_line
    Output:
        - rows with status per year and week. This means that one row could be converted
        to multiple rows, as in the example. 
        - thereafter, the time filter is applied 
    Example: 
    
        this row:
        
        (u'Change Request Name', 5, u'Applicant name', u'112 Improvement Study', 56, u'Possible impact', u'1Me
        diation', u'zie MMD', 593, u'', datetime.date(2017, 3, 9), datetime.date(2017, 3
        , 29), u'In progress')
        
        would be converted to these rows:
        
        (u'Change Request Name', 5, u'Applicant name', u'112 Improvement Study', 56, u'Possible impact', u'1Me
        diation', u'zie MMD', u'In progress', 593, u'', 2017, 11)
        (u'Change Request Name', 5, u'Applicant name', u'112 Improvement Study', 56, u'Possible impact', u'1Me
        diation', u'zie MMD', u'In progress', 593, u'', 2017, 12)
        (u'Change Request Name', 5, u'Applicant name', u'112 Improvement Study', 56, u'Possible impact', u'1Me
        diation', u'zie MMD', u'In progress'593, u'', 2017, 13)  
    """
    sy, sw, ey, ew = time_line  # s: start, e: end, y: year, w: week
    
    data = []
    for row in in_query.all():
        
        for yearweek in gen_weekyear_list(row[12 + ids], row[13 + ids]):
            
            if sy == ey:
                if yearweek[1] >= sw and yearweek[1] <= ew and yearweek[0] == sy:
                    row = row[:12 + ids] + (yearweek[0], yearweek[1])
                    data.append(row)
                    
            if sy < ey:
                if (yearweek[0] == sy and yearweek[1] >= sw) or (yearweek[0] > sy and yearweek[0] < ey) or (yearweek[0] == ey and yearweek[1] <= ew):
                    row = row[:12 + ids] + (yearweek[0], yearweek[1])
                    data.append(row)
    return data

def add_conflicted_projects(DBSession, old_data, ids = 3, report = False):
    """
    Description: function for report type "change request" to add the conflicted projects to the change request"
    Example:
    change request data: 
        (u'Upgrade PCRF SPC110', 2, u'Paling Kees', u'VoLTE', 7, u'Possible impact', u'PCRF', u'GVTEPP3', 13, datetime.date(2017, 4, 6),
        u'10:00', datetime.date(2017, 4, 6), u'12:00', u'', u'Accepted', 2017, 14)
    data of conflicted project(s):
        [[u'Groeneveld Martin', u'PCRF', u'GVTEPP3', u'Future of Mobile Step 5', u'Test uitvoering'],
        [u'Alkemade Willem', u'PCRF', u'GVTEPP3', u'Converged Messaging', u'Test uitvoering']]
    Results in:
        [(u'Upgrade PCRF SPC110', 2, u'Paling Kees', u'VoLTE', 7, u'Possible impact', u'PCRF', u'GVTEPP3', 13, datetime.date(2017, 4, 6),
        u'10:00', datetime.date(2017, 4, 6), u'12:00', u'', u'Accepted', u'Groeneveld Martin', u'Future of Mobile Step 5', u'Test uitvoering',
        2017, 14), (u'Upgrade PCRF SPC110', 2, u'Paling Kees', u'VoLTE', 7, u'Possible impact', u'PCRF', u'GVTEPP3', 13, datetime.date(2017, 4, 6),
        u'10:00', datetime.date(2017, 4, 6), u'12:00', u'', u'Accepted', u'Alkemade Willem', u'Converged Messaging', u'Test uitvoering', 2017, 14)]
    When there are no conlicted projects (conflicted projects list is empty), the new row(s) only contain information about the change request itself, for example:
        [u'request', 40, Applicant, u'000 TEST voorbeeld project IPIT netwerk', 29, u'No impact', u'1Mediation', u'Judith', 690, u'', datetime.date(2017, 4, 6),
        u'10:00', datetime.date(2017, 4, 6), u'12:00', u'', u'In progress', u'', u'', u'', 2017, 14]
    """
    new_data = []
    for old_row in old_data:
        time_line = [old_row[12 + ids], old_row[13 + ids], old_row[12 + ids], old_row[13 + ids]] #conflicted elements are calculated per week
        if report == True:
            conflicted_projects = get_conflicted_elements(DBSession, time_line, [get_element_id(DBSession, "{0}:{1}".format(old_row[4], old_row[5]))])[0]
        else:
            conflicted_projects = get_conflicted_elements(DBSession, time_line, [old_row[5 + ids]])[0]
        if not conflicted_projects: # a row is added with only the change request information
            new_row = list(old_row)
            new_row.insert(12 + ids, u'')
            new_row.insert(13 + ids, u'')
            new_row.insert(14 + ids, u'')
            new_data.append(tuple(new_row))
        for project in conflicted_projects:
            new_row = list(old_row)
            new_row.insert(12 + ids, project[0])
            new_row.insert(13 + ids, project[3])
            new_row.insert(14 + ids, project[4])
            new_data.append(tuple(new_row))
     
    return new_data

def get_demand_hours(DBSession, time_line, role_id=3):
    """
    Description:
        Used for "Person Project Matching".
        Given a time line and a role_id (tester is 3 and Testmanager is 4)
        Return all projects demanding hours.
    Inputs:
        DBSession: SQLAlchemy session maker. Used to generate a session querying
        IPIT DB.
        time_line: a list to define start week and finish week. [start_year,
        start_week, end_year, end_week].
        role_id: The ID of a project role. Default 3.
    Outputs:
        target_data: list of lists. Each list contains
        [prject name, project ID, hours for wk1, hours2,...]

    """
    session = DBSession()
    raw_query = session.query(Projects.name, ProjectPlans.project_id,
        ProjectPlans.year, ProjectPlans.week, ProjectPlans.hours).filter(
        ProjectPlans.role_id == role_id).filter(
        Projects.project_id == ProjectPlans.project_id)
    raw_query = add_time_filter(raw_query, ProjectPlans, time_line)
    raw_data = raw_query.order_by(Projects.name).all()
    session.close()
    target_data = cross_tab([
        [x[0], x[1], (x[2], x[3]), float(x[4])] for x in raw_data],
        gen_yw_list(*time_line))

    return target_data

def gen_element_list(DBSession, full=False):
    """
    Description:
        Used to make a list of elements. The list contains node type and Element Hostname
        by default. And when optional parameter full is set to True, the list contains more
        Columns.
    Input:
        DBSession, used to query IPIT DB
        full: controls whether this is for the /elements page which requires
    Outputs:
        List of tuples, each tuple is (Element node + hostnames (strings)).
    """
    session = DBSession()
    # Query
    if full:
        q = session.query(Elements.element_id, Domains.domain, Nodes.node,
            Elements.hostname, Elements.note)
    else:
        q = session.query(Nodes.node, Elements.hostname)
    # Joins
    q = q.filter(Elements.node_id == Nodes.node_id)
    if full:
        q = q.filter(Nodes.domain_id == Domains.domain_id)
    # Order
    q = q.order_by(Nodes.node, Elements.hostname)
    result = q.all() if full else ['{0}:{1}'.format(x[0], x[1]) for x in q.all()]
    session.close()
    return result

def gen_usages_list(DBSession):
    """
    Get a list of all Element Usages.
    """
    session = DBSession()
    q = session.query(ElementUsages.element_usage).order_by(ElementUsages.element_usage)
    result = [x[0] for x in q.all()]
    session.close()
    return result

def valid_date(datestring):
    """Validates whether the input of the datestring is valid"""
    
    try:
        datetime.strptime(datestring, '%d-%m-%Y')
        return True
    except ValueError:
        return False

def is_valid_time_line(time_line):
    """
    Check the time_line.
    Return a validated value or None + error codes if it is not valid.
    Input:
        time_line: list of 4 strings/int
    return:
        valid_time_line: None or a list.
        errors, list of error string or empty string.
    """
    # initialization.
    valid_time_line = 1
    error_str_y = ""
    error_str_w = ""
    error_end_y = ""
    error_end_w = ""
    # Error hints
    NON_DIGITS_HINT = "Please only type digits."
    EMPTY_HINT = "This field can't be empty."
    YEAR_RANGE_HINT = "Only allow year between {0} and {1}."
    WEEK_NUM_LOW_HINT = "End week number starts from {0}."
    WEEK_NUM_HIGH_HINT = "Week number for year {0} must <= {1}."
    # In order to use .isdigit, force inputs to be strings.
    tl = map(str, time_line)
    # Check start year
    if not tl[0]:  # Empty?
        error_str_y = EMPTY_HINT
        valid_time_line = None
    elif not tl[0].isdigit():  # All digits?
        error_str_y = NON_DIGITS_HINT
        valid_time_line = None
    elif int(tl[0]) not in VALID_YEARS:  # Valid range?
        error_str_y = YEAR_RANGE_HINT.format(VALID_YEARS[0], VALID_YEARS[-1])
        valid_time_line = None
    if valid_time_line:
        valid_time_line = [int(tl[0])]
    # Check start week
    if valid_time_line:  # only check if the start year is valid.
        if not tl[1]:  # Empty
            error_str_w = EMPTY_HINT
            valid_time_line = None
        elif not tl[1].isdigit():  # All digites?
            error_str_w = NON_DIGITS_HINT
            valid_time_line = None
        elif int(tl[1]) < 1:
            error_str_w = WEEK_NUM_LOW_HINT.format(1)
            valid_time_line = None
        elif int(tl[1]) > the_last_week(int(tl[0])):
            error_str_w = WEEK_NUM_HIGH_HINT.format(tl[0], the_last_week(
                int(tl[0])))
            valid_time_line = None
        if valid_time_line:
            valid_time_line.append(int(tl[1]))
    # Check the finishing year
    if valid_time_line:
        if not tl[2]:  # Empty?
            error_end_y = EMPTY_HINT
            valid_time_line = None
        elif not tl[2].isdigit():  # All digits?
            error_end_y = NON_DIGITS_HINT
            valid_time_line = None
        elif int(tl[2]) < int(tl[0]) or int(tl[2]) > VALID_YEARS[-1]:  # Valid range?
            error_end_y = YEAR_RANGE_HINT.format("start year (" + str(tl[0]) + ")", VALID_YEARS[-1])
            valid_time_line = None
        if valid_time_line:
            valid_time_line.append(int(tl[2]))
    # Check the end week
    if valid_time_line:  # only check if the start year is valid.
        if not tl[3]:  # Empty
            error_end_w = EMPTY_HINT
            valid_time_line = None
        elif not tl[3].isdigit():  # All digites?
            error_end_w = NON_DIGITS_HINT
            valid_time_line = None
        elif int(tl[3]) < 1:  #
            error_end_w = WEEK_NUM_LOW_HINT.format(1)
            valid_time_line = None
        elif int(tl[0]) == int(tl[2]) and int(tl[3]) < int(tl[1]):
            error_end_w = WEEK_NUM_LOW_HINT.format(int(tl[1]))
            valid_time_line = None
        elif int(tl[3]) > the_last_week(int(tl[2])):
            error_end_w = WEEK_NUM_HIGH_HINT.format(tl[2], the_last_week(
                int(tl[2])))
            valid_time_line = None
        if valid_time_line:
            valid_time_line.append(int(tl[3]))
    errors = [error_str_y, error_str_w, error_end_y, error_end_w]
    return valid_time_line, errors

def is_valid_date_time(start_dates, start_times, end_dates, end_times, elements):
    """Check whether the start date and time and the end date and time are valid
    on the pages of "change requests"
        Input:
        start_date
        start_time
        end_date
        end_time
        elements
    return:
        valid_date_time: None or a list.
        errors, list of error string or empty string."""
    
        # initialization.
    valid_date_time = 1
    error_str_d = ""
    error_str_t = ""
    error_end_d = ""
    error_end_t = ""
    elements_error = ""
    errors = ["","","",""]
    
    EMPTY_HINT = "This field can't be empty."
    NON_DIGITS_HINT = "Please give valid date input for Element {}."
    YEAR_RANGE_HINT = "Only allow year between {0} and {1}."
    YEAR_NUM_LOW_HINT = "End date {0} must be later than {1} for Element {2}."
    HOUR_RANGE_HINT = "Time {0}:00 must be earlier than {1}:00 for Element {2}"
    NO_ELEMENTS_HINT = "No elements selected"
    NO_END_TIME_HINT = "End time is missing"
    NO_START_TIME_HINT = "Start time is missing"
    
    elements_check = [element for element in elements if element != '']
    if len(elements_check) == 0:
        elements_error = NO_ELEMENTS_HINT
        errors.append(elements_error)
        valid_date_time = 0
        
    for i in range(len(elements)):
        element = elements[i]
        
        if element != '': #only validate date/times when element is chosen 
            start_date = start_dates[i]
            end_date = end_dates[i]
            start_time = start_times[i]
            end_time = end_times[i]
            
            date_time = [start_date, start_time.split(":")[0], end_date, end_time.split(":")[0]] # only get the ints from the time
            if date_time[0]:
                if valid_date(date_time[0]):
                    start_year = date_time[0].split('-')[2]
            if date_time[2]:
                if valid_date(date_time[2]):
                    end_year = date_time[2].split('-')[2]

            # Check start date
            if not date_time[0]:  # Empty?
                error_str_d = EMPTY_HINT
                valid_date_time = None
            elif valid_date(date_time[0]) == False:
                error_str_d = NON_DIGITS_HINT.format(element)
                valid_date_time = None
            elif int(start_year) not in VALID_YEARS:  # Valid range?
                error_str_d = YEAR_RANGE_HINT.format(VALID_YEARS[0], VALID_YEARS[-1], element)
                valid_date_time = None
            elif valid_date_time:
                valid_date_time = [(date_time[0])]
            
            # Check start time
            if valid_date_time:
                if not date_time[1]:  # Empty?
                    error_str_t = EMPTY_HINT
                    valid_date_time = None
                else:
                    if date_time[3].isnumeric() and date_time[1] == "NA":
                        error_str_t = NO_START_TIME_HINT
                        valid_date_time = None
                if valid_date_time:
                    valid_date_time.append(date_time[1])
            
            # Check end date
            if valid_date_time:
                if not date_time[2]:  # Empty?
                    error_end_d = EMPTY_HINT
                    valid_date_time = None
                elif valid_date(date_time[2]) == False:
                    error_end_d = NON_DIGITS_HINT.format(element)
                    valid_date_time = None
                elif convert_date_format(date_time[2]) < convert_date_format(date_time[0]):
                    error_end_d = YEAR_NUM_LOW_HINT.format(date_time[2], date_time[0], element)
                    valid_date_time = None
                elif int(end_year) > VALID_YEARS[-1]:  # Valid range?
                    error_end_d = YEAR_RANGE_HINT.format(VALID_YEARS[0], VALID_YEARS[-1], element)
                    valid_date_time = None
                elif valid_date_time:
                    valid_date_time.append(date_time[2])
                    
            # Check the end time
            if valid_date_time:
                if not date_time[3]:  # Empty?
                    error_end_t = EMPTY_HINT
                    valid_date_time = None
                else:
                    if date_time[3].isnumeric() and date_time[1].isnumeric():
                        if date_time[0] == date_time[2] and int(date_time[3]) < int(date_time[1]):
                            error_end_t = HOUR_RANGE_HINT.format(date_time[1], date_time[3], element)
                            valid_date_time = None
                    if date_time[1].isnumeric() and date_time[3] == "NA":
                        error_end_t = NO_END_TIME_HINT
                        valid_date_time = None
                if valid_date_time:
                    valid_date_time.append(date_time[3])
            errors = [error_str_d, error_str_t, error_end_d, error_end_t]
    return valid_date_time, errors

   # if start_date == end_date:
def get_project_name_byid(DBSession, prj_id, zero_name="All Projects"):
    """
    Given project id value, return project name.
    If the prj_id == 0, return zero_name. By default,  zero_name="All Projects"
    If id is invalid, return None
    """
    if int(prj_id) == 0:
        return zero_name
    else:
        session = DBSession()
        q = session.query(Projects.name).filter(Projects.project_id == int(prj_id)).first()
        session.close()
        if q:
            return q[0]

def get_dept_name_byid(DBSession, dept_id):
    """
    Given department id, return department name.
    If id is invalid, return None
    """
    session = DBSession()
    q = session.query(Departments.department).filter(
        Departments.department_id == int(dept_id)).first()
    session.close()
    if q:
        return q[0]

def get_role_name_byid(DBSession, role_id):
    """
    Given role id, return role name.
    If id is invalid, return None
    """
    session = DBSession()
    q = session.query(Roles.role).filter(Roles.role_id == int(role_id)).first()
    session.close()
    if q:
        return q[0]

def update_project_human_plan(DBSession, time_line, hours, project_id, role_id, department_id):
    """
    Used to update Table ProjectPlans.
    Note hours value 0 means remove.
    Inputs:
        time_line: list of 4 int.
        hours: float
        project_id, role_id, department_id: int

    Output:
        result_msg: String. If successfully updated, provide message starts with "SUC" If failed starts with "ERR"
    """
    # Query existing value.
    session = DBSession()
    q = session.query(ProjectPlans).filter(
        (ProjectPlans.project_id == project_id) & 
        (ProjectPlans.role_id == role_id) & 
        (ProjectPlans.department_id == department_id))
    q = add_time_filter(q, ProjectPlans, time_line)

    # Remove existing value.
    result = q.all()
    for r in result:
        session.delete(r)
    result_msg = "SUCCESSFUL: {} records deleted".format(len(result))

    if float(hours) > 0.00001:  # Hours 0 means deleting records.
        kwargs = {}
        kwargs['hours'] = float(hours)
        kwargs['project_id'] = project_id
        kwargs['department_id'] = department_id
        kwargs['role_id'] = role_id
        yw_list = gen_yw_list(*time_line)
        for t in yw_list:
            record = ProjectPlans(year=t[0], week=t[1], **kwargs)
            session.add(record)
        result_msg = "SUCCESSFUL: {} records updated.".format(len(yw_list))
    try:
        session.commit()
    except:
        session.rollback()
        result_msg = "ERROR:" + sys.exc_info()[0]
    session.close()

    return result_msg

def get_project_info(DBSession, prj_id=None):
    """
    Used to generate a table to show in page /projects
    Option parameter prj_id. When not present. Result is generated for a whole projects list view.
    When prj_id present, result is for one project to show in page /single_project
    """
    session = DBSession()
    # First set Common query part
    # nkwargs = [Projects.name, Projects.management, Employees.name, Projects.code,
    #     Priorities.priority, Departments.department, Domains.domain,
    #     Projects.date_EL, Projects.active]

    # nkwargs = [Projects.name, Projects.management, Employees.name, Employees.name, Projects.code,
    #            Priorities.priority, Departments.department, Domains.domain,
    #            Projects.date_EL, Projects.active]

    nkwargs = [Projects.name, Projects.management, Employees.name, Managers.name, Projects.code,
               Priorities.priority, Departments.department, Domains.domain,
               Projects.date_EL, Projects.active]
    # Depends on the situation, modify the query inputs.
    if prj_id:
        nkwargs.append(Projects.note)
        q = session.query(*nkwargs).filter(Projects.project_id == prj_id)
    else:
        nkwargs.insert(0, Projects.project_id)
        q = session.query(*nkwargs)

    q = q.outerjoin(Employees, Projects.test_manager_id == Employees.employee_id
        ).outerjoin(Managers, Projects.implementation_manager_id == Managers.manager_id
        ).outerjoin(Priorities, Projects.priority_id == Priorities.priority_id
        ).outerjoin(Departments, Projects.department_id == Departments.department_id
        ).outerjoin(Domains, Projects.domain_id == Domains.domain_id
        ).order_by(Projects.active.desc(), Projects.date_EL.desc())

    # q = q.outerjoin(Employees, Projects.test_manager_id == Employees.employee_id
    #     ).outerjoin(Priorities, Projects.priority_id == Priorities.priority_id
    #     ).outerjoin(Departments, Projects.department_id == Departments.department_id
    #     ).outerjoin(Domains, Projects.domain_id == Domains.domain_id
    #     ).order_by(Projects.active.desc(), Projects.date_EL.desc())
    if prj_id:
        result = q.one()
    else:
        result = q.all()
    session.close()
    return result

def get_change_request_info(DBSession, req_id=None):
    """
    Used to generate a table to show in page /change_requests
    Option parameter req_id. When not present. Result is generated for a whole change requests list view.
    When req_id present, result is for one change request to show in page /single_change_request
    """
    session = DBSession()
    
    # First set Common query part
    nkwargs = [ChangeRequests.description, Applicants.applicant, Projects.name, Impact.impact, Nodes.node,
               Elements.hostname, ChangeRequestsElements.start_date, ChangeRequestsElements.start_time, ChangeRequestsElements.end_date, 
               ChangeRequestsElements.end_time, ChangeRequestsElements.note, Status.status]
    # Depends on the situation, modify the query inputs.
    if req_id:
        nkwargs.append(ChangeRequestsElements.note)
        q = session.query(*nkwargs).filter(ChangeRequests.change_request_id == req_id).order_by(ChangeRequestsElements.request_element_id)
    else:
        nkwargs.insert(0, ChangeRequests.change_request_id)
        q = session.query(*nkwargs).order_by(ChangeRequestsElements.request_element_id)

    q = q.outerjoin(Applicants, ChangeRequests.applicant_id == Applicants.applicant_id
        ).outerjoin(Impact, ChangeRequests.impact_id == Impact.impact_id
        ).outerjoin(Projects, ChangeRequests.project_id == Projects.project_id
        ).outerjoin(Status, ChangeRequests.status_id == Status.status_id    
        ).outerjoin(ChangeRequestsElements, ChangeRequests.change_request_id == ChangeRequestsElements.change_request_id                
        ).outerjoin(Elements, ChangeRequestsElements.element_id == Elements.element_id
        ).outerjoin(Nodes, Elements.node_id == Nodes.node_id)
##      
    if req_id:
        result = q.all()
    else:
        result = q.all()
        
    session.close()
    return result

def get_conflicted_elements(DBSession, valid_time_line, element_ids):
    """ 
    Description: Given element and start date/end date.
    Show a table with the projects that are hit by this change.
    Inputs:
        description
        valid_time_line
        element(s)
    fixed columns:
        test_manager
        node/hostname
        project
    Output: 
        week/year number with usage 
     """
     
    session = DBSession()
    q = session.query(
            Employees.name, Nodes.node, Elements.hostname,
            Projects.name, ProjectElementUsages.year,
            ProjectElementUsages.week, ElementUsages.element_usage)
    
    q = add_time_filter(q, ProjectElementUsages, valid_time_line)
    
    q = q.filter(
        (Projects.test_manager_id == Employees.employee_id) &
        (ProjectElementUsages.element_id == Elements.element_id) &
        (ProjectElementUsages.element_usage_id == ElementUsages.element_usage_id) &
        (ProjectElementUsages.project_id == Projects.project_id) & 
        (Elements.node_id == Nodes.node_id) &
        (Nodes.domain_id == Domains.domain_id ) )
    
    # Filter
    q = q.filter(ProjectElementUsages.element_id.in_(element_ids))
    
    q = q.order_by(Nodes.node, Elements.hostname)
    
    yw_list = gen_yw_list(*valid_time_line)
    d = [x[:4] + ((x[4], x[5]), x[6]) for x in q.all()]
    update_msg = "SUCCESSFUL: found {} conflicting records.".format(len(d))
    session.close()
    data = cross_tab(d, yw_list, 4)
    column_names = ['Test Manager', 'Node', 'Hostname', 'Project']  + [" " + str(x[1]) + '-' + str(x[0]) for x in yw_list]

    return data, column_names
    
def get_allocation_plan_by_prjid(DBSession, time_line, project_id):
    """
    Description:
        Given project id, time line.
        Show a table of the allocated data.
        Introduced for handle 'allocation_plan_edit'
    Inputs:
        time_line
    Outputs:
        data and column_names
    """
    valid_time_line = is_valid_time_line(time_line)[0]

    session = DBSession()
    q = session.query(Departments.department, Employees.name, ProjectHumanUsages.year,
        ProjectHumanUsages.week, ProjectHumanUsages.hours)

    # Add filter
    q = q.filter(
        (Departments.department_id == Employees.department_id) & 
        (Employees.employee_id == ProjectHumanUsages.employee_id) & 
        (ProjectHumanUsages.project_id == int(project_id))
        )
    q = add_time_filter(q, ProjectHumanUsages, valid_time_line)
    #
    raw_data = [x[:2] + ((x[2], x[3]), float_or_none(x[4])) for x in q.all()]
    x_series = gen_yw_list(*valid_time_line)
    data = cross_tab(raw_data, x_series, unique_len=2)
    column_names = ['Department', 'Employee']
    column_names += gen_year_week_columns(*valid_time_line)[0].split(', ')

    return data, column_names

def update_human_allocation(DBSession, time_line, hour, project_id, role_id, employee_id, note=None):
    """
    Description:
        Given time line, hours per week, project_id, role_id, employee id and note (option).
        Used to update table ProjectHumanUsages.
    Inputs:
        time_line: list of str or int.
        hour: str or float.
        project_id: int or str.
        role_id: int or str.
        employee_id: int or str.
    Output:
        update_msg: string. Tells it is SUCCESSFUL or ERROR. And how many records impacted.
    """
    # Query existing value.
    session = DBSession()
    q = session.query(ProjectHumanUsages).filter(
        (ProjectHumanUsages.project_id == project_id) & 
        (ProjectHumanUsages.role_id == role_id) & 
        (ProjectHumanUsages.employee_id == employee_id))
    valid_time_line = is_valid_time_line(time_line)[0]
    q = add_time_filter(q, ProjectHumanUsages, valid_time_line)

    # Remove existing value.
    result = q.all()
    for r in result:
        session.delete(r)
    result_msg = "SUCCESSFUL: {} records deleted".format(len(result))

    if float(hour) > 0.00001:  # Hour 0 means deleting records.
        kwargs = {}
        kwargs['hours'] = float(hour)
        kwargs['project_id'] = project_id
        kwargs['employee_id'] = employee_id
        kwargs['role_id'] = role_id
        kwargs['note'] = note
        yw_list = gen_yw_list(*valid_time_line)
        for t in yw_list:
            record = ProjectHumanUsages(year=t[0], week=t[1], **kwargs)
            session.add(record)
        result_msg = "SUCCESSFUL: {} records updated.".format(len(yw_list))
    try:
        session.commit()
    except:
        session.rollback()
        result_msg = "ERROR:" + sys.exc_info()[0]
    session.close()

    return result_msg

def update_human_allocation_per_week(DBSession, hour_input, employee_id, project, valid_time_line):
    """
    Description
        This function is made for report type "Human Resoucres" at page /reports.
        This function stores the values that are edited in the table to the DB
    Input
        - DBSession
        - hour_input (contains list with values from the table)
        - employee_id
        - project_id
    Output
        - update_msg: tells if SUCCESFULL of ERROR and how many values are changed.
        
    """
    # Query existing values.
    session = DBSession()
    if project[0] == 0:
        project_id = Projects.project_id
    else:
        project_id = project[0]
    q = session.query(ProjectHumanUsages).filter(
                (ProjectHumanUsages.project_id == project_id) & 
                (ProjectHumanUsages.role_id == Roles.role_id) & 
                (ProjectHumanUsages.employee_id == employee_id))
    
    q = add_time_filter(q, ProjectHumanUsages, valid_time_line)
    
    yw_list = gen_yw_list(*valid_time_line)
    hour_inputs = split_list(hour_input, len(yw_list)) # make array for every project
    
    if project[0] == 0: # more projects might be queried
        q = q.order_by(Projects.name)
        result = q.all()    
        prjs = (r.project_id for r in result) # save id of projects
        prjs = unique(prjs)
    else:
        result = q.all()    
        prjs = [project[0]] #save id of one project
    
    n_prj = len(set([r.project_id for r in result])) # count amount of projects
    
    deleted = 0
    updated = 0
    added = 0
    for p, pr in enumerate(prjs):
        q_prj = q.filter(ProjectHumanUsages.project_id == pr)
        hours = hour_inputs[p]
        prj_result = q_prj.all()
        role_id = [project.role_id for project in prj_result]
        role_id = role_id[0]
        note = [project.note for project in prj_result]
        note = note[0]
        for count, yw in enumerate(yw_list):
            q_yw = q_prj.filter(ProjectHumanUsages.year == yw[0], ProjectHumanUsages.week == yw[1])
            db_rec = q_yw.one_or_none()
            if db_rec:
                yw_result = q_yw.one()
                if hour_is_zero(hours[count]): #delete record from database
                    session.delete(yw_result)
                    deleted += 1
                else: # update record in database
                    if yw_result.hours != float(hours[count]):
                        yw_result.hours = hours[count]
                        updated += 1
            else:
                if not hour_is_zero(hours[count]): # add record to database
                    kwargs = {'hours': float(hours[count]),
                              'project_id': pr,
                              'employee_id': employee_id,
                              'role_id': role_id,
                              'note': note,
                              'year': yw_list[count][0],
                              'week': yw_list[count][1]
                              }
                    record = ProjectHumanUsages(**kwargs)
                    session.add(record)
                    added += 1
    
    try:
        session.commit()
        result_msg = "SUCCESSFUL: {0} record(s) added, {1} record(s) updated and {2} record(s) deleted.".format(added, updated, deleted)
    except:
        session.rollback()
        result_msg = "ERROR:" + str(sys.exc_info()[0])
    session.close()

    return result_msg
    
def hour_is_zero(hour):
    """
    supporting function for update_human_allocation_per_week
    returns whether the given value is zero or empty
    """
    if hour == '' or hour == 0 or hour == 0.0:
        return True
    else:
        return False
    
def split_list(the_list, chunk_size):
    """
    supporting function for update_human_allocation_per_week
    
    input:
    list with hour inputs (for editable table) 
    example: [u'',u'7.0', u'8.0', u'9.0']
    output: 
    list is split in parts per project
    example (for two projects):  [[u'',u'7.0'],[u'8.0', u'9.0']]
    """
    result_list = []
    while the_list:
        result_list.append(the_list[:chunk_size])
        the_list = the_list[chunk_size:]
    return result_list

def unique( list ):
    """
    supporting function for update_human_allocation_per_week
    input: list
    output: list with unique parts, where the order is preserved 
    """ 
    uniq = []
    for i in list:
        if i not in uniq:
            uniq.append(i)
    return uniq

def gen_request_report(DBSession, rep, contain_id=True):
    """
    Inputs:
    - DBsession to acces ipit_db
    - rep: string from url with project id, weeks and years
    - Contain_id: neceserry to create a hyper link to the page /change_request
    Outputs:
    - data: nested array
    - column names: list with names of columns 
    - update_msg: summary message (string)
    """

    # rep : /peu_<int:prj_id>_<int:str_y>_<int:str_w>_<int:end_y>_<int:end_w>
    # Initialize
    rep = rep[1:].split('_')
    prj_id = int(rep[1])
    time_line = map(int, rep[2:])
    valid_time_line = is_valid_time_line(time_line)[0]
    
    session = DBSession()
    if contain_id:
        q = session.query(ChangeRequests.description, ChangeRequests.change_request_id, Applicants.applicant, Projects.name,
                          Projects.project_id, Impact.impact, Nodes.node, Elements.hostname, Elements.element_id,
                          ChangeRequestsElements.start_date, ChangeRequestsElements.start_time, ChangeRequestsElements.end_date,
                          ChangeRequestsElements.end_time, ChangeRequestsElements.note, Status.status, ChangeRequestsElements.start_date,
                          ChangeRequestsElements.end_date)
    else:
        q = session.query(ChangeRequests.description, Applicants.applicant, Projects.name, Impact.impact, Nodes.node,
               Elements.hostname, ChangeRequestsElements.start_date, ChangeRequestsElements.start_time, ChangeRequestsElements.end_date,
                          ChangeRequestsElements.end_time, ChangeRequestsElements.note, Status.status, ChangeRequestsElements.start_date,
                          ChangeRequestsElements.end_date)
    
    q = q.outerjoin(Applicants, ChangeRequests.applicant_id == Applicants.applicant_id
        ).outerjoin(Impact, ChangeRequests.impact_id == Impact.impact_id
        ).outerjoin(Projects, ChangeRequests.project_id == Projects.project_id
        ).outerjoin(Status, ChangeRequests.status_id == Status.status_id    
        ).outerjoin(ChangeRequestsElements, ChangeRequests.change_request_id == ChangeRequestsElements.change_request_id                
        ).outerjoin(Elements, ChangeRequestsElements.element_id == Elements.element_id
        ).outerjoin(Nodes, Elements.node_id == Nodes.node_id)
##      
    # Filter
    if prj_id > 0:  # prj_id = 0 : No reports for all projects.
        q = q.filter(ChangeRequests.project_id == prj_id)
        # Order
    q = q.order_by(ChangeRequestsElements.start_date, ChangeRequestsElements.start_time)
    session.close()
    
    if contain_id:
        raw_data = add_date_filter(q, valid_time_line)
        raw_data = add_conflicted_projects(DBSession, raw_data)
        raw_data = (convert_dates_for_table(raw_data))
    else:
        raw_data = add_date_filter(q, valid_time_line, ids = 0)
        raw_data = add_conflicted_projects(DBSession, raw_data, ids = 0, report = True)
        raw_data = (convert_dates_for_table(raw_data))

  # Fetch raw data
    if contain_id:
        d = [x[:9] + [str(x[9]) + ' ' + str(x[10])] + [str(x[11]) + ' ' + str(x[12])] + x[13:17] + [(x[18], x[19]), x[17]] for x in raw_data]
    else:
        d = [x[:6] + [str(x[6]) + ' ' + str(x[7])] + [str(x[8]) + ' ' + str(x[9])] + x[10:14] + [(x[15], x[16]), x[14]] for x in raw_data]
    update_msg = "SUCCESSFUL: {} records retrieved.".format(len(d))
    

    # Pivote along time
    yw_list = gen_yw_list(*valid_time_line)
    
    
    if contain_id:
        data = cross_tab(d, yw_list, 12)  
    else:
        data = cross_tab(d, yw_list, 9)  

    # Prepare
    column_names = (['Description', 'Applicant', 'Project', 'Impact', 'Node', 'Hostname', 'Start date', 'End date', 'Note', 'Status', 'Testmanager',
     'Conflicting project'] + [" " + str(x[1]) + '-' + str(x[0]) for x in yw_list])  # Use Swaen's format.

    return data, column_names, update_msg

def gen_peu_report(DBSession, rep, contain_id=True):
    """
    Inputs:
        DBSession: used to access IPIT DB.
        rep: a compount URL string.  '/peu_<int:prj_id>_<int:str_y>_<int:str_w>_<int:end_y>_<int:end_w>'
        It contains the filter information for this report.
        contain_id, bool val. default true.
        Controls whether in output data column 1,4,6, contains employee_id, element_id, project_id.
        This function is called in two situantion. Number 1, by page to give online display. In this case
        , we need to contain_id so that we can make hyper links to the items. Number 2, called when user want to
        down load a file. In this case, we don't need to contain the ids.
    Outputs:
        data: List of lists.
          Example of a sub list:
            contain_id = True
            data[0] is [u'Groeneveld Martin', 15, u'ARP HUB', u'ARP HUB 02', 595, u'Future of Mobile Step 5', 91, None, u'Configuratie aanpassing']
            contain_id = False
            data[0] is [u'Groeneveld Martin', u'ARP HUB', u'ARP HUB 02', u'Future of Mobile Step 5', None, u'Configuratie aanpassing']

        column_names: list of strings.
        update_msg: a summary message. string type.
    """
    # rep : /peu_<int:prj_id>_<int:str_y>_<int:str_w>_<int:end_y>_<int:end_w>
    # Initialize
    rep = rep[1:].split('_')
    prj_id = int(rep[1])
    time_line = map(int, rep[2:])
    valid_time_line = is_valid_time_line(time_line)[0]

    # Make query
    session = DBSession()
    if contain_id:
        q = session.query(
            Employees.name, Employees.employee_id, Nodes.node, Elements.hostname,
            Elements.element_id, Projects.name, Projects.project_id,
            ProjectElementUsages.note, ProjectElementUsages.year,
            ProjectElementUsages.week, ElementUsages.element_usage)
    else:
        q = session.query(
            Employees.name, Nodes.node, Elements.hostname,
            Projects.name, ProjectElementUsages.note, ProjectElementUsages.year,
            ProjectElementUsages.week, ElementUsages.element_usage)

    # OUTER JOIN 13-Sep Bug fix: Adding this out Join statement. Because some project has no Test Manager ID.
    q = q.select_from(Projects).outerjoin(Employees, Projects.test_manager_id == Employees.employee_id)

    # INNER JOIN
    q = q.filter(
        (ProjectElementUsages.element_usage_id == ElementUsages.element_usage_id) & 
        (ProjectElementUsages.element_id == Elements.element_id) & 
        (ProjectElementUsages.project_id == Projects.project_id) & 
        (Elements.node_id == Nodes.node_id))
    # Filter
    if prj_id > 0:  # prj_id = 0 : No reports for all projects.
        q = q.filter(ProjectElementUsages.project_id == prj_id)
    q = add_time_filter(q, ProjectElementUsages, valid_time_line)

    # Order
    q = q.order_by(Nodes.node, Elements.hostname)

    # Fetch raw data
    if contain_id:
        d = [x[:8] + ((x[8], x[9]), x[10]) for x in q.all()]
    else:
        d = [x[:5] + ((x[5], x[6]), x[7]) for x in q.all()]
    update_msg = "SUCCESSFUL: {} records retrieved.".format(len(d))
    session.close()

    # Pivote along time
    yw_list = gen_yw_list(*valid_time_line)
    if contain_id:
        data = cross_tab(d, yw_list, 7)  # set to 8 - 1 because the note doesn't account.
    else:
        data = cross_tab(d, yw_list, 4)  # set to 8 - 1 because the note doesn't account.

    # Prepare
    column_names = (['Test Manager', 'Node', 'Hostname', 'Project', 'Note'] + 
        # gen_year_week_columns(*time_line)[0].split(', ')
        [" " + str(x[1]) + '-' + str(x[0]) for x in yw_list])  # Use Swaen's format.

    return data, column_names, update_msg

def gen_phu_report(DBSession, rep, contain_id=True, employee_id = None):
    """
    Description:
        Used to query IPIT DB for ProjectHumanUsage report for page /reports.
        rep is a string that contains query filter information.
        rep :: '/phu_<int:prj_id>_<int:str_y>_<int:str_w>_<int:end_y>_<int:end_w>'
    Inputs:
        DBSession, session maker to access IPIT DB.
        rep: string. Tells the query information.
        contain_id: optional input. Decides if employee_id and project_id are included in the new_data.

    Outputs:
        data: A 2D table. List of tuples. See IPIT Access tool, report Human resource/ Projects
        column_names: List of strings.
        update_msg: String.
    """
    # Initialize
    rep = rep[1:].split('_')
    prj_id = int(rep[1])  # 0 means All projects.
    time_line = map(int, rep[2:])
    valid_time_line = is_valid_time_line(time_line)[0]

    # Make query
    session = DBSession()
    if contain_id:
        q = session.query(
                Departments.department, Employees.name, Employees.employee_id,
                Projects.name, Projects.project_id, Roles.role, Employees.contract_type,
                ProjectHumanUsages.note, ProjectHumanUsages.year, ProjectHumanUsages.week,
                ProjectHumanUsages.hours)
    else:
        q = session.query(
                Departments.department, Employees.name, Projects.name, Roles.role,
                Employees.contract_type, ProjectHumanUsages.note, ProjectHumanUsages.year,
                ProjectHumanUsages.week, ProjectHumanUsages.hours)

    # JOINs
    q = q.filter(
            (Departments.department_id == Employees.department_id) & 
            (Employees.employee_id == ProjectHumanUsages.employee_id) & 
            (ProjectHumanUsages.project_id == Projects.project_id) & 
            (ProjectHumanUsages.role_id == Roles.role_id))

    # Filters
    if prj_id:
        q = q.filter(ProjectHumanUsages.project_id == prj_id)
    if employee_id:
        q = q.filter(ProjectHumanUsages.employee_id == employee_id)
            
    q = add_time_filter(q, ProjectHumanUsages, valid_time_line)

    # Orders
    q = q.order_by(Departments.department, Employees.name, Projects.name)

    # Get Data
    d = q.all()
    update_msg = "SUCCESSFUL: {} records retrieved.".format(len(d))
    session.close()

    # Process Data
    if contain_id:
        data = [x[:8] + ('Assigned', (x[8], x[9]), float(x[10])) for x in d]  # Add one more column.
    else:
        data = [x[:6] + ('Assigned', (x[6], x[7]), float(x[8])) for x in d]

    # Pivot
    yw_list = gen_yw_list(*valid_time_line)
    if contain_id:
        data = cross_tab(data, yw_list, 8)
    else:
        data = cross_tab(data, yw_list, 6)
    # Prepare
    column_names = (['Department', 'Employee', 'Project', 'Role', 'Personel Type',
     'Note', 'Type'] + [" " + str(x[1]) + '-' + str(x[0]) for x in yw_list])

    if prj_id == 0:  # These extra rows are only added when query on "All projects"
        data = add_rows_phu_report(DBSession, data, time_line, contain_id=contain_id)

    return data, column_names, update_msg

def add_rows_phu_report(DBSession, data, time_line, contain_id=True):
    """
    Description:
        In page "/reports", we need to generate phu report. The direct query from SQL DB only contains
        allocated hours. But the report asks for available hours and difference hours per sub per
        project per week. This function is used to add available hours and difference hours.
        Note: The input data must be ordered. All record from same person must be together.
    Input:
        DBSession: session maker
        data: The query new_data, list of tuples
        time_line: list of 4 ints.
        contain_id: tells if the data contains employee_id and project_id.
        When containing id:
        # dept, name, employee_id, project, project_id, rold, contract_type, note, type, hour1, hour2, ...
        [('Innovation Test Data', 'Daamen Camille', 21, '4G EPC UGW capaciteit extensie', 50, 'Tester', 'OP', 'OP', 'Assigned', 10.0, 10.0, 10.0)]
        when not containing id:
        # dept, name, project, rold, contract_type, note, hour1, hour2, ...
        [('Innovation Test Data', 'Daamen Camille','4G EPC UGW capaciteit extensie', 'Tester', 'OP', 'OP', 'Assigned', 10.0, 10.0, 10.0)]
    Output:
        For each employee, a start row of available hours and an end row of difference hours.
        Difference = Available - sum(assigned)
    """
    # Initialization
    new_data = []
    if data:
        diff_rows = {}
        # diff_rows. A dictionary,
        # key: Employee name, value: a tuple of two element.
        # element 1 is the "header" in a difference row, element 2 is list of hours.
        # element 1 + element 2 we get a row in position of 'difference' for a employee
        last_name = None
        week_qty = len(gen_yw_list(*time_line))
        col_qty = len(data[0])
        # Scan the data row by row.
        for asgn_row in data:
            name = asgn_row[1]
            if not diff_rows.get(name):  # New name found.
                if last_name:
                    new_data.append(diff_rows.get(last_name))  # append last name's difference row to new_data
                avl_row = (asgn_row[:col_qty - week_qty - 2] + 
                        [None, "Available"] + gen_employee_hours(DBSession, name, time_line))  # Create available row for this name
                # Remove the project infor for this row. its location is 3 or 2 depends on the contain_id.
                avl_row[3 if contain_id else 2] = None
                # Updates when seeing a new name.
                new_data.append(avl_row)
                diff_rows[name] = avl_row[:col_qty - week_qty - 1] + ["Difference"
                    ] + avl_row[col_qty - week_qty:]
            # Updates at end of one loop
            diff_hours = diff_rows[name][col_qty - week_qty:]
            asgn_hours = asgn_row[col_qty - week_qty:]
            diff_rows[name][col_qty - week_qty:] = [float_or_zero(diff_hours[i])
             - float_or_zero(asgn_hours[i]) for i in range(week_qty)]
            new_data.append(asgn_row)
            last_name = name
        # Update for the last name after leave the loop.
        if last_name:
            new_data.append(diff_rows.get(last_name))
    return new_data

def temp_phu_data(DBSession, data, hour_input, valid_time_line, project, calculate_diff = False):
    """
    support function for page /reports, report type: "human resources"
    Description: The input data is saved in this variable, to render the template
    with the input, when it is not saved to the DB yet. 
    input:
        - data (nested array)
        - hour_input (array)
        - calculate_diff (bool)
    output:
        - data where the hours are replaced with hour_input
    
    When calculate_diff is true, this function also returns updated differences between available and assigned hours 
    """
    chunk_size = len(data[0][9:]) 
    hour_inputs = split_list(hour_input, chunk_size)
    data_len = len(data)
    new_data = []
    project_id = project[0]
    
    if project_id != 0: #when project is selected
        for i, row in enumerate(data): 
            row = row[:9] + hour_inputs[i-1]
            new_data.append(row)
    else: 
        for i, row in enumerate(data): # for all projects
            if i == 0 or i == data_len-1:
                if calculate_diff == False:
                    new_data.append(row)
            else: 
                row = row[:9] + hour_inputs[i-1]
                new_data.append(row)
        
        if calculate_diff == True:
            new_data = add_rows_phu_report(DBSession, new_data, valid_time_line)
        
    return new_data

def get_employee_byid(DBSession, emp_id, hide_sensitive=True):
    """
    Support function for page /employee_x
    emp_id is int.
    hide_sensitive means whether or not hide the hours info
    """
    session = DBSession()
    if hide_sensitive:
        q = session.query(Employees.name, Departments.department, Employees.email,
            Employees.contract_type, Employees.registration_number, Employees.if_left)
    else:
        q = session.query(Employees.name, Employees.hours, Employees.hours_available,
            Departments.department, Employees.email, Employees.contract_type,
            Employees.registration_number, Employees.if_left)
    q = q.filter(
        (Employees.employee_id == emp_id) & 
        (Employees.department_id == Departments.department_id))
    result = list(q.one())
    session.close()
    if not hide_sensitive:
        result[1:3] = map(float, result[1:3])  # Convert hours & hours_available from type Decimal to float.
    return result


def get_test_manager_email(DBSession, prj_id):
    """
    Support page handler /project_x.
    We use email to check if a logged web GUI user is the test manager of a project.

    If prj_id is 0, we retrieve all emails.
    """
    session = DBSession()
    q = session.query(Employees.email)
    q = q.filter(Employees.employee_id == Projects.test_manager_id)
    if prj_id == 0 or prj_id == '0':
        result = q.all()  # Some project doesn't have test manager.
        session.close()
        return [x[0] for x in result]
    else:
        q = q.filter(Projects.project_id == int(prj_id))
        result = q.one_or_none()  # Some project doesn't have test manager.
        session.close()
        if result:
            return result[0]

def is_valid_new_domain(DBSession, domain_name):
    """
    Support function for page handler /new_domain
    Verify if the domain name given by user is valid.
    Input:
        DBSession: SQLAlchemy session maker.
        domain_name: string, name of domain
    Output:
        valid_domain: string or None when not valid.
        msg: string, describe reason why not valid.
    """
    valid_domain, msg = None, ''
    if not domain_name:
        msg = "Domain can't be empty."
    elif domain_name in gen_domain_list(DBSession):
        msg = "The domain name already exists"
    else:
        valid_domain = domain_name
    return valid_domain, msg

def add_domain(DBSession, domain):
    """
    To add a new domain to table Domains.
    DBSession: sqlalchemy session maker.
    Inputs:
        form: HTTP request form from '/new_domain'
          -'domain'
    Outputs:
        msg: A string describing successful or not and why.
    """
    session = DBSession()
    dm = Domains(domain=normalize_db_value(domain))
    session.add(dm)

    try:
        session.commit()
        msg = u"Domain {0} added successfully.".format(domain)
    except:
        session.rollback()
        msg = u"Domain {0} added failed.".format(domain)
    session.close()
    return msg

def is_valid_domain(DBSession, domain_name):
    """
    Support function for page handler /new_node
    Verify if the domain name given by user is valid.
    Input:
        DBSession: SQLAlchemy session maker.
        domain_name: string, name of domain
    Output:
        valid_domain: string or None when not valid.
        msg: string, describe reason why not valid.
    """
    valid_domain, msg = None, ''
    if not domain_name:
        msg = "Domain can't be empty."
    elif domain_name not in gen_domain_list(DBSession):
        msg = "The domain name is not defined in IPIT."
    else:
        valid_domain = domain_name
    return valid_domain, msg

def is_valid_node(DBSession, node_name):
    """
    Support function for page handler /new_node
    Verify if the node name given by user is valid.
    Input:
        DBSession: SQLAlchemy session maker.
        node_name: string, name of node
    Output:
        valid_node: string or None when not valid.
        msg: string, describe reason why not valid.
    """
    valid_node, msg = None, ''
    if not node_name:
        msg = "Node name can't be empty."
    elif node_name in gen_node_list(DBSession):
        msg = "The node name already exists."
    else:
        valid_node = node_name

    return valid_node, msg

def add_node(DBSession, form):
    """
    To add a new node to table Nodes.
    DBSession: sqlalchemy session maker.
    Inputs:
        form: HTTP request form from '/new_node'
          -'domain'
          -'node'
          -'note'
    Outputs:
        msg: A string describing successful or not and why.
    """

    session = DBSession()
    nd = Nodes(node=normalize_db_value(form['node']), note=form['note'] if form['note'] else None,
        domain_id=session.query(
            Domains.domain_id).filter_by(domain=form['domain']).first()[0])
    session.add(nd)
    try:
        session.commit()
        msg = u"Node {0} added successfully.".format(normalize_db_value(form['node']))
    except:
        session.rollback()
        msg = u"Node {0} added failed.".format(normalize_db_value(form['node']))
    session.close()
    return msg

def del_node(DBSession, node_id):
    """
    removes node from database
    input: node_id
    output: msg - a string describing wether the operation was succesfull or not
    """
    session = DBSession()
    node = session.query(Nodes).filter(Nodes.node_id == int(node_id)).first()
    node_name = node.node
    hostname_list = []
    for element in gen_element_list(DBSession):
        if node_name == element.split(":")[0]: #check which hostnames are attached to the node
            hostname_list.append(element.split(":")[1]) #append hostname
    if len(hostname_list) == 0: # only delete when there are no hostnames attached to the node
        session.delete(node)
        try:
            session.commit()
            msg = u"Deleted {0} succesfully".format(node_name)
        except:
            session.rollback()
            msg = u"Oops! Something went wrong.."
    else:
        msg = u"Deleting not allowed. Node {0} exists in following hostname(s): {1}".format(node_name, ', '.join(
            map(str, hostname_list)))
    session.close
    return msg

def convert_date_format(date):
    """
    converts a string with date format:
    from yyyy-mm-dd to dd-mm-yyyy
    or dd-mm-yyyy to yyyy-mm-dd
    """
    new_date = date.split('-')[2]+'-'+date.split('-')[1] + '-' + date.split('-')[0]

    return new_date

def convert_dates_for_table(table, one_row = False):
    """
    converts the dates from the database from datetime format to dd-mm-yyyy 
    """
    if one_row == True: #if the table consist only of one row
        new_data = replace_date(list(table))
    else:
        new_data = []
        for row in table:
            row = replace_date(list(row))
            new_data.append(row)
          
    return new_data

def replace_date(list):
    """
    converts datetimeobjects in a list to dd-mm-yyyy format
    """
    for i,v in enumerate(list):
         if isinstance(v, date):
             list.pop(i)
             list.insert(i, convert_date_format(str(v)))
             
    return list
    

def gen_template_list(DBSession, full=True):
    """
    Make a list of Element templates data in order to display in page /element_templates
    + /element_template_x also use this function to get a list of template names.
    output: data
    Format:
    Bydefault, full is True. So full info is queried.
    When no data return []
    When contains data return [(tpl_1),(tpl_2) ...]
    tpl_1 contains: name, template_id, note, sum(elements inside the template)
    When full = False, only returns a list of names.
    ['tpl1_name', 'tpl2_name', ...]
    or []
    """
    session = DBSession()
    if full:
        q = session.query(ElementTemplates.template_id, ElementTemplates.name, ElementTemplates.note,
            func.count(ElementTemplateContents.content_id)
            ).group_by(ElementTemplates.template_id)
        q = q.outerjoin(ElementTemplateContents, ElementTemplates.template_id == 
            ElementTemplateContents.template_id)
        q = q.order_by(ElementTemplates.template_id)
        data = q.all()
    else:
        q = session.query(ElementTemplates.name)
        q = q.order_by(ElementTemplates.template_id)
        data = [x[0] for x in q.all()]

    session.close()
    return data

def get_template(DBSession, tpl_id):
    """
    Use tpl_id to query the template name, note.
    Return a tuple of the name and note.
    """
    session = DBSession()
    q = session.query(ElementTemplates.name, ElementTemplates.note)
    q = q.filter(ElementTemplates.template_id == int(tpl_id))
    data = q.one_or_none()  # None or a tuple
    session.close()
    if data:
        return data
    else:
        return None, None

def get_change_request_by_id(DBSession, request_id):
    """
    input: change request id
    output: change request name
    """

    session = DBSession()
    q = session.query(ChangeRequests).filter(ChangeRequests.change_request_id == request_id).first()
    request_name = q.description
    session.close()
    return request_name

def update_template(DBSession, tpl_id, name, note):
    """
    Used to update table ElementTemplates.
    Return a message.
    Called like:
    kwargs['up_msg'] = update_template(DBSession, tpl_id, kwargs['name'], kwargs['note'])
    """
    if not name:
        return u"Updating failed, please input a name."
    session = DBSession()
    q = session.query(ElementTemplates).filter(ElementTemplates.template_id == int(tpl_id))
    try:
       tpl = q.one()
       tpl.name, tpl.note = name, note
       session.commit()
       msg = u"Template {0} updated successfully.".format(name)
    except:
        session.rollback()
        msg = u"Template updating failed."
    session.close()
    return msg

def get_element_id(DBSession, element):
    """
    element: string, "BSC - EVO8100:GVTEGB1"
    """
    node_name, host_name = element.split(':')  # element syntax is "node:host"
    session = DBSession()
    q = session.query(Elements.element_id).filter(Elements.hostname == host_name
        ).filter(Elements.node_id == Nodes.node_id
        ).filter(Nodes.node == node_name)
    elmt_id = q.one()[0]
    session.close()
    return elmt_id

def get_node_id(DBSession, node):
    """
    input: node name
    output: node id
    """
    session = DBSession()
    q = session.query(Nodes.node_id).filter(Nodes.node == node)
    node_id = q.one()[0]
    session.close()
    return node_id

def get_employee_id(DBSession, employee):
    """
    input: employee name
    output: employee id
    """
    session = DBSession()
    q = session.query(Employees.employee_id).filter(Employees.name == employee)
    empl_id = q.one()
    session.close()
    return empl_id

def get_project_id(DBSession, project):
    """
    input: project name
    output: project id
    """
    session = DBSession()
    q = session.query(Projects.project_id).filter(Projects.name == project)
    prj_id = q.one()
    session.close()
    return prj_id
    

def get_usage_id(DBSession, usage):

    session = DBSession()
    usg_id = session.query(ElementUsages.element_usage_id
        ).filter(ElementUsages.element_usage == usage).one()[0]
    session.close()
    return usg_id

def get_request_element_info(REQUEST_ELEMENTS, form):
    kwargs = {}
    start_dates = []
    end_dates = []
    start_times = []
    end_times = []
    notes = []
    elements = []
    for i in range(REQUEST_ELEMENTS):
        if form['element_{}'.format(i)] != '':
            kwargs['element_{}'.format(i)] = form['element_{}'.format(i)]
            kwargs['start_date_{}'.format(i)] = form['start_date_{}'.format(i)]
            kwargs['start_time_{}'.format(i)] = form['start_time_{}'.format(i)]
            kwargs['end_date_{}'.format(i)] = form['end_date_{}'.format(i)]
            kwargs['end_time_{}'.format(i)] = form['end_time_{}'.format(i)]
            kwargs['note_{}'.format(i)] = form['note_{}'.format(i)] 
            start_dates.append(form['start_date_{}'.format(i)])
            end_dates.append(form['end_date_{}'.format(i)])
            start_times.append(form['start_time_{}'.format(i)])
            end_times.append(form['end_time_{}'.format(i)])
            elements.append(form['element_{}'.format(i)])
            notes.append(form['note_{}'.format(i)])
    kwargs['elements'] = elements
    kwargs['start_times'] = start_times
    kwargs['end_times'] = end_times
    kwargs['start_dates'] = start_dates
    kwargs['end_dates'] = end_dates
    kwargs['notes'] = notes 
    kwargs['description'] = description=normalize_db_value(form['description'])
    kwargs['applicant'] = form.get('applicant')
    kwargs['project'] = form.get('project')
    kwargs['impact'] = form.get('impact')
    
    return kwargs

def update_template_content(DBSession, tpl_id, update_type, element, usage):
    """
    Called like:
    kwargs['up_msg'] = update_template_content(DBSession, tpl_id, request.form.get('user_action_dyn'),
            kwargs['selected_element'], kwargs['selected_usage'])
    Policy:
    When (tpl_id, element_id) already exist, adding can succeed. But the usage_id overwrites.
    deleting also succeed.

    When (tpl_id, element_id) doesn't exist, adding succeed. Deleting also succeed.
    """

    if not element or not usage:
        return u"Updating failed, make sure element and usage are not empty."

    elmt_id = get_element_id(DBSession, element)
    usg_id = get_usage_id(DBSession, usage)
    # Before modify, query to see if it already exist
    session = DBSession()
    old_record = session.query(ElementTemplateContents
        ).filter(ElementTemplateContents.template_id == int(tpl_id)
        ).filter(ElementTemplateContents.element_id == elmt_id
        ).one_or_none()

    if update_type == "Add":
        # Check first if the template element combination already exists.
        if old_record:
            old_record.element_usage_id = usg_id
        else:
            content = ElementTemplateContents(template_id=int(tpl_id),
                element_id=elmt_id, element_usage_id=usg_id)
            session.add(content)
        try:
            session.commit()
            session.close()
            msg = "Template overwritten successfully." if old_record else "Template added successfully."
        except:
            session.rollback()
            session.close()
            msg = "Template updating failed."

    elif update_type == "Delete":
        if old_record:
            session.delete(old_record)
        try:
            session.commit()
            session.close()
            msg = "Template record deleted successfully" if old_record else "The record doesn't exist."
        except:
            session.rollback()
            session.close()
            msg = "Template updating failed."
    else:
        session.close()
        msg = u"Updating failed. update type can only be 'Add' or 'Delete'."
    return msg

def delete_template(DBSession, tpl_id):
    """

    Called like:
    delete_template(DBSession, tpl_id)
    return string message
    """
    session = DBSession()
    qc = session.query(ElementTemplateContents).filter(ElementTemplateContents.template_id == int(tpl_id))
    contents = qc.all()
    if contents:
        qc.delete()
        try:
            session.commit()
        except:
            session.rollback()
            session.close()
            return "Template deleting failed."
    qt = session.query(ElementTemplates).filter(ElementTemplates.template_id == int(tpl_id))
    tpl = qt.one_or_none()
    if not tpl:
        msg = "The template doesn't exist."
    else:
        session.delete(tpl)
        try:
            session.commit()
            msg = "Template deleted successfully"
        except:
            session.rollback()
            msg = "Template deleting failed."
    session.close()
    return msg

def gen_template_content(DBSession, tpl_id):
    """
    Used to get a list of template usages
    Called like:
    kwargs['data'] = gen_template_content(DBSession, tpl_id)  # [(elmt_1, usg_1), (elmt_1, usg_1)]
    elemt_1 looks like "node:hostname"

    """
    session = DBSession()
    q = session.query(Nodes.node, Elements.hostname, ElementUsages.element_usage)
    q = q.filter(ElementTemplateContents.template_id == int(tpl_id)
        ).filter(ElementTemplateContents.element_id == Elements.element_id
        ).filter(Elements.node_id == Nodes.node_id
        ).filter(ElementTemplateContents.element_usage_id == ElementUsages.element_usage_id
        ).order_by(Nodes.node, Elements.hostname)
    data = q.all()
    session.close()
    return data

def add_template(DBSession, name, note):
    """
    Used to insert a new element template to IPIT DB.
    name and note are strings input.
    Note can be None or ''
    Use the input to insert a new record to table "ElementTemplates"
    Out put a string message describing the outcome is successful or failed.
    """
    if not name:
        return u"Adding failed, please input a name."
    session = DBSession()
    tpl = ElementTemplates(name=name, note=note)
    session.add(tpl)
    try:
       session.commit()
       msg = u"Template {0} added successfully.".format(name)
    except:
        session.rollback()
        msg = u"Template adding failed."
    session.close()
    return msg

def is_valid_year_week(year, week):
    """
    Perform a validation check on the year week.
    If valid, return valid_yw and msg.
    year: string or None
    week: string or None
    valid_yw: [int: y, int: w] or None if not valid.
    msg: when valid, ['',''] when not valid, is a list of two string describing the result.
    """
    valid_yw, msg = None, ['', '']
    is_valid = True
    # Empty
    if not year:
        msg[0], is_valid = "Year can't be empty.", False
    if not week:
        msg[1], is_valid = "Week number can't be empty.", False
    # Data type
    if is_valid:
        try:
            v_year = int(year)
        except (ValueError, TypeError):
            msg[0], is_valid = "Please type year with only digits.", False
            return valid_yw, msg
        try:
            v_week = int(week)
        except (ValueError, TypeError):
            msg[1], is_valid = "Please type week with only digits.", False
            return valid_yw, msg
        # year in range
        if v_year not in VALID_YEARS:
            msg[0] = "The year must be between {0} and {1}".format(VALID_YEARS[0], VALID_YEARS[1])
            is_valid = False
        # week in range
        if is_valid and v_week < 1 or v_week > the_last_week(v_year):
            msg[1] = "The week for year {0} must be > 1 and < {1}".format(v_year, the_last_week(v_year))
            is_valid = False
        if is_valid:
            valid_yw = [v_year, v_week]

    return valid_yw, msg

def get_tpl_content_by_name(DBSession, tpl_name):
    """
    Given a template name, return a list of (element_id, element_usage_id) pairs.
    Or an empty list []
    """
    session = DBSession()
    result = session.query(ElementTemplateContents.element_id,
        ElementTemplateContents.element_usage_id
        ).filter(
        (ElementTemplateContents.template_id == ElementTemplates.template_id) & 
        (ElementTemplates.name == tpl_name)
        ).all()
    session.close()
    return result

def get_tpl_content_by_project(DBSession, prj_id, valid_time):
    """
    Used to generate a project element usage lists. This list is then used as a template to set
    Project element usage plan.
    prj_id: int or string.
    valid_time: [year, week]
    Return:
    a list of (element_id, element_usage_id) pairs or an empty list []
    """

    session = DBSession()
    q = session.query(ProjectElementUsages.element_id, ProjectElementUsages.element_usage_id)
    q = q.filter(
        (ProjectElementUsages.project_id == int(prj_id)) & 
        (ProjectElementUsages.year == int(valid_time[0])) & 
        (ProjectElementUsages.week == int(valid_time[1]))
        )
    session.close()
    return q.all()

def update_element_plan(DBSession, prj_id, time_line, tpl_content, delete=False):
    """
    Given a project, a time line and a weekly element plan template, update the project element plan
    by removing all its existing plan records and copy the template records.

    When delete is True, element plan is only deleted, but not updated.

    tpl_content: List [(element_id1, usage_id1), (element_id2, usage_id2), ...] or []
    """
    prj_id = int(prj_id)
    session = DBSession()
    # Add element-usage
    # Outside loop is each week
    yw_list = gen_yw_list(*time_line)
    old_qty = 0
    for y, w in yw_list:
        for c in tpl_content:
        # Inside loop is each element in the template.
            # Clear the existing week plan of that week for that element
            q = session.query(ProjectElementUsages)
            q = q.filter(
                 (ProjectElementUsages.project_id == prj_id) & 
                 (ProjectElementUsages.year == y) & 
                 (ProjectElementUsages.week == w) & 
                 (ProjectElementUsages.element_id == c[0])
				 )
            records = q.all()
            old_qty += len(records)
            for r in records:
                session.delete(r)
            if delete == False:
                new_record = ProjectElementUsages(year=y, week=w,
                element_id=c[0], element_usage_id=c[1],
                project_id=prj_id
                )
                session.add(new_record)
                updated_records = len(tpl_content) * len(yw_list)
            else:
                updated_records = 0
    # Return the result msg. It should start with SUC if successful.
    try:
        session.commit()
        session.close()
        msg = "SUCCESSFULL: Delete {0} old record(s) and add/update {1} records.".format(old_qty, updated_records)
    except:
        session.rollback()
        session.close()
        msg = "Error: updating project element plan failed."

    return msg

def filter_conflicts(data, contain_id=True, report_type = 'pcu'):
    """
    Used to fullfill project conflict detection.
    Input data comes from function gen_peu_report. It is a matrix of element weekly usages per element per project.
    This function output another matrix which only contain possible conflicts
    Depends on wether containning id, one row in the input data can be:
    contain_id = True
    data[0] is [u'Groeneveld Martin', 15, u'ARP HUB', u'ARP HUB 02', 595, u'Future of Mobile Step 5', 91, None, u'Configuratie aanpassing']
    * 595 is the element id.
    contain_id = False
    data[0] is [u'Groeneveld Martin', u'ARP HUB', u'ARP HUB 02', u'Future of Mobile Step 5', None, u'Configuratie aanpassing']
    """
    # Algorithm: scan through the rows in data.
    # Save rows read from data to a temp varibale.
    # if element changed, make a decision whether to keep last elements usages data.
    # The decision is done by call a check function that can perform a check in if contains conflicts.
    # Append those kept data to result.
    def filter_one_group(matrix, contain_id, report_type):
        """Local function. If matrix data contains conflicts, output the data. Else, output None.
        Rule:
        1 If matrix contains only 1 row. No conflicts.
        2 If matrix contains multiple rows. Scan through the week columns.
        Map usage string into ints: 1 and 0. 1 means can impact others, 0 means doesn't impact.
        make running sum all ints belonging to one column.
        make count of valid digits added to sum. (None or '' is not valid digits.)
        If sum >= 1 and count >= 2: there is conflicts.
        Eles, no conflicts.
        Stop scanning through weeks if conflicts already detected.
        """
        H = len(matrix)  # Number of rows.
        if H in [0]:
            return None
        head = 8 if contain_id else 5
        W = len(matrix[0]) - head  # Number of weeks.
        for col in range(W):
            sums = 0
            count = 0
            for row in range(H):
                if matrix[row][head + col] in CONFLICT_USAGES:
                    sums += 1
                if matrix[row][head + col]:  # It is not an empty field.
                    count += 1
                if count >= 2 and sums >= 1:
                    return matrix
            for row in range(H): # also add important usages for the weekly element report
                if report_type == 'pwu'and matrix[row][head + col] in IMPORTANT_ELEMENT_USAGES:
                    return [matrix[row]]

    result = []
    last_element = ''
    temp = []
    for row in data:
        cur_elmt = '_'.join(row[2:4]) if contain_id else '_'.join(row[1:3])
        # If a new element encountered?
        if last_element and cur_elmt != last_element:
            if report_type == 'pcu':
                filtered = filter_one_group(temp, contain_id, report_type = 'pcu')  # filter_conflicts checks if there is conflicts. Only keep data if there is conflicts.
            elif report_type == 'pwu':
                filtered = filter_one_group(temp, contain_id, report_type = 'pwu')
            if filtered:
                result.extend(filtered)
            temp = []  # clear temp variable.
        temp.append(row)
        last_element = cur_elmt
    # When finished scanning, check last round.
    if last_element:
        if report_type == 'pcu':
            filtered = filter_one_group(temp, contain_id, report_type = 'pcu')
        elif report_type == 'pwu':
            filtered = filter_one_group(temp, contain_id, report_type = 'pwu')
        if filtered:
            result.extend(filtered)
    return result


def summary_conflict_msg(msg, data, contain_id=True):
    """
    When apply filter_conflicts on top of the peu data.
    We need to update the report message also.
    """
    if not msg.startswith('SUCC'):
        return msg
    H = len(data)
    if H == 0:
        return "SUCCESSFUL: 0 record retrieved."
    head = 8 if contain_id else 5
    W = len(data[0]) - head
    count = 0
    for col in range(W):
        for row in range(H):
            if data[row][head + col]:
                count += 1
    return "SUCCESSFUL: {} records retrieved.".format(count)

