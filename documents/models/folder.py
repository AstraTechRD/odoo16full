# -*- coding: utf-8 -*-
from odoo import _, api, Command, fields, models
from odoo.exceptions import ValidationError


class DocumentFolder(models.Model):
    _name = 'documents.folder'
    _description = 'Documents Workspace'
    _parent_name = 'parent_folder_id'
    _parent_store = True
    _order = 'sequence'

    _sql_constraints = [
        ('check_user_specific', 'CHECK(not ((NOT user_specific OR user_specific IS NULL) and user_specific_write))',
            'Own Documents Only may not be enabled for write groups if it is not enabled for read groups.')
    ]

    @api.constrains('parent_folder_id')
    def _check_parent_folder_id(self):
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive folders.'))

    @api.model
    def default_get(self, fields):
        res = super(DocumentFolder, self).default_get(fields)
        if 'parent_folder_id' in fields and self._context.get('folder_id') and not res.get('parent_folder_id'):
            res['parent_folder_id'] = self._context.get('folder_id')

        return res

    def name_get(self):
        name_array = []
        hierarchical_naming = self.env.context.get('hierarchical_naming', True)
        for record in self:
            if hierarchical_naming and record.parent_folder_id:
                name_array.append((record.id, "%s / %s" % (record.parent_folder_id.name, record.name)))
            else:
                name_array.append((record.id, record.name))
        return name_array

    company_id = fields.Many2one('res.company', 'Company',
                                 help="This workspace will only be available to the selected company")
    parent_folder_id = fields.Many2one('documents.folder',
                                       string="Parent Workspace",
                                       ondelete="cascade",
                                       help="A workspace will inherit the tags of its parent workspace")
    parent_path = fields.Char(index=True, unaccent=False)
    name = fields.Char(required=True, translate=True)
    description = fields.Html(string="Description", translate=True, copy=True)
    children_folder_ids = fields.One2many('documents.folder', 'parent_folder_id', string="Sub workspaces")
    document_ids = fields.One2many('documents.document', 'folder_id', string="Documents")
    sequence = fields.Integer('Sequence', default=10)
    share_link_ids = fields.One2many('documents.share', 'folder_id', string="Share Links")
    is_shared = fields.Boolean(compute='_compute_is_shared')
    facet_ids = fields.One2many('documents.facet', 'folder_id', copy=True,
                                string="Tag Categories",
                                help="Tag categories defined for this workspace")
    group_ids = fields.Many2many('res.groups', copy=True,
        string="Write Groups", help='Groups able to see the workspace and read/create/edit its documents.')
    read_group_ids = fields.Many2many('res.groups', 'documents_folder_read_groups', copy=True,
        string="Read Groups", help='Groups able to see the workspace and read its documents without create/edit rights.')

    user_specific = fields.Boolean(string="Own Documents Only",
                                   help="Limit Read Groups to the documents of which they are owner.")
    user_specific_write = fields.Boolean(string="Own Documents Only (Write)",
                                    compute='_compute_user_specific_write', store=True, readonly=False,
                                    help="Limit Write Groups to the documents of which they are owner.")
    has_write_access = fields.Boolean('Document User Upload Rights', compute="_compute_has_write_access")

    #stat buttons
    action_count = fields.Integer('Action Count', compute='_compute_action_count')
    document_count = fields.Integer('Document Count', compute='_compute_document_count')

    def _compute_is_shared(self):
        ancestor_ids_by_folder = {folder.id: [int(ancestor_id) for ancestor_id in folder.parent_path[:-1].split('/')[-2::-1]] for folder in self}
        ancestor_ids_set = set().union(*ancestor_ids_by_folder.values())

        search_domain = [
            '&',
                '|',
                    ('date_deadline', '=', False),
                    ('date_deadline', '>', fields.Date.today()),
                '&',
                    ('type', '=', 'domain'),
                    '|',
                        ('folder_id', 'in', self.ids),
                        '&',
                            ('folder_id', 'in', list(ancestor_ids_set)),
                            ('include_sub_folders', '=', True),
        ]

        doc_share_read_group = self.env['documents.share']._read_group(
            search_domain,
            ['folder_id', 'include_sub_folders'],
            ['folder_id', 'include_sub_folders'],
            lazy=False,
        )

        doc_share_count_per_folder_id = {(res['folder_id'][0], res['include_sub_folders']): res['__count'] for res in doc_share_read_group}
        for folder in self:
            folder.is_shared = doc_share_count_per_folder_id.get((folder.id, True)) \
                or doc_share_count_per_folder_id.get((folder.id, False)) \
                or any(doc_share_count_per_folder_id.get((ancestor_id, True)) for ancestor_id in ancestor_ids_by_folder[folder.id])

    @api.depends('user_specific')
    def _compute_user_specific_write(self):
        for folder in self:
            if not folder.user_specific:
                folder.user_specific_write = False

    @api.depends('group_ids', 'read_group_ids')
    @api.depends_context('uid')
    def _compute_has_write_access(self):
        current_user_groups_ids = self.env.user.groups_id
        has_write_access = self.user_has_groups('documents.group_documents_manager')
        if has_write_access:
            self.has_write_access = True
            return
        for record in self:
            folder_has_groups = not record.group_ids and not record.read_group_ids or (record.group_ids & current_user_groups_ids)
            record.has_write_access = folder_has_groups

    def _compute_action_count(self):
        read_group_var = self.env['documents.workflow.rule'].read_group(
            [('domain_folder_id', 'in', self.ids)],
            fields=['domain_folder_id'],
            groupby=['domain_folder_id'])

        action_count_dict = dict((d['domain_folder_id'][0], d['domain_folder_id_count']) for d in read_group_var)
        for record in self:
            record.action_count = action_count_dict.get(record.id, 0)

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get('create_from_search_panel'):
            # Folders created from the search panel inherit the parent's rights.
            for vals in vals_list:
                if 'folder_id' not in vals:
                    continue
                vals.update(self.browse(vals['folder_id'])._get_inherited_settings_as_vals())
        return super().create(vals_list)

    def _get_old_id_to_new_id_maps(self, copied_folder):
        """
        After a folder (self) is copied, this method creates dictionaries
        mapping original facets and tags to the copied ones, that will be used
        to update them in other copied fields.

        If ancestors of the current folder are being copied in the same copy,
        their mappings should be in the context, in which case the returned
        mappings will be an union of the current folder's and its ancestors'.
        """
        self.ensure_one()
        ancestors_facet_map = self.env.context.get('ancestors_facet_map') or {}
        ancestors_tag_map = self.env.context.get('ancestors_tag_map') or {}

        def get_old_id_to_new_id_map(old_folder_id, new_folder_id, table):
            query = f"""
                SELECT t1.id AS old_id, t2.id AS new_id
                  FROM {table} t1
                  JOIN {table} t2
                    ON t1.name = t2.name
                 WHERE t1.folder_id = %s
                   AND t2.folder_id = %s
            """
            self.env.cr.execute(query, (old_folder_id, new_folder_id))
            res = self.env.cr.dictfetchall()
            return {key: value for key, value in [line.values() for line in res]}

        copied_folder_facet_map, copied_folder_tag_map = [get_old_id_to_new_id_map(self.id, copied_folder.id, table) for table in ('documents_facet', 'documents_tag')]
        return {**ancestors_facet_map, **copied_folder_facet_map}, {**ancestors_tag_map, **copied_folder_tag_map}

    def _copy_workflow_rules_and_actions(self, copied_folder, old_facet_id_to_new_facet_id, old_tag_id_to_new_tag_id):
        self.ensure_one()

        old_workflow_rule_id_to_new_workflow_rule_id = {}
        for workflow_rule in self.env['documents.workflow.rule'].search([('domain_folder_id', '=', self.id)]):
            new_workflow_rule = workflow_rule.copy({
                'domain_folder_id': copied_folder.id,
                'required_tag_ids': [Command.set(old_tag_id_to_new_tag_id[tag_id] for tag_id in workflow_rule.required_tag_ids.ids if tag_id in old_tag_id_to_new_tag_id)],
                'excluded_tag_ids': [Command.set(old_tag_id_to_new_tag_id[tag_id] for tag_id in workflow_rule.excluded_tag_ids.ids if tag_id in old_tag_id_to_new_tag_id)],
            })
            old_workflow_rule_id_to_new_workflow_rule_id[workflow_rule.id] = new_workflow_rule.id

        old_workflow_actions = self.env['documents.workflow.action'].search([
            ('workflow_rule_id', 'in', list(old_workflow_rule_id_to_new_workflow_rule_id)),
        ])
        for workflow_action in old_workflow_actions:
            facet_id, tag_id = False, False
            if workflow_action.facet_id:
                # If the facet/tag comes from an ancestor (including the folder itself)
                # that is being copied, update its value to the copied facet/tag.
                # If the ancestor is not being copied, remove the value.
                if str(workflow_action.facet_id.folder_id.id) in self.parent_path[:-1].split('/'):
                    facet_id = old_facet_id_to_new_facet_id.get(workflow_action.facet_id.id, False)
                    tag_id = workflow_action.tag_id.id and old_tag_id_to_new_tag_id.get(workflow_action.tag_id.id, False)
                # If the facet/tag comes from an unrelated folder, keep the values
                else:
                    facet_id = workflow_action.facet_id.id
                    tag_id = workflow_action.tag_id.id

            workflow_action.copy({
                'workflow_rule_id': old_workflow_rule_id_to_new_workflow_rule_id[workflow_action.workflow_rule_id.id],
                'facet_id': facet_id,
                'tag_id': tag_id,
            })

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        folder = super().copy(default)
        folder.flush_recordset(['children_folder_ids'])
        self.env['documents.tag'].flush_model(['folder_id'])

        old_facet_id_to_new_facet_id, old_tag_id_to_new_tag_id = self._get_old_id_to_new_id_maps(folder)
        self._copy_workflow_rules_and_actions(folder, old_facet_id_to_new_facet_id, old_tag_id_to_new_tag_id)

        for child in self.children_folder_ids:
            child.with_context({
                'ancestors_facet_map': old_facet_id_to_new_facet_id,
                'ancestors_tag_map': old_tag_id_to_new_tag_id,
            }).copy({'parent_folder_id': folder.id})

        return folder

    def action_see_actions(self):
        return {
            'name': _('Actions'),
            'res_model': 'documents.workflow.rule',
            'type': 'ir.actions.act_window',
            'views': [(False, 'list'), (False, 'form')],
            'view_mode': 'tree,form',
            'context': {
                'default_domain_folder_id': self.id,
                'search_default_domain_folder_id': self.id,
            }
        }

    def _compute_document_count(self):
        read_group_var = self.env['documents.document'].read_group(
            [('folder_id', 'in', self.ids)],
            fields=['folder_id'],
            groupby=['folder_id'])

        document_count_dict = dict((d['folder_id'][0], d['folder_id_count']) for d in read_group_var)
        for record in self:
            record.document_count = document_count_dict.get(record.id, 0)

    def action_see_documents(self):
        domain = [('folder_id', '=', self.id)]
        return {
            'name': _('Documents'),
            'domain': domain,
            'res_model': 'documents.document',
            'type': 'ir.actions.act_window',
            'views': [(False, 'list'), (False, 'form')],
            'view_mode': 'tree,form',
            'context': "{'default_folder_id': %s}" % self.id
        }

    def _get_inherited_settings_as_vals(self):
        self.ensure_one()
        return {
            'group_ids': [(6, 0, self.group_ids.ids)],
            'read_group_ids': [(6, 0, self.read_group_ids.ids)],
            'user_specific': self.user_specific,
            'user_specific_write': self.user_specific_write,
        }

    def set_parent_folder(self, parent_folder_id):
        self.ensure_one()
        parent_folder = self.browse(parent_folder_id)
        if self.parent_folder_id == parent_folder:
            return
        parent_folder.check_access_rule('write')
        if parent_folder and parent_folder.parent_path.startswith(self.parent_path):
            self.children_folder_ids.parent_folder_id = self.parent_folder_id
        self.parent_folder_id = parent_folder
        if not parent_folder:
            return
        self.write(parent_folder._get_inherited_settings_as_vals())
