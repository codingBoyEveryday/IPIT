#!/usr/bin/python
# -*- coding: UTF-8 -*-

import unittest
import sqlite3
import re
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from werkzeug.datastructures import ImmutableMultiDict

from ipit_functions import is_valid_time as ivt
from ipit_functions import is_valid_email as ive
from ipit_functions import gen_yw_list as gyl
from ipit_functions import ErrorInvalidTime
from ipit_functions import gen_year_week_columns as gywc
from ipit_functions import query_human_plan as qhp
from ipit_functions import query_element_plan as qep #db
from ipit_functions import normalize_db_value as ndb
from ipit_functions import allocation_plan #db
from ipit_functions import query_element_plan #db
from ipit_functions import update_project #db
from ipit_functions import update_employee #db
from ipit_functions import gen_employee_list #db
from ipit_functions import gen_priority_list #db
from ipit_functions import gen_department_list #db
from ipit_functions import gen_project_list #db
from ipit_functions import gen_domain_list #db
from ipit_functions import add_project #db
from ipit_functions import del_project #db
from ipit_functions import gen_node_list #db
from ipit_functions import update_element #db
from ipit_functions import del_element_byid #db
from ipit_functions import get_element_byid #db
from ipit_functions import query_element_usages #db
from ipit_functions import add_element #db
from ipit_functions import add_employee #db
from ipit_functions import gen_element_list #db
from ipit_functions import gen_usages_list #db
from ipit_functions import is_valid_time_line as vtl
from ipit_functions import get_project_name_byid #db
from ipit_functions import gen_role_list #db
from ipit_functions import get_dept_name_byid #db
from ipit_functions import get_role_name_byid #db
from ipit_functions import is_valid_hour as vh
from ipit_functions import update_project_human_plan #db
from ipit_functions import get_project_info #db
from ipit_functions import get_allocation_plan_by_prjid #db
from ipit_functions import update_human_allocation #db
from ipit_functions import gen_phu_report
from ipit_functions import gen_peu_report
from ipit_functions import get_employee_byid
from ipit_functions import is_valid_name as ivn
from ipit_functions import is_valid_regnum as ivr
from ipit_functions import get_test_manager_email
from ipit_functions import is_valid_domain #db
from ipit_functions import is_valid_new_domain #db
from ipit_functions import is_valid_node #db
from ipit_functions import add_node #db
from ipit_functions import add_domain #db
from ipit_functions import gen_template_list #db
from ipit_functions import get_template #db
from ipit_functions import update_template #db
from ipit_functions import update_template_content #db
from ipit_functions import delete_template #db
from ipit_functions import gen_template_content #db
from ipit_functions import add_template #db
from ipit_functions import is_valid_year_week as vyw
from ipit_functions import get_tpl_content_by_name #db
from ipit_functions import get_tpl_content_by_project #db
from ipit_functions import update_element_plan #db
from ipit_functions import get_element_id #db
from ipit_functions import get_usage_id #db
from ipit_functions import filter_conflicts as fc
from ipit_functions import summary_conflict_msg as scm
from ipit_functions import get_change_request_info #db
from ipit_functions import gen_impact_list #db
from ipit_functions import gen_change_request_list #db
from ipit_functions import add_change_request #db
from ipit_functions import get_conflicted_elements #db
from ipit_functions import get_yw_by_date as ywbd
from ipit_functions import gen_status_list #db
from ipit_functions import update_change_request #db
from ipit_functions import del_change_request #db
from ipit_functions import gen_applicant_list #db
from ipit_functions import is_valid_applicant #db
from ipit_functions import add_applicant #db
from ipit_functions import is_valid_date_time as vdt
from ipit_functions import gen_request_report #db
from ipit_functions import get_employee_id #db
from ipit_functions import update_human_allocation_per_week #db
from ipit_functions import temp_phu_data #db
from ipit_functions import valid_hours_from_list as vhfl
from ipit_functions import get_request_element_info #db
from ipit_functions import project_selected as ps
from ipit_functions import impact_selected as imps
from ipit_functions import del_applicant #db
from ipit_functions import valid_project_input as vpi
from ipit_functions import gen_element_id_list #db
from ipit_functions import convert_date_format as cdf
from ipit_functions import convert_dates_for_table
from ipit_functions import add_department
from ipit_functions import is_valid_department
from ipit_functions import del_department
from ipit_functions import update_department

from database_setup import Base

from credential import is_valid_username as ivu
from credential import is_valid_password as ivp
from credential import register_user as ru
from credential import valid_pw
from credential import make_conn_c
from credential import login_user as lu
from credential import check_secure_val
from credential import get_by_id as gbi

class TestIsValidTime(unittest.TestCase):
    """
       Function: is_valid_time, ivt for short.
    """
    # True
    def test_the_earliest_valid_year_week(self):
        self.assertTrue(ivt(2014, 1, 2020, 51))
    def test_valid_input_1(self):
        self.assertTrue(ivt(2015, 53, 2016, 11))
    def test_valid_input_2(self):
        self.assertTrue(ivt(2016, 1, 2016, 52))
    def test_float_value_input(self):
        self.assertTrue(ivt(2015.5, 53, 2016, 11.8))
    # False
    def test_the_last_invalid(self):
        self.assertFalse(ivt(2013, 52, 2014,1))
    def test_wrong_input_data_type_1(self):
        self.assertFalse(ivt('a', 'b', 'c', 'd'))
    def test_wrong_input_data_type_2(self):
        self.assertFalse(ivt([],[],[],[]))
    def test_all_0(self):
        self.assertFalse(ivt(0, 0, 0, 0))
    def test_all_none(self):
        self.assertFalse(ivt(None, None, None, None))
    def test_in_valid_week(self):
        self.assertFalse(ivt(2015, 54, 2016, 11))
    def test_start_later_than_end(self):
        self.assertFalse(ivt(2016, 11, 2015, 53))
    # Exception

