---
name: gslides
description: "Google Slides creation and upload. When Claude needs to create presentations for Google Slides format and upload to Google Drive for: (1) Creating new Google Slides presentations, (2) Uploading presentations to Google Drive, (3) Sharing presentations with collaborators, or any other Google Slides tasks"
license: Proprietary. LICENSE.txt has complete terms
---

# Google Slides Creation and Upload

## Overview

This guide covers creating presentations in Google Slides format and uploading them to Google Drive. Google Slides is Google's cloud-based presentation software that allows real-time collaboration and access from any device.

### Brand Guidelines Integration

**IMPORTANT**: Before creating any presentation, check for brand guidelines:
1. **Check for brand guidelines**: If `.claude/skills/brand-guidelines/SKILL.md` exists, read it FIRST
2. **Apply brand colors**: Use official brand colors for all styling, headers, and accents
3. **Apply typography**: Use the brand's recommended fonts
4. **Reference guidelines**: Always refer to brand guidelines rather than hardcoding colors or fonts

## Workflow Options

### Option 1: Create PowerPoint then Convert (Recommended)

The most reliable approach is to create a PowerPoint (.pptx) file first, then convert and upload to Google Drive.

#### Step 1: Create PowerPoint Presentation

Follow the standard pptx skill workflow to create a presentation using html2pptx or templates.

#### Step 2: Upload to Google Drive (Root Directory)

**Using rclone (Recommended):**

```bash
# Install rclone (if not installed)
brew install rclone  # macOS
# Or: curl https://rclone.org/install.sh | sudo bash  # Linux

# Configure Google Drive (first time only)
rclone config create gdrive drive
# This will open a browser for authentication

# Upload to root directory of Google Drive
rclone copy presentation.pptx gdrive: -P
```

The `-P` flag shows upload progress. The file will be uploaded to the **root directory** of your Google Drive. You can manually move it to a specific folder later using the Google Drive web interface.

**Verify upload:**
```bash
# List files in root directory
rclone ls gdrive: | grep presentation.pptx
```

**Google will automatically convert .pptx to Google Slides format** when you open it in Google Drive.

#### Step 3: Access Your Presentation

After uploading:
1. Go to https://drive.google.com
2. Find your `.pptx` file in the root directory
3. Right-click → "Open with" → "Google Slides"
4. Google will convert it to Google Slides format
5. Move the file to your desired folder manually if needed

### Option 2: Google Slides API (Advanced)

For direct Google Slides creation using the API:

**Prerequisites:**
1. Enable Google Slides API in Google Cloud Console
2. Create OAuth 2.0 credentials
3. Install Google Client Library: `pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib`

**Authentication Setup:**
```python
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os.path
import pickle

SCOPES = [
    'https://www.googleapis.com/auth/presentations',
    'https://www.googleapis.com/auth/drive.file'
]

def authenticate():
    """Authenticate and return credentials."""
    creds = None

    # Token file stores user's access and refresh tokens
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # If no valid credentials, let user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        # Save credentials for next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return creds
```

**Creating a Presentation:**
```python
def create_presentation(title, creds):
    """Create a new Google Slides presentation."""
    slides_service = build('slides', 'v1', credentials=creds)

    presentation = {
        'title': title
    }

    presentation = slides_service.presentations().create(
        body=presentation
    ).execute()

    print(f'Created presentation: {presentation.get("presentationId")}')
    return presentation.get('presentationId')
```

**Adding Slides:**
```python
def add_slide(presentation_id, creds, layout='TITLE_AND_BODY'):
    """Add a slide to the presentation."""
    slides_service = build('slides', 'v1', credentials=creds)

    requests = [
        {
            'createSlide': {
                'slideLayoutReference': {
                    'predefinedLayout': layout
                }
            }
        }
    ]

    body = {'requests': requests}
    response = slides_service.presentations().batchUpdate(
        presentationId=presentation_id, body=body
    ).execute()

    return response
```

**Adding Text:**
```python
def add_text_to_slide(presentation_id, page_id, text, creds):
    """Add text to a specific slide."""
    slides_service = build('slides', 'v1', credentials=creds)

    # Create a text box
    requests = [
        {
            'createShape': {
                'objectId': f'text_box_{page_id}',
                'shapeType': 'TEXT_BOX',
                'elementProperties': {
                    'pageObjectId': page_id,
                    'size': {
                        'height': {'magnitude': 100, 'unit': 'PT'},
                        'width': {'magnitude': 500, 'unit': 'PT'}
                    },
                    'transform': {
                        'scaleX': 1,
                        'scaleY': 1,
                        'translateX': 50,
                        'translateY': 50,
                        'unit': 'PT'
                    }
                }
            }
        },
        {
            'insertText': {
                'objectId': f'text_box_{page_id}',
                'text': text
            }
        }
    ]

    body = {'requests': requests}
    response = slides_service.presentations().batchUpdate(
        presentationId=presentation_id, body=body
    ).execute()

    return response
```

