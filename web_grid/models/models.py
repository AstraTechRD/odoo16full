# -*- coding: utf-8 -*-
import datetime
from dateutil import rrule

import collections
from functools import partial

import babel.dates
from dateutil.relativedelta import relativedelta, MO, TU, WE, TH, FR, SA, SU
import pytz

from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools.misc import format_date, get_lang


class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def read_grid(self, row_fields, col_field, cell_field, domain=None, range=None, readonly_field=None, orderby=None):
        """
        Current anchor (if sensible for the col_field) can be provided by the
        ``grid_anchor`` value in the context

        :param list[str] row_fields: group row header fields
        :param str col_field: column field
        :param str cell_field: cell field, summed
        :param range: displayed range for the current page
        :param readonly_field: make cell readonly based on value of readonly_field given
        :type range: None | {'step': object, 'span': object}
        :type domain: None | list
        :returns: dict of prev context, next context, matrix data, row values
                  and column values
        """
        domain = expression.normalize_domain(domain)
        column_info = self._grid_column_info(col_field, range)

        grid_select = set([col_field, cell_field])

        # readonly field should be in select clause with group_operator, or in group by clause too
        if readonly_field:
            grid_select.add(readonly_field)
            if readonly_field != column_info.grouping and not self._fields[readonly_field].group_operator:
                raise UserError(_("The field used as readonly type must have a group_operator attribute."))

        # [{ __count, __domain, grouping, **row_fields, cell_field }]
        groups = self._read_group_raw(
            expression.AND([domain, column_info.domain]),
            list(grid_select) + [f.partition(':')[0] for f in row_fields],
            [column_info.grouping] + row_fields,
            lazy=False, orderby=orderby
        )

        results = self._build_grid(row_fields, col_field, cell_field, column_info,
                                groups=groups, domain=domain, readonly_field=readonly_field)

        return self._apply_grid_grouped_expand(domain, row_fields, results)

    @api.model
    def read_grid_grouped(self, row_fields, col_field, cell_field, section_field, domain,
                          current_range=None, readonly_field=None, orderby=None):
        """
        Fetches grouped grid data.

        :param list[str] row_fields: group row header fields
        :param str col_field: column field
        :param str cell_field: cell field, summed
        :param str section_field: section field
        :param list domain: default domain to apply
        :param current_range: displayed range for the current page
        :param readonly_field: make cell readonly based on value of readonly_field given
        :type current_range: None | {'step': object, 'span': object}
        :type domain: None | list
        :returns: list of dict with prev context, next context, matrix data, row values
                  and column values
        """
        grid_domain = self.read_grid_domain(col_field, current_range)
        grid_domain = grid_domain + (domain or [])

        column_info = self._grid_column_info(col_field, current_range)

        grid_select = set([col_field, cell_field])

        # readonly field should be in select clause with group_operator, or in group by clause too
        if readonly_field:
            grid_select.add(readonly_field)
            if readonly_field != column_info.grouping and not self._fields[readonly_field].group_operator:
                raise UserError(_("The field used as readonly type must have a group_operator attribute."))

        # [{ __count, __domain, grouping, **row_fields, cell_field }]
        groups = self._read_group_raw(
            expression.AND([grid_domain, column_info.domain]),
            list(grid_select) + [f.partition(':')[0] for f in row_fields] + [section_field],
            [column_info.grouping] + row_fields + [section_field],
            lazy=False, orderby=orderby
        )

        section_all_groups = {}
        s_field = self._fields[section_field]
        if s_field.group_expand:
            section_read_group = self.read_group(grid_domain, [section_field], [section_field])
            section_all_groups = {group[section_field]: group['__domain'] for group in section_read_group}

        section_groups = collections.defaultdict(lambda: {'__domain': [], 'groups': []})
        group_expand_section_values = set()

        for group in groups:
            section_field_value = group[section_field]
            section_group = section_groups[section_field_value]
            section_all_groups.pop(section_field_value, None)
            if s_field.type == 'many2one' and section_field_value:
                section_field_value = section_field_value[0]
            group_expand_section_values.add(section_field_value)
            if not section_group['__domain']:
                section_group['__domain'] = expression.AND([
                    grid_domain,
                    [(section_field, '=', section_field_value)],
                ])
            section_group['groups'].append(group)

        for key, value in section_all_groups.items():
            section_field_value = key
            if s_field.type == 'many2one' and key:
                section_field_value = key[0]
            group_expand_section_values.add(section_field_value)
            section_groups[key]['__domain'] = value

        if not section_groups:
            # if there are no groups in the output we still need to fetch an empty grid
            # so we can render the table's decoration (pagination and columns &etc)
            # otherwise we get a completely empty grid
            results = [{
                **self._build_grid(row_fields, col_field, cell_field, column_info,
                                   domain=domain, readonly_field=readonly_field),
                '__label': False,
            }]
        else:
            results = [{
                **self._build_grid(row_fields, col_field, cell_field, column_info,
                                   groups=section_group['groups'], domain=section_group['__domain'],
                                   readonly_field=readonly_field),
                '__label': section_group_label,
            } for section_group_label, section_group in section_groups.items()]

        return self._apply_grid_grouped_expand(
            grid_domain, row_fields, results,
            section_field, group_expand_section_values
        )

    @api.model
    def _apply_grid_grouped_expand(
            self, grid_domain, row_fields, built_grids, section_field=None, group_expand_section_values=None):
        """ Returns the built_grids, after having applied the group_expand on it, according to the grid_domain,
            row_fields, section_field and group_expand_domain_info.

            :param grid_domain: The grid domain.
            :param row_fields: The row fields.
            :param built_grids: The grids that have been previously built and on top of which the group expand has to
                                be performed.
            :param section_field: The section field.
            :param group_expand_section_values: A set containing the record ids for the section field, resulting from the
                                             read_group_raw. The ids can be used in order to limit the queries scopes.
            :return: The modified built_grids.
        """
        return built_grids

    @api.model
    def _build_grid(self, row_fields, col_field, cell_field, column_info,
                    groups=None, domain=None, readonly_field=None):
        if groups is None:
            groups = []

        def row_key(it, fs=row_fields):
            return tuple(it[f] for f in fs)

        # [{ values: { field1: value1, field2: value2 } }]
        rows = self._grid_get_row_headers(row_fields, groups, key=row_key)
        # column_info.values is a [(value, label)] seq
        # convert to [{ values: { col_field: (value, label) } }]
        cols = column_info.values

        # map of cells indexed by row_key (tuple of row values) then column value
        cell_map = collections.defaultdict(dict)
        for group in groups:
            row = row_key(group)
            col = column_info.format(group[column_info.grouping])
            cell_map[row][col] = self._grid_format_cell(group, cell_field, readonly_field)

        # pre-build whole grid, row-major, h = len(rows), w = len(cols),
        # each cell is
        #
        # * size (number of records)
        # * value (accumulated cell_field)
        # * domain (domain for the records of that cell
        grid = []
        for r in rows:
            row = []
            grid.append(row)
            r_k = row_key(r['values'])
            for c in cols:
                col_value = c['values'][col_field][0]
                it = cell_map[r_k].get(col_value)
                if it: # accumulated cell exists, just use it
                    row.append(it)
                else:
                    # generate de novo domain for the cell
                    # The domain of the cell is the combination of the domain of the row, the
                    # column and the view.
                    row.append(self._grid_make_empty_cell(r['domain'], c['domain'], domain))
                row[-1]['is_current'] = c.get('is_current', False)
                row[-1]['is_unavailable'] = c.get('is_unavailable', False)

        return {
            'prev': column_info.prev,
            'next': column_info.next,
            'initial': column_info.initial,
            'cols': cols,
            'rows': rows,
            'grid': grid,
        }

    def _grid_make_empty_cell(self, row_domain, column_domain, view_domain):
        cell_domain = expression.AND([row_domain, column_domain, view_domain])
        return {'size': 0, 'domain': cell_domain, 'value': 0}

    def _grid_format_cell(self, group, cell_field, readonly_field):
        return {
            'size': group['__count'],
            'domain': group['__domain'],
            'value': group[cell_field],
            'readonly': group.get(readonly_field, False),
        }

    def _grid_get_row_headers(self, row_fields, groups, key):
        seen = {}
        rows = []
        for cell in groups:
            k = key(cell)
            if k in seen:
                seen[k][1].append(cell['__domain'])
            else:
                r = (
                    {f: cell[f] for f in row_fields},
                    [cell['__domain']],
                )
                seen[k] = r
                rows.append(r)

        # TODO: generates pretty long domains, is there a way to simplify them?
        return [
            {'values': values, 'domain': expression.OR(domains)}
            for values, domains in rows
        ]

    def _grid_column_info(self, name, range):
        """
        :param str name:
        :param range:
        :type range: None | dict
        :rtype: ColumnMetadata
        """
        if not range:
            range = {}
        field = self._fields[name]
        context_anchor = self.env.context.get('grid_anchor')

        if field.type == 'selection':
            return ColumnMetadata(
                grouping=name,
                domain=[],
                prev=False,
                next=False,
                initial=False,
                values=[{
                        'values': { name: v },
                        'domain': [(name, '=', v[0])],
                        'is_current': False,
                        'is_unavailable': False
                    } for v in field._description_selection(self.env)
                ],
                format=lambda a: a,
            )
        elif field.type == 'many2one':
            return ColumnMetadata(
                grouping=name,
                domain=[],
                prev=False,
                next=False,
                initial=False,
                values=[{
                        'values': { name: v },
                        'domain': [(name, '=', v[0])],
                        'is_current': False
                    } for v in self.env[field.comodel_name].search([]).name_get()
                ],
                format=lambda a: a and a[0],
            )
        elif field.type == 'date':
            # seemingly sane defaults
            step = range.get('step', 'day')
            span = range.get('span', 'month')

            today = anchor = field.from_string(field.context_today(self))
            if context_anchor:
                anchor = field.from_string(context_anchor)

            r = self._grid_range_of(span, step, anchor, field)
            pagination = self._grid_pagination(field, span, step, anchor)
            return ColumnMetadata(
                grouping='{}:{}'.format(name, step),
                domain=[
                    '&',
                    (name, '>=', field.to_string(r.start)),
                    (name, '<=', field.to_string(r.end))
                ],
                prev=pagination.get('prev'),
                next=pagination.get('next'),
                initial=pagination.get('initial'),
                values=[{
                        'values': {
                            name: self._get_date_column_label(d, field, span, step)
                        },
                        'domain': ['&',
                                   (name, '>=', field.to_string(d)),
                                   (name, '<', field.to_string(d + self._grid_step_by(step)))],
                        'is_current': self._grid_date_is_current(field, span, step, d),
                        'is_unavailable': self._grid_datetime_is_unavailable(field, span, step, d)
                    } for d in r.iter(step)
                ],
                format=lambda a: a and a[0],
            )
        elif field.type == 'datetime':
            # seemingly sane defaults
            step = range.get('step', 'day')
            span = range.get('span', 'month')

            anchor = field.from_string(field.today(self))
            if context_anchor:
                anchor = field.from_string(context_anchor)

            r = self._grid_range_of(span, step, anchor, field)
            pagination = self._grid_pagination(field, span, step, anchor)
            return ColumnMetadata(
                grouping='{}:{}'.format(name, step),
                domain=[
                    '&',
                    (name, '>=', r.start_utc),
                    (name, '<=', r.end_utc)
                ],
                prev=pagination.get('prev'),
                next=pagination.get('next'),
                initial=pagination.get('initial'),
                values=[{
                        'values': {
                            name: self._get_date_column_label(d[0], field, span, step)
                        },
                        'domain': ['&',
                                   (name, '>=', field.to_string(d[0])),
                                   (name, '<', field.to_string(d[1]))],
                        'is_current': self._grid_datetime_is_current(field, span, step, d),
                        'is_unavailable': self._grid_datetime_is_unavailable(field, span, step, d),
                        } for d in r.iter()],
                format=lambda a: a and a[0],
            )
        else:
            raise ValueError(_("Can not use fields of type %s as grid columns", field.type))

    @api.model
    def read_grid_domain(self, field, range):
        """ JS grid view may need to know the "span domain" of the grid before
        it has been able to read the grid at all. This provides only that part
        of the grid processing

        .. warning:: the result domain *must* be properly normalized
        """
        if not range:
            range = {}
        field = self._fields[field]
        if field.type == 'selection':
            return []
        elif field.type == 'many2one':
            return []
        elif field.type == 'date':
            step = range.get('step', 'day')
            span = range.get('span', 'month')

            anchor = field.from_string(field.context_today(self))
            context_anchor = self.env.context.get('grid_anchor')
            if context_anchor:
                anchor = field.from_string(context_anchor)

            r = self._grid_range_of(span, step, anchor, field)
            return [
                '&',
                (field.name, '>=', field.to_string(r.start)),
                (field.name, '<=', field.to_string(r.end))
            ]
        elif field.type == 'datetime':
            step = range.get('step', 'day')
            span = range.get('span', 'month')

            anchor = field.from_string(field.today(self))
            context_anchor = self.env.context.get('grid_anchor')
            if context_anchor:
                anchor = field.from_string(context_anchor)

            r = self._grid_range_of(span, step, anchor, field)
            return [
                '&',
                (field.name, '>=', field.to_string(r.start_utc)),
                (field.name, '<=', field.to_string(r.end_utc))
            ]
        raise UserError(_("Can not use fields of type %s as grid columns", field.type))

    def _get_date_column_label(self, date, field, span, step):
        """
            :param date: date of period beginning (datetime object)
            :param field: odoo.field object of the current model
        """
        locale = get_lang(self.env).code
        _labelize = self._get_date_formatter(step, field, locale=locale)

        if field.type == 'datetime':  # we want the column label to be the infos in user tz, while the date domain should still be in UTC
            _date_tz = date.astimezone(pytz.timezone(self._context.get('tz') or 'UTC'))
        else:
            _date_tz = date

        return ("%s/%s" % (field.to_string(date), field.to_string(date + self._grid_step_by(step))), _labelize(_date_tz))

    def _get_date_formatter(self, step, field, locale):
        """ Returns a callable taking a single positional date argument and
        formatting it for the step and locale provided.
        """

        # Week number calculation does not have a dedicated format in `FORMAT['week']`. So its method is a little more
        # complex. More over, `babel` lib does not return correct number. See below.
        if step == 'week':

            def _week_format(date):
                if field.type == 'date':
                    weeknumber = babel.dates.format_date(date, format=FORMAT[step], locale=locale)
                elif field.type == 'datetime':
                    # For some reason, babel returns the '2018-12-31' as "Week 53" instead of "Week 1"
                    # Check https://github.com/python-babel/babel/issues/619 and change this when Odoo will use a fixed Babel version
                    weeknumber = date.strftime('%V')  # ISO 8601 week as a decimal number with Monday as the first day of the week.
                return _("Week %(weeknumber)s\n%(week_start)s - %(week_end)s") % {
                    'weeknumber': weeknumber,
                    'week_start': format_date(self.env, date, locale, "MMM\u00A0dd"),
                    'week_end': format_date(self.env, date + self._grid_step_by(step) - relativedelta(days=1), locale, "MMM\u00A0dd")
                }
            return _week_format

        if hasattr(babel.dates, 'format_skeleton'):
            def _format(d, _fmt=babel.dates.format_skeleton, _sk=SKELETONS[step], _l=locale):
                result = _fmt(datetime=d, skeleton=_sk, locale=_l)
                # approximate distribution over two lines, for better
                # precision should be done by rendering with an actual
                # proportional font, for even better precision should be done
                # using the fonts the browser asks for, here we just use
                # non-whitespace length which is really gross. Also may need
                # word-splitting in non-latin scripts.
                #
                # also ideally should not split the lines at all under a
                # certain width
                cl = lambda l: sum(len(s) for s in l)
                line1 = result.split(u' ')
                halfway = cl(line1) / 2.
                line2 = collections.deque(maxlen=int(halfway) + 1)
                while cl(line1) > halfway:
                    line2.appendleft(line1.pop())

                middle = line2.popleft()
                if cl(line1) < cl(line2):
                    line1.append(middle)
                else:
                    line2.appendleft(middle)

                return u"%s\n%s" % (
                    u'\u00A0'.join(line1),
                    u'\u00A0'.join(line2),
                )
            return _format
        else:
            return partial(babel.dates.format_date,
                           format=FORMAT[step],
                           locale=locale)

    def _grid_pagination(self, field, span, step, anchor):
        if field.type in ['date', 'datetime']:
            if field.type == 'datetime':
                today_utc = pytz.utc.localize(field.today(self))
                today = today_utc.astimezone(pytz.timezone(self._context.get('tz') or 'UTC'))
            else:
                today = field.from_string(field.context_today(self))
            diff = self._grid_step_by(span)
            period_prev = field.to_string(anchor - diff)
            period_next = field.to_string(anchor + diff)
            return {
                'prev': {'grid_anchor': period_prev, 'default_%s' % field.name: period_prev},
                'next': {'grid_anchor': period_next, 'default_%s' % field.name: period_next},
                'initial': {'grid_anchor': field.to_string(today), 'default_%s' % field.name: field.to_string(today)}
            }
        return dict.fromkeys(['prev', 'initial', 'next'], False)

    def _grid_step_by(self, span):
        return STEP_BY.get(span)

    def _grid_range_of(self, span, step, anchor, field):
        """
            For `datetime` field, this method will return a range object containing the list of column date
            bounds. Those datetime are timezoned in UTC. The closing date should not be included in column
            domain.

            :param span: name of the grid range (total period displayed)
            :param step: name of the time unit used as step for grid column
            :param anchor: the `date` or `datetime` in the period to display
            :param field: `odoo.field` used as grouping criteria
        """
        if field.type == 'datetime':
            user_tz = pytz.timezone(self._context.get('tz') or 'UTC')
            return datetime_range(self._grid_start_of(span, step, anchor), self._grid_end_of(span, step, anchor), step, user_tz)
        return date_range(self._grid_start_of(span, step, anchor), self._grid_end_of(span, step, anchor))

    def _grid_start_of(self, span, step, anchor):
        if step == 'week':
            return anchor + self._get_start_of_week(span)
        return anchor + self._get_start_of(span)

    def _grid_end_of(self, span, step, anchor):
        if step == 'week':
            return anchor + self._get_end_of_week(span)
        return anchor + self._get_end_of(span)

    def _grid_start_of_period(self, span, step, anchor):
        if step == 'day':
            return anchor
        return anchor + self._get_start_of(span)

    def _grid_end_of_period(self, span, step, anchor):
        if step == 'day':
            return anchor
        return anchor + self._get_end_of(span)

    def _grid_date_is_current(self, field, span, step, date):
        today = field.from_string(field.context_today(self))
        if step == 'day':
            return today == date
        elif step in ['week', 'month']:
            return self._grid_start_of_period(span, step, date) <= today < self._grid_end_of_period(span, step, date)
        return False

    def _grid_datetime_is_current(self, field, span, step, column_dates):
        """
            :param column_dates: tuple of start/stop dates of a grid column, timezoned in UTC
        """
        today_utc = pytz.utc.localize(field.now())
        return column_dates[0] <= today_utc < column_dates[1]

    def _grid_datetime_is_unavailable(self, field, span, step, column_dates):
        """
            :param column_dates: tuple of start/stop dates of a grid column, timezoned in UTC
            This method is meant to be overriden by each model that want to
            implement this feature on a Grid view.
        """
        return False

    def _get_start_of(self, span):
        if span == 'week':
            user_lang = self.env['res.lang'].search([('code', '=', self.env.user.lang)])
            week_start_map = {'1': MO(-1), '2': TU(-1), '3': WE(-1), '4': TH(-1), '5': FR(-1), '6': SA(-1), '7': SU(-1)}
            return relativedelta(weekday=week_start_map.get(user_lang.week_start, MO(-1)))
        return START_OF[span]

    def _get_start_of_week(self, span):
        user_lang = self.env['res.lang'].search([('code', '=', self.env.user.lang)])
        week_start_map = {'1': MO(-1), '2': TU(-1), '3': WE(-1), '4': TH(-1), '5': FR(-1), '6': SA(-1), '7': SU(-1)}
        week_start_delta = relativedelta(weekday=week_start_map.get(user_lang.week_start, MO(-1)))
        if span == 'week':
            return week_start_delta
        return START_OF[span] + week_start_delta

    def _get_end_of(self, span):
        if span == 'week':
            user_lang = self.env['res.lang'].search([('code', '=', self.env.user.lang)])
            week_end_map = {'1': SU, '2': MO, '3': TU, '4': WE, '5': TH, '6': FR, '7': SA}
            return relativedelta(weekday=week_end_map.get(user_lang.week_start, SU))
        return END_OF[span]

    def _get_end_of_week(self, span):
        user_lang = self.env['res.lang'].search([('code', '=', self.env.user.lang)])
        week_end_map = {'1': SU, '2': MO, '3': TU, '4': WE, '5': TH, '6': FR, '7': SA}
        week_end_delta = relativedelta(weekday=week_end_map.get(user_lang.week_start, SU))
        if span == 'week':
            return week_end_delta
        return END_OF[span] + week_end_delta


