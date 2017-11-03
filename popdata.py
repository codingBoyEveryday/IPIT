#!/usr/bin/env python
"""
propdata.py
Run this module to initialize the IPIT DB.
CSV files from Access IPIT must be in the same directory.
"""
import sys
import os
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pandas as pd
from psycopg2 import IntegrityError
from database_setup import Base
from database_setup import Roles
from database_setup import Domains
from database_setup import Departments
from database_setup import Priorities
from database_setup import ElementUsages
from database_setup import Nodes
from database_setup import Employees
from database_setup import Elements
from database_setup import Projects
from database_setup import ProjectPlans
from database_setup import ProjectHumanUsages
from database_setup import ProjectElementUsages
#from database_setup import EmployeeDefaultHours

def delete_empty_rows(df, column_list):
    """
    The Data might contains some rows with Empty value NaN.
    This function delete those rows.

    Input:
        df: pandas DataFrame
        column_list: list of String, each item is column name in the DF
    Output:
        df: pandas DataFrame
    """
    empty_rows=[]
    len_1 = len(df)
    if isinstance(column_list, str):
        df = df[pd.notnull(df[column_list])]
    elif isinstance(column_list, list):
        for column in column_list:
            df = df[pd.notnull(df[column])]
            empty_rows.append(df[pd.isnull(df[column])])
    else:
        raise ValueError("Unsupported input!")
    if len_1 - len(df) > 0:
        note = "{0} rows deleted because containing empty value in column {1}."
        print note.format(len_1 - len(df), str(column_list))
        print empty_rows
    return df

def replace_nan_with_none(df):
    """
    Replace all the NaN values in pandas DF to None value of Python.
    Input:
        df: pandas DataFrame
    return:
        pandas DataFrame
    """
    return df.where(pd.notnull(df), None)


def set_fk(DBSession, df, df_col, foreign_col, foreign_key):
    """
    Given a df, replace one column's value with the Foreign key ID.
    Input:
        DBSession: session maker
        df: The df containing useful data, pandas DataFrame.
        df_col: the name of column containing interesting data, String.
        foreign_col: Column in foreign table. It contains the same content as df_col,
                     Class.Attribute
        foreign_key: Primary key column in Foreign table, Class.Attribute.
    Output:
        No return value, it operats on view of the original df
    """
    session =  DBSession()
    # Make a mapping from foreign value to FK id.
    fk_dict = {}
    for fname, fkey in session.query(foreign_col, foreign_key):
        if not fk_dict.get(fname):
            fk_dict[fname] = fkey
        else:
            raise Exception("No unique mapping!")
    session.close()
    df[df_col] = df[df_col].apply(fk_dict.get)

def strip_whitings(df, column_list):
    """
    Remove leading and trailing whitespaces from given columns of the data frame.
    input:
        df: Pandas DataFrame (unistring)
        column_list: List of string, The column names in df to be striped.
    Output:
        No return value, the df is changed.
    """
    for index in column_list:
        df[index] = df[index].apply(
            lambda text: text.strip() if text else None)

# Added 7-Jul-2016 by Dewei
def remove_duplicates(data):
    """
    To remove duplicates from the source data.
    Input:
        data: pandas.dataframe.
    Return:
        new_data: pandas.dataframe.
    Note: All the source data from Access contains one column called id.
    """
    cols = list(data.columns)
    try:
        cols.remove('id')
    except ValueError:
        cols.remove('ID')
    len_pre = len(data)
    new_data = data.drop_duplicates(subset=cols, keep='first')
    print "Removed {0} duplicated rows".format(len_pre - len(new_data))
    return new_data
# End Adding 7-Jul-2016 by Dewei

def int_or_none(num, def_val = None):
    """
    Supporting function for import_data.
    The raw_data is numpy.int64
    Input:
        num, numpy.int64 or None
    Outputs:
        int or a def_val value.
    """
    try:
        return int(num)
    except TypeError:
        return def_val

def float_or_none(num, def_val = None):
    """
    Supporting function for import_data.
    The raw_data is string or numpy special data type.
    Input:
        num: might be a string or numpy special data type.
        def_val: the default value when convertion to float fails.
    Outputs:
        float or def_val.
    """
    try:
        return float(num)
    except TypeError:
        return def_val

