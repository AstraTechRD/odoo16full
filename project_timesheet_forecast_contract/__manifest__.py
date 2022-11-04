# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Timesheet, Planning and Employee Contracts",
    'summary': """Bridge module for project_timesheet_forecast and hr_contract""",
    'description': """
        Better plan your future schedules by considering time effectively spent on old plannings
        taking employees' contracts into account
    """,
    'category': 'Hidden',
    'version': '1.0',
    'depends': ['project_timesheet_forecast', 'hr_contract'],
    'auto_install': True,
    'license': 'OEEL-1',
}
