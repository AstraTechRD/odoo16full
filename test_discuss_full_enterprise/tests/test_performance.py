# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_discuss_full.tests.test_performance import TestDiscussFullPerformance

old_method = TestDiscussFullPerformance._get_init_messaging_result


def _get_init_messaging_result(self):
    res = old_method(self)
    res['current_user_settings'].update({
        'how_to_call_on_mobile': 'ask',
        'external_device_number': False,
        'onsip_auth_username': False,
        'should_call_from_another_device': False,
        'should_auto_reject_incoming_calls': False,
        'voip_secret': False,
        'voip_username': False,
    })
    res['voipConfig'] = {
        'mode': 'demo',
        'pbxAddress': "localhost",
        'webSocketUrl': "ws://localhost",
    }
    res['hasDocumentsUserGroup'] = False
    res['helpdesk_livechat_active'] = 0
    return res

def _get_query_count(self):
    return 86


TestDiscussFullPerformance._get_init_messaging_result = _get_init_messaging_result
TestDiscussFullPerformance._get_query_count = _get_query_count
