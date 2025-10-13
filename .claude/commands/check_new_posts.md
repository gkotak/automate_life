# Check New Posts

Run the post checker to scan all configured newsletter/podcast feeds for new posts and display what was discovered.

## Instructions

1. Run the post checker script to check for new posts from all configured feeds
2. Wait for the script to complete and capture the output
3. After completion, query the processed_posts.json file to find posts that were added in the last 5 minutes (newly discovered in this run)
4. Display a summary of the newly discovered posts in a clear format showing:
   - Total number of new posts found
   - List of new posts with titles and sources
   - Post IDs for easy reference
5. If no new posts were found, clearly state that
6. Provide helpful next steps for processing the discovered posts

## Technical Details

- Post checker location: `programs/check_new_posts/processors/post_checker.py`
- Tracking file: `programs/article_summarizer/output/processed_posts.json`
- Look for posts with `found_at` timestamps from the last 5 minutes
- All newly discovered posts will have status "discovered"