class TestValidTimeLine(unittest.TestCase):
    def test_empty_input(self):
        self.assertEqual(vtl(['', 5, 2016, 6])[0], None)
        self.assertEqual(vtl(['', 5, 2016, 6])[1][0], "This field can't be empty.")
        self.assertEqual(vtl([2016, '', 2016, 6])[0], None)
        self.assertEqual(vtl([2016, '', 2016, 6])[1][1], "This field can't be empty.")
        self.assertEqual(vtl([2016, 5, '', 6])[0], None)
        self.assertEqual(vtl([2016, 5, '', 6])[1][2], "This field can't be empty.")
        self.assertEqual(vtl([2016, 5, 2016, ''])[0], None)
        self.assertEqual(vtl([2016, 5, 2016, ''])[1][3], "This field can't be empty.")

    def test_non_digits(self):
        self.assertEqual(vtl(['er was eens een konijntje', 5, 2016, 6])[0], None)
        self.assertEqual(vtl(['er was eens een konijntje', 5, 2016, 6])[1][0], "Please only type digits.")
        self.assertEqual(vtl([2016, 'er was eens een konijntje', 2016, 6])[0], None)
        self.assertEqual(vtl([2016, 'er was eens een konijntje', 2016, 6])[1][1], "Please only type digits.")
        self.assertEqual(vtl([2016, 5, 'er was eens een konijntje', 6])[0], None)
        self.assertEqual(vtl([2016, 5, 'er was eens een konijntje', 6])[1][2], "Please only type digits.")
        self.assertEqual(vtl([2016, 5, 2016, 'er was eens een konijntje'])[0], None)
        self.assertEqual(vtl([2016, 5, 2016, 'er was eens een konijntje'])[1][3], "Please only type digits.")

    def test_exceed_year_range(self):
        self.assertEqual(vtl([2000, 5, 2020, 6])[0], None)
        self.assertEqual(vtl([2000, 5, 2020, 6])[1][0], "Only allow year between {0} and {1}.".format(2014,2019))

    def test_low_week_number(self):
        self.assertEqual(vtl([2016, 6, 2016, 5])[0], None)
        self.assertEqual(vtl([2016, 6, 2016, 5])[1][3], "End week number starts from {0}.".format(6))

    def test_high_week_number(self):
        self.assertEqual(vtl([2016, 6, 2016, 54])[0], None)
        self.assertEqual(vtl([2016, 6, 2016, 54])[1][3], "Week number for year {0} must <= {1}.".format(2016, 52))

    def test_valid_time_line(self):
        self.assertEqual(vtl([2016, 5, 2016, 6])[0], [2016, 5, 2016, 6])

class TestValidHour(unittest.TestCase):
    def test_empty_hour(self):
        self.assertEqual(vh("")[0], None)
        self.assertEqual(vh("")[1], "This field can't be empty")

    def test_negative_hour(self):
        self.assertEqual(vh(-1)[0], None)
        self.assertEqual(vh(-1)[1], "Hour can't be negative.")

    def test_max_hour(self):
        self.assertEqual(vh(44, h_max=40)[0], None)
        self.assertEqual(vh(44, h_max=40)[1], "Hour should be lower than {}.".format(40))

    def test_non_digit(self):
        self.assertEqual(vh("er liep een schaap in de wei.. ", h_max=40)[0], None)
        self.assertEqual(vh("er liep een schaap in de wei.. ", h_max=40)[1], "Please only type digit and (maximum) one dot.")

    def test_valid_hour(self):
        self.assertEqual(vh(20, 40)[0], 20)
        self.assertEqual(vh(20, 40)[1], "")

class TestValidName(unittest.TestCase):
    def test_empty_name(self):
        self.assertEqual(ivn("")[0], None)
        self.assertEqual(ivn("")[1], "Name can't be empty.")

    def test_name_in_use(self):
        self.assertEqual(ivn("hond", name_list=["hond", "kat", "zwaan"])[0], None)
        self.assertEqual(ivn("hond", name_list=["hond", "kat", "zwaan"])[1], "This name is already in use.")

    def test_valid_name(self):
        self.assertEqual(ivn("hond")[0], "hond")
        self.assertEqual(ivn("hond")[1], "")

class TestValidRegnr(unittest.TestCase):
    def test_empty_regnum(self):
        self.assertEqual(ivr("")[0], None)
        self.assertEqual(ivr("")[1], "This field can't be empty.")

    def test_invalid_regnum(self):
        self.assertEqual(ivr("lalalalalalalalalalala")[0], None)
        self.assertEqual(ivr("lalalalalalalalalalala")[1], "This is not a valid registration number.")

    def test_valid_regnum(self):
        self.assertEqual(ivr(123456)[0], '123456')
        self.assertEqual(ivr(123456)[1], "")

class TestValidYearWeek(unittest.TestCase):
    def test_empty_year_week(self):
        self.assertEqual(vyw('', 7)[0], None)
        self.assertEqual(vyw('', 7)[1][0], "Year can't be empty.")
        self.assertEqual(vyw(2016, '')[0], None)
        self.assertEqual(vyw(2016, '')[1][1], "Week number can't be empty.")

    def test_non_digit_year_week(self):
        self.assertEqual(vyw('op een mooie zomerse dag..', 7)[0], None)
        self.assertEqual(vyw('op een mooie zomerse dag..', 7)[1][0], "Please type year with only digits.")
        self.assertEqual(vyw(2016, 'op een mooie zomerse dag..')[0], None)
        self.assertEqual(vyw(2016, 'op een mooie zomerse dag..')[1][1], "Please type week with only digits.")

    def test_invalid_years(self):
        self.assertEqual(vyw(2040, 7)[0], None)
        self.assertEqual(vyw(2040, 7)[1][0], "The year must be between {0} and {1}".format(2014,2015))

    def test_invalid_week(self):
        self.assertEqual(vyw(2016, 54)[0], None)
        self.assertEqual(vyw(2016, 54)[1][1], "The week for year {0} must be > 1 and < {1}".format(2016,52))

    def test_valid_year_week(self):
        self.assertEqual(vyw(2016, 7)[0], [2016, 7])
        self.assertEqual(vyw(2016, 7)[1][0], '')
        self.assertEqual(vyw(2016, 7)[1][1], '')

