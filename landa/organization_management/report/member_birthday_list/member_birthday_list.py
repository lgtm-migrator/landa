# Copyright (c) 2013, Real Experts GmbH and contributors
# For license information, please see license.txt

import pandas as pd
import numpy as np
from datetime import date
import calendar

import frappe


def calculate_this_years_birthday(date_of_birth):
	if isinstance(date_of_birth, date):
		today = date.today()
		if not calendar.isleap(today.year) and date_of_birth.month==2 and date_of_birth.day==29:
			# handle dates of birth on February 29th in a leap year
			this_years_birthday=date_of_birth.replace(year=today.year,month=3,day=1)
		else:
			# for every other date of birth
			this_years_birthday=date_of_birth.replace(year=today.year)
		return this_years_birthday
	else:
		return np.nan

def calculate_age(date_of_birth,reference_date=date.today()):
	if not reference_date:
		reference_date = date.today()
	this_years_birthday=calculate_this_years_birthday(date_of_birth)
	if isinstance(this_years_birthday, date):
		if this_years_birthday > reference_date:
			return reference_date.year - date_of_birth.year - 1
		else:
			return reference_date.year - date_of_birth.year
	else:
		return np.nan

def calculate_upcoming_birthday(date_of_birth):
	this_years_birthday=calculate_this_years_birthday(date_of_birth)
	if isinstance(this_years_birthday, date):
		today = date.today()
		# check if upcoming birthday is this year or next year
		if today<=this_years_birthday:
			upcoming_birthday=this_years_birthday
		else:
			upcoming_birthday=this_years_birthday.replace(year=today.year+1)
		return upcoming_birthday
	else:
		return np.nan

def calculate_decadal_birthday(date_of_birth):
	if isinstance(date_of_birth, date):
		upcoming_birthday=calculate_upcoming_birthday(date_of_birth)
		age_at_upcoming_birthday=calculate_age(date_of_birth,reference_date=upcoming_birthday)
		return int((age_at_upcoming_birthday%10)==0)
	else:
		return np.nan
class Birthday(object):
	def __init__(self, filters):
		# set filters
		self.filter_name = {}

		def add_key_from_filters(key, dict):
			if key in filters:
				dict[key] = filters[key]

		for n in ["first_name", "last_name"]:
			add_key_from_filters(n, self.filter_name)
		self.filter_member = self.filter_name.copy()
		add_key_from_filters("organization", self.filter_member)

	def run(self):
		return self.get_columns(), self.get_data()

	def get_data(self):
		def frappe_tuple_to_pandas_df(frappe_tuple, fields):
			# convert to pandas dataframe
			df = pd.DataFrame(frappe_tuple, columns=fields)
			# set by member ID as dataframe index
			df.set_index("member", inplace=True)
			return df

		# define the member master data that are supposed to be loaded
		member_fields = [
			"name",
			"first_name",
			"last_name",
			"date_of_birth",
			"organization",
			"organization_name",
		]
		members = frappe.db.get_list(
			"LANDA Member",
			filters=self.filter_member,
			fields=member_fields,
			as_list=True,
		)

		# convert to pandas dataframe
		member_df = frappe_tuple_to_pandas_df(members, ["member"] + member_fields[1:])
		# calculate todays age from birth date
		member_df["age"] = [
			calculate_age(bd) for bd in member_df["date_of_birth"].values
		]
		# calculate upcoming birthday
		member_df["upcoming_birthday"] = [
			calculate_upcoming_birthday(bd) for bd in member_df["date_of_birth"].values
		]
		# calculate if decadal birthday
		member_df["is_decadal_birthday"] = [
			calculate_decadal_birthday(bd) for bd in member_df["date_of_birth"].values
		]
		# move organization columns to the end of the dataframe
		member_df = member_df[
			[c for c in member_df if c not in ["organization", "organization_name"]]
			+ ["organization", "organization_name"]
		]

		# merge all dataframes from different doctypes and load data of all members without member functions only if necessary
		data = member_df
		# replace NaNs with empty strings
		data.fillna("", inplace=True)
		# convert data back to tuple
		data.reset_index(inplace=True)
		data = tuple(data.itertuples(index=False, name=None))
		return data

	def get_columns(self):
		return [
			{
				"fieldname": "landa_member",
				"fieldtype": "Link",
				"options": "LANDA Member",
				"label": "Member",
			},
			{"fieldname": "first_name", "fieldtype": "Data", "label": "First Name"},
			{"fieldname": "last_name", "fieldtype": "Data", "label": "Last Name"},
			{
				"fieldname": "date_of_birth",
				"fieldtype": "Date",
				"label": "Date of Birth",
			},
			{"fieldname": "member_age", "fieldtype": "Data", "label": "Age"},
			{
				"fieldname": "upcoming_birthday",
				"fieldtype": "Date",
				"label": "Upcoming Birthday",
			},
			{
				"fieldname": "is_decadal_birthday",
				"fieldtype": "Check",
				"label": "Is Decadal Birthday",
			},
			{
				"fieldname": "organization",
				"fieldtype": "Link",
				"options": "Organization",
				"label": "Organization",
			},
			{
				"fieldname": "organization_name",
				"fieldtype": "Data",
				"label": "Organization Name",
			},
		]


def execute(filters=None):
	return Birthday(filters).run()
