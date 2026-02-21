"""
BUSY ERP Integration Utilities
Handles XML-based uploads to BUSY ERP via DLL (SaveVchFromXML, SaveMasterFromXML).
NOTE: In SQL Server mode, COM-based uploads are disabled.
      XML is built and printed for debugging, but not sent to BUSY.
"""

from xml.sax.saxutils import escape


def escape_xml(text):
    """Escape XML special characters in text."""
    if text is None:
        return ""
    return escape(str(text))


# ---------------------------------------------------------------------------
# Master helpers (AddMaster via COM) — disabled in SQL Server mode
# ---------------------------------------------------------------------------

def _add_master_via_dll(master_type):
    """
    Previously opened BUSY Add Master form via COM AddMaster.
    Disabled in SQL Server mode.
    """
    return False, "BUSY COM integration is disabled. Using SQL Server mode.", None


def upload_item_to_busy(item_name=None, unit=None, hsn=None, tax_category=None):
    """Open Busy Add Item form — disabled in SQL Server mode."""
    return _add_master_via_dll(6)


def upload_party_to_busy(party_name=None):
    """Open Busy Add Party form — disabled in SQL Server mode."""
    return _add_master_via_dll(2)


# ---------------------------------------------------------------------------
# Purchase Voucher upload
# ---------------------------------------------------------------------------