class TestValidDateTime(unittest.TestCase):
    def test_valid_date_time(self):
        self.assertEqual(vdt(["12-04-2016"], [u"10:00"], ["12-11-2016"], [u"12:00"], ["my_element"]),
                         (["12-04-2016", u"10", "12-11-2016", u"12"], ["","","",""]))
        self.assertEqual(vdt(["12-04-2016", "12-04-2016"], [u"10:00", u"10:00"], ["12-11-2016", "12-11-2016"], [u"12:00", u"12:00"],
                             ["my_element", "my_element2"]), (["12-04-2016", u"10", "12-11-2016", u"12"], ["","","",""]))

    def test_no_element(self):
        self.assertEqual(vdt(["12-04-2016"], [u"10:00"], ["12-11-2016"], [u"12:00"], []),
                     (0, ["", "", "", "", "No elements selected"]))

    def test_empty_start_date(self):
        self.assertEqual(vdt([""], [u"10:00"], ["12-11-2016"], [u"12:00"], ["my_element"]), (None,["This field can't be empty.","","",""]))

    def test_empty_end_date(self):
        self.assertEqual(vdt(["12-04-2016"], [u"10:00"], [""], [u"12:00"], ["my_element"]),
                         (None, ["", "", "This field can't be empty.", ""]))

    def test_start_date_no_digits(self):
        self.assertEqual(vdt(["lalala"], [u"10:00"], ["12-11-2016"], [u"12:00"], ["my_element"]),
                         (None, ["Please give valid date input for Element {}.".format("my_element"), "", "", ""]))

    def test_end_date_no_digits(self):
        self.assertEqual(vdt(["12-04-2016"], [u"10:00"], ["lalala"], [u"12:00"], ["my_element"]),
                         (None, ["", "", "Please give valid date input for Element {}.".format("my_element"), ""]))

    def test_start_date_out_of_range(self):
        self.assertEqual(vdt(["12-04-2000"], [u"10:00"], ["12-11-2016"], [u"12:00"], ["my_element"]), (None,["Only allow year between {0} and {1}.".format(2014, 2019),"","",""]))

    def test_end_date_out_of_range(self):
        self.assertEqual(vdt(["12-04-2016"], [u"10:00"], ["12-11-2022"], [u"12:00"], ["my_element"]), (None,["","","Only allow year between {0} and {1}.".format(2014, 2019),""]))

    def test_end_date_too_early(self):
        self.assertEqual(vdt(["12-04-2017"], [u"10:00"], ["12-11-2015"], [u"12:00"], ["my_element"]),
                         (None, ["", "", "End date {0} must be later than {1} for Element {2}.".format("12-11-2015", "12-04-2017", "my_element"), ""]))

    def test_start_time_empty(self):
        self.assertEqual(vdt(["12-04-2016"], [u""], ["12-11-2016"], [u"12:00"], ["my_element"]),
                             (None, ["", "This field can't be empty.", "", ""]))

    def test_end_time_empty(self):
        self.assertEqual(vdt(["12-04-2016"], [u"10:00"], ["12-11-2016"], [u""], ["my_element"]),
                             (None, ["", "", "", "This field can't be empty."]))

    def test_start_time_na(self):
        self.assertEqual(vdt(["12-04-2016"], [u"NA"], ["12-11-2016"], [u"12:00"], ["my_element"]),
                             (None, ["", "Start time is missing", "", ""]))

    def test_end_time_na(self):
        self.assertEqual(vdt(["12-04-2016"], [u"10:00"], ["12-11-2016"], [u"NA"], ["my_element"]),
                             (None, ["", "", "", "End time is missing"]))

    def test_end_time_too_early(self):
        self.assertEqual(vdt(["12-04-2016"], [u"10:00"], ["12-04-2016"], [u"8:00"], ["my_element"]),
                         (None, ["", "", "", "Time {0}:00 must be earlier than {1}:00 for Element {2}".format(10, 8, "my_element")]))

class TestGenYwList(unittest.TestCase):
    def test_same_year(self):
        self.assertEqual(
            gyl(2016, 11, 2016, 14),
            [(2016, 11), (2016, 12), (2016, 13), (2016, 14)]
            )
    def test_two_year(self):
        self.assertEqual(
            gyl(2015, 53, 2016, 1),
            [(2015, 53), (2016, 1)])
    def test_same_week(self):
        self.assertEqual(
            gyl(2014, 5, 2014, 5),
            [(2014, 5)]
            )
    def test_three_weeks(self):
        self.assertEqual(
            gyl(2015, 53, 2016, 2),
            [(2015, 53), (2016, 1), (2016, 2)]
            )
    def test_start_later_than_end(self):
        self.assertRaises(
            ErrorInvalidTime,
            gyl,
            2016, 11, 2015, 14
            )

class TestGenYearWeekColumns(unittest.TestCase):
    def gen_outs(self, start_year, start_week, end_year, end_week):
        self.o1, self.o2, self.o3  = gywc(start_year,
            start_week, end_year, end_week)
    def test_same_year(self):
        self.gen_outs(2016, 11, 2016, 14)
        self.assertEqual(self.o1, "yw_2016_11, yw_2016_12, yw_2016_13, yw_2016_14")
        self.assertEqual(self.o2, "yw_2016_11 text, yw_2016_12 text, yw_2016_13 text, yw_2016_14 text")
        self.assertEqual(self.o3, "(2016, 11), (2016, 12), (2016, 13), (2016, 14)")

    def test_two_year(self):
        self.gen_outs(2015, 53, 2016, 1)
        self.assertEqual(self.o1, "yw_2015_53, yw_2016_1")
        self.assertEqual(self.o2, "yw_2015_53 text, yw_2016_1 text")
        self.assertEqual(self.o3, "(2015, 53), (2016, 1)")

    def test_same_week(self):
        self.gen_outs(2014, 5, 2014, 5)
        self.assertEqual(self.o1, "yw_2014_5")
        self.assertEqual(self.o2, "yw_2014_5 text")
        self.assertEqual(self.o3, "(2014, 5)")

    def test_three_weeks(self):
        self.gen_outs(2015, 53, 2016, 2)
        self.assertEqual(self.o1, "yw_2015_53, yw_2016_1, yw_2016_2")
        self.assertEqual(self.o2, "yw_2015_53 text, yw_2016_1 text, yw_2016_2 text")
        self.assertEqual(self.o3, "(2015, 53), (2016, 1), (2016, 2)")

    def test_start_later_than_end(self):
        self.assertRaises(
            ErrorInvalidTime,
            gywc,
            2016, 11, 2015, 14
            )

class TestQueryHumanPlan(unittest.TestCase):
    def setUp(self):
        ENGINE = create_engine('postgresql://dewei:853852@localhost/ipit_db')
        Base.metadata.bind = ENGINE
        self.DBSession = sessionmaker(bind=ENGINE)

    def tearDown(self):
        #self.session.close()
        pass

  #  def test_same_year_2_weeks(self):
   #     human_plan = [
    #        [u'Innovation Test Data', u'Tester', 4.0, 4.0],
     #       [u'Innovation Test Voice', u'Tester', 3.0, 3.0],
      #      [u'Innovation Test Radio', u'Tester', 3.0, 3.0]
       #     ]
  #      column_names = ['Departments', 'Resource Type', '2015-2', '2015-3']

   #     self.assertEqual(
    #        (human_plan, column_names),
     #       qhp(self.DBSession, 1, (2015, 2, 2015, 3))
      #      )
    def test_invalid_time_given(self):
        self.assertRaises(ErrorInvalidTime,
            qhp, self.DBSession, 1, (2014, 54, 2015, 3))

