#!/usr/bin/env python
"""database_setup.py -- Create Postgresql DB for IPIT, defining table and Columns."""


from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import Numeric
from sqlalchemy import Text
from sqlalchemy import ForeignKey
from sqlalchemy import Date
from sqlalchemy import Boolean
from sqlalchemy import UniqueConstraint
from sqlalchemy import create_engine
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.sqltypes import DateTime
from sqlalchemy.dialects.postgresql.base import TIMESTAMP

Base = declarative_base()

class Roles(Base):
    """IPIT Table Roles"""

    __tablename__ = 'Roles'
    role_id = Column(Integer, primary_key=True)
    role = Column(Text, nullable=False, unique=True)
    ProjectPlans = relationship("ProjectPlans")
    ProjectHumanUsages = relationship("ProjectHumanUsages") # Added 11-Aug

class Domains(Base):
    """IPIT Table Domains"""

    __tablename__ = 'Domains'
    domain_id = Column(Integer, primary_key=True)
    domain = Column(Text, nullable=False, unique=True)
    nodes = relationship("Nodes")

class Departments(Base):
    """IPIT Table Departments"""

    __tablename__ = 'Departments'
    department_id = Column(Integer, primary_key=True)
    department = Column(Text, nullable=False, unique=True)
    hide_department = Column(Boolean) #option to hide department from department list

    employees = relationship("Employees")
    projects = relationship("Projects")
    ProjectPlans = relationship("ProjectPlans")

class Priorities(Base):
    """IPIT Table Priorities"""

    __tablename__ = 'Priorities'
    priority_id = Column(Integer, primary_key=True)
    priority = Column(Text, nullable=False, unique=True)
    projects = relationship("Projects")

class ElementUsages(Base):
    """IPIT Table ElementUsages"""

    __tablename__ = "ElementUsages"
    element_usage_id = Column(Integer, primary_key=True)
    element_usage = Column(Text, nullable=False, unique=True)

    ProjectElementUsages = relationship("ProjectElementUsages")
    ElementTemplateContents = relationship("ElementTemplateContents")

class Nodes(Base):
    """IPIT Table Nodes"""

    __tablename__ = 'Nodes'
    node_id = Column(Integer, primary_key=True)
    node = Column(Text, nullable=False, unique=True)
    note = Column(Text)
    domain_id = Column(Integer, ForeignKey('Domains.domain_id'))

    elements = relationship("Elements")

class Employees(Base):
    """IPIT Table Employees"""

    __tablename__ = 'Employees'
    employee_id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False, unique=True)
    hours = Column(Numeric)
    hours_available = Column(Numeric) #Added 6-Jul
    department_id = Column(Integer, ForeignKey('Departments.department_id'))
    email = Column(Text)
    contract_type = Column(Text)
    registration_number = Column(Text, nullable=False, unique=True)
    if_left = Column(Boolean, nullable=False)  #Added 18-Oct-2016.

    project = relationship("Projects")
    ProjectHumanUsages = relationship("ProjectHumanUsages")

class Elements(Base):
    """IPIT Table Elements"""

    __tablename__ = 'Elements'
    element_id = Column(Integer, primary_key=True)
    node_id = Column(Integer, ForeignKey('Nodes.node_id'), nullable=False)
    hostname = Column(Text, nullable=False)
    note = Column(Text)
    current_version = Column(Text)
    current_version_date = Column(Date)
    previous_version = Column(Text)
    previous_version_date = Column(Date)
    previous2_version = Column(Text)
    previous2_version_date = Column(Date)
    # Added 17-Jun for Importing table "ProjectElementUsages" Dewei
    access_id = Column(Integer)
    ProjectElementUsages = relationship("ProjectElementUsages")
    ElementTemplateContents = relationship("ElementTemplateContents")
    ChangeRequestsElements = relationship("ChangeRequestsElements")
    UniqueConstraint('node_id', 'hostname', name='unique_node_host')

class Projects(Base):
    """IPIT Table Projects"""

    __tablename__ = 'Projects'
    project_id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False, unique=True)
    management = Column(Text)
    active = Column(Boolean, nullable=False)
    note = Column(Text)
    department_id = Column(Integer, ForeignKey('Departments.department_id'))
    test_manager_id = Column(Integer, ForeignKey('Employees.employee_id'))
    domain_id = Column(Integer, ForeignKey('Domains.domain_id'))
    priority_id = Column(Integer, ForeignKey('Priorities.priority_id'))
    code = Column(Text)  # 2-Aug removed the nullable restriction cause so many projcts doesn't have code.
    date_EL = Column(Date)

    ProjectElementUsages = relationship("ProjectElementUsages")
    ProjectHumanUsages = relationship("ProjectHumanUsages")
    ProjectPlans = relationship("ProjectPlans")
    ChangeRequests = relationship("ChangeRequests")