# Make all data importing as functions. ==========
def import_data(DBsession, table, folder=os.path.abspath('source_data')):
    """
    Import data from folder to 'table' in IPIT DB.
    FILE_NAMES maintains the source file name list for each table.
    Inputs:
        DBsession: Used to generate a DB session to access IPIT DB.
        table: IPIT table class name. Used to point out the source data file (using FILE_NAMES) and target table.
        folder: Path string. folder + '\\' + filename makes the absolute path for a file.
    Outputs:
        Bool: Representing successful or not.
    """
    FILE_NAMES = {
        Roles: 'resource_type.csv',
        Departments: 'departments.csv',
        Domains: 'element_domains.csv',
        Priorities: 'project_prios.csv',
        Nodes: 'elements.csv',
        Elements: 'element_types.csv',
        ElementUsages:'element_usages.csv',
        Employees:'employees.csv',
        Projects: 'projects.csv',
        ProjectElementUsages: 'project_element.csv',
        ProjectHumanUsages: 'project_employee.csv',
        ProjectPlans: 'project_planned.csv'
        }

    session = DBSession()

    if os.name == 'nt':  # Windows
        source_file = folder + '\\' + FILE_NAMES[table]
    else:  # Linux
        source_file = folder + '/' + FILE_NAMES[table]

    data = pd.read_csv(source_file, delimiter=';', encoding='utf-8')
    data = remove_duplicates(data)

    if table is Roles:
        session.add_all(
            [table(role=x) for x in data['name']]
            )
    elif table is Departments:
        session.add_all(
            [table(department=x) for x in data['name']]
            )
    elif table is Domains:
        session.add_all(
            [table(domain=x) for x in data['name']]
            )
    elif table is Priorities:
        session.add_all(
            [table(priority=x) for x in data['name']]
            )
    elif table is Nodes:
        set_fk(DBSession, data, 'element_domain_id', Domains.domain, Domains.domain_id)
        data = delete_empty_rows(data, 'name')
        data = replace_nan_with_none(data)
        session.add_all(
            [table(domain_id=int_or_none(x.element_domain_id),
                node=x.name, note=x.note) for x in data.itertuples()  # intertuples is faster than interrows.
            ])
    elif table is ElementUsages:
        data = delete_empty_rows(data, 'name')
        data = replace_nan_with_none(data)
        session.add_all(
            [table(element_usage=x) for x in data['name']]
            )
    elif table is Employees:
        data = delete_empty_rows(data, ['name', 'registration_nr'])
        strip_whitings(data, ['name', 'department', 'email', 'contract_type',
            'registration_nr'])
        data = remove_duplicates(data)

        try:
            data['hours'] = data['hours'].apply(unicode.replace, args=(',', '.'))
        except TypeError:
            pass
        try:
            data['hours_available'] = (data['hours_available']
                .apply(unicode.replace, args=(',', '.'))
                )
        except TypeError:
            pass
        set_fk(DBSession, data, 'department', Departments.department, Departments.department_id)
        data = replace_nan_with_none(data)
        session.add_all(
            [table(
                name=x.name, hours=float_or_none(x.hours),
                hours_available=float_or_none(x.hours_available),
                department_id=int_or_none(x.department), email=x.email,
                contract_type=x.contract_type,
                registration_number=x.registration_nr)
            for x in data.itertuples()]
            )
    elif table is Elements:
        strip_whitings(data, ['name'])
        data = delete_empty_rows(data, ['element_id', 'name'])
        data = remove_duplicates(data)
        set_fk(DBSession, data, 'element_id', Nodes.node, Nodes.node_id)
        data = replace_nan_with_none(data)
        session.add_all(
        [table(node_id=int_or_none(x.element_id), hostname=x.name, note=x.note,
            access_id=int_or_none(x.id)) for x in data.itertuples()]
        )
    elif table is Projects:
        data = delete_empty_rows(data, ['name'])
        data = replace_nan_with_none(data)
        strip_whitings(data,["name", "department", "testmanager", "domain", "note", "prio",
            "code", "date_el"])
        data = remove_duplicates(data)
        set_fk(DBSession, data, 'department', Departments.department,
            Departments.department_id)
        set_fk(DBSession, data, 'testmanager', Employees.name, Employees.employee_id)
        set_fk(DBSession, data, 'domain', Domains.domain, Domains.domain_id)
        set_fk(DBSession, data, 'prio', Priorities.priority, Priorities.priority_id)
        data = replace_nan_with_none(data)
        # Handle the date time column. Only leave the date part.
        data['date_el'] = (data['date_el']
            .apply(lambda x: x.split()[0])
            .apply(lambda x: x.split('-')[::-1])
            )
        data['active'] = data['active'].apply(lambda x: x == 'Yes')
        session.add_all(
            [table(name=x.name, management=x.management, active=bool(x.active),
                note=x.note, department_id=int_or_none(x.department),
                test_manager_id=int_or_none(x.testmanager),
                domain_id=int_or_none(x.domain),
                priority_id=int_or_none(x.prio),
                code=x.code, date_EL=date(*map(int, x.date_el))
                ) for x in data.itertuples()]
            )
    elif table is ProjectElementUsages:
        data = replace_nan_with_none(data)
        strip_whitings(data, ['note', 'project_id'])
        data = remove_duplicates(data)
        set_fk(DBSession, data, 'element_type_id', Elements.access_id,
               Elements.element_id)
        set_fk(DBSession, data, 'element_usage_id',
               ElementUsages.element_usage_id, ElementUsages.element_usage_id)
        set_fk(DBSession, data, 'project_id', Projects.name, Projects.project_id)
        data = replace_nan_with_none(data)
        session.add_all(
            [table(
                week=int_or_none(x.week), year=int_or_none(x.year),
                note=x.note, element_usage_id=int_or_none(x.element_usage_id),
                element_id=int_or_none(x.element_type_id),
                project_id=int_or_none(x.project_id)
                )
            for x in data.itertuples()]
            )
        # Because there are some rows doesn't contain a valid Element, so we delete those rows.
        for row in session.query(ProjectElementUsages).filter_by(element_id=None):
            session.delete(row)
        session.commit()
    elif table is ProjectHumanUsages:

        data = replace_nan_with_none(data)
        strip_whitings(data, ['note', 'employee_id', 'project_id'])
        data = remove_duplicates(data)
        set_fk(DBSession, data, 'employee_id', Employees.name, Employees.employee_id)
        set_fk(DBSession, data, 'project_id', Projects.name, Projects.project_id)
        data = replace_nan_with_none(data)
        try:
            data['hours'] = (
                data['hours'].apply(unicode.replace, args=(',', '.'))
                .apply(float)
                )
        except TypeError:
            pass
        session.add_all(
            [table(
                hours=float_or_none(x.hours),
                week=int_or_none(x.week),
                year=int_or_none(x.year),
                note=x.note,
                employee_id=int_or_none(x.employee_id),
                project_id=int_or_none(x.project_id),
                role_id = 3 #  Note: IPIT doesn't has role_id now. We take 'Tester' as default.
                )
            for x in data.itertuples()]
            )
    elif table is ProjectPlans:
        data = replace_nan_with_none(data)
        strip_whitings(data, ['note', 'project_id', 'department_id',
            'resource_id'])
        data = remove_duplicates(data)
        set_fk(DBSession, data, 'project_id', Projects.name,
            Projects.project_id)
        set_fk(DBSession, data, 'department_id',
               Departments.department, Departments.department_id)
        set_fk(DBSession, data, 'resource_id', Roles.role, Roles.role_id)
        data = replace_nan_with_none(data)
        data['hours'] = data['hours'].apply(unicode.replace, args=(',', '.'))
        session.add_all(
            [table(week=int_or_none(x.week), year=int_or_none(x.year), note=x.note,
                hours=float_or_none(x.hours), project_id=int_or_none(x.project_id),
                department_id=int_or_none(x.department_id),
                role_id=int_or_none(x.resource_id)
                ) for x in data.itertuples()
            ]
            )

    try:
        session.commit()
        session.close()
        return True
    except:
        session.rollback()
        session.close()
        print "Unexpected error:{0}".format(sys.exc_info()[0])
        return False

