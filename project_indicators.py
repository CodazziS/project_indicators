from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
from lxml import etree as ET



class project_indicators_task(osv.osv):
    _inherit = 'project.task'

    def add_value(self, cr, uid, fields=None, context=None):
        action = self.pool.get('ir.actions.act_window').for_xml_id(
            cr,
            uid,
            'project_indicators',
            'project_indicators_values_new',
            context=context
        )
        return action

    _columns = {
        'indicators_definitions': fields.one2many(
            'project_indicators.indicators_definition',
            'tasks_ids',
            'Indicators definitions'),
    }


class project_indicators_indicators_definition(osv.osv):
    _name = 'project_indicators.indicators_definition'
    _description = 'Indicators projects definitions'
    _order = 'sequence'
    _rec_name = 'field_name'

    def fields_get(self, cr, uid, fields=None, context=None):
        if not context:
            context = {}
        res = super(project_indicators_indicators_definition, self).\
            fields_get(
                cr,
                uid,
                fields,
                context=context)
        return res

    def read(self,
        cr,
        uid,
        ids,
        fields=None,
        context=None,
        load='_classic_read'):
        if not context:
            context = {}
        res = super(project_indicators_indicators_definition, self).read(
            cr,
            uid,
            ids,
            fields,
            context=context,
            load=load)

        infos = {}
        for ind_id in ids:
            infos[ind_id] = {}
            definition = self.\
                pool['project_indicators.indicators_definition'].browse(
                    cr,
                    uid,
                    ind_id,
                    context=context)
            infos[ind_id]['mov'] = definition.obj_month_value
            infos[ind_id]['moo'] = definition.obj_month_operator
            infos[ind_id]['sov'] = definition.obj_sum_value
            infos[ind_id]['soo'] = definition.obj_sum_operator
            infos[ind_id]['dates'] = {}
            values = definition.values_ids
            for val in values:
                date = str(val.year).zfill(4) + "-" + str(val.month).zfill(2)
                infos[ind_id]['dates'][date] = val.value

        for line in res:
            current_sum = 0
            for date in infos[line['id']]['dates']:
                line[date] = infos[line['id']]['dates'][date]
                if infos[line['id']]['dates'][date] and infos[line['id']]['dates'][date].isdigit():
                    current_sum += int(infos[line['id']]['dates'][date])
                else:
                    current_sum = '-'

            line['sum'] = current_sum
            line['objectives'] = ""
            if infos[line['id']]['moo'] and infos[line['id']]['mov']:
                line['objectives'] += ('Monthly: \n' +
                    str(infos[line['id']]['moo']) + ' ' +
                    str(infos[line['id']]['mov']) + '\n') 

            if infos[line['id']]['soo'] and infos[line['id']]['sov']:
                line['objectives'] += ('Total: \n' +
                str(infos[line['id']]['soo']) + ' ' +
                str(infos[line['id']]['sov']))
        return res

    def delete_value(self, cr, uid, ids, context=None):
        definition = self.\
            pool['project_indicators.indicators_definition'].browse(
            cr,
            uid,
            ids[0],
            context=context)
        values = definition.values_ids
        year = int(context['date'][:4])
        month = int(context['date'][5:])
        for val in values:
            if val.year == year and val.month == month:
                val.unlink()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def __getattr__(self, name, *args, **kwargs):
        if name[:13] == 'delete_value_':
            date = name[13:]
            self.date = date
            return self.delete_value
        else:
            return super(project_indicators_indicators_definition, self).\
                __getattr__(name, *args, **kwargs)

    def fields_view_get(self, cr, uid, view_id=None, view_type='form',
        context=None, toolbar=False, submenu=False):
        if not context:
            context = {}

        res = super(
            project_indicators_indicators_definition,
            self).fields_view_get(
                cr,
                uid,
                view_id,
                view_type,
                context,
                toolbar,
                submenu)

        task_id = context.get('id', False)
        if not task_id is False:
            if view_type == 'tree':
                task = self.pool['project.task'].browse(
                    cr,
                    uid,
                    task_id,
                    context=context)
                definitions = task.indicators_definitions
                months_str = ""
                months = {}

                for definition in definitions:
                    values = definition.values_ids
                    for value in values:
                        date = str(value.year).zfill(4) + "-" + \
                            str(value.month).zfill(2)
                        if not date in months:
                            months[date] = True

                for key in months:
                    months_str += '<field string="%(key)s" name="%(key)s" />'% {'key': key}
                    months_str += '\
                        <button name="delete_value_%(key)s" type="object"\
                        icon="gtk-close"\
                        context="{\'date\': \'%(key)s\'}"/>' % {'key': key}

                arch = """
                    <tree string="Indicators projects value">
                        <field string="Indicators" name="field_name"/>
                        <field string="Objectives" name="objectives"/>
                        %s
                        <field string="Sum" name="sum" />
                    </tree>
                """ % months_str
                res['arch'] = arch
        return res

    _columns = {
        'field_name': fields.char('Field name', required="True"),
        'field_type': fields.selection((
            ('number', 'Number'),
            ('text', 'Text')),
            'Field type', required="True"),
        'obj_month_operator': fields.selection((
                ('==', 'Equal'),
                ('<', '<'),
                ('>', '>'),
            ),
            'Monthly objectives operator'),
        'obj_month_value': fields.char('Monthly objective value'),
        'obj_sum_operator': fields.selection((
                ('==', 'Equal'),
                ('<', '<'),
                ('>', '>'),
            ),
            'Total objectives operator'),
        'obj_sum_value': fields.char('Total objective value'),
        'values_ids': fields.one2many(
            'project_indicators.indicators_value',
            'definition_id',
            'Values'),
        'tasks_ids': fields.many2one(
            'project.task',
            'indicators_definitions',
            'Task'),
        'sequence': fields.integer('Sequence'),
     }


class project_indicators_indicators_value(osv.osv):
    _name = 'project_indicators.indicators_value'
    _description = 'Indicators projects value'
    _order = 'year,month'

    def write(self, cr, uid, ids, values, context=None):
        super(project_indicators_indicators_value, self).write(
            cr,
            uid,
            ids,
            values,
            context=context
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    _columns = {
        'value': fields.char('Value', required="True"),
        'month': fields.integer('Month', required="True"),
        'year': fields.integer('Year', required="True"),
        'definition_id': fields.many2one(
            'project_indicators.indicators_definition',
            'value_ids',
            'Definition',
            required="True"),
    }

    _sql_constraints = [('unique_sheme_type',
        'unique(month,year,definition_id)',
        'Error! This Type already exists!')]
