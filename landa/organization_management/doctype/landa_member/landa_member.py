# -*- coding: utf-8 -*-
# Copyright (c) 2021, Real Experts GmbH and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.contacts.address_and_contact import delete_contact_and_address
from frappe.model.naming import make_autoname
from frappe.model.naming import revert_series_if_last
from frappe.permissions import add_user_permission

from landa.overrides import get_default_company
from landa.organization_management.doctype.member_function.member_function import apply_active_member_functions


class LANDAMember(Document):
	
	def autoname(self):
		"""Generate the unique member number (name field)

		Organization:				AVL-001-0001, AVE-001-0001, ...
		Local group:				AVL-001-01-0001, AVL-001-02-0001, ...
		"""
		if self.name:
			return

		self.name = make_autoname(self.organization + '-.####', 'LANDA Member')

	def onload(self):
		load_address_and_contact(self)

	def validate(self):
		organization_is_group = lambda: frappe.db.get_value('Organization', self.organization, 'is_group')

		if organization_is_group():
			frappe.throw(_('Cannot be a member of organization {} because it is a group.').format(self.organization))
			
		self.full_name = get_full_name(self.first_name, self.last_name)

	def on_update(self):
		def create_user():
			user = frappe.get_doc(
				{
					"doctype": "User",
					"email": self.email,
					"first_name": self.first_name,
					"last_name": self.last_name,
					"module_profile": "LANDA User",
					"language": "de",
					"landa_member": self.name,
					"organization": self.organization,
				}
			).insert(ignore_permissions=True)
			user.add_roles("LANDA Member")

			return user.name

		is_new_user = False
		if not self.user and self.create_user_account:
			is_new_user = True
			self.user = create_user()
			self.email = None
			self.create_user_account = False
			self.save()

		if self.user and self.has_value_changed('user'):
			self.create_user_permissions()
			apply_active_member_functions({"member": self.name})

		if self.user and not is_new_user and self.has_value_changed("user_enabled"):
			user = frappe.get_doc("User", self.user)
			user.enabled = self.user_enabled
			user.save(ignore_permissions=True)

	def on_trash(self):
		delete_contact_and_address(self.doctype, self.name)
		self.revert_series()

	def create_user_permissions(self):
		"""Restrict LANDA Member to itself and it's Organization."""
		# LANDAMembers always have access at level 2 (Local Organization)
		add_user_permission("LANDA Member", self.name, self.user, ignore_permissions=True)
		add_user_permission("Organization", self.organization, self.user, ignore_permissions=True)
		add_user_permission("Company", get_default_company(self.organization), self.user, ignore_permissions=True)

	def revert_series(self):
		"""Decrease the naming counter when the newest member gets deleted."""
		# reconstruct the key used to generate the name
		number_part_len = len(self.name.split('-')[-1])
		key = self.name[:-number_part_len] + '.' + '#' * number_part_len

		revert_series_if_last(key, self.name)

def get_full_name(first_name,last_name):
	return (first_name or "") + (" " if (last_name and first_name) else "") + (last_name or "") 
