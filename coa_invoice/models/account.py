
from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError

INTEGRITY_HASH_LINE_FIELDS = ('debit', 'credit', 'account_id', 'partner_id')


class AccountAccount(models.Model):
    _inherit='account.account'

    def action_invoice(self):
        account_move_line = self.env['account.move.line'].search([('account_id', '=', self.id)])
        account_move = self.env['account.move']
        for account in account_move_line:
            account_move += account.move_id
        account_move = list(set(account_move.ids))
        action = self.env.ref('account.action_move_journal_line').read()[0]
        action['context'] = {
            'search_default_id': self.id,
            'default_id': self.id,
            'default_state': 'draft',
        }
        action['domain'] = [('id', 'in', account_move)]
        return action

    def _compute_tax_lock_date_message(self):
        if self._context.get('quickbook'):
            self.state = 'draft'
        res = super(AccountAccount, self)._compute_tax_lock_date_message()
        return res
    
    def _affect_tax_report(self):
        return super(AccountAccount, self)._affect_tax_report()


class AccountMove(models.Model):
    _inherit='account.move'

    state = fields.Selection(selection_add=[
        ('bad', 'Bad Dept'),
    ], ondelete={'bad': lambda recs: recs.write({'state': 'draft', 'active': False})})

    def action_write_off(self):
        # self.state = 'bad'
        action = self.env["ir.actions.actions"]._for_xml_id("coa_invoice.action_view_account_move_writeoff")

        if self.is_invoice():
            action['name'] = _('Write off/Bad dept')

        return action


