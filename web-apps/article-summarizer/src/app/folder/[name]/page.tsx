import HomePageClient from '@/components/HomePageClient'

// Disable caching for this page to ensure fresh data on navigation
export const dynamic = 'force-dynamic'
export const revalidate = 0

interface FolderPageProps {
  params: Promise<{ name: string }>
}

export default async function FolderPage({ params }: FolderPageProps) {
  const { name } = await params
  const decodedName = decodeURIComponent(name)

  // Reuse HomePageClient with initial folder name
  return <HomePageClient initialFolderName={decodedName} />
}