**Apply Brand Colors:**
```python
def apply_brand_colors(presentation_id, page_id, element_id, color_hex, creds):
    """Apply brand colors to elements."""
    slides_service = build('slides', 'v1', credentials=creds)

    # Convert hex to RGB (0-1 scale)
    color_hex = color_hex.lstrip('#')
    r = int(color_hex[0:2], 16) / 255
    g = int(color_hex[2:4], 16) / 255
    b = int(color_hex[4:6], 16) / 255

    requests = [
        {
            'updateShapeProperties': {
                'objectId': element_id,
                'shapeProperties': {
                    'shapeBackgroundFill': {
                        'solidFill': {
                            'color': {
                                'rgbColor': {
                                    'red': r,
                                    'green': g,
                                    'blue': b
                                }
                            }
                        }
                    }
                },
                'fields': 'shapeBackgroundFill.solidFill.color'
            }
        }
    ]

    body = {'requests': requests}
    response = slides_service.presentations().batchUpdate(
        presentationId=presentation_id, body=body
    ).execute()

    return response
```

**Complete Example:**
```python
from google_slides_helpers import authenticate, create_presentation, add_slide, add_text_to_slide, apply_brand_colors

# Read brand guidelines
BRAND_PRIMARY = '#077331'  # From brand-guidelines/SKILL.md
BRAND_DARK = '#030712'

# Authenticate
creds = authenticate()

# Create presentation
presentation_id = create_presentation('Automate Life Presentation', creds)

# Add title slide
response = add_slide(presentation_id, creds, layout='TITLE')
slide_id = response['replies'][0]['createSlide']['objectId']

# Add title text
add_text_to_slide(presentation_id, slide_id, 'Automate Life', creds)

# Apply brand colors
apply_brand_colors(presentation_id, slide_id, 'text_box_' + slide_id, BRAND_PRIMARY, creds)

print(f'Presentation created: https://docs.google.com/presentation/d/{presentation_id}')
```

### Option 3: Convert PowerPoint to Google Slides Format

**Using clasp (Google Apps Script CLI):**
```bash
# Install clasp
npm install -g @google/clasp

# Login to Google
clasp login

# Create a new Apps Script project
clasp create --type standalone --title "PPT Converter"

# Create a script to upload and convert
cat > Code.gs << 'EOF'
function uploadAndConvert() {
  var file = DriveApp.createFile(blob);
  var pptxFile = DriveApp.getFileById(file.getId());

  // Convert to Google Slides
  var resource = {
    title: pptxFile.getName(),
    mimeType: MimeType.GOOGLE_SLIDES
  };

  var slide = Drive.Files.copy(resource, pptxFile.getId());
  Logger.log('Slides URL: https://docs.google.com/presentation/d/' + slide.id);
}
EOF

clasp push
```

## Google Drive Upload Options

### Using rclone (Recommended for automation)

```bash
# Install rclone
# macOS: brew install rclone
# Linux: curl https://rclone.org/install.sh | sudo bash

# Configure Google Drive
rclone config
# Follow prompts to add Google Drive remote (name it 'gdrive')

# Upload file
rclone copy presentation.pptx gdrive:

# Upload to specific folder
rclone copy presentation.pptx gdrive:Presentations/

# Get shareable link (requires gdrive CLI)
# After upload, use gdrive to share
```

### Using Google Drive API (Python)

