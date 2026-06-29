import csv
import io
from typing import List, Dict, Any, Tuple
from utilities.uuid_utils import generate_uuid7

REQUIRED_COLUMNS = {
    "client_name",
    "client_type",
    "address_line_1",
    "city",
    "poc_full_name",
    "poc_email",
    "poc_phone"
}

VALID_CLIENT_TYPES = {"Customer", "Vender"}
VALID_ADDRESS_TYPES = {"Office", "Home", "Others"}

def _normalise_header(raw_header: List[str]) -> (List[str]):
    return [h.strip().lower() for h in raw_header]

def _parse_csv(raw_bytes: bytes) -> Tuple[List[str], List[Dict[str, str]]]:
    text = raw_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    
    if reader.fieldnames is None:
        raise ValueError("CSV is empty or has no header row")
    
    normalised = _normalise_header(list(reader.fieldnames))
    missing = REQUIRED_COLUMNS - set(normalised)
    if missing:
        raise ValueError(f"CSV is missing required columns: {', '.join(sorted(missing))}")
    rows: List[Dict[str, str]] = []
    for raw_row in reader:
        row = {k.strip().lower(): (v or "").strip() for k, v in raw_row.items()}
        rows.append(row)
    if not rows:
        raise ValueError("CSV file has a header row but no data rows")
    
    return normalised, rows

def _validate_row(row: Dict[str, str], row_number: int) -> List[str]:
    
    errors: List[str] = []
    
    for col in REQUIRED_COLUMNS:
        if not row.get(col):
            errors.append(f"{col} is required and cannot be empty")
            
    name = row.get("client_name", "")
    if name and (len(name) < 2 or len(name) > 50):
        errors.append("'client_name' must be between 2 and 50 characters")
        
    ct = row.get("client_name", "").strip().title()
    if ct and ct not in VALID_CLIENT_TYPES:
        errors.append(f"'client_type' must be one of: {', '.join(VALID_CLIENT_TYPES)}. GOT '{ct}'")
    
    at = row.get("address_type", "").strip().title()
    if at and at not in VALID_ADDRESS_TYPES:
        errors.append(
            f"'address_type' must be one of: {', '.join(VALID_ADDRESS_TYPES)}. Got '{at}'"
        )
        
    fname = row.get("poc_full_name", "")
    if fname and len(fname) > 100:
            errors.append("'poc_full_name' must be at most 100 characters")
            
    email = row.get("poc_email", "")
    if email and len(email) > 100:
        errors.append("'poc_email' must be at most 100 characters")
        
    phone = row.get("poc_phone", "")
    if phone and len(phone) > 20:
        errors.append("'poc_phone' must be at most 20 characters")
        
    return errors


def _title_or_default(value: str, default: str) -> str:
    v = value.strip().title()
    return v if v else default


async def _client_name_exists(cur, name:str) -> bool:
    await cur.execute(
    """
    SELECT 1 FROM tbl_client 
    WHERE LOWER(client_name) = LOWER(%s) AND deleted_on IS NULL
    LIMIT 1
    """,(name,)
    )
    return bool(await cur.fetchone())

async def _poc_email_exists(cur, email: str) -> bool:
    await cur.execute(
    """
    SELECT 1 FROM tbl_client_poc
    WHERE email = %s AND deleted_on IS NULL
    LIMIT 1
    """,(email,)
    )
    return bool(await cur.fetchone())

async def _poc_phone_exists(cur, phone:str) -> bool:
    await cur.execute(
    """
    SELECT 1 FROM tbl_client_poc 
    WHERE phone = %s AND deleted_on IS NULL
    LIMIT 1
    """,(phone,)
    )
    
    return bool(await cur.fetchone())

async def import_csv(cur, raw_bytes: bytes, user_id: str) -> Dict[str, Any]:
    _, rows = _parse_csv(raw_bytes)
    seen_emails: set = set()
    seen_phones: set = set()
    seen_names: set = set()
    imported_count = 0
    skipped_count = 0
    results = []
    
    for idx, row in enumerate(rows, start=2):
        errors = _validate_row(row, idx)
        
        client_name  = row.get("client_name", "").strip()
        poc_email    = row.get("poc_email", "").strip()
        poc_phone    = row.get("poc_phone", "").strip()
        client_type  = _title_or_default(row.get("client_type", ""), "Customer")
        address_type = _title_or_default(row.get("address_type", ""), "Office")
        country      = row.get("country", "").strip() or "Pakistan"
        is_primary   = str(row.get("is_primary", "true")).lower() not in ("false", "0", "no")
        
        if client_name.lower() in seen_names:
            errors.append(f"Duplicate client_name within this file: '{client_name}'")
        if poc_email.lower() in seen_emails:
            errors.append(f"Duplicate poc_email within this file: '{poc_email}'")
        if poc_phone in seen_phones:
            errors.append(f"Duplicate poc_phone within this file: '{poc_phone}'")
        if not errors:
            if await _client_name_exists(cur, client_name):
                errors.append(f"Client name '{client_name}' already exists")
            if await _poc_email_exists(cur, poc_email):
                errors.append(f"POC email '{poc_email}' already exists")
            if await _poc_phone_exists(cur, poc_phone):
                errors.append(f"POC phone '{poc_phone}' already exists")
 
        if errors:
            skipped_count += 1
            results.append({
                "row_number":  idx,
                "client_name": client_name,
                "status":      "skipped",
                "client_id":   None,
                "errors":      errors,
            })
            continue
        
        #insert client information
        client_id = generate_uuid7()
        await cur.execute("""
                          INSERT INTO tbl_client
                          (client_id, client_name, client_type, status, created_by, updated_by)
                          VALUES
                          (%s, %s, %s, 1, %s, %s)
                          """, (client_id, client_name, client_type, user_id, user_id),
                          )
        #Insert client address
        address_id = generate_uuid7()
        await cur.execute(
            """
            INSERT INTO tbl_client_address
                (address_id, client_id, address_line_1, address_line_2,
                 city, state, zip_code, country, address_type, is_primary, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
            """,
            (
                address_id,
                client_id,
                row.get("address_line_1", "").strip(),
                row.get("address_line_2", "").strip() or None,
                row.get("city", "").strip(),
                row.get("state", "").strip() or None,
                row.get("zip_code", "").strip() or None,
                country,
                address_type,
                1 if is_primary else 0,
            ),
        )
        #insert poc detail
        poc_id = generate_uuid7()
        await cur.execute("""
                          INSERT INTO tbl_client_poc
                          (poc_id, client_id, address_id, full_name, email, phone, status)
                          VALUES
                          (%s, %s, %s, %s, %s, %s, 1)
                          """, (
                              poc_id,
                              client_id,
                              address_id,
                              row.get("poc_full_name", "").strip(),
                              poc_email,
                              poc_phone,
                          ),
                          )
        seen_names.add(client_name.lower())
        seen_emails.add(poc_email.lower())
        seen_phones.add(poc_phone)
        imported_count+=1
        results.append({
            "row_number": idx,
            "client_name": client_name,
            "status": "imported",
            "client_id": client_id,
            "errors": [],
        })
        
        return{
            "total_rows": len(rows),
            "imported_count": imported_count,
            "skipped_count": skipped_count,
            "results": results
        }
        
        
        
        
        
        
        