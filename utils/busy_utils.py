"""
BUSY ERP Integration Utilities
Handles XML-based uploads to BUSY ERP system
"""

import requests
from xml.sax.saxutils import escape
from database.api_config import get_api_config

def escape_xml(text):
    """Escape XML special characters in text."""
    if text is None:
        return ""
    return escape(str(text))

def upload_item_to_busy(item_name, unit, hsn, tax_category):
    """
    Upload item master to BUSY ERP via XML.
    Uses only the 4 fields: Item Name, Unit, HSN, Tax Category.
    
    Args:
        item_name: Item name
        unit: Unit name
        hsn: HSN code
        tax_category: Tax category name
    
    Returns:
        Tuple: (success: bool, message: str, item_code: str or None)
    """
    BASE_URL, USERNAME, PASSWORD = get_busy_config()
    
    # Check if config is available
    if not BASE_URL or not USERNAME or not PASSWORD:
        return False, "BUSY configuration not found. Please configure API settings (URL, Username, Password).", None
    
    # Build XML with only the 4 required fields
    xml = ""
    xml += "<Item>"
    xml += f"<Name>{escape_xml(item_name)}</Name>"
    xml += f"<PrintName>{escape_xml(item_name)}</PrintName>"
    xml += f"<MainUnit>{escape_xml(unit)}</MainUnit>"
    xml += f"<TaxCategory>{escape_xml(tax_category)}</TaxCategory>"
    xml += f"<HSNCodeGST>{escape_xml(hsn)}</HSNCodeGST>"
    xml += "</Item>"
    
    # Debug: Print XML being sent
    print("=" * 50)
    print("BUSY Item XML Being Sent:")
    print("=" * 50)
    print(xml)
    print("=" * 50)
    
    # Headers for BUSY API - following the reference code pattern
    HEADERS = {
        "SC": "5",                 # Service Code: Add Master
        "MasterType": "6",         # 6 = Item
        "UserName": USERNAME,
        "Pwd": PASSWORD,
        "MasterXML": xml
    }
    
    print(f"URL: {BASE_URL}")
    print(f"Username: {USERNAME}")
    print(f"Headers: {list(HEADERS.keys())}")
    
    try:
        print("Sending item to BUSY...")
        response = requests.get(BASE_URL, headers=HEADERS, timeout=30)
        
        print(f"Response Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Text: {response.text[:500]}")
        
        if response.status_code != 200:
            error_msg = f"HTTP Error {response.status_code}: {response.text[:500]}"
            print(f"FAILED: {error_msg}")
            return False, error_msg, None
        
        result = response.headers.get("Result", "")
        print(f"Result header: '{result}'")
        
        if result == "T":
            item_code = response.text.strip()
            print(f"Success! Item Code: {item_code}")
            return True, f"Item uploaded to BUSY successfully. Code: {item_code}", item_code
        else:
            error_desc = response.headers.get("Description", response.text[:200] or "Unknown error")
            error_msg = f"BUSY upload failed.\nResult: {result}\nError: {error_desc}"
            print(f"FAILED: {error_msg}")
            return False, error_msg, None
    
    except requests.exceptions.ConnectionError as e:
        error_msg = f"Cannot connect to BUSY server.\nURL: {BASE_URL}\nError: {str(e)}\n\nPlease check:\n1. BUSY server is running\n2. URL is correct in API Config\n3. Firewall settings"
        print(f"CONNECTION ERROR: {error_msg}")
        return False, error_msg, None
    except requests.exceptions.Timeout as e:
        error_msg = f"Request to BUSY timed out.\nURL: {BASE_URL}\n\nPlease check if BUSY server is responding."
        print(f"TIMEOUT ERROR: {error_msg}")
        return False, error_msg, None
    except requests.RequestException as e:
        error_msg = f"Error during BUSY upload.\nError: {str(e)}\nType: {type(e).__name__}"
        print(f"REQUEST ERROR: {error_msg}")
        return False, error_msg, None
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}\nType: {type(e).__name__}"
        print(f"UNEXPECTED ERROR: {error_msg}")
        import traceback
        traceback.print_exc()
        return False, error_msg, None

