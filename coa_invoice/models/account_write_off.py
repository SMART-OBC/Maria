
from odoo import api, fields, models, _


class AccountWriteoff(models.Model):
    _name='account.write.off'
    _description = 'Account Move Writeoff'

    account_id = fields.Many2one('account.account',string="Account")
    account_move_id = fields.Many2one('account.move',string="Invoices")

    def action_writeoff_moves(self):
        reverse = self.env['account.move.reversal'].create({'refund_method':'refund',
                                                            'date_mode':'custom',
                                                            'move_ids':self.account_move_id
                                                            })
        action = reverse.reverse_moves()
        action['name'] = 'Write off/Bad Dept'
        self.account_move_id.state = 'bad'
        mov_id = self.env['account.move'].search([('id', '=', action.get('res_id'))])
        mov_id.state = self.account_move_id.state
        mov_id.ref = mov_id.ref+'/Bad Dept'
        # mov_id.name = mov_id.ref+'/Bad Dept'
        self.env['account.move.line'].create({'move_id':mov_id.id,
                                              'move_name':action['name'],
                                              'ref':mov_id.ref,
                                              'parent_state':mov_id.state,
                                              'journal_id':mov_id.journal_id.id,
                                              'account_id':self.account_id.id,
                                              'name':action['name'],
                                              })
        return action
