from fastapi import FastAPI, HTTPException
from gspread.utils import ValueInputOption
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# --- Google Sheets Setup ---
try:
    scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
             "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
    creds_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_PATH")
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
    client = gspread.authorize(creds)
    sheet_name = os.getenv("GOOGLE_SHEET_NAME")
    user_email = os.getenv("GOOGLE_USER_EMAIL")
    price_multiplier = float(os.getenv("PRICE_MULTIPLIER", 1.4))
    image_layout = os.getenv("IMAGE_LAYOUT", "VERTICAL").upper()

    try:
        spreadsheet = client.open(sheet_name)
        sheet = spreadsheet.sheet1
    except gspread.exceptions.SpreadsheetNotFound:
        print(f"Spreadsheet ''{sheet_name}'' not found. Creating a new one.")
        spreadsheet = client.create(sheet_name)
        spreadsheet.share(user_email, perm_type='user', role='writer')
        sheet = spreadsheet.sheet1
        header_row = ["id", "link", "name", "photo", "size", "price", "price.commission", "item", "composition", "comment", "SKU", "color"]
        sheet.append_row(header_row)
        with open("google_sheet.txt", "w") as f:
            f.write(spreadsheet.url)
    # Set word wrap for all columns
    sheet.format("A:Z", {'wrapStrategy': 'WRAP'})
    print(f"Sheet URL: {spreadsheet.url}")

except Exception as e:
    print(f"Error connecting to Google Sheets: {e}")
    sheet = None

class ProductData(BaseModel):
    product_url: HttpUrl
    name: Optional[str] = None
    sku: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    availability: Optional[str] = None
    main_image_url: Optional[HttpUrl] = None
    all_image_urls: Optional[List[HttpUrl]] = None
    color: Optional[str] = None
    available_sizes: Optional[List[str]] = None
    composition: Optional[str] = None
    item: Optional[str] = None
    comment: Optional[str] = None

@app.post("/api/v1/scrape")
async def scrape_product(data: ProductData):
    print("Received data:", data.model_dump_json(indent=4))

    if not sheet:
        raise HTTPException(status_code=500, detail="Google Sheets not configured correctly.")

    try:
        # Get the next ID
        last_row = len(sheet.get_all_values()) 
        next_id = last_row + 1

        # Prepare row data in the correct order
        if data.all_image_urls:
            images_part = ';'.join([f'IMAGE("{url}")' for url in data.all_image_urls])
            photo_formula = f"={{{images_part}}}"
        else:
            photo_formula = ''
        price_commission = data.price * price_multiplier if data.price else 0

        row = [
            next_id,
            str(data.product_url),
            data.name,
            photo_formula,
            ', '.join(data.available_sizes) if data.available_sizes else '',
            data.price,
            price_commission,
            data.item,
            data.composition,
            data.comment,
            data.sku,
            data.color,
        ]
        sheet.append_row(row, value_input_option=ValueInputOption('USER_ENTERED'))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error writing to Google Sheet: {e}")

    # Placeholder for Telegram logic
    return {"status": "success", "data": data}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