class TestQueryElementPlan(unittest.TestCase):
    def setUp(self):
        ENGINE = create_engine('postgresql://dewei:853852@localhost/ipit_db')
        Base.metadata.bind = ENGINE
        self.DBSession = sessionmaker(bind=ENGINE)
    def tearDown(self):
        #self.session.close()
        pass
    # def test_Volte(self):
    #     element_plan = [
    #         ['Data', 'PCRF', 'GVTEPP2', 'Impliciet Test'],
    #         ['Data', 'PCRF', 'GVTEPP3', 'Impliciet Test'],
    #         ['Data', 'SeGw', 'GVTEEF1', 'Impliciet Test'],
    #         ['Data', 'SeGw', 'GVTEEF2', 'Impliciet Test'],
    #         ['Data', 'UGW (PGW /SGW)', 'GVTEPG5', 'Impliciet Test'],
    #         ['Data', 'UGW (PGW /SGW)', 'GVTEPG6', 'Cfg aanp. + Test Uitv.'],
    #         ['Data', 'USN (MME / SGSN)', 'GVTEEM1', 'Impliciet Test'],
    #         ['Data', 'USN (MME / SGSN)', 'GVTEEM2', 'Cfg aanp. + Test Uitv.'],
    #         ['Radio', 'eNodeB - 6201', 'RBS7', 'Impliciet Test'],
    #         ['Radio', 'NodeB', 'rbs099039 (RBS3)', 'Impliciet Test'],
    #         ['Voice', 'DRA - HPc7000', 'GVDRS1', 'Cfg aanp. + Test Uitv.'],
    #         ['Voice', 'MGW', 'EXT-GVTEMW1', 'Impliciet Test'],
    #         ['Voice', 'MGW', 'EXT-GVTEMW2', 'Impliciet Test'],
    #         ['Voice', 'MSC-S - ATCA', 'GVTMSS1', 'Impliciet Test'],
    #         ['Voice', 'MSC-S - ATCA', 'GVTMSS2', 'Impliciet Test'],
    #         ['Voice', 'MSTP - Eagle 5 SAS (Tekelec)', 'GVTEGX1', 'Impliciet Test'],
    #         ['Voice', 'MSTP - Eagle 5 SAS (Tekelec)', 'GVTEGX2', 'Impliciet Test']
    #      ]
    #     column_names = ['Domain', 'Node', 'Hostname', '2016-1']

    #     self.assertEqual(
    #         (element_plan, column_names),
    #         qep(self.DBSession, 8, (2016, 1, 2016, 1))
    #         )

