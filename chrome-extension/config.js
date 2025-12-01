/**
 * Configuration for Particles Extension
 *
 * Change ENVIRONMENT to switch between local development and production
 */

// Set this to 'local' for development or 'production' for production
const ENVIRONMENT = 'local';

const CONFIG = {
  local: {
    API_URL: 'http://localhost:8000',
    WEB_APP_URL: 'http://localhost:3000',
    SUPABASE_URL: 'https://gmwqeqlbfhxffxpsjokf.supabase.co'
  },
  production: {
    API_URL: 'https://article-summarizer-backend-production.up.railway.app',
    WEB_APP_URL: 'https://tryparticles.com',
    SUPABASE_URL: 'https://gmwqeqlbfhxffxpsjokf.supabase.co'
  }
};

// Export the active configuration
export const { API_URL, WEB_APP_URL, SUPABASE_URL } = CONFIG[ENVIRONMENT];
export { ENVIRONMENT };
