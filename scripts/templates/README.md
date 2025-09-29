# HTML Templates

This directory contains HTML templates used by the hybrid article summarizer.

## Template Structure

### Main Template: `article_summary.html`

This is the primary template for generating article summary pages. It uses a simple variable substitution system with double curly braces.

### Template Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{{TITLE}}` | Article title | "AI Evals are the Hottest New Skill" |
| `{{DOMAIN}}` | Source domain | "lennysnewsletter.com" |
| `{{URL}}` | Full article URL | "https://example.com/article" |
| `{{EXTRACTED_AT}}` | Analysis timestamp | "2025-09-29T14:30:00" |
| `{{HAS_VIDEO}}` | Video content indicator | "Yes" or "No" |
| `{{SUMMARY_CONTENT}}` | Main AI-generated summary | HTML content |
| `{{GENERATION_DATE}}` | Human-readable date | "September 29, 2025" |

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

This separation makes the hybrid approach even more maintainable and customizable!