```python
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def upload_to_drive(file_path, file_name, creds):
    """Upload file to Google Drive."""
    drive_service = build('drive', 'v3', credentials=creds)

    file_metadata = {
        'name': file_name,
        'mimeType': 'application/vnd.google-apps.presentation'
    }

    media = MediaFileUpload(
        file_path,
        mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation',
        resumable=True
    )

    file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webViewLink'
    ).execute()

    print(f'File uploaded: {file.get("webViewLink")}')
    return file.get('id')

def share_file(file_id, email, role, creds):
    """Share file with specific user."""
    drive_service = build('drive', 'v3', credentials=creds)

    permission = {
        'type': 'user',
        'role': role,  # 'reader', 'writer', 'commenter'
        'emailAddress': email
    }

    drive_service.permissions().create(
        fileId=file_id,
        body=permission,
        sendNotificationEmail=True
    ).execute()

    print(f'Shared with {email}')

def make_public(file_id, creds):
    """Make file accessible to anyone with link."""
    drive_service = build('drive', 'v3', credentials=creds)

    permission = {
        'type': 'anyone',
        'role': 'reader'
    }

    drive_service.permissions().create(
        fileId=file_id,
        body=permission
    ).execute()

    # Get shareable link
    file = drive_service.files().get(
        fileId=file_id,
        fields='webViewLink'
    ).execute()

    print(f'Public link: {file.get("webViewLink")}')
    return file.get('webViewLink')
```

## Recommended Workflow

**For most users:**
1. Create presentation using pptx skill (html2pptx workflow)
2. Apply brand guidelines (colors, fonts, spacing)
3. Upload .pptx to Google Drive using `gdrive` CLI or `rclone`
4. Google Drive automatically converts to Google Slides format
5. Share using gdrive CLI or Drive API

**For developers with API access:**
1. Check brand guidelines
2. Use Google Slides API to create presentation programmatically
3. Apply brand colors using hex values from guidelines
4. Share directly via API

## Authentication & Setup

### First-Time Setup for gdrive CLI

```bash
# Install gdrive
brew install gdrive  # macOS
# or download from https://github.com/prasmussen/gdrive

# Authenticate (opens browser)
gdrive about

# This creates ~/.gdrive/token_v2.json with your credentials
```

### First-Time Setup for Google API

1. Go to https://console.cloud.google.com
2. Create a new project or select existing
3. Enable APIs:
   - Google Slides API
   - Google Drive API
4. Create OAuth 2.0 credentials:
   - Application type: Desktop app
   - Download credentials.json
5. Place credentials.json in your working directory
6. First run will open browser for authentication
7. Token saved to token.pickle for future use

## Common Operations

### Upload and Share Workflow

```bash
# 1. Create presentation (using pptx skill)
node create-presentation.js

# 2. Upload to Google Drive
gdrive upload Automate_Life_Presentation.pptx

# Output: Uploaded <file_id> at <timestamp>

# 3. Share with specific user
gdrive share --type user --role writer --email colleague@example.com <file_id>

# 4. Or make public with link
gdrive share --type anyone --role reader <file_id>

# 5. Get link
gdrive info <file_id> | grep ViewUrl
```

### Complete Python Workflow

```python
#!/usr/bin/env python3
"""Upload PowerPoint to Google Drive and convert to Google Slides."""

from google_drive_helpers import authenticate, upload_to_drive, make_public

# Authenticate
creds = authenticate()

# Upload presentation (automatically converts to Google Slides)
file_id = upload_to_drive(
    'Automate_Life_Presentation.pptx',
    'Automate Life Presentation',
    creds
)

# Make publicly shareable
link = make_public(file_id, creds)

print(f'Presentation available at: {link}')
```

## Brand Guidelines Integration

When creating Google Slides presentations, always:
1. Read `.claude/skills/brand-guidelines/SKILL.md` if it exists
2. Extract brand colors (Primary Green #077331, Dark Green #055a24, etc.)
3. Apply colors using hex-to-RGB conversion for Google Slides API
4. Use brand fonts (Arial, Helvetica) in text elements
5. Apply design system values (spacing, border radius) where applicable

## Dependencies

**For gdrive CLI:**
```bash
brew install gdrive  # macOS
# Or download from https://github.com/prasmussen/gdrive
```

**For Python API:**
```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

**For rclone:**
```bash
brew install rclone  # macOS
curl https://rclone.org/install.sh | sudo bash  # Linux
```

## Troubleshooting

**Authentication Issues:**
- Delete token.pickle and re-authenticate
- Check credentials.json is valid
- Ensure APIs are enabled in Google Cloud Console

**Upload Failures:**
- Check file size (Google Drive has 100MB limit for automatic conversion)
- Verify file is valid .pptx format
- Check internet connection

**Sharing Issues:**
- Verify email address is correct
- Check if organizational policies restrict sharing
- Ensure you have permission to share files

## Security Notes

- Never commit credentials.json or token files to git
- Add to .gitignore: `credentials.json`, `token.pickle`, `*.json` (for Google credentials)
- Use environment variables for sensitive data in production
- Regularly review and revoke unused OAuth tokens
