from odoo import models, modules, api


class Module(models.Model):
    _inherit = "ir.module.module"

    @api.multi
    def _button_immediate_function(self, function):
        function(self)

        self._cr.commit()
        api.Environment.reset()
        modules.registry.Registry.new(self._cr.dbname, update_module=True)

        self._cr.commit()
        env = api.Environment(self._cr, self._uid, self._context)
        config = env['res.config'].next() or {}
        if config.get('type') not in ('ir.actions.act_window_close',):
            return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                    }

        # reload the client; open the first available root menu
        menu = env['ir.ui.menu'].search([('parent_id', '=', False)])[:1]
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {'menu_id': menu.id},
        }