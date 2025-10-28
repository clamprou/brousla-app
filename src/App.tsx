import React, { useState, useEffect } from 'react';
import { Login } from './pages/Login';
import { SubscriptionRequired } from './pages/SubscriptionRequired';
import { Account } from './pages/Account';
import { getAuthState } from './utils/auth';
import { isEntitled, fetchEntitlements } from './utils/license';

export const App: React.FC = () => {
  const [authState, setAuthState] = useState(getAuthState());
  const [currentPage, setCurrentPage] = useState<'home' | 'account'>('home');
  const [needsSubscription, setNeedsSubscription] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkEntitlements();
  }, [authState.isAuthenticated]);

  const checkEntitlements = async () => {
    if (!authState.isAuthenticated) {
      setLoading(false);
      return;
    }

    // For local dev mode, skip entitlement check
    if (authState.mode === 'local') {
      setNeedsSubscription(false);
      setLoading(false);
      return;
    }

    try {
      // Try to fetch fresh entitlements if we have an access token
      if (authState.accessToken) {
        await fetchEntitlements(authState.accessToken);
      }

      // Check if user has basic entitlements
      const result = await isEntitled('render', 0);
      setNeedsSubscription(!result.entitled);
    } catch (error) {
      console.error('Error checking entitlements:', error);
      // If we can't check, assume subscription is needed
      setNeedsSubscription(true);
    } finally {
      setLoading(false);
    }
  };

  const handleLoginSuccess = () => {
    const newAuthState = getAuthState();
    setAuthState(newAuthState);
  };

  if (!authState.isAuthenticated) {
    return <Login onLoginSuccess={handleLoginSuccess} />;
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh' }}>
        <div>Loading...</div>
      </div>
    );
  }

  if (needsSubscription && currentPage !== 'account') {
    return <SubscriptionRequired />;
  }

  if (currentPage === 'account') {
    return (
      <div>
        <nav style={navStyle}>
          <button onClick={() => setCurrentPage('home')}>← Back to Home</button>
        </nav>
        <Account />
      </div>
    );
  }

  // Main app content
  return (
    <div>
      <nav style={navStyle}>
        <h1 style={{ margin: 0 }}>Brousla</h1>
        <div>
          <span style={{ marginRight: 20 }}>{authState.email}</span>
          <button onClick={() => setCurrentPage('account')}>Account</button>
        </div>
      </nav>

      <div style={{ padding: 40 }}>
        <h1>Welcome to Brousla! 🎨</h1>
        <p>Your AI Content Creation App is ready.</p>
        <p>You are logged in as: <strong>{authState.email}</strong></p>
        <p>Mode: <strong>{authState.mode === 'local' ? 'Local Dev' : 'Cloud'}</strong></p>

        <div style={{ marginTop: 30 }}>
          <h2>Next Steps:</h2>
          <ul>
            <li>Build your content creation features</li>
            <li>Implement render usage tracking</li>
            <li>Add entitlement checks before premium features</li>
            <li>Test subscription flow with Stripe test cards</li>
          </ul>
        </div>

        <div style={{ marginTop: 30, padding: 20, background: '#f0f0f0', borderRadius: 8 }}>
          <h3>Example: Check Entitlements</h3>
          <button
            style={buttonStyle}
            onClick={async () => {
              const result = await isEntitled('render', 5);
              alert(
                result.entitled
                  ? `✓ Entitled to render (${result.currentUsage}/${result.limit})`
                  : `✗ ${result.reason}`
              );
            }}
          >
            Check Render Entitlement
          </button>
        </div>
      </div>
    </div>
  );
};

const navStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '20px 40px',
  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  color: 'white',
};

const buttonStyle: React.CSSProperties = {
  padding: '10px 20px',
  background: '#667eea',
  color: 'white',
  border: 'none',
  borderRadius: 6,
  cursor: 'pointer',
  fontSize: 14,
};
