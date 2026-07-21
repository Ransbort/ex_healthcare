app_name = "ex_healthcare"
app_title = "Ex Healthcare"
app_publisher = "Ransbort"
app_description = "Healthcare module built on Marley Healthcare -- Frappe"
app_email = "ransbort@outlook.com"
app_license = "mit"

# Apps
# ------------------

required_apps = ["erpnext", "healthcare"]

# Each item in the list will be shown as an app in the apps page
add_to_apps_screen = [
	{
		"name": "ex_healthcare",
		"logo": "/assets/ex_healthcare/images/ex_healthcare.png",
		"title": "Ex Healthcare",
		"route": "/app/ex-healthcare",
		"has_permission": "ex_healthcare.api.permission.has_app_permission"
	}
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/ex_healthcare/css/ex_healthcare.css"
# app_include_js = "/assets/ex_healthcare/js/ex_healthcare.js"

# include js, css files in header of web template
# web_include_css = "/assets/ex_healthcare/css/ex_healthcare.css"
# web_include_js = "/assets/ex_healthcare/js/ex_healthcare.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "ex_healthcare/public/scss/website"

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

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "ex_healthcare/public/icons.svg"

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

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "ex_healthcare.utils.jinja_methods",
# 	"filters": "ex_healthcare.utils.jinja_filters"
# }

# Installation
# ------------

after_install = "ex_healthcare.ex_healthcare.setup.setup"

# before_install = "ex_healthcare.install.before_install"

# Uninstallation
# ------------

before_uninstall = "ex_healthcare.ex_healthcare.setup.uninstall"

# after_uninstall = "ex_healthcare.uninstall.after_uninstall"

# Migration
# ------------

# Re-installs the workspace(s) defined under
# apps/ex_healthcare/ex_healthcare/ex_healthcare/workspace/*.json on every
# `bench migrate`. Without this, editing a workspace JSON (adding/removing
# shortcuts or links) never takes effect until someone manually calls
# workspace_installer() from the bench console.
after_migrate = [
	"ex_healthcare.ex_healthcare.workspace_installer.workspace_installer"
]

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "ex_healthcare.utils.before_app_install"
# after_app_install = "ex_healthcare.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "ex_healthcare.utils.before_app_uninstall"
# after_app_uninstall = "ex_healthcare.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "ex_healthcare.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "ex_healthcare.notifications.get_notification_config"

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

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"ex_healthcare.tasks.all"
# 	],
# 	"daily": [
# 		"ex_healthcare.tasks.daily"
# 	],
# 	"hourly": [
# 		"ex_healthcare.tasks.hourly"
# 	],
# 	"weekly": [
# 		"ex_healthcare.tasks.weekly"
# 	],
# 	"monthly": [
# 		"ex_healthcare.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "ex_healthcare.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "ex_healthcare.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "ex_healthcare.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "ex_healthcare.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["ex_healthcare.utils.before_request"]
# after_request = ["ex_healthcare.utils.after_request"]

# Job Events
# ----------
# before_job = ["ex_healthcare.utils.before_job"]
# after_job = ["ex_healthcare.utils.after_job"]

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
# 	"ex_healthcare.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []
