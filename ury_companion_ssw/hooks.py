from . import __version__ as app_version

app_name = "ury_companion_ssw"
app_title = "Ury Companion Ssw"
app_publisher = "Soft Served Web"
app_description = "Adds more functions to ury"
app_email = "aswin@softservedweb.com"
app_license = "MIT"

# Required Apps
required_apps = ["erpnext"]


# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/ury_companion_ssw/css/ury_companion_ssw.css"
# app_include_js = "/assets/ury_companion_ssw/js/ury_companion_ssw.js"

# include js, css files in header of web template
# web_include_css = "/assets/ury_companion_ssw/css/ury_companion_ssw.css"
# web_include_js = "/assets/ury_companion_ssw/js/ury_companion_ssw.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "ury_companion_ssw/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "ury_companion_ssw.utils.jinja_methods",
# 	"filters": "ury_companion_ssw.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "ury_companion_ssw.install.before_install"
# after_install = "ury_companion_ssw.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "ury_companion_ssw.uninstall.before_uninstall"
# after_uninstall = "ury_companion_ssw.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "ury_companion_ssw.utils.before_app_install"
# after_app_install = "ury_companion_ssw.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "ury_companion_ssw.utils.before_app_uninstall"
# after_app_uninstall = "ury_companion_ssw.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "ury_companion_ssw.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
	"URY KOT": "ury_companion_ssw.ury_companion_ssw.overrides.doctype.ury_kot.CustomURYKOT"
}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"POS Invoice": {
		"validate": "ury_companion_ssw.ury_companion_ssw.hooks.ury_companion_pos_invoice.validate"
	}
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"ury_companion_ssw.tasks.all"
# 	],
# 	"daily": [
# 		"ury_companion_ssw.tasks.daily"
# 	],
# 	"hourly": [
# 		"ury_companion_ssw.tasks.hourly"
# 	],
# 	"weekly": [
# 		"ury_companion_ssw.tasks.weekly"
# 	],
# 	"monthly": [
# 		"ury_companion_ssw.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "ury_companion_ssw.install.before_tests"

# Overriding Methods
# ------------------------------
#
override_whitelisted_methods = {
	 "ury.ury_pos.api.getRestaurantMenu": "ury_companion_ssw.ury_companion_ssw.overrides.api.get_restaurant_menu_override",
     "ury.ury_pos.api.getDefaultCustomer": "ury_companion_ssw.ury_companion_ssw.overrides.api.get_default_customer_override",
	 "ury.ury.api.ury_print.network_printing": "ury_companion_ssw.ury_companion_ssw.overrides.api.network_printing_override"
}
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "ury_companion_ssw.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["ury_companion_ssw.utils.before_request"]
# after_request = ["ury_companion_ssw.utils.after_request"]

# Job Events
# ----------
# before_job = ["ury_companion_ssw.utils.before_job"]
# after_job = ["ury_companion_ssw.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"ury_companion_ssw.auth.validate"
# ]
