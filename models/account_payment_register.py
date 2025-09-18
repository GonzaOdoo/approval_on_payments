from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class AccountPayment(models.TransientModel):
    _inherit = 'account.payment.register'

    installment_number = fields.Integer('Cuota Nro')
    payment_details = fields.Text('Detalle de pago')

    def _create_payment_vals_from_wizard(self, batch_result):
        # Llama al método original para obtener los valores base
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)

        # Agrega tus campos personalizados al diccionario
        payment_vals.update({
            'installment_number': self.installment_number,
            'payment_details': self.payment_details,
        })

        return payment_vals
    
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
            payment = vals['payment']
            payment.to_reconcile_move_line_ids = [(6, 0, vals['to_reconcile'].ids)]
            invoices = vals['to_reconcile'].move_id.filtered(lambda m: m.is_invoice())

            if not invoices:
                # Si no son facturas, mandar a aprobación
                payments |= payment
                continue
            # Verificar que todas las facturas sean de cliente (out_invoice, out_refund, etc.)
            if all(inv.move_type in ('out_invoice', 'out_refund', 'out_receipt') for inv in invoices):
                # Son facturas de cliente: publicar directamente
                payment.action_post()
            else:
                # Incluye facturas de proveedor: enviar a aprobación
                payments |= payment
                payments.action_submit_for_approval()