def upload_purchase_voucher_to_busy(voucher_data):
    """
    Build XML for a Purchase Voucher and attempt to save it to BUSY ERP.

    In SQL Server mode the COM upload is disabled. The function builds and
    logs the XML for debugging, then returns a success=False with a clear
    message so the UI can report it gracefully.

    Args:
        voucher_data: dict with keys:
            date, series, voucher_no, purchase_type, party_name,
            narration (optional), items (list), bill_sundries (list)

    Returns:
        (success: bool, message: str, voucher_code: str|None)
    """
    purchase_type = voucher_data.get('purchase_type', 'Central-ItemWise')

    is_local_itemwise = (
        'local' in purchase_type.lower()
        and ('itemwise' in purchase_type.lower() or 'taxincl' in purchase_type.lower())
    )
    is_multirate = "multirate" in purchase_type.lower()

    # ── Build XML ─────────────────────────────────────────────────────────
    xml_data = "<Purchase>"

    # Header
    xml_data += f"<VchSeriesName>{escape_xml(voucher_data.get('series', 'Main'))}</VchSeriesName>"
    xml_data += f"<Date>{escape_xml(voucher_data.get('date', ''))}</Date>"
    xml_data += "<VchType>2</VchType>"
    xml_data += f"<VchNo>{escape_xml(voucher_data.get('voucher_no', ''))}</VchNo>"
    xml_data += f"<STPTName>{escape_xml(purchase_type)}</STPTName>"
    xml_data += f"<MasterName1>{escape_xml(voucher_data.get('party_name', ''))}</MasterName1>"

    if voucher_data.get('narration'):
        xml_data += (
            f"<VchOtherInfoDetails>"
            f"<Narration1>{escape_xml(voucher_data.get('narration'))}</Narration1>"
            f"</VchOtherInfoDetails>"
        )

    # ── Item Entries ───────────────────────────────────────────────────────
    from database.db import get_setting
    from utils.setting_keys import SETTING_ACTIVE_DISCOUNT_STRUCT
    active_struct = get_setting(SETTING_ACTIVE_DISCOUNT_STRUCT, "Simple Discount")

    xml_data += "<ItemEntries>"
    for idx, item in enumerate(voucher_data.get('items', []), start=1):
        xml_data += "<ItemDetail>"
        xml_data += f"<SrNo>{idx}</SrNo>"
        xml_data += f"<ItemName>{escape_xml(item.get('item_name', ''))}</ItemName>"
        xml_data += f"<UnitName>{escape_xml(item.get('unit_name', ''))}</UnitName>"
        xml_data += f"<Qty>{escape_xml(item.get('qty', '0'))}</Qty>"
        xml_data += f"<ListPrice>{escape_xml(item.get('list_price', '0'))}</ListPrice>"

        # Discount
        discount_val = str(item.get('compound_discount', '')).strip()
        if "Simple" in active_struct and discount_val:
            if "+" in discount_val:
                parts = discount_val.split("+")
                if len(parts) == 2 and parts[0].strip() == "0":
                    xml_data += f"<Discount>{escape_xml(parts[1].strip())}</Discount>"
                else:
                    xml_data += "<DiscountPercent>0</DiscountPercent>"
            else:
                pct = discount_val.replace("%", "").strip()
                xml_data += f"<DiscountPercent>{escape_xml(pct)}</DiscountPercent>"
        else:
            xml_data += f"<CompoundDiscount>{escape_xml(discount_val)}</CompoundDiscount>"

        xml_data += f"<Price>{escape_xml(item.get('price', '0'))}</Price>"
        xml_data += f"<Amt>{escape_xml(item.get('amt', '0'))}</Amt>"

        if is_multirate:
            if item.get('tax_category'):
                xml_data += f"<ItemTaxCategory>{escape_xml(item.get('tax_category'))}</ItemTaxCategory>"
            if item.get('mc'):
                xml_data += f"<MC>{escape_xml(item.get('mc'))}</MC>"

        elif "exempt" in purchase_type.lower():
            if item.get('mc'):
                xml_data += f"<MC>{escape_xml(item.get('mc'))}</MC>"

        else:
            xml_data += f"<STAmount>{escape_xml(item.get('st_amount', '0'))}</STAmount>"
            if is_local_itemwise:
                try:
                    half_pct  = float(item.get('st_percent', '0')) / 2
                    half_tax  = float(item.get('tax_before_surcharge', '0')) / 2
                except (ValueError, TypeError):
                    half_pct = half_tax = 0.0
                xml_data += f"<STPercent>{half_pct}</STPercent>"
                xml_data += f"<STPercent1>{half_pct}</STPercent1>"
                xml_data += f"<TaxBeforeSurcharge>{half_tax}</TaxBeforeSurcharge>"
                xml_data += f"<TaxBeforeSurcharge1>{half_tax}</TaxBeforeSurcharge1>"
            else:
                xml_data += f"<STPercent>{escape_xml(item.get('st_percent', '0'))}</STPercent>"
                xml_data += f"<TaxBeforeSurcharge>{escape_xml(item.get('tax_before_surcharge', '0'))}</TaxBeforeSurcharge>"
            if item.get('mc'):
                xml_data += f"<MC>{escape_xml(item.get('mc'))}</MC>"

        xml_data += "</ItemDetail>"
    xml_data += "</ItemEntries>"

    # ── Bill Sundries ──────────────────────────────────────────────────────
    if voucher_data.get('bill_sundries'):
        xml_data += "<BillSundries>"
        for idx, bs in enumerate(voucher_data.get('bill_sundries', []), start=1):
            xml_data += "<BSDetail>"
            xml_data += f"<SrNo>{idx}</SrNo>"
            xml_data += f"<BSName>{escape_xml(bs.get('name', ''))}</BSName>"
            xml_data += f"<PercentVal>{escape_xml(bs.get('percent_val', '0'))}</PercentVal>"
            xml_data += f"<Amt>{escape_xml(bs.get('amount', '0'))}</Amt>"
            xml_data += "</BSDetail>"
        xml_data += "</BillSundries>"

    xml_data += "</Purchase>"

    # ── Log XML (for debugging) ────────────────────────────────────────────
    print("=== Generated Purchase Voucher XML ===")
    print(xml_data)
    print("======================================")

    # ── Upload via COM (disabled in SQL Server mode) ───────────────────────
    return (
        False,
        "BUSY COM upload is disabled in SQL Server mode.\n\n"
        "The voucher XML has been printed to the console for reference.\n"
        "To re-enable uploads, reconfigure the application for BUSY COM mode.",
        None,
    )
