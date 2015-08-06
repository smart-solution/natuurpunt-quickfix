# -*- coding: utf-8 -*-
from __future__ import division
from openerp.osv import fields, orm
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _

class purchase_line_invoice(orm.TransientModel):

    _inherit = 'purchase.order.line_invoice'

    _columns = {
        'line_ids': fields.one2many('purchase.order.line_invoice.line', 'wizard_id', 'Lines'),
        'invoiced_amount': fields.float('Amount to invoice', digits_compute=dp.get_precision('Product Unit of Measure'), readonly=True),
    }

    def default_get(self, cr, uid, fields, context=None):
        po_line_obj = self.pool.get('purchase.order.line')
        lines = []
        for po_line in po_line_obj.browse(cr, uid, context.get('active_ids', []), context=context):
            lines.append({
                'po_line_id': po_line.id,
                # remaining quantity
                'product_qty': po_line.product_qty - po_line.invoiced_qty,
                # quantity to invoice (equals to remaining quantity by default)
                'invoiced_qty': po_line.product_qty - po_line.invoiced_qty,
                'invoiced_amount': po_line.price_subtotal - po_line.invoiced_amount,
                'price_unit': po_line.price_unit,
            })
        defaults = super(purchase_line_invoice, self).default_get(cr, uid, fields, context=context)
        defaults['line_ids'] = lines
        return defaults

    def makeInvoices(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        PurchaseOrderLine = self.pool.get('purchase.order.line')
        changed_lines = {}
        context['active_ids'] = []
        wizard = self.browse(cr, uid, ids[0], context=context)
        for line in wizard.line_ids:
#            if line.invoiced_qty > line.product_qty:
#                raise orm.except_orm(_('Error'), _("""Quantity to invoice is greater than available quantity"""))
            context['active_ids'].append(line.po_line_id.id)
            changed_lines[line.po_line_id.id] = line.po_line_id.product_qty
            line.po_line_id.write({'product_qty': line.invoiced_qty})

        record_ids =  context.get('active_ids',[])
        if record_ids:
            res = False
            invoices = {}
            invoice_obj = self.pool.get('account.invoice')
            purchase_obj = self.pool.get('purchase.order')
            purchase_line_obj = self.pool.get('purchase.order.line')
            invoice_line_obj = self.pool.get('account.invoice.line')
            account_jrnl_obj = self.pool.get('account.journal')

            def multiple_order_invoice_notes(orders):
                notes = ""
                for order in orders:
                    notes += "%s \n" % order.notes
                return notes



            def make_invoice_by_partner(partner, orders, lines_ids):
                """
                    create a new invoice for one supplier
                    @param partner : The object partner
                    @param orders : The set of orders to add in the invoice
                    @param lines : The list of line's id
                """
                name = ""
                for order in orders:
                    name = name + " " + order.name
                journal_id = account_jrnl_obj.search(cr, uid, [('po_line_invoice_journal', '=', True)], context=None)
                journal_id = journal_id and journal_id[0] or False
                a = partner.property_account_payable.id
                inv = { 
                    'name': name,
                    'origin': name,
                    'type': 'in_invoice',
                    'journal_id':journal_id,
                    'reference' : partner.ref,
                    'account_id': a,
                    'partner_id': partner.id,
                    'invoice_line': [(6,0,lines_ids)],
                    'currency_id' : orders[0].pricelist_id.currency_id.id,
                    'comment': multiple_order_invoice_notes(orders),
                    'payment_term': orders[0].payment_term_id.id,
                    'fiscal_position': partner.property_account_position.id
                }
                inv_id = invoice_obj.create(cr, uid, inv)
                for order in orders:
                    order.write({'invoice_ids': [(4, inv_id)]})
                return inv_id

            for line in purchase_line_obj.browse(cr, uid, record_ids, context=context):
                if (not line.invoiced) and (line.state not in ('draft', 'cancel')):
                    if not line.partner_id.id in invoices:
                        invoices[line.partner_id.id] = []
                    acc_id = purchase_obj._choose_account_from_po_line(cr, uid, line, context=context)
                    inv_line_data = purchase_obj._prepare_inv_line(cr, uid, acc_id, line, context=context)
                    inv_line_data.update({'origin': line.order_id.name})
                    inv_id = invoice_line_obj.create(cr, uid, inv_line_data, context=context)
                    purchase_line_obj.write(cr, uid, [line.id], {'invoiced': True, 'invoice_lines': [(4, inv_id)]})
                    invoices[line.partner_id.id].append((line,inv_id))

            res = []
            for result in invoices.values():
                il = map(lambda x: x[1], result)
                orders = list(set(map(lambda x : x[0].order_id, result)))

                res.append(make_invoice_by_partner(orders[0].partner_id, orders, il))

        for po_line in PurchaseOrderLine.browse(cr, uid, changed_lines.keys(), context=context):
            invoiced_qty = 0.0
            invoiced_amount = 0.0
            for inv_line in po_line.invoice_lines:
                invoiced_qty += inv_line.quantity
                invoiced_amount += inv_line.price_subtotal
            PurchaseOrderLine.write(cr, uid, [po_line.id], {'product_qty': changed_lines[po_line.id]}, context=context)
            if invoiced_qty != changed_lines[po_line.id] and po_line.order_id.quantity_check:
                print "In 1"
                po_line.write({'invoiced': False})
#            if invoiced_amount != po_line.price_subtotal and not po_line.order_id.quantity_check:
#                print "In 2"
#                po_line.write({'invoiced': False})


        return {
            'domain': "[('id','in', ["+','.join(map(str,res))+"])]",
            'name': _('Supplier Invoices'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'view_id': False,
            'context': "{'type':'in_invoice', 'journal_type': 'purchase'}",
            'type': 'ir.actions.act_window'
        }


class purchase_line_invoice_line(orm.TransientModel):

    _name = 'purchase.order.line_invoice.line'

    _columns = {
        'wizard_id': fields.many2one('purchase.order.line_invoice', 'Wizard'),
        'po_line_id': fields.many2one('purchase.order.line', 'Purchase order line', readonly=True),
        'price_unit': fields.related('po_line_id', 'price_unit', type='float', string='Unit Price', readonly=True),
        'product_qty': fields.float('Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), readonly=True),
        'invoiced_qty': fields.float('Quantity to invoice', digits_compute=dp.get_precision('Product Unit of Measure')),
        'invoiced_amount': fields.float('Amount to invoice', digits_compute=dp.get_precision('Product Unit of Measure'), readonly=True),
    }


class account_invoice_line(orm.Model):

    _inherit = 'account.invoice.line'


    def _delivery_qty_get(self, cr, uid, ids, name, args, context=None):
        """Get the delivery qty from the po line"""
        res = {}
        for line in self.browse(cr, uid, ids, context):
            if line.purchase_order_line_ids: 
                res[line.id] = line.purchase_order_line_ids[0].delivery_quantity
            else:
                res[line.id] = 0.0

        return res 

    _columns = { 
        'po_delivery_qty': fields.function(_delivery_qty_get, method=True, string='Delivery Quantity', type="float", readonly=True, store=False),
    }   

    def write(self, cr, uid, ids, vals, context=None):
        """Remove the invoiced flag on po line if the invoice line amount is modified"""
        res =  super(account_invoice_line, self).write(cr, uid, ids, vals=vals, context=context)

        for line in self.browse(cr, uid, ids):
            po_lines = []
            po_lines_amount = 0.0
            if line.purchase_order_line_ids:
                order_id = line.purchase_order_line_ids[0].order_id
                for po_line in line.purchase_order_line_ids:
                    po_lines_amount += po_line.price_subtotal
                    po_lines.append(po_line.id)
                    print "INV PO LINE:",po_line.id
                print "PO LINE AMOUNT",po_lines_amount
                print "LINE AMOUNT",line.price_subtotal
                if po_lines_amount != line.price_subtotal and not order_id.quantity_check:
                    print "A"
                    self.pool.get('purchase.order.line').write(cr, uid, po_lines, {'invoiced':False})
                if po_lines_amount == line.price_subtotal and not order_id.quantity_check:
                    print "B"
                    self.pool.get('purchase.order.line').write(cr, uid, po_lines, {'invoiced':True})
        return res

class purchase_order_line_delivery(orm.TransientModel):

    _inherit = "purchase.order.line.delivery"

    _columns = { 
        'delivery_quantity': fields.float('Delivered Quantity')
    }   

    def delivery_state_set(self, cr, uid, ids, context=None):
        for wiz in self.browse(cr, uid ,ids):
            self.pool.get('purchase.order.line').write(cr, uid, [context['active_id']], {'delivery_state':wiz.delivery_state,'delivery_quantity':wiz.delivery_quantity})
            po_line = self.pool.get('purchase.order.line').browse(cr, uid, context['active_id'])
            user = self.pool.get('res.users').browse(cr, uid, uid)
            log_vals = { 
                'author_id': user.partner_id.id,
                'type': 'notification',
                'model': 'purchase.order',
                'res_id': po_line.order_id.id,
                'body': "Delivery status of line %s <br/>Changed to : %s"%(po_line.name, wiz.delivery_state)
            }
            self.pool.get('mail.message').create(cr, uid, log_vals)
        return True

    def default_get(self, cr, uid, fields, context=None):
        po_line_obj = self.pool.get('purchase.order.line')
        lines = []
        po_line = po_line_obj.browse(cr, uid, context.get('active_id', []), context=context)
        defaults = super(purchase_order_line_delivery, self).default_get(cr, uid, fields, context=context)
        defaults['delivery_quantity'] = po_line.delivery_quantity or 0.0
        defaults['delivery_state'] = po_line.delivery_state or ""
        return defaults


class purchase_order_line(orm.Model):

    _inherit = "purchase.order.line"

    _columns = { 
        'delivery_quantity': fields.float('Delivered Quantity')
    }   

class account_invoice(orm.Model):

    _inherit = "account.invoice"

    _columns = { 
        'state': fields.selection([
            ('draft','Draft'),
            ('proforma','Pro-forma'),
            ('proforma2','Pro-forma'),
            ('open','Open'),
            ('confirmed','Waiting Approval'),
            ('approved','Approved'),
            ('paid','Paid'),
            ('cancel','Cancelled'),
            ('payment_blocked','Blocked for Payment'),
            ],'Status', select=True, readonly=True, track_visibility='onchange',
            help=' * The \'Draft\' status is used when a user is encoding a new and unconfirmed Invoice. \
            \n* The \'Pro-forma\' when invoice is in Pro-forma status,invoice does not have an invoice number. \
            \n* The \'Open\' status is used when user create invoice,a invoice number is generated.Its in open status till user does not pay invoice. \
            \n* The \'Waiting Approval\' when supplier invoice is waiting for approval. \
            \n* The \'Approved\' when supplier invoice is approved. \
            \n* The \'Paid\' status is set automatically when the invoice is paid. Its related journal entries may or may not be reconciled. \
            \n* The \'Cancelled\' status is used when user cancel invoice.'),

    }   

    def invoice_unblock(self, cr, uid, ids, context=None):
        context['unblock'] = True
        context['skip_write'] = True
        self.write(cr, uid, ids, {'state':'approved'}, context=context)
        return True

    def write(self, cr, uid, ids, vals, context=None):
        res = super(account_invoice, self).write(cr, uid, ids, vals=vals, context=context)
        if context is None:
            context = {}

        if isinstance(ids, (int, long)):
            ids = [ids]

        for invoice in self.browse(cr, uid, ids):
            if invoice.state == 'approved' and 'unblock' not in context:
                # Check if invoice should be blocked
                blocked = False
                for line in invoice.invoice_line:
                    if line.po_delivery_qty < line.purchase_order_line_ids[0].invoiced_qty:
                        self.write(cr, uid, ids, {'state':'payment_blocked'})
                        blocked = True
                        break
                    if line.price_unit > line.purchase_order_line_ids[0].price_unit:
                        self.write(cr, uid, ids, {'state':'payment_blocked'})
                        blocked = True
                        break

                # Check if po should be closed
                if not blocked:
                    for line in invoice.invoice_line:
                        if line.purchase_order_line_ids[0].order_id.quantity_check:
                            if line.purchase_order_line_ids[0].product_qty == line.quantity:
                                self.pool.get('purchase.order').write(cr, uid, [line.purchase_order_line_ids[0].order_id.id], {'state':'done'})
                                break
                        else:
                            if line.purchase_order_line_ids[0].order_id.amount_total == line.invoice_id.amount_total:
                                self.pool.get('purchase.order').write(cr, uid, [line.purchase_order_line_ids[0].order_id.id], {'state':'done'})
                                break
                else:
                    for line in invoice.invoice_line:
                        self.pool.get('purchase.order').write(cr, uid, [line.purchase_order_line_ids[0].order_id.id], {'state':'approved'})
                        break


        return res


class account_invoice_refund(orm.TransientModel):
    
    _inherit = 'account.invoice.refund'

    def invoice_refund(self, cr, uid, ids, context=None):
        res = super(account_invoice_refund, self).invoice_refund(cr, uid, ids, context=context)
        inv_obj = self.pool.get('account.invoice')
        inv_line_obj = self.pool.get('account.invoice.line')
        print "REFUND CONTEXT:",context
        # remove the link between the invoice and the po
        for invoice in inv_obj.browse(cr, uid, context['active_ids']):

            for line in invoice.invoice_line:
                for po_line in line.purchase_order_line_ids:
                    inv_line_obj.write(cr, 1, [po_line.id], {'purchase_order_line_ids':[(3,po_line.id,False)]}) 

            for po in invoice.purchase_order_ids:
                inv_obj.write(cr, uid, [invoice.id], {'purchase_order_ids':[(3,po.id,False)]}) 

        return res