def upload_party_to_busy(party_name):
    """
    Upload party master (Sundry Creditor) to BUSY ERP via XML.
    Uses only: Name, PrintName, Group='Sundry Creditors'.
    MasterType=2 (Party).
    """
    # Trim/validate name
    party_name = (party_name or "").strip()
    if not party_name:
        return False, "Party Name is required (cannot be blank).", None

    BASE_URL, USERNAME, PASSWORD = get_busy_config()

    if not BASE_URL or not USERNAME or not PASSWORD:
        return False, "BUSY configuration not found. Please configure API settings (URL, Username, Password).", None

    xml = ""
    xml += "<Account>"
    xml += f"<Name>{escape_xml(party_name)}</Name>"
    xml += f"<PrintName>{escape_xml(party_name)}</PrintName>"
    xml += f"<Group>Sundry Creditors</Group>"
    xml += "</Account>"

    print("=" * 50)
    print("BUSY Party XML Being Sent:")
    print("=" * 50)
    print(xml)
    print("=" * 50)

    HEADERS = {
        "SC": "5",          # Add Master
        "MasterType": "2",  # 2 = Party
        "UserName": USERNAME,
        "Pwd": PASSWORD,
        "MasterXML": xml
    }

    print(f"URL: {BASE_URL}")
    print(f"Username: {USERNAME}")
    print(f"Headers: {list(HEADERS.keys())}")

    try:
        print("Sending party to BUSY...")
        response = requests.get(BASE_URL, headers=HEADERS, timeout=30)

        print(f"Response Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Text: {response.text[:500]}")

        if response.status_code != 200:
            error_msg = f"HTTP Error {response.status_code}: {response.text[:500]}"
            print(f"FAILED: {error_msg}")
            return False, error_msg, None

        result = response.headers.get("Result", "")
        print(f"Result header: '{result}'")

        if result == "T":
            party_code = response.text.strip()
            print(f"Success! Party Code: {party_code}")
            return True, f"Party uploaded to BUSY successfully. Code: {party_code}", party_code
        else:
            error_desc = response.headers.get("Description", response.text[:200] or "Unknown error")
            error_msg = f"BUSY upload failed.\nResult: {result}\nError: {error_desc}"
            print(f"FAILED: {error_msg}")
            return False, error_msg, None

    except requests.exceptions.ConnectionError as e:
        error_msg = f"Cannot connect to BUSY server.\nURL: {BASE_URL}\nError: {str(e)}\n\nPlease check:\n1. BUSY server is running\n2. URL is correct in API Config\n3. Firewall settings"
        print(f"CONNECTION ERROR: {error_msg}")
        return False, error_msg, None
    except requests.exceptions.Timeout as e:
        error_msg = f"Request to BUSY timed out.\nURL: {BASE_URL}\n\nPlease check if BUSY server is responding."
        print(f"TIMEOUT ERROR: {error_msg}")
        return False, error_msg, None
    except requests.RequestException as e:
        error_msg = f"Error during BUSY upload.\nError: {str(e)}\nType: {type(e).__name__}"
        print(f"REQUEST ERROR: {error_msg}")
        return False, error_msg, None
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}\nType: {type(e).__name__}"
        print(f"UNEXPECTED ERROR: {error_msg}")
        import traceback
        traceback.print_exc()
        return False, error_msg, None

def get_busy_config():
    """
    Get BUSY configuration from api_config database.
    Returns: (base_url, username, password)
    """
    config = get_api_config()
    if config and config[0] and config[1] and config[2]:
        # config is (url, username, password)
        return config[0], config[1], config[2]
    else:
        # Return None if config not found - will be handled in upload function
        return None, None, None

