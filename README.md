# Odoo Tally Connector

Odoo Tally Connector is a module that exports Odoo accounting data into Tally-compatible XML vouchers.

The module supports Odoo versions 14–17 and allows users to generate XML files that can be imported directly into Tally using:
Gateway of Tally → Import Data → Vouchers.

## Features

- Export Customer Invoices as Sales Vouchers
- Export Vendor Bills as Purchase Vouchers
- Export Customer & Vendor Payments
- Support for GST (CGST, SGST, IGST, CESS)
- Product and Category Ledger Mapping
- Payment Journal to Tally Ledger Mapping
- Automatic Ledger Creation
- High-performance XML generation for large datasets

## Workflow

1. Configure Tally mappings in Odoo
2. Generate XML vouchers from accounting documents
3. Import the XML file into Tally

## Technical Information

Module Name: `odoo_tally_connector`  
License: LGPL-3  
Category: Accounting  
Compatible Versions: Odoo 14, 15, 16, 17

## Use Case

This module helps businesses that use Odoo for operations but maintain accounting in Tally by enabling a structured export of accounting data.
