# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
from lxml import etree
from textwrap import dedent

from odoo import models
from odoo.tools.json import scriptsafe
from odoo.addons.base.models.ir_qweb import indent_code


class IrQWeb(models.AbstractModel):
    """
    allows to render reports with full branding on every node, including the context available
    to evaluate every node. The context is composed of all the variables available at this point
    in the report, and their type.
    """
    _inherit = 'ir.qweb'

    def _get_template(self, template):
        element, document, ref = super()._get_template(template)
        if self.env.context.get('full_branding'):
            if not isinstance(ref, int):
                raise ValueError("Template '%s' undefined" % template)

            root = element.getroottree()
            basepath = len('/'.join(root.getpath(root.xpath('//*[@t-name]')[0]).split('/')[0:-1]))
            for node in element.iter(tag=etree.Element):
                node.set('data-oe-id', str(ref))
                node.set('data-oe-xpath', root.getpath(node)[basepath:])
        return (element, document, ref)

    def _get_template_cache_keys(self):
        return super()._get_template_cache_keys() + ['full_branding']

    def _prepare_environment(self, values):
        values['json'] = scriptsafe
        return super()._prepare_environment(values)

    def _is_static_node(self, el, options):
        return not options.get('full_branding') and super()._is_static_node(el, options)

    def _compile_directive_att(self, el, options, level):
        code = super()._compile_directive_att(el, options, level)

        if options.get('full_branding'):
            code.append(indent_code("""
                attrs['data-oe-context'] = values['json'].dumps({
                    key: values[key].__class__.__name__
                    for key in values.keys()
                    if  key
                        and key != 'true'
                        and key != 'false'
                        and not key.startswith('_')
                        and ('_' not in key or key.rsplit('_', 1)[0] not in values or key.rsplit('_', 1)[1] not in ['even', 'first', 'index', 'last', 'odd', 'parity', 'size', 'value'])
                        and (values[key].__class__.__name__ not in ['LocalProxy', 'function', 'method', 'Environment', 'module', 'type'])
                })
                """, level))

        return code