def upload_purchase_voucher_to_busy(voucher_data):
    """
    Upload purchase voucher to BUSY ERP via XML.
    Supports both "Central-ItemWise" and "Local-ItemWise" purchase types.
    
    Args:
        voucher_data: Dictionary containing:
            - date: Voucher date (format: DD-MM-YYYY)
            - series: Voucher series name (default: "Main")
            - voucher_no: Voucher number
            - purchase_type: Purchase type (e.g., "Central-ItemWise", "Local-ItemWise")
            - party_name: Party/Account name (used as MasterName1)
            - narration: Optional narration text
            - items: List of item dictionaries with:
                - item_name, unit_name, qty, list_price, compound_discount, price, 
                  amount, st_amount, st_percent, tax_before_surcharge, mc (optional)
            - bill_sundries: List of bill sundry dictionaries with:
                - name, percent_val, amount
    
    Returns:
        Tuple: (success: bool, message: str, voucher_code: str or None)
    """
    BASE_URL, USERNAME, PASSWORD = get_busy_config()
    
    # Check if config is available
    if not BASE_URL or not USERNAME or not PASSWORD:
        return False, "BUSY configuration not found. Please configure API settings (URL, Username, Password).", None
    
    # Get purchase type from voucher data
    purchase_type = voucher_data.get('purchase_type', 'Central-ItemWise')
    
    # Determine if we need to split taxes (Local types)
    # Applies to Local-ItemWise and Local-TaxIncl.
    is_local_itemwise = 'local' in purchase_type.lower() and ('itemwise' in purchase_type.lower() or 'taxincl' in purchase_type.lower())
    
    # Build XML for Purchase Voucher
    xml_data = "<Purchase>"
    
    # Voucher Header
    xml_data += f"<VchSeriesName>{escape_xml(voucher_data.get('series', 'Main'))}</VchSeriesName>"
    xml_data += f"<Date>{escape_xml(voucher_data.get('date', ''))}</Date>"
    xml_data += "<VchType>2</VchType>"  # 2 = Purchase
    xml_data += f"<VchNo>{escape_xml(voucher_data.get('voucher_no', ''))}</VchNo>"
    xml_data += f"<STPTName>{escape_xml(purchase_type)}</STPTName>"  # Dynamic purchase type
    xml_data += f"<MasterName1>{escape_xml(voucher_data.get('party_name', ''))}</MasterName1>"
    
    # Narration (optional)
    if voucher_data.get('narration'):
        xml_data += f"<VchOtherInfoDetails><Narration1>{escape_xml(voucher_data.get('narration'))}</Narration1></VchOtherInfoDetails>"
    
    # Check if MultiRate type
    is_multirate = "multirate" in purchase_type.lower()

    # Item Entries
    xml_data += "<ItemEntries>"
    for idx, item in enumerate(voucher_data.get('items', []), start=1):
        xml_data += "<ItemDetail>"
        xml_data += f"<SrNo>{idx}</SrNo>"
        xml_data += f"<ItemName>{escape_xml(item.get('item_name', ''))}</ItemName>"
        xml_data += f"<UnitName>{escape_xml(item.get('unit_name', ''))}</UnitName>"
        xml_data += f"<Qty>{escape_xml(item.get('qty', '0'))}</Qty>"
        xml_data += f"<ListPrice>{escape_xml(item.get('list_price', '0'))}</ListPrice>"
        xml_data += f"<CompoundDiscount>{escape_xml(item.get('compound_discount', ''))}</CompoundDiscount>"
        xml_data += f"<Price>{escape_xml(item.get('price', '0'))}</Price>"
        xml_data += f"<Amt>{escape_xml(item.get('amt', '0'))}</Amt>"
        
        if is_multirate:
            # MultiRate uses ItemTaxCategory instead of tax fields
            # We need to extract tax category name from item data. 
            # purchase_voucher.py passes 'item_name', 'unit_name', 'qty', 'list_price', 'compound_discount', 'price', 
            # 'amt', 'st_amount', 'st_percent', 'tax_before_surcharge'.
            # It DOES NOT pass 'ItemTaxCategory' name directly in 'items' dict currently.
            # We need to check finding source of TaxCategory. 
            # In purchase_voucher.py, voucher_data['items'] construction logic (lines 969-981) 
            # assumes tax data is for ItemWise.
            # However, lines 944 extract tax_category string. 
            # But line 969 doesn't add it to dict.
            # I must assume I need to fix purchase_voucher.py as well to pass 'tax_category'.
            # For now, I'll assume 'tax_category' key will be available.
            
            # Use 'tax_category' if available, otherwise try to construct or ignore?
            # User example: <ItemTaxCategory>GST 12%</ItemTaxCategory>
            if item.get('tax_category'):
                 xml_data += f"<ItemTaxCategory>{escape_xml(item.get('tax_category'))}</ItemTaxCategory>"
            
            if item.get('mc'):
                xml_data += f"<MC>{escape_xml(item.get('mc'))}</MC>"
            
            # Optional description
            # xml_data += "<ItemDescInfo>sample</ItemDescInfo>"
        
        elif "exempt" in purchase_type.lower():
            # Exempt Purchase Logic
            # Standard item fields are already added.
            # No tax fields (STAmount, STPercent, TaxBeforeSurcharge) required.
            if item.get('mc'):
                xml_data += f"<MC>{escape_xml(item.get('mc'))}</MC>"
            
        else:
            # ItemWise and TaxInclusive Logic
            xml_data += f"<STAmount>{escape_xml(item.get('st_amount', '0'))}</STAmount>"
            
            if is_local_itemwise:
                # Split tax percentage and amount in half for CGST/SGST
                try:
                    st_percent_full = float(item.get('st_percent', '0'))
                    st_percent_half = st_percent_full / 2
                    xml_data += f"<STPercent>{st_percent_half}</STPercent>"
                    xml_data += f"<STPercent1>{st_percent_half}</STPercent1>"
                except (ValueError, TypeError):
                    xml_data += f"<STPercent>0</STPercent>"
                    xml_data += f"<STPercent1>0</STPercent1>"
                
                try:
                    tax_before_surcharge_full = float(item.get('tax_before_surcharge', '0'))
                    tax_before_surcharge_half = tax_before_surcharge_full / 2
                    xml_data += f"<TaxBeforeSurcharge>{tax_before_surcharge_half}</TaxBeforeSurcharge>"
                    xml_data += f"<TaxBeforeSurcharge1>{tax_before_surcharge_half}</TaxBeforeSurcharge1>"
                except (ValueError, TypeError):
                    xml_data += f"<TaxBeforeSurcharge>0</TaxBeforeSurcharge>"
                    xml_data += f"<TaxBeforeSurcharge1>0</TaxBeforeSurcharge1>"
            else:
                # Central-ItemWise: use full tax values (no split)
                xml_data += f"<STPercent>{escape_xml(item.get('st_percent', '0'))}</STPercent>"
                xml_data += f"<TaxBeforeSurcharge>{escape_xml(item.get('tax_before_surcharge', '0'))}</TaxBeforeSurcharge>"
            
            if item.get('mc'):
                xml_data += f"<MC>{escape_xml(item.get('mc'))}</MC>"
                
        xml_data += "</ItemDetail>"
    xml_data += "</ItemEntries>"
    
    # Bill Sundries
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
    
    # Debug: Print XML being sent
    print("=" * 50)
    print("BUSY Purchase XML Being Sent:")
    print("=" * 50)
    print(xml_data)
    print("=" * 50)
    
    # Headers for BUSY API
    headers = {
        "SC": "2",  # Service Code: Add Voucher
        "VchType": "2",  # 2 = Purchase
        "VchXML": xml_data,
        "UserName": USERNAME,
        "Pwd": PASSWORD,
    }
    
    print(f"URL: {BASE_URL}")
    print(f"Username: {USERNAME}")
    print(f"Headers: {list(headers.keys())}")
    
    try:
        print("Sending purchase voucher to BUSY...")
        response = requests.get(BASE_URL, headers=headers, timeout=30)
        
        print(f"Response Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Text: {response.text[:500]}")
        
        if response.status_code != 200:
            error_msg = f"HTTP Error {response.status_code}: {response.text[:500]}"
            print(f"FAILED: {error_msg}")
            return False, error_msg, None
        
        result = response.headers.get("Result", "")
        print(f"Result header: '{result}'")
        
        if result == "T":
            voucher_code = response.text.strip()
            print(f"Success! Voucher Code: {voucher_code}")
            return True, f"Purchase voucher uploaded to BUSY successfully. Code: {voucher_code}", voucher_code
        else:
            error_desc = response.headers.get("Description", response.text[:200] or "Unknown error")
            error_msg = f"BUSY upload failed.\nResult: {result}\nError: {error_desc}"
            print(f"FAILED: {error_msg}")
            return False, error_msg, None
    
    except requests.exceptions.ConnectionError as e:
        error_msg = f"Cannot connect to BUSY server.\nURL: {BASE_URL}\nError: {str(e)}\n\nPlease check:\n1. BUSY server is running\n2. URL is correct in API Config\n3. Firewall settings"
        print(f"CONNECTION ERROR: {error_msg}")
        return False, error_msg, None
    except requests.exceptions.Timeout as e:
        error_msg = f"Request to BUSY timed out.\nURL: {BASE_URL}\n\nPlease check if BUSY server is responding."
        print(f"TIMEOUT ERROR: {error_msg}")
        return False, error_msg, None
    except requests.RequestException as e:
        error_msg = f"Error during BUSY upload.\nError: {str(e)}\nType: {type(e).__name__}"
        print(f"REQUEST ERROR: {error_msg}")
        return False, error_msg, None
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}\nType: {type(e).__name__}"
        print(f"UNEXPECTED ERROR: {error_msg}")
        import traceback
        traceback.print_exc()
        return False, error_msg, None