# ---------------------------------------------------------
# Internal Data Structure:
#  - namedtuple for Metadata of grid column
#  - date/datetime range objects
# ---------------------------------------------------------

ColumnMetadata = collections.namedtuple('ColumnMetadata', 'grouping domain prev next initial values format')


class date_range(object):
    def __init__(self, start, stop):
        assert start <= stop
        self.start = start
        self.end = stop

    def iter(self, step):
        v = self.start
        step = STEP_BY[step]
        while v <= self.end:
            yield v
            v += step


class datetime_range(object):
    def __init__(self, start, stop, step, user_tz):
        assert start <= stop
        self._start = user_tz.localize(datetime.datetime.combine(start, datetime.time.min))
        self._end = user_tz.localize(datetime.datetime.combine(stop, datetime.time.max))
        self.step = step
        self._user_tz = user_tz
        self._periods = self._generate_period()

    @property
    def start_utc(self):
        return self._user_tz.localize(self._start.replace(tzinfo=None)).astimezone(pytz.utc)

    @property
    def end_utc(self):
        return self._user_tz.localize(self._end.replace(tzinfo=None)).astimezone(pytz.utc)

    def _generate_period(self):
        """ Generate tuple reprenseting grid column period with start datetime and end datetime. We use `rrule` as this lib takes
            DST (Daylight Saving Time) into account. We select the period the user wants in its timezone (the `read_group` groups by
            datetime in current user TZ). Then, convert it into UTC to be sent and use by the sytem.
        """
        start = self._start.replace(tzinfo=None)
        stop = self._end.replace(tzinfo=None) + STEP_BY[self.step]  # add a step as the given stop limit is not included in column domain

        if self.step == 'day':
            r = rrule.rrule(rrule.DAILY, dtstart=start, until=stop)

        if self.step == 'week':
            # Seems that PostgresSQL consider Monday as first week day (The ISO-8601 week starts on
            # Monday). See https://www.postgresql.org/docs/9.1/functions-datetime.html
            start = start + relativedelta(weekday=MO(-1))
            stop = stop + relativedelta(weekday=MO(-1))
            r = rrule.rrule(rrule.WEEKLY, dtstart=start, until=stop, wkst=MO)

        if self.step == 'month':
            r = rrule.rrule(rrule.MONTHLY, dtstart=start, until=stop)

        date_range = []
        previous_dt = None
        for dt in r:
            current_dt = self._user_tz.localize(dt)
            if previous_dt:
                date_range.append((previous_dt.astimezone(pytz.utc), current_dt.astimezone(pytz.utc)))
            previous_dt = current_dt

        return date_range

    def iter(self):
        return iter(self._periods)


# ---------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------

START_OF = {
    'day': relativedelta(days=0),
    'month': relativedelta(day=1),
    'year': relativedelta(yearday=1),
}
END_OF = {
    'day': relativedelta(days=0),
    'month': relativedelta(months=1, day=1, days=-1),
    'year': relativedelta(years=1, yearday=1, days=-1),
}
STEP_BY = {
    'day': relativedelta(days=1),
    'week': relativedelta(weeks=1),
    'month': relativedelta(months=1),
    'year': relativedelta(years=1),
}

FORMAT = {
    'day': u"EEE\nMMM\u00A0dd",
    'week': u'w',
    'month': u'MMMM\u00A0yyyy',
}
SKELETONS = {
    'day': u"MMMEEEdd",
    'month': u'yyyyMMMM',
}