# Call functions to import data.
if __name__ == "__main__":
    ENGINE = create_engine('postgresql://dewei:853852@localhost/ipit_db')
    Base.metadata.bind = ENGINE
    DBSession = sessionmaker(bind=ENGINE)
    session = DBSession()

    print "Inserting Table Roles"
    import_data(DBSession, Roles)

    print "Inserting Table Departments"
    import_data(DBSession, Departments)

    print "Inserting Table Domains"
    import_data(DBSession, Domains)

    print "Inserting Table Priorities"
    import_data(DBSession, Priorities)

    print "Inserting Table Nodes"
    import_data(DBSession, Nodes)

    print "Inserting Table ElementUsages"
    import_data(DBSession, ElementUsages)

    print "Inserting Table Employees"
    import_data(DBSession, Employees)

    print "Inserting Table Elements"
    import_data(DBSession, Elements)

    print "Inserting Table Projects"
    import_data(DBSession, Projects)

    print "Inserting Table ProjectElementUsages"
    import_data(DBSession, ProjectElementUsages)

    print "Inserting Table ProjectHumanUsages"
    import_data(DBSession, ProjectHumanUsages)

    print "Inserting Table ProjectPlans"
    import_data(DBSession, ProjectPlans)

    # print "Inserting EmployeeDefaultHours"

    # EMPLOYEES = session.query(Employees.employee_id, Employees.hours).all()
    # for employee in EMPLOYEES:
    #     row = EmployeeDefaultHours(
    #         employee_id=employee[0],
    #         default_hour=employee[1],
    #         start_year=2014,
    #         start_week=1)
    #     session.add(row)
    # try:
    #     session.commit()
    #     session.close()
    # except IntegrityError:
    #     session.rollback()
    #     session.close()
    #     print "Insert Failed"
    # print "Deleting junk data"
    # Remove invalid weeks from Project Human Usages
    # TODO: Remove invalid 2016 week 53 data
    session = DBSession()
    q = session.query(ProjectHumanUsages).filter(
        (ProjectHumanUsages.year == 2016) &
        (ProjectHumanUsages.week == 53)
        )
    for x in q.all():
        session.delete(x)
    session.commit()
    session.close()
