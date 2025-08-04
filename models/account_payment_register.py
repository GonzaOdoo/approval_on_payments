from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountPayment(models.TransientModel):
    _inherit = 'account.payment.register'


    def _post_payments(self, to_process, edit_mode=False):
        """ Post the newly created payments.

        :param to_process:  A list of python dictionary, one for each payment to create, containing:
                            * create_vals:  The values used for the 'create' method.
                            * to_reconcile: The journal items to perform the reconciliation.
                            * batch:        A python dict containing everything you want about the source journal items
                                            to which a payment will be created (see '_compute_batches').
        :param edit_mode:   Is the wizard in edition mode.
        """
        payments = self.env['account.payment']
        for vals in to_process:
            payments |= vals['payment']
            payments.to_reconcile_move_line_ids = [(6, 0, vals['to_reconcile'].ids)]
        payments.action_submit_for_approval()
