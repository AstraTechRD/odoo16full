from odoo import models, _


class HolidaysRequest(models.Model):
    _name = "hr.leave"
    _inherit = 'hr.leave'

    def action_validate(self):
        res = super(HolidaysRequest, self).action_validate()
        for leave in self:
            if leave.employee_id.company_id.country_id.code == "BE" and \
                    leave.holiday_status_id.work_entry_type_id.code in self._get_drs_work_entry_type_codes():
                drs_link = "https://www.socialsecurity.be/site_fr/employer/applics/drs/index.htm"
                drs_link = '<a href="%s" target="_blank">%s</a>' % (drs_link, drs_link)
                leave.activity_schedule(
                    'mail.mail_activity_data_todo',
                    note=_('%s is in %s. Fill in the appropriate eDRS here: %s',
                           leave.employee_id.name,
                           leave.holiday_status_id.name,
                           drs_link),
                    user_id=leave.holiday_status_id.responsible_id.id or self.env.user.id,
                )
        return res

    def _get_drs_work_entry_type_codes(self):
        drs_work_entry_types = [
            'LEAVE290', # Breast Feeding
            'LEAVE280', # Long Term Sick
            'LEAVE210', # Maternity
            'LEAVE230', # Paternity Time Off (Legal)
            'YOUNG01',  # Youth Time Off
            'LEAVE115', # Work Accident
        ]
        return drs_work_entry_types