class ProjectPlans(Base):
    """IPIT Table ProjectPlans"""

    __tablename__ = "ProjectPlans"
    project_plan_id = Column(Integer, primary_key=True)
    week = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    note = Column(Text)
    hours = Column(Numeric, nullable=False)
    project_id = Column(Integer, ForeignKey('Projects.project_id'), nullable=False)
    role_id = Column(Integer, ForeignKey('Roles.role_id'))
    department_id = Column(Integer, ForeignKey('Departments.department_id'))

class ProjectHumanUsages(Base):
    """IPIT Table ProjectHumanUsages"""

    __tablename__ = "ProjectHumanUsages"
    project_human_usage_id = Column(Integer, primary_key=True)
    hours = Column(Numeric, nullable=False)
    week = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    note = Column(Text)
    employee_id = Column(Integer, ForeignKey('Employees.employee_id'), nullable=False)
    project_id = Column(Integer, ForeignKey('Projects.project_id'), nullable=False)
    role_id = Column(Integer, ForeignKey('Roles.role_id'), nullable=False) # Added 22-Aug.

class ProjectElementUsages(Base):
    """IPIT Table ProjectElementUsages"""

    __tablename__ = "ProjectElementUsages"
    project_element_usage_id = Column(Integer, primary_key=True)
    week = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    note = Column(Text)
    element_usage_id = Column(Integer, ForeignKey('ElementUsages.element_usage_id'), nullable=False)
    project_id = Column(Integer, ForeignKey('Projects.project_id'), nullable=False)
    element_id = Column(Integer, ForeignKey('Elements.element_id'), nullable=False)

class ElementTemplates(Base):
    """IPIT Table ElementTemplates """

    __tablename__ = "ElementTemplates"
    template_id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False, unique=True)
    note = Column(Text)

    ElementTemplateContents = relationship("ElementTemplateContents")

class ElementTemplateContents(Base):
    """IPIT Table ElementTemplateContents"""

    __tablename__ = "ElementTemplateContents"
    content_id = Column(Integer, primary_key=True)
    template_id = Column(Integer, ForeignKey('ElementTemplates.template_id'), nullable=False)
    element_id = Column(Integer, ForeignKey('Elements.element_id'), nullable=False)
    element_usage_id = Column(Integer, ForeignKey('ElementUsages.element_usage_id'), nullable=False)

    __table_args__ = (UniqueConstraint('template_id', 'element_id', name='_template_element_uc'),)

class ChangeRequests(Base):
    """IPIT Table ChangeRequests"""
    
    __tablename__ = "ChangeRequests"
    change_request_id = (Column(Integer, primary_key=True))
    applicant_id = Column(Integer, ForeignKey('Applicants.applicant_id'))
    project_id = Column(Integer, ForeignKey('Projects.project_id'))
    description = Column(Text, nullable=False, unique=True)
    impact_id = Column(Integer, ForeignKey('Impact.impact_id'))
    status_id = Column(Integer, ForeignKey('Status.status_id'))
    
    ChangeRequestsElements = relationship("ChangeRequestsElements")
    
class ChangeRequestsElements(Base):
    """IPIT Table ChangeRequestsElements"""
    
    __tablename__ = "ChangeRequestsElements"
    request_element_id = Column(Integer, primary_key=True)
    change_request_id = Column(Integer, ForeignKey('ChangeRequests.change_request_id'), nullable=False)
    element_id = Column(Integer, ForeignKey('Elements.element_id'), nullable=False)
    start_date = Column(Date, nullable=False)
    start_time = Column(Text)
    end_date = Column(Date, nullable=False)
    end_time = Column(Text)
    note = Column(Text)
    
class Impact(Base):
    """IPIT Table Impact"""

    __tablename__ = "Impact"
    impact_id = Column(Integer, primary_key=True)
    impact = Column(Text, nullable=False, unique=True)
    ChangeRequests = relationship("ChangeRequests")

class Status(Base):
    """IPIT Table Impact"""

    __tablename__ = "Status"
    status_id = Column(Integer, primary_key=True)
    status = Column(Text, nullable=False, unique=True)
    
    ChangeRequests = relationship("ChangeRequests")
    
class Applicants(Base):
    """IPIT Table Applicants"""
    
    __tablename__ = "Applicants"
    applicant_id = Column(Integer, primary_key=True)
    applicant = Column(Text, nullable=False, unique=True)
    hide_applicant = Column(Boolean) #option to hide applicant from applicant list
    
    ChangeRequests = relationship("ChangeRequests")
    
    
    
if __name__ == '__main__':
    ENGINE = create_engine('postgresql://dewei:853852@localhost/ipit_db')
    Base.metadata.create_all(ENGINE)
    # Added 4-Jul To Enable Postgressql function crosstab
    #ENGINE.execute('CREATE EXTENSION tablefunc;')
    print "Data Base Setup successful"
