import React, { useState } from 'react';
import { loginCloud, registerCloud, loginLocal, registerDevice } from '../utils/auth';
import { fetchEntitlements } from '../utils/license';

interface LoginProps {
  onLoginSuccess: () => void;
}

export const Login: React.FC<LoginProps> = ({ onLoginSuccess }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isRegister, setIsRegister] = useState(false);
  const [isLocalMode, setIsLocalMode] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isLocalMode) {
        // Local dev mode - bypass cloud
        loginLocal(email);
        onLoginSuccess();
      } else {
        // Cloud mode
        const authResponse = isRegister
          ? await registerCloud(email, password)
          : await loginCloud(email, password);

        // Register device
        const deviceId = getDeviceId();
        const appVersion = getAppVersion();
        await registerDevice(authResponse.access_token, deviceId, appVersion);

        // Fetch entitlements and cache license
        await fetchEntitlements(authResponse.access_token);

        onLoginSuccess();
      }
    } catch (err: any) {
      setError(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  const getDeviceId = (): string => {
    let deviceId = localStorage.getItem('brousla_device_id');
    if (!deviceId) {
      deviceId = `device_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      localStorage.setItem('brousla_device_id', deviceId);
    }
    return deviceId;
  };

  const getAppVersion = (): string => {
    return '1.0.0'; // TODO: Get from package.json
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <h1>Brousla</h1>
        <h2>{isRegister ? 'Create Account' : 'Sign In'}</h2>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={loading}
              placeholder="you@example.com"
            />
          </div>

          {!isLocalMode && (
            <div className="form-group">
              <label>Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={loading}
                placeholder="••••••••"
              />
            </div>
          )}

          {error && <div className="error-message">{error}</div>}

          <button type="submit" disabled={loading} className="btn-primary">
            {loading ? 'Loading...' : isRegister ? 'Create Account' : 'Sign In'}
          </button>

          {!isLocalMode && (
            <button
              type="button"
              onClick={() => setIsRegister(!isRegister)}
              className="btn-link"
              disabled={loading}
            >
              {isRegister ? 'Already have an account? Sign in' : "Don't have an account? Sign up"}
            </button>
          )}

          <div className="divider">or</div>

          <button
            type="button"
            onClick={() => setIsLocalMode(!isLocalMode)}
            className="btn-secondary"
            disabled={loading}
          >
            {isLocalMode ? 'Use Cloud Login' : 'Use Local Dev Mode'}
          </button>
        </form>
      </div>

      <style>{`
        .login-container {
          display: flex;
          justify-content: center;
          align-items: center;
          min-height: 100vh;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          padding: 20px;
        }

        .login-card {
          background: white;
          border-radius: 12px;
          padding: 40px;
          max-width: 400px;
          width: 100%;
          box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }

        .login-card h1 {
          margin: 0 0 10px 0;
          font-size: 32px;
          color: #667eea;
          text-align: center;
        }

        .login-card h2 {
          margin: 0 0 30px 0;
          font-size: 20px;
          color: #666;
          text-align: center;
          font-weight: normal;
        }

        .form-group {
          margin-bottom: 20px;
        }

        .form-group label {
          display: block;
          margin-bottom: 8px;
          font-weight: 500;
          color: #333;
        }

        .form-group input {
          width: 100%;
          padding: 12px;
          border: 1px solid #ddd;
          border-radius: 6px;
          font-size: 14px;
          transition: border-color 0.3s;
          box-sizing: border-box;
        }

        .form-group input:focus {
          outline: none;
          border-color: #667eea;
        }

        .error-message {
          background: #fee;
          color: #c33;
          padding: 12px;
          border-radius: 6px;
          margin-bottom: 20px;
          font-size: 14px;
        }

        .btn-primary, .btn-secondary, .btn-link {
          width: 100%;
          padding: 12px;
          border: none;
          border-radius: 6px;
          font-size: 16px;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.3s;
          margin-bottom: 10px;
        }

        .btn-primary {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
        }

        .btn-primary:hover:not(:disabled) {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }

        .btn-secondary {
          background: #f5f5f5;
          color: #666;
        }

        .btn-secondary:hover:not(:disabled) {
          background: #e0e0e0;
        }

        .btn-link {
          background: transparent;
          color: #667eea;
          text-decoration: underline;
        }

        .btn-link:hover:not(:disabled) {
          color: #764ba2;
        }

        button:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .divider {
          text-align: center;
          margin: 20px 0;
          color: #999;
          position: relative;
        }

        .divider::before,
        .divider::after {
          content: '';
          position: absolute;
          top: 50%;
          width: 45%;
          height: 1px;
          background: #ddd;
        }

        .divider::before {
          left: 0;
        }

        .divider::after {
          right: 0;
        }
      `}</style>
    </div>
  );
};
