# Copyright (c) 2013, Rohit Industries Ltd. and contributors
# For license information, please see license.txt
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import frappe
from frappe import msgprint, _
from frappe.utils import flt, cstr

def execute(filters=None):
	if not filters: filters = {}
	
	emp_lst = get_employee(filters)
	salary_str = get_salary_str(filters, emp_lst)
	columns, earning_types, ded_types, cont_types = get_columns(filters, salary_str)
	data = []
	
	if filters.get("without_salary_structure")<>1:
		ss_earning_map = get_ss_earning_map(salary_str)
		ss_ded_map = get_ss_ded_map(salary_str)
		ss_cont_map = get_ss_cont_map(salary_str)
				
		for ss in salary_str:
			row = [ss.name, ss.from_date, ss.to_date, ss.employee, ss.employee_name]
			
			for e in earning_types:
				row.append(ss_earning_map.get(ss.name, {}).get(e))
			row += [ss.total_earning]
			for d in ded_types:
				row.append(ss_ded_map.get(ss.name, {}).get(d))
			row += [ss.total_deduction, ss.net_pay]
			for c in cont_types:
				row.append(ss_cont_map.get(ss.name, {}).get(c))
			row += [ss.total_ctc]
			data.append(row)
	else:
		conditions_emp, conditions_ss, filters = get_conditions(filters)
		query = """SELECT emp.name, emp.employee_name, ifnull(emp.branch,"-"), 
			ifnull(emp.department,"-"), ifnull(emp.designation,"-"), emp.date_of_joining,
			IFNULL(emp.relieving_date, '2099-12-31')
			FROM `tabEmployee` emp
			WHERE
				emp.name NOT IN (
				SELECT emp.name
				FROM `tabSalary Structure` ss, `tabEmployee` emp
				WHERE emp.name = ss.employee %s
				) AND
				IFNULL(emp.relieving_date,'2099-12-31') > '%s' %s
			ORDER BY emp.date_of_joining""" %(conditions_ss, filters.get("from_date"),conditions_emp)
		data = frappe.db.sql(query, as_list=1)
	
	return columns, data

def get_employee(filters):
	conditions_emp, conditions_ss, filters = get_conditions(filters)
	query = """SELECT * FROM `tabEmployee` emp
		WHERE emp.docstatus =0 %s 
		ORDER BY emp.date_of_joining""" %(conditions_emp)
	emp_lst = frappe.db.sql(query, as_dict=1)
	if emp_lst:
		pass
	else:
		frappe.throw("No Employees in the Given Criterion")
	return emp_lst

def get_salary_str(filters, emp_lst):
	conditions_emp, conditions_ss, filters = get_conditions(filters)
	
	salary_str = frappe.db.sql("""SELECT * from `tabSalary Structure` ss 
		WHERE ss.docstatus = 0 {condition} AND ss.employee IN (%s)
		ORDER BY ss.employee""".format(condition=conditions_ss) %(", ".join(['%s']*len(emp_lst))), \
		tuple([d.name for d in emp_lst]), as_dict=1)
	
	if salary_str:
		pass
	else:
		frappe.throw("No Salary Structure found for given criterion")
	
	return salary_str
	
def get_ss_earning_map(salary_str):
	ss_earnings = frappe.db.sql("""SELECT parent, e_type, modified_value
		from `tabSalary Structure Earning` where parent in (%s)""" % \
		(', '.join(['%s']*len(salary_str))), tuple([d.name for d in salary_str]), as_dict=1)
	ss_earning_map = {}
	for d in ss_earnings:
		ss_earning_map.setdefault(d.parent, frappe._dict()).setdefault(d.e_type, [])
		ss_earning_map[d.parent][d.e_type] = flt(d.modified_value)
	
	return ss_earning_map
	
