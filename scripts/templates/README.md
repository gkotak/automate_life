# HTML Templates

This directory contains HTML templates used by the hybrid article summarizer.

## Template Structure

### Article Template: `article_summary.html`

This is the primary template for generating individual article summary pages. It uses a simple variable substitution system with double curly braces.

### Index Template: `index.html`

This template generates the main index page that lists all article summaries with statistics and enhanced navigation features.

### Article Template Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{{TITLE}}` | Article title | "AI Evals are the Hottest New Skill" |
| `{{DOMAIN}}` | Source domain | "lennysnewsletter.com" |
| `{{URL}}` | Full article URL | "https://example.com/article" |
| `{{EXTRACTED_AT}}` | Analysis timestamp | "2025-09-29T14:30:00" |
| `{{HAS_VIDEO}}` | Video content indicator | "Yes" or "No" |
| `{{SUMMARY_CONTENT}}` | Main AI-generated summary | HTML content |
| `{{GENERATION_DATE}}` | Human-readable date | "September 29, 2025" |
| `{{VIDEO_EMBED_SECTION}}` | Video player embed | YouTube iframe HTML |

### Index Template Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{{TOTAL_ARTICLES}}` | Total number of articles | "5" |
| `{{VIDEO_ARTICLES}}` | Number of articles with video | "2" |
| `{{DOMAINS_COUNT}}` | Number of unique source domains | "3" |
| `{{ARTICLES_LIST}}` | HTML list of all articles | Generated `<li>` elements |
| `{{LAST_UPDATED}}` | Last update timestamp | "September 29, 2025 at 3:45 PM" |

### Dynamic Sections

These sections are conditionally included based on AI analysis results:

| Section | Variable | When Included |
|---------|----------|---------------|
| Key Insights | `{{INSIGHTS_SECTION}}` | When `key_insights` found in AI summary |
| Video Timestamps | `{{TIMESTAMPS_SECTION}}` | When `video_timestamps` found in AI summary |
| Recommended Sections | `{{RECOMMENDED_SECTION}}` | When `recommended_sections` found in AI summary |

## Customization

### Styling
- All CSS is embedded in the template for portability
- Modify the `<style>` section to change appearance
- Uses system fonts and responsive design

### Adding New Variables
1. Add the variable to the template: `{{NEW_VARIABLE}}`
2. Update `_generate_html_content()` in the Python script
3. Add the variable to the `template_vars` dictionary

### Creating New Templates
1. Create a new `.html` file in this directory
2. Use the same `{{VARIABLE}}` syntax
3. Call `_load_template("new_template.html")` in Python

## Benefits of Separated Templates

✅ **Easy Customization**: Modify HTML/CSS without touching Python code
✅ **Version Control**: Track template changes separately from logic
✅ **Reusability**: Same template can be used by different scripts
✅ **Maintainability**: Designers can work on templates independently
✅ **Testing**: Templates can be tested with sample data

## Template Processing Flow

```
1. Load template from file
2. Generate dynamic sections (insights, timestamps, etc.)
3. Create template_vars dictionary with all substitutions
4. Replace {{VARIABLE}} patterns with actual values
5. Return final HTML content
```

## Index Template Features

### Enhanced Statistics Dashboard
- **Article Count:** Total number of summaries
- **Video Content:** Count of articles with embedded videos
- **Domain Diversity:** Number of unique source websites
- **Update Tracking:** Last modification timestamp

### Visual Indicators
- **📹 VIDEO:** Red badge for articles with embedded videos
- **🔄 UPDATED:** Orange badge for articles that have been updated
- **Hover Effects:** Interactive feedback on article tiles

### Smart Organization
- **Reverse Chronological:** Most recent articles appear first
- **Duplicate Prevention:** Updates existing entries instead of creating duplicates
- **Responsive Design:** Works on all device sizes

## Benefits of Template Separation

✅ **Easy Customization**: Modify HTML/CSS without touching Python code
✅ **Version Control**: Track template changes separately from logic
✅ **Reusability**: Same templates can be used by different scripts
✅ **Maintainability**: Designers can work on templates independently
✅ **Testing**: Templates can be tested with sample data
✅ **Consistency**: Unified styling across article and index pages

This separation makes the hybrid approach even more maintainable and customizable!