class AccountMoveLine(models.Model):
    _inherit='account.move.line'

    def _check_reconciliation(self):
        if not self._context.get('quickbook'):
            res = super(AccountMoveLine, self)._check_reconciliation()
            return res

    @api.onchange('account_id')
    def onchange_account(self):
        pass

    def write(self, vals):
        if not self._context.get('quickbook'):
            # self.parent_state = self.move_id.state
            return super(AccountMoveLine, self).write(vals)
        # if self._context.get('quickbook'):
        #     self.parent_state = 'posted'
        return True

    # def write(self, vals):
    #     # OVERRIDE
    #     ACCOUNTING_FIELDS = ('debit', 'credit', 'amount_currency')
    #     BUSINESS_FIELDS = ('price_unit', 'quantity', 'discount', 'tax_ids')
    #     PROTECTED_FIELDS_TAX_LOCK_DATE = ['debit', 'credit', 'tax_line_id', 'tax_ids', 'tax_tag_ids']
    #     PROTECTED_FIELDS_LOCK_DATE = PROTECTED_FIELDS_TAX_LOCK_DATE + ['account_id', 'journal_id', 'amount_currency',
    #                                                                    'currency_id', 'partner_id']
    #     PROTECTED_FIELDS_RECONCILIATION = ('account_id', 'date', 'debit', 'credit', 'amount_currency', 'currency_id')
    #
    #     account_to_write = self.env['account.account'].browse(vals['account_id']) if 'account_id' in vals else None
    #
    #     # Check writing a deprecated account.
    #     if account_to_write and account_to_write.deprecated:
    #         raise UserError(_('You cannot use a deprecated account.'))
    #
    #     for line in self:
    #         if line.parent_state == 'posted' and not self._context.get('quickbook'):
    #             if line.move_id.restrict_mode_hash_table and set(vals).intersection(INTEGRITY_HASH_LINE_FIELDS):
    #                 raise UserError(
    #                     _("You cannot edit the following fields due to restrict mode being activated on the journal: %s.") % ', '.join(
    #                         INTEGRITY_HASH_LINE_FIELDS))
    #             if any(key in vals for key in ('tax_ids', 'tax_line_ids')) and not self._context.get('quickbook'):
    #                 raise UserError(
    #                     _('You cannot modify the taxes related to a posted journal item, you should reset the journal entry to draft to do so.'))
    #
    #         # Check the lock date.
    #         if any(self.env['account.move']._field_will_change(line, vals, field_name) for field_name in
    #                PROTECTED_FIELDS_LOCK_DATE):
    #             line.move_id._check_fiscalyear_lock_date()
    #
    #         # Check the tax lock date.
    #         if any(self.env['account.move']._field_will_change(line, vals, field_name) for field_name in
    #                PROTECTED_FIELDS_TAX_LOCK_DATE):
    #             line._check_tax_lock_date()
    #
    #         # Check the reconciliation.
    #         if any(self.env['account.move']._field_will_change(line, vals, field_name) for field_name in
    #                PROTECTED_FIELDS_RECONCILIATION):
    #             line._check_reconciliation()
    #
    #         # Check switching receivable / payable accounts.
    #         if account_to_write:
    #             account_type = line.account_id.user_type_id.type
    #             if line.move_id.is_sale_document(include_receipts=True):
    #                 if (account_type == 'receivable' and account_to_write.user_type_id.type != account_type) \
    #                         or (account_type != 'receivable' and account_to_write.user_type_id.type == 'receivable'):
    #                     raise UserError(
    #                         _("You can only set an account having the receivable type on payment terms lines for customer invoice."))
    #             if line.move_id.is_purchase_document(include_receipts=True):
    #                 if (account_type == 'payable' and account_to_write.user_type_id.type != account_type) \
    #                         or (account_type != 'payable' and account_to_write.user_type_id.type == 'payable'):
    #                     raise UserError(
    #                         _("You can only set an account having the payable type on payment terms lines for vendor bill."))
    #
    #     # Tracking stuff can be skipped for perfs using tracking_disable context key
    #     if not self.env.context.get('tracking_disable', False):
    #         # Get all tracked fields (without related fields because these fields must be manage on their own model)
    #         tracking_fields = []
    #         for value in vals:
    #             field = self._fields[value]
    #             if hasattr(field, 'related') and field.related:
    #                 continue  # We don't want to track related field.
    #             if hasattr(field, 'tracking') and field.tracking:
    #                 tracking_fields.append(value)
    #         ref_fields = self.env['account.move.line'].fields_get(tracking_fields)
    #
    #         # Get initial values for each line
    #         move_initial_values = {}
    #         for line in self.filtered(lambda l: l.move_id.posted_before):  # Only lines with posted once move.
    #             for field in tracking_fields:
    #                 # Group initial values by move_id
    #                 if line.move_id.id not in move_initial_values:
    #                     move_initial_values[line.move_id.id] = {}
    #                 move_initial_values[line.move_id.id].update({field: line[field]})
    #
    #         # Create the dict for the message post
    #         tracking_values = {}  # Tracking values to write in the message post
    #         for move_id, modified_lines in move_initial_values.items():
    #             tmp_move = {move_id: []}
    #             for line in self.filtered(lambda l: l.move_id.id == move_id):
    #                 changes, tracking_value_ids = line._mail_track(ref_fields,
    #                                                                modified_lines)  # Return a tuple like (changed field, ORM command)
    #                 tmp = {'line_id': line.id}
    #                 if tracking_value_ids:
    #                     selected_field = tracking_value_ids[0][
    #                         2]  # Get the last element of the tuple in the list of ORM command. (changed, [(0, 0, THIS)])
    #                     tmp.update({
    #                         **{'field_name': selected_field.get('field_desc')},
    #                         **self._get_formated_values(selected_field)
    #                     })
    #                 elif changes:
    #                     field_name = line._fields[changes.pop()].string  # Get the field name
    #                     tmp.update({
    #                         'error': True,
    #                         'field_error': field_name
    #                     })
    #                 else:
    #                     continue
    #                 tmp_move[move_id].append(tmp)
    #             if len(tmp_move[move_id]) > 0:
    #                 tracking_values.update(tmp_move)
    #
    #         # Write in the chatter.
    #         for move in self.mapped('move_id'):
    #             fields = tracking_values.get(move.id, [])
    #             if len(fields) > 0:
    #                 msg = self._get_tracking_field_string(tracking_values.get(move.id))
    #                 move.message_post(body=msg)  # Write for each concerned move the message in the chatter
    #
    #     result = True
    #     for line in self:
    #         cleaned_vals = line.move_id._cleanup_write_orm_values(line, vals)
    #         if not cleaned_vals:
    #             continue
    #
    #         # Auto-fill amount_currency if working in single-currency.
    #         if 'currency_id' not in cleaned_vals \
    #                 and line.currency_id == line.company_currency_id \
    #                 and any(field_name in cleaned_vals for field_name in ('debit', 'credit')):
    #             cleaned_vals.update({
    #                 'amount_currency': vals.get('debit', 0.0) - vals.get('credit', 0.0),
    #             })
    #
    #         result |= super(AccountMoveLine, line).write(cleaned_vals)
    #
    #         if not line.move_id.is_invoice(include_receipts=True):
    #             continue
    #
    #         # Ensure consistency between accounting & business fields.
    #         # As we can't express such synchronization as computed fields without cycling, we need to do it both
    #         # in onchange and in create/write. So, if something changed in accounting [resp. business] fields,
    #         # business [resp. accounting] fields are recomputed.
    #         if any(field in cleaned_vals for field in ACCOUNTING_FIELDS):
    #             price_subtotal = line._get_price_total_and_subtotal().get('price_subtotal', 0.0)
    #             to_write = line._get_fields_onchange_balance(price_subtotal=price_subtotal)
    #             to_write.update(line._get_price_total_and_subtotal(
    #                 price_unit=to_write.get('price_unit', line.price_unit),
    #                 quantity=to_write.get('quantity', line.quantity),
    #                 discount=to_write.get('discount', line.discount),
    #             ))
    #             result |= super(AccountMoveLine, line).write(to_write)
    #         elif any(field in cleaned_vals for field in BUSINESS_FIELDS):
    #             to_write = line._get_price_total_and_subtotal()
    #             to_write.update(line._get_fields_onchange_subtotal(
    #                 price_subtotal=to_write['price_subtotal'],
    #             ))
    #             result |= super(AccountMoveLine, line).write(to_write)
    #
    #     # Check total_debit == total_credit in the related moves.
    #     if self._context.get('check_move_validity', True):
    #         self.mapped('move_id')._check_balanced()
    #
    #     self.mapped('move_id')._synchronize_business_models({'line_ids'})
    #
    #     return result