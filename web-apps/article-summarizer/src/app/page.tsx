import HomePageClient from '@/components/HomePageClient'

// Disable caching for this page to ensure fresh data on navigation
export const dynamic = 'force-dynamic'
export const revalidate = 0

export default function Home() {
  return <HomePageClient />
}
