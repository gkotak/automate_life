const { createClient } = require('@supabase/supabase-js');
require('dotenv').config({ path: '.env.local' });

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_ANON_KEY
);

async function checkArticle() {
  const { data, error } = await supabase
    .from('articles')
    .select('id, title, url, content_source, transcript_text')
    .eq('id', 75)
    .single();
  
  if (error) {
    console.error('Error:', error);
  } else {
    console.log('Article ID:', data.id);
    console.log('Title:', data.title);
    console.log('URL:', data.url.substring(0, 100) + '...');
    console.log('Content Source:', data.content_source);
    console.log('Has Transcript:', data.transcript_text ? 'YES' : 'NO');
    if (data.transcript_text) {
      console.log('Transcript length:', data.transcript_text.length, 'chars');
      console.log('Transcript preview:', data.transcript_text.substring(0, 200));
    }
  }
}

checkArticle();
