'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import {
  getContentSources,
  createContentSource,
  updateContentSource,
  deleteContentSource,
  ContentSource,
  ContentSourceCreate,
  ContentSourceUpdate,
} from '@/lib/api-client';
import { Plus, Edit2, Trash2, X, Check, AlertCircle } from 'lucide-react';

type NotificationType = 'success' | 'error' | 'info';

interface Notification {
  id: string;
  type: NotificationType;
  message: string;
}

export default function ContentSourcesPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();

  const [sources, setSources] = useState<ContentSource[]>([]);
  const [loading, setLoading] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingSource, setEditingSource] = useState<ContentSource | null>(null);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [includeInactive, setIncludeInactive] = useState(false);

  // Form state
  const [formData, setFormData] = useState<ContentSourceCreate>({
    name: '',
    url: '',
    description: '',
    is_active: true,
  });

  // Protect this page - redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login');
    }
  }, [user, authLoading, router]);

  // Load sources on mount
  useEffect(() => {
    if (user) {
      loadSources();
    }
  }, [user, includeInactive]);

  const addNotification = (type: NotificationType, message: string) => {
    const id = Date.now().toString();
    const notification: Notification = { id, type, message };
    setNotifications((prev) => [...prev, notification]);

    // Auto-remove after 5 seconds
    setTimeout(() => {
      removeNotification(id);
    }, 5000);
  };

  const removeNotification = (id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  };

  const loadSources = async () => {
    try {
      setLoading(true);
      const data = await getContentSources(includeInactive);
      setSources(data.sources);
    } catch (error) {
      console.error('Error loading sources:', error);
      addNotification('error', error instanceof Error ? error.message : 'Failed to load sources');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      if (editingSource) {
        // Update existing source
        const updates: ContentSourceUpdate = {
          name: formData.name !== editingSource.name ? formData.name : undefined,
          url: formData.url !== editingSource.url ? formData.url : undefined,
          description: formData.description !== editingSource.description ? formData.description : undefined,
          is_active: formData.is_active !== editingSource.is_active ? formData.is_active : undefined,
        };

        await updateContentSource(editingSource.id, updates);
        addNotification('success', 'Source updated successfully!');
      } else {
        // Create new source
        await createContentSource(formData);
        addNotification('success', 'Source created successfully!');
      }

      // Reset form and reload
      resetForm();
      loadSources();
    } catch (error) {
      console.error('Error saving source:', error);
      addNotification('error', error instanceof Error ? error.message : 'Failed to save source');
    }
  };

  const handleEdit = (source: ContentSource) => {
    setEditingSource(source);
    setFormData({
      name: source.name,
      url: source.url,
      description: source.description || '',
      is_active: source.is_active,
    });
    setShowAddForm(true);
  };

  const handleDelete = async (source: ContentSource) => {
    if (!confirm(`Are you sure you want to delete "${source.name}"?`)) {
      return;
    }

    try {
      await deleteContentSource(source.id);
      addNotification('success', 'Source deleted successfully!');
      loadSources();
    } catch (error) {
      console.error('Error deleting source:', error);
      addNotification('error', error instanceof Error ? error.message : 'Failed to delete source');
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      url: '',
      description: '',
      is_active: true,
    });
    setEditingSource(null);
    setShowAddForm(false);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // Show loading while checking auth
  if (authLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-600">Loading...</div>
      </div>
    );
  }

  // Don't render if not authenticated (will redirect)
  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-6xl mx-auto">
        {/* Notifications */}
        {notifications.length > 0 && (
          <div className="fixed top-4 right-4 z-50 space-y-2">
            {notifications.map((notification) => (
              <div
                key={notification.id}
                className={`flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg max-w-md transition-all duration-300 ${
                  notification.type === 'success'
                    ? 'bg-green-50 border border-[#077331] text-[#077331]'
                    : notification.type === 'error'
                    ? 'bg-red-50 border border-red-200 text-red-800'
                    : 'bg-blue-50 border border-blue-200 text-blue-800'
                }`}
              >
                {notification.type === 'success' && <Check className="h-5 w-5 flex-shrink-0" />}
                {notification.type === 'error' && <AlertCircle className="h-5 w-5 flex-shrink-0" />}
                {notification.type === 'info' && <AlertCircle className="h-5 w-5 flex-shrink-0" />}
                <span className="flex-1 text-sm font-medium">{notification.message}</span>
                <button
                  onClick={() => removeNotification(notification.id)}
                  className="text-gray-400 hover:text-gray-600 transition-colors"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="bg-white rounded-lg shadow-md p-8">
          {/* Header */}
          <div className="mb-8 flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">Content Sources</h1>
              <p className="text-gray-600">Manage your RSS feeds and newsletter subscriptions</p>
            </div>
            <button
              onClick={() => setShowAddForm(true)}
              className="inline-flex items-center px-4 py-2 bg-[#077331] text-white rounded-lg hover:bg-[#055a24] transition-colors"
            >
              <Plus className="h-5 w-5 mr-2" />
              Add Source
            </button>
          </div>

          {/* Add/Edit Form */}
          {showAddForm && (
            <div className="mb-8 p-6 border-2 border-[#077331] rounded-lg bg-green-50">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                {editingSource ? 'Edit Source' : 'Add New Source'}
              </h2>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g., My Tech Blog"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-[#077331] focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    RSS Feed URL <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="url"
                    required
                    value={formData.url}
                    onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                    placeholder="https://example.com/feed.xml"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-[#077331] focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    placeholder="Optional description..."
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-[#077331] focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData.is_active}
                      onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                      className="rounded border-gray-300 text-[#077331] focus:ring-[#077331] mr-2"
                    />
                    <span className="text-sm font-medium text-gray-700">Active</span>
                  </label>
                </div>

                <div className="flex gap-3 pt-4">
                  <button
                    type="submit"
                    className="px-4 py-2 bg-[#077331] text-white rounded-lg hover:bg-[#055a24] transition-colors"
                  >
                    {editingSource ? 'Update Source' : 'Add Source'}
                  </button>
                  <button
                    type="button"
                    onClick={resetForm}
                    className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* Filter Toggle */}
          <div className="mb-6">
            <label className="flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={includeInactive}
                onChange={(e) => setIncludeInactive(e.target.checked)}
                className="rounded border-gray-300 text-[#077331] focus:ring-[#077331] mr-2"
              />
              <span className="text-sm font-medium text-gray-700">Show inactive sources</span>
            </label>
          </div>

          {/* Sources List */}
          {loading ? (
            <div className="text-center py-12">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-[#077331]"></div>
              <p className="mt-4 text-gray-600">Loading sources...</p>
            </div>
          ) : sources.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-600">No content sources found</p>
              <button
                onClick={() => setShowAddForm(true)}
                className="mt-4 px-4 py-2 bg-[#077331] text-white rounded-lg hover:bg-[#055a24] transition-colors"
              >
                Add Your First Source
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {sources.map((source) => (
                <div
                  key={source.id}
                  className={`p-6 border rounded-lg transition-colors ${
                    source.is_active
                      ? 'border-gray-200 hover:border-[#077331]'
                      : 'border-gray-200 bg-gray-50 opacity-60'
                  }`}
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-lg font-semibold text-gray-900">{source.name}</h3>
                        <span
                          className={`px-2 py-1 rounded text-xs font-medium ${
                            source.is_active
                              ? 'bg-green-100 text-green-800'
                              : 'bg-gray-200 text-gray-600'
                          }`}
                        >
                          {source.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </div>

                      {source.description && (
                        <p className="text-sm text-gray-600 mb-2">{source.description}</p>
                      )}

                      <a
                        href={source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-[#077331] hover:underline break-all"
                      >
                        {source.url}
                      </a>

                      <div className="mt-3 text-xs text-gray-500 space-y-1">
                        <div>Created: {formatDate(source.created_at)}</div>
                        {source.last_checked_at && (
                          <div>Last checked: {formatDate(source.last_checked_at)}</div>
                        )}
                      </div>
                    </div>

                    <div className="flex gap-2 ml-4">
                      <button
                        onClick={() => handleEdit(source)}
                        className="p-2 text-gray-500 hover:text-[#077331] transition-colors"
                        title="Edit source"
                      >
                        <Edit2 className="h-5 w-5" />
                      </button>
                      <button
                        onClick={() => handleDelete(source)}
                        className="p-2 text-gray-500 hover:text-red-600 transition-colors"
                        title="Delete source"
                      >
                        <Trash2 className="h-5 w-5" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Footer */}
          <div className="mt-8 pt-6 border-t border-gray-200 flex justify-between items-center">
            <a
              href="/new/posts"
              className="text-sm text-gray-600 hover:text-[#077331] transition-colors"
            >
              ← Check for New Posts
            </a>
            <a
              href="/"
              className="text-sm text-gray-600 hover:text-[#077331] transition-colors"
            >
              Home
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