def get_ss_ded_map(salary_str):
	ss_deductions = frappe.db.sql("""SELECT parent, d_type, d_modified_amt 
		from `tabSalary Structure Deduction` where parent in (%s)""" %
		(', '.join(['%s']*len(salary_str))), tuple([d.name for d in salary_str]), as_dict=1)
	
	ss_ded_map = {}
	for d in ss_deductions:
		ss_ded_map.setdefault(d.parent, frappe._dict()).setdefault(d.d_type, [])
		ss_ded_map[d.parent][d.d_type] = flt(d.d_modified_amt)
	
	return ss_ded_map
	
def get_ss_cont_map(salary_str):
	ss_contri = frappe.db.sql("""SELECT parent, contribution_type, amount 
		from `tabSalary Structure Contribution` where parent in (%s)""" %
		(', '.join(['%s']*len(salary_str))), tuple([d.name for d in salary_str]), as_dict=1)
	
	ss_cont_map = {}
	for d in ss_contri:
		ss_cont_map.setdefault(d.parent, frappe._dict()).setdefault(d.contribution_type, [])
		ss_cont_map[d.parent][d.contribution_type] = flt(d.amount)
	
	return ss_cont_map
	
def get_columns(filters, salary_str):
	if filters.get("without_salary_structure")<>1:
		columns = [
			_("Salary Structure") + ":Link/Salary Structure:60", _("From Date") + ":Date:80", 
			_("To Date") + ":Date:80", _("Employee") + ":Link/Employee:80",
			_("Name") + "::150"
		]
		
		earning_types = frappe.db.sql_list("""SELECT DISTINCT e_type 
		FROM `tabSalary Structure Earning`
		WHERE modified_value != 0 and parent in (%s)""" % 
		(', '.join(['%s']*len(salary_str))), tuple([d.name for d in salary_str]))
		
		ded_types = frappe.db.sql_list("""SELECT DISTINCT d_type 
		FROM `tabSalary Structure Deduction`
		WHERE d_modified_amt != 0 and parent in (%s)""" % 
		(', '.join(['%s']*len(salary_str))), tuple([d.name for d in salary_str]))
		
		cont_types = frappe.db.sql_list("""SELECT DISTINCT contribution_type 
		FROM `tabSalary Structure Contribution`
		WHERE amount != 0 and parent in (%s)""" % 
		(', '.join(['%s']*len(salary_str))), tuple([d.name for d in salary_str]))
		
		columns = columns + [(e + ":Currency:120") for e in earning_types] + \
			["Total Earning:Currency:100"] + \
			[(d + ":Currency:120") for d in ded_types] + ["Total Deductions:Currency:100"] + \
			["Net Pay:Currency:100"] + \
			[(c + ":Currency:120") for c in cont_types] + ["Total CTC:Currency:100"]
	else:
		columns = [
			"Employee ID:Link/Employee:100", "Employee Name::200", "Branch::80", "Department::80",
			"Designation::100", "Joining Date:Date:80", "Relieving Date:Date:80"
			]
		earning_types = {}
		ded_types = {}
		cont_types = {}
	
	return columns, earning_types, ded_types, cont_types

def get_conditions(filters):
	conditions_emp = ""
	conditions_ss = ""
	
	if filters.get("branch"):
		conditions_emp += " AND emp.branch = '%s'" % filters["branch"]

	if filters.get("department"):
		conditions_emp += " AND emp.department = '%s'" % filters["department"]
		
	if filters.get("designation"):
		conditions_emp += " AND emp.designation = '%s'" % filters["designation"]
		
	if filters.get("employee"):
		conditions_emp += " AND emp.name = '%s'" % filters["employee"]
		
	if filters.get("from_date") and filters.get("to_date"):
		if filters["from_date"] > filters["to_date"]:
			frappe.throw("From Date cannot be after To Date")
		else:
			conditions_ss += " AND ((ss.from_date <='%s' AND ss.to_date <= '%s' AND \
				ss.to_date >= '%s') OR (ss.from_date <= '%s' AND ss.to_date >= '%s'))" % \
				(filters["from_date"], filters["to_date"], filters["from_date"], \
				filters["to_date"], filters["from_date"])
		
	return conditions_emp, conditions_ss, filters