class TestIsValidUsername(unittest.TestCase):

    def setUp(self):
        self.MSG_EMPTY = "User Name can't be empty."
        self.MSG_NO_MATCH = "Name must be 3 t 20 letters or digits or - or _ or . "
        self.MSG_EXISTS = "This name already exists."
    def test_name_none_1(self):
        self.assertEqual(
            (None, self.MSG_EMPTY), ivu(None)
            )
    def test_name_none_2(self):
        self.assertEqual(
            (None, self.MSG_EMPTY), ivu("")
            )
    def test_name_too_short(self):
        self.assertEqual(
            (None, self.MSG_NO_MATCH),
            ivu("a")
            )
    def test_name_too_long(self):
        self.assertEqual(
            (None, self.MSG_NO_MATCH),
            ivu("xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
            )
    def test_name_3_char(self):
        self.assertEqual(
            ("abc", ''), ivu("abc")
            )
    def test_name_20_char(self):
        self.assertEqual(
            ("AB3DEFGHI_a2cd-fghi.", ''),
            ivu('AB3DEFGHI_a2cd-fghi.')
            )
    def test_name_invalid_char_1(self):
        self.assertEqual(
            (None, self.MSG_NO_MATCH), ivu('AB@#')
            )
    def test_name_invalid_char_2(self):
        self.assertEqual(
            (None, self.MSG_NO_MATCH), ivu('Martin Swaen')
            )
    def test_name_already_exists(self):
        self.assertEqual(
            (None, self.MSG_EXISTS), ivu('admin')
            )

class TestIsValidPassword(unittest.TestCase):
    def setUp(self):
        self.MSG_EMPTY = "Password can't be empty."
        self.MSG_NO_MATCH = "Password must be 3 to 20 characters long."
        self.MSG_REPEAT = "Password and repeat don't match."
    def test_empty_1(self):
        self.assertEqual(
            (None, self.MSG_EMPTY), ivp(None, 'abc')
            )
    def test_empty_2(self):
        self.assertEqual(
            (None, self.MSG_EMPTY), ivp("", 'abc')
            )
    def test_too_short(self):
        self.assertEqual(
            (None, self.MSG_NO_MATCH), ivp('ab', 'ab')
            )
    def test_too_long(self):
        self.assertEqual(
            (None, self.MSG_NO_MATCH), ivp('cccccccccccccccccccccccccccccccccccccccccccccc','aa')
            )
    def test_repeat_no_match(self):
        self.assertEqual(
            (None, self.MSG_REPEAT), ivp('ccc','aaa')
            )
    def test_space(self):
        self.assertEqual(
            ('c c', ''), ivp('c c','c c')
            )
    def test_valid(self):
        self.assertEqual(
            ('1good#Pwd',''), ivp('1good#Pwd', '1good#Pwd')
            )

class TestIsValidEmail(unittest.TestCase):
    def setUp(self):
        self.MSG_EMPTY = "This field can't be empty"
        self.MSG_NO_MATCH = "This is not an valid email"
    def test_empty_1(self):
        self.assertEqual(
            (None, self.MSG_EMPTY), ive(None)
            )
    def test_empty_2(self):
        self.assertEqual(
            (None, self.MSG_EMPTY), ive("")
            )
    def test_no_at(self):
        self.assertEqual(
            (None, self.MSG_NO_MATCH), ive('abc')
            )
    def test_no_dot(self):
        self.assertEqual(
            (None, self.MSG_NO_MATCH), ive('abc@c')
            )
    def test_no_head(self):
        self.assertEqual(
            (None, self.MSG_NO_MATCH), ive('@google.com')
            )
    def valid_email(self):
        self.assertEqual(
            ('cc@google.com', ''), ive('cc@google.com')
            )

class TestRegisterUser(unittest.TestCase):
    def setUp(self):
        self.conn, self.c = make_conn_c()
    def tearDown(self):
        try:
            self.c.execute("DELETE FROM USERS WHERE name = 'Alice';")
            self.c.execute("DELETE FROM USERS WHERE name = 'Bob';")
            self.conn.commit()
        except:
            pass
        self.conn.close()
    def test_normal_sub(self):
        ru('Alice', '1234', 'alice@kpn.com')
        data = self.c.execute("SELECT * FROM USERS WHERE name = 'Alice';").fetchall()
        saved_id, saved_name, saved_hash, saved_email, saved_group = data[0]
        self.assertEqual(saved_name, 'Alice')
        self.assertTrue(valid_pw('Alice', '1234', saved_hash))
        self.assertEqual(saved_email, 'alice@kpn.com')
        self.assertEqual(saved_group, 'guest')
    def test_admin_sub(self):
        ru('Bob', '1234', 'bob@kpn.com', 'human_admin')
        data = self.c.execute("SELECT * FROM USERS WHERE name = 'Bob';").fetchall()
        saved_id, saved_name, saved_hash, saved_email, saved_group = data[0]
        self.assertEqual(saved_name, 'Bob')
        self.assertTrue(valid_pw('Bob', '1234', saved_hash))
        self.assertEqual(saved_email, 'bob@kpn.com')
        self.assertEqual(saved_group, 'human_admin')
    def test_exist_user(self):
        msg = ru('admin', '1234', 'bob@kpn.com')
        self.assertEqual(msg, "ERR: <class 'sqlite3.IntegrityError'>")

class TestLoginUser(unittest.TestCase):
    def setUp(self):
        ru('Alice', '1234', 'alice.aya@excellent.com')
    def tearDown(self):
        self.conn, self.c =  make_conn_c()
        self.c.execute("DELETE FROM USERS WHERE name = 'Alice';")
        self.conn.commit()
        self.conn.close()
    def test_normal_user(self):
        uid = check_secure_val(lu('Alice', '1234'))
        self.assertNotEqual(None, uid)
    def test_wrong_pwd(self):
        uid = check_secure_val(lu('Alice', '124'))
        self.assertEqual(None, uid)
    def test_wrong_user(self):
        uid = check_secure_val(lu('Alice999', '1234'))
        self.assertEqual(None, uid)

class TestGetById(unittest.TestCase):
    def test_get_name(self):
        self.assertEqual('admin', gbi('1'))
    def test_notexist(self):
        self.assertEqual(None, gbi('0'))
    def test_noneinput(self):
        self.assertEqual(None, gbi(None))

class TestNormalizeDBValue(unittest.TestCase):
    def test_remove_spaces(self):
        self.assertEqual('DBValue Test', ndb('DBValue               Test'))
    def test_spaces_on_end(self):
        self.assertEqual('DBValue Test', ndb('DBValue Test               '))

class TestFilterConflicts(unittest.TestCase):
    def test_pcu_with_id(self):
        input_data =        [[u'Verhaeg Leon', 18, u'DRA - HPc7000', u'GVDRS1', 283, u'VoLTE', 7, u'Voice', u'Cfg aanp. + Test Uitv.'],
         [u'Verhaeg Leon', 18, u'PCRF', u'GVTEPP2', 12, u'VoLTE', 7, u'Data', u'Cfg aanp. + Test Uitv.'],
         [u'Verhaeg Leon', 18, u'Radio Nodes', u'nog onbekend welke', 550, u'VoLTE', 7, u'nog specificeren welke',
          u'Cfg aanp. + Test Uitv.'], [u'Hannina Robin', 29, u'Radio Nodes', u'nog onbekend welke', 550, u'X+1', 25,
                                       u'3G node (waarschijnlijk 6000/3000)', u'Cfg aanp. + Test Uitv.'],
         [u'Verhaeg Leon', 18, u'UGW (PGW /SGW)', u'GVTEPG6', 11, u'VoLTE', 7, u'Data', u'Cfg aanp. + Test Uitv.'],
         [u'Verhaeg Leon', 18, u'USN (MME / SGSN)', u'GVTEEM2', 6, u'VoLTE', 7, u'Data', u'Cfg aanp. + Test Uitv.']]
        output_data =         [[u'Verhaeg Leon', 18, u'Radio Nodes', u'nog onbekend welke', 550, u'VoLTE', 7, u'nog specificeren welke',
          u'Cfg aanp. + Test Uitv.'], [u'Hannina Robin', 29, u'Radio Nodes', u'nog onbekend welke', 550, u'X+1', 25,
                                       u'3G node (waarschijnlijk 6000/3000)', u'Cfg aanp. + Test Uitv.']]

        self.assertEqual(output_data, fc(input_data, contain_id=True, report_type = 'pcu'))

    def test_pcu_without_id(self, ):
        input_data = [[u'Verhaeg Leon', u'DRA - HPc7000', u'GVDRS1', u'VoLTE', u'Voice', u'Cfg aanp. + Test Uitv.'],
         [u'Verhaeg Leon', u'PCRF', u'GVTEPP2', u'VoLTE', u'Data', u'Cfg aanp. + Test Uitv.'],
         [u'Verhaeg Leon', u'Radio Nodes', u'nog onbekend welke', u'VoLTE', u'nog specificeren welke',
          u'Cfg aanp. + Test Uitv.'],
         [u'Hannina Robin', u'Radio Nodes', u'nog onbekend welke', u'X+1', u'3G node (waarschijnlijk 6000/3000)',
          u'Cfg aanp. + Test Uitv.'],
         [u'Verhaeg Leon', u'UGW (PGW /SGW)', u'GVTEPG6', u'VoLTE', u'Data', u'Cfg aanp. + Test Uitv.'],
         [u'Verhaeg Leon', u'USN (MME / SGSN)', u'GVTEEM2', u'VoLTE', u'Data', u'Cfg aanp. + Test Uitv.']]
        output_data = [[u'Verhaeg Leon', u'Radio Nodes', u'nog onbekend welke', u'VoLTE', u'nog specificeren welke',
          u'Cfg aanp. + Test Uitv.'],
         [u'Hannina Robin', u'Radio Nodes', u'nog onbekend welke', u'X+1', u'3G node (waarschijnlijk 6000/3000)',
          u'Cfg aanp. + Test Uitv.']]

        self.assertEqual(output_data, fc(input_data, contain_id=False, report_type='pcu'))

    def test_pwu_with_id(self):
        input_data =         [[u'Verhaeg Leon', 18, u'DRA - HPc7000', u'GVDRS1', 283, u'VoLTE', 7, u'Voice', u'Cfg aanp. + Test Uitv.'],
         [u'Verhaeg Leon', 18, u'eNodeB - 6201', u'RBS7', 333, u'VoLTE', 7, u'4G 3x Sectors LTE800 (band20)',
          u'Impliciet Test'],
         [u'Verhaeg Leon', 18, u'MGW', u'EXT-GVTEMW1', 277, u'VoLTE', 7, u'Voice', u'Impliciet Test'],
         [u'Verhaeg Leon', 18, u'MGW', u'EXT-GVTEMW2', 278, u'VoLTE', 7, u'Voice', u'Impliciet Test'],
         [u'Verhaeg Leon', 18, u'MSC-S - ATCA', u'GVTMSS1', 289, u'VoLTE', 7, u'Huawei (CS2)', u'Impliciet Test'],
         [u'Verhaeg Leon', 18, u'MSC-S - ATCA', u'GVTMSS2', 290, u'VoLTE', 7, u'Huawei (CS2)', u'Impliciet Test'],
         [u'Verhaeg Leon', 18, u'MSTP - Eagle 5 SAS (Tekelec)', u'GVTEGX1', 270, u'VoLTE', 7, u'oud: GVBIGX1',
          u'Impliciet Test'],
         [u'Verhaeg Leon', 18, u'NodeB', u'rbs099039 (RBS3)', 647, u'VoLTE', 7, u'3G under GVBIUR7 (RNC7)',
          u'Impliciet Test'],
         [u'Verhaeg Leon', 18, u'PCRF', u'GVTEPP3', 13, u'VoLTE', 7, u'Data Active (Adam)', u'Impliciet Test'],
         [u'Verhaeg Leon', 18, u'SeGw', u'GVTEEF1', 3, u'VoLTE', 7, u'Data', u'Impliciet Test'],
         [u'Verhaeg Leon', 18, u'SeGw', u'GVTEEF2', 4, u'VoLTE', 7, u'Data', u'Impliciet Test'],
         [u'Verhaeg Leon', 18, u'UGW (PGW /SGW)', u'GVTEPG5', 10, u'VoLTE', 7,
          u'UGW PGP 16 / V900R011C00SPC200 SPH210 (dd 2015-01)', u'Impliciet Test'],
         [u'Verhaeg Leon', 18, u'UGW (PGW /SGW)', u'GVTEPG6', 11, u'VoLTE', 7, u'Data', u'Cfg aanp. + Test Uitv.'],
         [u'Verhaeg Leon', 18, u'USN (MME / SGSN)', u'GVTEEM1', 5, u'VoLTE', 7,
          u'USN=V900R011C02SPC200 SPH220 / CGP=V100R006C03SPC600 SPH609 (dd2015-01)', u'Impliciet Test'],
         [u'Verhaeg Leon', 18, u'USN (MME / SGSN)', u'GVTEEM2', 6, u'VoLTE', 7, u'Data', u'Cfg aanp. + Test Uitv.']]
        output_data =         [[u'Verhaeg Leon', 18, u'DRA - HPc7000', u'GVDRS1', 283, u'VoLTE', 7, u'Voice', u'Cfg aanp. + Test Uitv.'],
         [u'Verhaeg Leon', 18, u'UGW (PGW /SGW)', u'GVTEPG6', 11, u'VoLTE', 7, u'Data', u'Cfg aanp. + Test Uitv.'],
         [u'Verhaeg Leon', 18, u'USN (MME / SGSN)', u'GVTEEM2', 6, u'VoLTE', 7, u'Data', u'Cfg aanp. + Test Uitv.']]

        self.assertEqual(output_data, fc(input_data, contain_id=True, report_type='pwu'))

    def test_pwu_without_id(self):
        input_data = [[u'Verhaeg Leon', u'DRA - HPc7000', u'GVDRS1', u'VoLTE', u'Voice', u'Cfg aanp. + Test Uitv.'],
         [u'Verhaeg Leon', u'eNodeB - 6201', u'RBS7', u'VoLTE', u'4G 3x Sectors LTE800 (band20)', u'Impliciet Test'],
         [u'Verhaeg Leon', u'MGW', u'EXT-GVTEMW1', u'VoLTE', u'Voice', u'Impliciet Test'],
         [u'Verhaeg Leon', u'MGW', u'EXT-GVTEMW2', u'VoLTE', u'Voice', u'Impliciet Test'],
         [u'Verhaeg Leon', u'MSC-S - ATCA', u'GVTMSS1', u'VoLTE', u'Huawei (CS2)', u'Impliciet Test'],
         [u'Verhaeg Leon', u'MSC-S - ATCA', u'GVTMSS2', u'VoLTE', u'Huawei (CS2)', u'Impliciet Test'],
         [u'Verhaeg Leon', u'MSTP - Eagle 5 SAS (Tekelec)', u'GVTEGX1', u'VoLTE', u'oud: GVBIGX1', u'Impliciet Test'],
         [u'Verhaeg Leon', u'NodeB', u'rbs099039 (RBS3)', u'VoLTE', u'3G under GVBIUR7 (RNC7)', u'Impliciet Test'],
         [u'Verhaeg Leon', u'PCRF', u'GVTEPP3', u'VoLTE', u'Data Active (Adam)', u'Impliciet Test'],
         [u'Verhaeg Leon', u'SeGw', u'GVTEEF1', u'VoLTE', u'Data', u'Impliciet Test'],
         [u'Verhaeg Leon', u'SeGw', u'GVTEEF2', u'VoLTE', u'Data', u'Impliciet Test'],
         [u'Verhaeg Leon', u'UGW (PGW /SGW)', u'GVTEPG5', u'VoLTE',
          u'UGW PGP 16 / V900R011C00SPC200 SPH210 (dd 2015-01)', u'Impliciet Test'],
         [u'Verhaeg Leon', u'UGW (PGW /SGW)', u'GVTEPG6', u'VoLTE', u'Data', u'Cfg aanp. + Test Uitv.'],
         [u'Verhaeg Leon', u'USN (MME / SGSN)', u'GVTEEM1', u'VoLTE',
          u'USN=V900R011C02SPC200 SPH220 / CGP=V100R006C03SPC600 SPH609 (dd2015-01)', u'Impliciet Test'],
         [u'Verhaeg Leon', u'USN (MME / SGSN)', u'GVTEEM2', u'VoLTE', u'Data', u'Cfg aanp. + Test Uitv.']]
        output_data = [[u'Verhaeg Leon', u'DRA - HPc7000', u'GVDRS1', u'VoLTE', u'Voice', u'Cfg aanp. + Test Uitv.'],
         [u'Verhaeg Leon', u'UGW (PGW /SGW)', u'GVTEPG6', u'VoLTE', u'Data', u'Cfg aanp. + Test Uitv.'],
         [u'Verhaeg Leon', u'USN (MME / SGSN)', u'GVTEEM2', u'VoLTE', u'Data', u'Cfg aanp. + Test Uitv.']]

        self.assertEqual(output_data, fc(input_data, contain_id=False, report_type='pwu'))

class TestSummaryConflictMessage(unittest.TestCase):
    def test_fail(self):
        self.assertEqual("fail", scm(msg="fail", data = [], contain_id = True))

    def test_0_records(self):
        self.assertEqual("SUCCESSFUL: {} record retrieved.".format(0),
                         scm(msg="SUCCESSFUL: {} records retrieved.".format(0), data=[], contain_id=True))
    def test_multiple_records(self):
        data =  [[u'Verhaeg Leon', 18, u'DRA - HPc7000', u'GVDRS1', 283, u'VoLTE', 7, u'Voice', u'Cfg aanp. + Test Uitv.'],
         [u'Verhaeg Leon', 18, u'UGW (PGW /SGW)', u'GVTEPG6', 11, u'VoLTE', 7, u'Data', u'Cfg aanp. + Test Uitv.'],
         [u'Verhaeg Leon', 18, u'USN (MME / SGSN)', u'GVTEEM2', 6, u'VoLTE', 7, u'Data', u'Cfg aanp. + Test Uitv.']]
        self.assertEqual("SUCCESSFUL: 3 records retrieved.", scm(msg= "SUCCESSFUL: 3 records retrieved.", data=data, contain_id=True))

class TestGetYearWeekByDate(unittest.TestCase):
    def test_valid_yearweek(self):
        self.assertEqual([2016, 15, 2016, 45], ywbd("12-04-2016", "12-11-2016"))

    def test_last_week(self):
        self.assertEqual([2016, 41, 2016, 52], ywbd("12-10-2016", "31-12-2016"))

    def test_first_week(self):
        self.assertEqual([2016, 1, 2016, 8], ywbd("01-01-2016", "23-02-2016"))

    def test_transition(self):
        self.assertEqual([2016, 52, 2017, 1], ywbd("31-12-2016", "01-01-2017"))

class TestValidHoursFromList(unittest.TestCase):
    def test_valid_hours(self):
        self.assertEqual(vhfl(ImmutableMultiDict([('end_y', u'2017'), ('user_action', u'Save'), ('end_w', u'32'),
                            ('selected_project', u"(0, 'All Projects')"), ('str_w', u'30'), ('report_type', u'phru'),
                            ('employee', u'Alkemade Willem'), ('hour_input', u'40.0'), ('hour_input', u'40.0'),
                            ('hour_input', u'40.0'), ('hour_input', u'23.0'), ('hour_input', u'23.0'),
                            ('hour_input', u''), ('hour_input', u'23.0'), ('hour_input', u'23.0'), ('hour_input', u''),
                            ('str_y', u'2017')])),([40.0, 40.0, 40.0, 23.0, 23.0, u'', 23.0, 23.0, u''], ['', '', '', '', '', '', '']))

    def test_negative_hours(self):
        self.assertEqual(vhfl(ImmutableMultiDict([('end_y', u'2017'), ('user_action', u'Save'), ('end_w', u'32'),
                                                      ('selected_project', u"(0, 'All Projects')"), ('str_w', u'30'),
                                                      ('report_type', u'phru'),
                                                      ('employee', u'Alkemade Willem'), ('hour_input', u'40.0'),
                                                      ('hour_input', u'-40.0'),
                                                      ('hour_input', u'40.0'), ('hour_input', u'23.0'),
                                                      ('hour_input', u'-23.0'),
                                                      ('hour_input', u''), ('hour_input', u'23.0'),
                                                      ('hour_input', u'23.0'), ('hour_input', u''),
                                                      ('str_y', u'2017')])),
                             ([40.0, None, 40.0, 23.0, None, u'', 23.0, 23.0, u''], ['', "Hour can't be negative.", '', '', "Hour can't be negative.", '', '']))


    def test_high_hours(self):
        self.assertEqual(vhfl(ImmutableMultiDict([('end_y', u'2017'), ('user_action', u'Save'), ('end_w', u'32'),
                                              ('selected_project', u"(0, 'All Projects')"), ('str_w', u'30'),
                                              ('report_type', u'phru'),
                                              ('employee', u'Alkemade Willem'), ('hour_input', u'40.0'),
                                              ('hour_input', u'50.0'),
                                              ('hour_input', u'60.0'), ('hour_input', u'23.0'),
                                              ('hour_input', u'23.0'),
                                              ('hour_input', u''), ('hour_input', u'23.0'),
                                              ('hour_input', u'23.0'), ('hour_input', u''),
                                              ('str_y', u'2017')])),
                     ([40.0, None, None, 23.0, 23.0, u'', 23.0, 23.0, u''], ['', 'Hour should be lower than 40.', 'Hour should be lower than 40.', '', '', '', '']))

    def test_non_hour_input(self):
        self.assertEqual(vhfl(ImmutableMultiDict([('end_y', u'2017'), ('user_action', u'Save'), ('end_w', u'32'),
                                                      ('selected_project', u"(0, 'All Projects')"), ('str_w', u'30'),
                                                      ('report_type', u'phru'),
                                                      ('employee', u'Alkemade Willem'), ('hour_input', u'40.0'),
                                                      ('hour_input', u'lalalalalala'),
                                                      ('hour_input', u'40.0'), ('hour_input', u'blablabla'),
                                                      ('hour_input', u'23.0'),
                                                      ('hour_input', u''), ('hour_input', u'23.0'),
                                                      ('hour_input', u'23.0'), ('hour_input', u''),
                                                      ('str_y', u'2017')])),
                             ([40.0, None, 40.0, None, 23.0, u'', 23.0, 23.0, u''], ['', 'Please only type digit and (maximum) one dot.', '', 'Please only type digit and (maximum) one dot.', '', '', '']))

class TestProjectSelected(unittest.TestCase):
    def test_project_selected(self):
        self.assertTrue(ps(ImmutableMultiDict([('applicant', u'Test'), ('project', u'00 TEST voorbeeld project IPIT netwerk'),
                                               ('start_time_1', u''), ('note_3', u''), ('note_2', u''), ('note_1', u''), ('note_0', u'')]))[0])

        self.assertEqual(ps(ImmutableMultiDict([('applicant', u'Test'), ('project', u'00 TEST voorbeeld project IPIT netwerk'),
                                            ('start_time_1', u''), ('note_3', u''), ('note_2', u''), ('note_1', u''),
                                            ('note_0', u'')]))[1], '')

    def test_no_project_selected(self):
        self.assertFalse(ps(ImmutableMultiDict([('applicant', u'Test'), ('project', u''),
                                   ('start_time_1', u''), ('note_3', u''), ('note_2', u''), ('note_1', u''),
                                   ('note_0', u'')]))[0])
        self.assertEqual(ps(ImmutableMultiDict([('applicant', u'Test'), ('project', u''),
                                   ('start_time_1', u''), ('note_3', u''), ('note_2', u''), ('note_1', u''),
                                   ('note_0', u'')]))[1],'please select a project')

class TestImpactSelected(unittest.TestCase):
    def test_impact_selected(self):
        self.assertTrue(imps( ImmutableMultiDict([('description', u'Test2'), ('user_action', u'Add'), ('element_0', u'1Mediation:zie MMD'),
                            ('element_1', u''), ('element_2', u''), ('element_3', u''), ('start_date_2', u''),
                            ('start_date_3', u''), ('start_date_0', u'06-07-2017'), ('start_date_1', u''),
                            ('impact', u'No impact')]))[0])
        self.assertEqual(imps( ImmutableMultiDict([('description', u'Test2'), ('user_action', u'Add'), ('element_0', u'1Mediation:zie MMD'),
                            ('element_1', u''), ('element_2', u''), ('element_3', u''), ('start_date_2', u''),
                            ('start_date_3', u''), ('start_date_0', u'06-07-2017'), ('start_date_1', u''),
                            ('impact', u'No impact')]))[1], "")

    def test_no_impact_selected(self):
        self.assertFalse(imps(ImmutableMultiDict(
            [('description', u'Test2'), ('user_action', u'Add'), ('element_0', u'1Mediation:zie MMD'),
             ('element_1', u''), ('element_2', u''), ('element_3', u''), ('start_date_2', u''),
             ('start_date_3', u''), ('start_date_0', u'06-07-2017'), ('start_date_1', u''),
             ('impact', u'')]))[0])
        self.assertEqual(imps(ImmutableMultiDict(
            [('description', u'Test2'), ('user_action', u'Add'), ('element_0', u'1Mediation:zie MMD'),
             ('element_1', u''), ('element_2', u''), ('element_3', u''), ('start_date_2', u''),
             ('start_date_3', u''), ('start_date_0', u'06-07-2017'), ('start_date_1', u''),
             ('impact', u'')]))[1], 'please select an impact value')

class TestValidProjectInput(unittest.TestCase):
    def test_valid_input(self):
        self.assertTrue(vpi(ImmutableMultiDict([('priority', u'Blauw'), ('domain', u'Data'), ('code', u' '), ('name', u'Test'),
                                                ('date_el', u'06-07-2017'), ('user_action', u'Add'), ('test_manager', u'Test Test'),
                                                ('note', u''), ('department', u'Innovation ACN'), ('management', u''), ('active', u'active')]))[0])
        self.assertEqual(
            vpi(ImmutableMultiDict([('priority', u'Blauw'), ('domain', u'Data'), ('code', u' '), ('name', u'Test'),
                                    ('date_el', u'06-07-2017'), ('user_action', u'Add'), ('test_manager', u'Test Test'),
                                    ('note', u''), ('department', u'Innovation ACN'), ('management', u''),
                                    ('active', u'active')]))[1], ['','',''])


    def test_missing_priority(self):
        self.assertFalse(
        vpi(ImmutableMultiDict([('priority', u''), ('domain', u'Data'), ('code', u' '), ('name', u'Test'),
                                ('date_el', u'06-07-2017'), ('user_action', u'Add'), ('test_manager', u'Test Test'),
                                ('note', u''), ('department', u'Innovation ACN'), ('management', u''),
                                ('active', u'active')]))[0])
        self.assertEqual(
        vpi(ImmutableMultiDict([('priority', u''), ('domain', u'Data'), ('code', u' '), ('name', u'Test'),
                                ('date_el', u'06-07-2017'), ('user_action', u'Add'), ('test_manager', u'Test Test'),
                                ('note', u''), ('department', u'Innovation ACN'), ('management', u''),
                                ('active', u'active')]))[1], ['Please select a priority','',''])

    def test_missing_department(self):
        self.assertFalse(
            vpi(ImmutableMultiDict([('priority', u'Blauw'), ('domain', u'Data'), ('code', u' '), ('name', u'Test'),
                                    ('date_el', u'06-07-2017'), ('user_action', u'Add'), ('test_manager', u'Test Test'),
                                    ('note', u''), ('department', u''), ('management', u''),
                                    ('active', u'active')]))[0])
        self.assertEqual(
            vpi(ImmutableMultiDict([('priority', u'Blauw'), ('domain', u'Data'), ('code', u' '), ('name', u'Test'),
                                    ('date_el', u'06-07-2017'), ('user_action', u'Add'), ('test_manager', u'Test Test'),
                                    ('note', u''), ('department', u''), ('management', u''),
                                    ('active', u'active')]))[1], ['', 'Please select a department', ''])

    def test_missing_domain(self):
        self.assertFalse(
            vpi(ImmutableMultiDict([('priority', u'Blauw'), ('domain', u''), ('code', u' '), ('name', u'Test'),
                                    ('date_el', u'06-07-2017'), ('user_action', u'Add'), ('test_manager', u'Test Test'),
                                    ('note', u''), ('department', u'Innovation ACN'), ('management', u''),
                                    ('active', u'active')]))[0])
        self.assertEqual(
            vpi(ImmutableMultiDict([('priority', u'Blauw'), ('domain', u''), ('code', u' '), ('name', u'Test'),
                                    ('date_el', u'06-07-2017'), ('user_action', u'Add'), ('test_manager', u'Test Test'),
                                    ('note', u''), ('department', u'Innovation ACN'), ('management', u''),
                                    ('active', u'active')]))[1], ['', '', 'Please select a domain'])

class TestConvertDataformat(unittest.TestCase):
    def test_yyyy_mm_dd_to_dd_mm_yyyy(self):
        self.assertEqual(cdf("2016-12-03"), "03-12-2016")

    def test_dd_mm_yyyy_to_yyyy_mm_dd(self):
        self.assertEqual(cdf("03-12-2016"), "2016-12-03")


if __name__ == '__main__':
    unittest.main(exit=False)
