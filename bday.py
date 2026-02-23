from __future__ import print_function
import datetime
import os.path
from dateutil.relativedelta import relativedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from PIL import Image, ImageDraw, ImageFont
from waveshare_epd import epd7in5_V2
import time

WIDTH = 800
HEIGHT = 480
FONT_PATH = "/usr/share/fonts/truetype/freefont/FreeSerifItalic.ttf"
FONT_SIZE = 36
BASE_CREDS_PATH = '/home/pi/Desktop/bday/'
TOKEN_PATH = os.path.join(BASE_CREDS_PATH, 'token.json')
CREDENTIALS_PATH = os.path.join(BASE_CREDS_PATH, 'credentials.json')

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def format_date(date: str) -> str:
    format_string = '%Y-%m-%d'
    datetime_object = datetime.datetime.strptime(date, format_string)
    return datetime_object.strftime("%m/%d")

def format_name(event_title: str) -> str:
    name = event_title.replace('birthday', '').replace('Birthday', '')
    name = name.replace('Father\'s Day', 'Dad*').replace('Mother\'s Day', 'Mom*')
    name = name.replace('Christmas Day', 'Christmas')
    return name.replace('’s', '').strip()

def fetch_bdays(num_bdays: int) -> list[str]:
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    # If no valid credentials available, request login.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_PATH, SCOPES)
            creds = flow.run_console()
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())

    service = build('calendar', 'v3', credentials=creds)

    now = datetime.datetime.utcnow().isoformat() + 'Z'
    month_range = (datetime.datetime.utcnow() + relativedelta(months=8)).isoformat() + 'Z'

    events_result = service.events().list(
        calendarId='primary',
        timeMin=now,
        timeMax=month_range,
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    events = events_result.get('items', [])

    # Filter for events with "birthday" in the summary/title, or Father's/Mother's Day, or Christmas.
    birthday_events = [e for e in events if ('birthday' in (e.get('summary') or '').lower())
                        or ('father\'s day' in (e.get('summary') or '').lower())
                        or ('mother\'s day' in (e.get('summary') or '').lower())
                        or ('christmas day' in (e.get('summary') or '').lower())
                    ]

    if not birthday_events:
        print("Error - No upcoming birthdays found.")
        return

    formatted_bdays = []
    today = datetime.datetime.today()
    for event in birthday_events:
        date_string = event['start'].get('date') or event['start'].get('dateTime')
        title = event['summary']
        name = format_name(title)
        formatted_date = format_date(date_string)
        is_bday_today = ((int(formatted_date.split('/')[0]), int(formatted_date.split('/')[1])) == (today.month, today.day))
        bday_string = "! {} ~~ {} !".format(formatted_date, name) if is_bday_today else "{} ~ {}".format(formatted_date, name)
        formatted_bdays.append(bday_string)

    return formatted_bdays[:num_bdays]

def render_birthday_image(birthdays):
    base_image = Image.new('1', (WIDTH, HEIGHT), 255)  # 1-bit (B&W), white background

    top_border = 92
    side_border = 32
    frame = Image.open(os.path.join(BASE_CREDS_PATH, "frame_pic.jpeg")).convert("1")
    frame_resized = frame.resize((WIDTH - top_border, HEIGHT - side_border))
    base_image.paste(frame_resized, (top_border // 2, (side_border // 2) - 4))

    base_image = base_image.rotate(90, expand=True)
    draw = ImageDraw.Draw(base_image)
    title_font = ImageFont.truetype(FONT_PATH, 48)
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)

    bbox = font.getbbox("Test")
    line_height = bbox[3] - bbox[1]
    y = 158  # Top padding

    text_left_padding = 98
    
    title_x = 150
    draw.text((title_x, y), "Birthdays", font=title_font, fill=0)
    underline_y = y + 50
    draw.line((title_x, underline_y, 323, underline_y), fill='black', width=3)
    
    y += (3 * line_height) + 14
    for line in birthdays:
        if y + line_height > WIDTH:
            break  # Stop if no more room
        draw.text((text_left_padding, y), line, font=font, fill=0)
        y += (line_height * 3)

    return base_image

def display_image_on_epd(image):
    epd = epd7in5_V2.EPD()
    epd.init()
    epd.Clear()
    epd.display(epd.getbuffer(image))
    time.sleep(2)
    epd.sleep()

def print_birthdays(bdays: list[str]):
    print("{} Upcoming Birthdays".format(len(bdays)))
    for bday in bdays:
        print(bday)

if __name__ == '__main__':
    bdays = fetch_bdays(num_bdays=5)
    
    image = render_birthday_image(bdays)
    
    display_image_on_epd(image)
