'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { ThemeWithCount } from '@/types/database';
import { Trash2, Plus, Edit2, X, Check, AlertCircle, ArrowLeft, Tag } from 'lucide-react';

type NotificationType = 'success' | 'error' | 'info';

interface Notification {
  id: string;
  type: NotificationType;
  message: string;
}

export default function ThemeManagementPage() {
  const { user, userProfile, loading: authLoading } = useAuth();
  const router = useRouter();

  const [themes, setThemes] = useState<ThemeWithCount[]>([]);
  const [loading, setLoading] = useState(true);
  const [notifications, setNotifications] = useState<Notification[]>([]);

  // Form state
  const [newThemeName, setNewThemeName] = useState('');
  const [newThemeDescription, setNewThemeDescription] = useState('');
  const [creating, setCreating] = useState(false);

  // Edit state
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingName, setEditingName] = useState('');
  const [editingDescription, setEditingDescription] = useState('');

  // Protect this page - redirect if not authenticated or not admin
  useEffect(() => {
    if (!authLoading) {
      if (!user) {
        router.push('/login');
      } else if (userProfile && userProfile.role !== 'admin') {
        router.push('/');
        addNotification('error', 'Only admins can access theme settings');
      }
    }
  }, [user, userProfile, authLoading, router]);

  // Load themes on mount
  useEffect(() => {
    if (user && userProfile?.role === 'admin') {
      loadThemes();
    }
  }, [user, userProfile]);

  const addNotification = (type: NotificationType, message: string) => {
    const id = Date.now().toString();
    const notification: Notification = { id, type, message };
    setNotifications((prev) => [...prev, notification]);

    setTimeout(() => {
      removeNotification(id);
    }, 5000);
  };

  const removeNotification = (id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  };

  const loadThemes = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/themes');
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to load themes');
      }

      setThemes(data.themes || []);
    } catch (error) {
      console.error('Error loading themes:', error);
      addNotification('error', error instanceof Error ? error.message : 'Failed to load themes');
    } finally {
      setLoading(false);
    }
  };

  const createTheme = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!newThemeName.trim()) {
      addNotification('error', 'Theme name is required');
      return;
    }

    try {
      setCreating(true);
      const response = await fetch('/api/themes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newThemeName.trim(),
          description: newThemeDescription.trim() || null,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to create theme');
      }

      setThemes((prev) => [...prev, data.theme]);
      setNewThemeName('');
      setNewThemeDescription('');
      addNotification('success', `Theme "${data.theme.name}" created`);
    } catch (error) {
      console.error('Error creating theme:', error);
      addNotification('error', error instanceof Error ? error.message : 'Failed to create theme');
    } finally {
      setCreating(false);
    }
  };

  const updateTheme = async (id: number) => {
    if (!editingName.trim()) {
      addNotification('error', 'Theme name is required');
      return;
    }

    try {
      const response = await fetch(`/api/themes/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: editingName.trim(),
          description: editingDescription.trim() || null,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to update theme');
      }

      setThemes((prev) =>
        prev.map((t) => (t.id === id ? { ...t, name: data.theme.name, description: data.theme.description } : t))
      );
      setEditingId(null);
      setEditingName('');
      setEditingDescription('');
      addNotification('success', 'Theme updated');
    } catch (error) {
      console.error('Error updating theme:', error);
      addNotification('error', error instanceof Error ? error.message : 'Failed to update theme');
    }
  };

  const deleteTheme = async (id: number, name: string) => {
    if (!confirm(`Delete theme "${name}"? This will also delete all insights associated with this theme.`)) {
      return;
    }

    try {
      const response = await fetch(`/api/themes/${id}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Failed to delete theme');
      }

      setThemes((prev) => prev.filter((t) => t.id !== id));
      addNotification('success', `Theme "${name}" deleted`);
    } catch (error) {
      console.error('Error deleting theme:', error);
      addNotification('error', error instanceof Error ? error.message : 'Failed to delete theme');
    }
  };

  const startEditing = (theme: ThemeWithCount) => {
    setEditingId(theme.id);
    setEditingName(theme.name);
    setEditingDescription(theme.description || '');
  };

  const cancelEditing = () => {
    setEditingId(null);
    setEditingName('');
    setEditingDescription('');
  };

  // Show loading while checking auth
  if (authLoading || !userProfile) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#077331]"></div>
      </div>
    );
  }

  // Don't render if not admin
  if (userProfile.role !== 'admin') {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Notifications */}
      <div className="fixed top-4 right-4 z-50 space-y-2">
        {notifications.map((notification) => (
          <div
            key={notification.id}
            className={`flex items-center gap-2 px-4 py-3 rounded-lg shadow-lg ${
              notification.type === 'success'
                ? 'bg-green-50 text-green-800 border border-green-200'
                : notification.type === 'error'
                ? 'bg-red-50 text-red-800 border border-red-200'
                : 'bg-blue-50 text-blue-800 border border-blue-200'
            }`}
          >
            {notification.type === 'success' ? (
              <Check className="h-5 w-5" />
            ) : notification.type === 'error' ? (
              <AlertCircle className="h-5 w-5" />
            ) : (
              <AlertCircle className="h-5 w-5" />
            )}
            <span className="text-sm">{notification.message}</span>
            <button
              onClick={() => removeNotification(notification.id)}
              className="ml-2 text-gray-500 hover:text-gray-700"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>

      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <Link
            href="/"
            className="inline-flex items-center text-sm text-gray-600 hover:text-[#077331] mb-4"
          >
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back to Articles
          </Link>
          <h1 className="text-2xl font-bold text-gray-900">Theme Management</h1>
          <p className="text-gray-600 mt-1">
            Configure organizational themes for strategic content analysis. Themes help categorize
            insights across articles (e.g., "Competition", "International Expansion", "AI Strategy").
          </p>
        </div>

        {/* Create Theme Form */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Create New Theme</h2>
          <form onSubmit={createTheme} className="space-y-4">
            <div className="flex gap-4">
              <input
                type="text"
                value={newThemeName}
                onChange={(e) => setNewThemeName(e.target.value)}
                placeholder="Enter theme name..."
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#077331] focus:border-[#077331] outline-none"
              />
              <button
                type="submit"
                disabled={creating || !newThemeName.trim()}
                className="px-6 py-2 bg-[#077331] text-white rounded-lg hover:bg-[#055a24] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                <Plus className="h-4 w-4" />
                {creating ? 'Creating...' : 'Create Theme'}
              </button>
            </div>
            <div>
              <textarea
                value={newThemeDescription}
                onChange={(e) => setNewThemeDescription(e.target.value)}
                placeholder="Optional: Add context for this theme (e.g., competitor names to track, specific focus areas, keywords to look for)..."
                rows={2}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#077331] focus:border-[#077331] outline-none resize-none text-sm"
              />
              <p className="text-xs text-gray-500 mt-1">
                This description helps AI generate more relevant insights for this theme.
              </p>
            </div>
          </form>
        </div>

        {/* Themes List */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">
              Themes ({themes.length})
            </h2>
          </div>

          {loading ? (
            <div className="px-6 py-12 text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#077331] mx-auto"></div>
              <p className="text-gray-500 mt-4">Loading themes...</p>
            </div>
          ) : themes.length === 0 ? (
            <div className="px-6 py-12 text-center">
              <Tag className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-500">No themes created yet.</p>
              <p className="text-gray-400 text-sm mt-1">
                Create your first theme above to start categorizing insights.
              </p>
            </div>
          ) : (
            <ul className="divide-y divide-gray-200">
              {themes.map((theme) => (
                <li key={theme.id} className="px-6 py-4">
                  {editingId === theme.id ? (
                    <div className="space-y-3">
                      <div className="flex items-center gap-4">
                        <input
                          type="text"
                          value={editingName}
                          onChange={(e) => setEditingName(e.target.value)}
                          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#077331] focus:border-[#077331] outline-none"
                          autoFocus
                          placeholder="Theme name"
                          onKeyDown={(e) => {
                            if (e.key === 'Escape') cancelEditing();
                          }}
                        />
                        <button
                          onClick={() => updateTheme(theme.id)}
                          className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                          title="Save"
                        >
                          <Check className="h-5 w-5" />
                        </button>
                        <button
                          onClick={cancelEditing}
                          className="p-2 text-gray-500 hover:bg-gray-50 rounded-lg transition-colors"
                          title="Cancel"
                        >
                          <X className="h-5 w-5" />
                        </button>
                      </div>
                      <textarea
                        value={editingDescription}
                        onChange={(e) => setEditingDescription(e.target.value)}
                        placeholder="Optional: Add context for this theme..."
                        rows={2}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#077331] focus:border-[#077331] outline-none resize-none text-sm"
                      />
                    </div>
                  ) : (
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-4">
                        <div className="h-10 w-10 bg-[#077331]/10 rounded-lg flex items-center justify-center flex-shrink-0">
                          <Tag className="h-5 w-5 text-[#077331]" />
                        </div>
                        <div className="min-w-0">
                          <Link
                            href={`/themes/${theme.id}`}
                            className="font-medium text-gray-900 hover:text-[#077331] transition-colors"
                          >
                            {theme.name}
                          </Link>
                          <p className="text-sm text-gray-500">
                            {theme.article_count} article{theme.article_count !== 1 ? 's' : ''} with insights
                          </p>
                          {theme.description && (
                            <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                              {theme.description}
                            </p>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0 ml-4">
                        <button
                          onClick={() => startEditing(theme)}
                          className="p-2 text-gray-500 hover:text-[#077331] hover:bg-gray-50 rounded-lg transition-colors"
                          title="Edit"
                        >
                          <Edit2 className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => deleteTheme(theme.id, theme.name)}
                          className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                          title="Delete"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Help Section */}
        <div className="mt-8 bg-blue-50 rounded-lg border border-blue-200 p-6">
          <h3 className="font-semibold text-blue-900 mb-2">How Themes Work</h3>
          <ul className="text-sm text-blue-800 space-y-2">
            <li>
              <strong>Creating Themes:</strong> Define strategic categories relevant to your organization (e.g., "Competition", "Market Trends", "Technology").
            </li>
            <li>
              <strong>Automatic Insights:</strong> When processing new private articles, AI will automatically generate insights relevant to each theme.
            </li>
            <li>
              <strong>Search Filtering:</strong> Filter your article library by theme to find content with relevant insights.
            </li>
            <li>
              <strong>Theme Pages:</strong> Click on a theme name to see aggregated insights across all articles for that theme.
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
