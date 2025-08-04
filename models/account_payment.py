from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # Extendemos el campo state con un nuevo estado
    state = fields.Selection(
        selection_add=[
            ('pending_approval', "Por aprobar"),('approved','Aprobado'),('in_process',),
        ],
        ondelete={
            'pending_approval': 'set default',
            'approved': 'set default',
        }
    )
    to_reconcile_move_line_ids = fields.Many2many(
        'account.move.line',
        string="Líneas a reconciliar",
        help="Líneas de factura que deben reconciliarse al confirmar el pago.",
        copy=False
    )

    def action_post(self):
        ''' draft -> posted '''
        # Do not allow posting if the account is required but not trusted
        for payment in self:
            if (
                payment.require_partner_bank_account
                and not payment.partner_bank_id.allow_out_payment
                and payment.payment_type == 'outbound'
            ):
                raise UserError(_(
                    "To record payments with %(method_name)s, the recipient bank account must be manually validated. "
                    "You should go on the partner bank account of %(partner)s in order to validate it.",
                    method_name=self.payment_method_line_id.name,
                    partner=payment.partner_id.display_name,
                ))
        self.filtered(lambda pay: pay.outstanding_account_id.account_type == 'asset_cash').state = 'paid'
        # Avoid going back one state when clicking on the confirm action in the payment list view and having paid expenses selected
        # We need to set values to each payment to avoid recomputation later
        self.filtered(lambda pay: pay.state in {False, 'approved', 'in_process'}).state = 'in_process'

        # === Reconciliación diferida ===
        domain = [
            ('parent_state', '=', 'posted'),
            ('account_type', 'in', self.env['account.payment']._get_valid_payment_account_types()),
            ('reconciled', '=', False),
        ]
    
        for payment in self:
            if not payment.to_reconcile_move_line_ids:
                continue
    
            payment_lines = payment.move_id.line_ids.filtered_domain(domain)
            lines = payment.to_reconcile_move_line_ids
    
            for account in payment_lines.account_id:
                (payment_lines + lines)\
                    .filtered_domain([
                        ('account_id', '=', account.id),
                        ('reconciled', '=', False),
                        ('parent_state', '=', 'posted'),
                    ])\
                    .reconcile()
    
            # Marcar que ya se reconcilió
            lines.move_id.matched_payment_ids += payment
            payment.to_reconcile_move_line_ids = [(5, 0, 0)]  # Vaciar relación
        
    def action_submit_for_approval(self):
        """ Cambia el estado a 'pending_approval' """
        for payment in self:
            payment.state = 'pending_approval'

    def action_approve(self):
        """ Aprobar: NO crea ni publica el asiento, solo marca como aprobado """
        for payment in self:
            if payment.state != 'pending_approval':
                raise UserError(_("Solo se pueden aprobar pagos en 'Por aprobar'."))
            payment.state = 'approved'
           
    def action_reject(self):
        """ Rechazar el pago """
        for payment in self:
            if payment.state != 'pending_approval':
                raise UserError(_("Solo se puede rechazar un pago pendiente de aprobación."))
            payment.state = 'rejected'