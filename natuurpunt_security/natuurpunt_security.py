# -*- coding: utf-8 -*-
##############################################################################
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import osv, fields

class res_partner(osv.osv):
    _name = 'res.partner'
    _inherit = 'res.partner'

    _columns = {
        'zip_ids': fields.many2many('res.country.city', 'res_organisation_city_rel', 'partner_id', 'zip_id', 'Gemeentes afdelingen',groups='organisation_structure.group_organisation_structure_user'),       
        'm2m_zip_ids': fields.many2many('res.country.city', 'res_organisation_city_m2m_rel', 'partner_id', 'zip_id', 'Gemeentes overige',groups='organisation_structure.group_organisation_structure_user'),
    }

res_partner()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
