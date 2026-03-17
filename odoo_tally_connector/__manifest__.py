{
    "name": "Odoo Tally XML Export",
    "version": "16.0.1.0.0",
    "summary": "Export Odoo accounting data to Tally vouchers XML",
    "author": "Gultaj Khan",
    "category": "Accounting",
    "images": ["static/img/connector_logo.jpeg"],
    "depends": ["account"],
    "data": [
        # Security
        "security/ir.model.access.csv",
        # Views and wizards
        "views/tally_config_view.xml",
        "views/tax_mapping_view.xml",
        "views/payment_mapping_view.xml",
        "views/tally_product_ledger_view.xml",
        "views/xml_tag_view.xml",
        "views/field_mapping_view.xml",
        "views/generate_xml_wizard_view.xml",
        # Data (demo, menus, etc.)
        "data/demo_data.xml",
        "data/menu.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
    "description": "static/description/index.html"
}
