import csv
import io
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from fastapi import HTTPException

FIELDS = ['email', 'name', 'company', 'amount', 'currency', 'created_at', 'external_id']

def parse_csv(content: bytes):
    try:
        text = content.decode('utf-8-sig')
    except UnicodeDecodeError:
        raise HTTPException(422, {'code':'csv_encoding'})
    if not text.strip() or '\x00' in text:
        raise HTTPException(422, {'code':'csv_empty'})
    try:
        dialect = csv.Sniffer().sniff(text[:8192], delimiters=',;')
    except csv.Error:
        dialect = csv.excel
    try:
        reader = csv.DictReader(io.StringIO(text), dialect=dialect, strict=True)
        columns = reader.fieldnames or []
        if not columns or len(columns)>30 or any(not c.strip() for c in columns) or len(columns)!=len(set(columns)):
            raise HTTPException(422, {'code':'csv_headers'})
        rows=[]
        for row in reader:
            if None in row or None in row.values():
                raise HTTPException(422, {'code':'csv_columns'})
            rows.append(row)
            if len(rows)>10000:
                raise HTTPException(413, {'code':'csv_limit'})
        if not rows:
            raise HTTPException(422, {'code':'csv_no_rows'})
        return columns, rows
    except csv.Error:
        raise HTTPException(422, {'code':'csv_parse'})

def classify(raw_rows, mapping, existing):
    seen=set(existing)
    rows=[]
    for index, raw in enumerate(raw_rows, 2):
        data={field: raw.get(column, '').strip() for field, column in mapping.items()}
        data['email']=data.get('email','').lower()
        issues=[]
        def issue(field, code):
            issues.append(dict(field=field, code=code))
        if len(data['email']) > 320 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', data['email']):
            issue('email','invalid_email')
        if data.get('amount'):
            try:
                amount=Decimal(data['amount'])
                if not amount.is_finite() or amount<0 or amount>Decimal('999999999999.99') or amount.as_tuple().exponent < -2:
                    raise InvalidOperation
            except InvalidOperation:
                issue('amount','negative_amount')
            if not data.get('currency'):
                issue('currency','required_field')
        if data.get('currency'):
            data['currency']=data['currency'].upper()
            if data['currency'] not in {'USD','EUR','GBP','UAH','CAD','AUD'}:
                issue('currency','invalid_currency')
        if data.get('created_at'):
            try:
                parsed = datetime.fromisoformat(data['created_at'].replace('Z','+00:00'))
                data['created_at'] = (parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)).isoformat()
            except (ValueError, OverflowError):
                issue('created_at','invalid_date')
        kind='invalid' if issues else 'duplicate' if data['email'] in seen else 'valid'
        if kind=='duplicate':
            issue('email','duplicate_record')
        if kind=='valid':
            seen.add(data['email'])
        rows.append(dict(row_number=index, data=data, classification=kind, issues=issues))
    return rows

def safe_csv(values):
    stream=io.StringIO()
    writer=csv.writer(stream)
    for row in values:
        writer.writerow(["'"+str(value) if str(value).lstrip().startswith(('=','+','-','@')) else str(value) for value in row])
    return stream.getvalue()
