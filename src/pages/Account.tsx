import React, { useEffect, useState } from 'react';
import { getCurrentPlan, LicenseClaims } from '../utils/license';
import { getAuthState, logout } from '../utils/auth';

const CLOUD_API_URL = process.env.BROUSLA_CLOUD_URL || 'http://localhost:8000';

export const Account: React.FC = () => {
  const [plan, setPlan] = useState<LicenseClaims | null>(null);
  const [loading, setLoading] = useState(true);
  const authState = getAuthState();

  useEffect(() => {
    loadPlan();
  }, []);

  const loadPlan = async () => {
    try {
      const currentPlan = await getCurrentPlan();
      setPlan(currentPlan);
    } catch (error) {
      console.error('Error loading plan:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleManageBilling = async () => {
    try {
      const response = await fetch(`${CLOUD_API_URL}/billing/create-portal-session`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authState.accessToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        window.open(data.url, '_blank');
      } else {
        alert('Failed to open billing portal');
      }
    } catch (error) {
      console.error('Error opening billing portal:', error);
    }
  };

  const handleLogout = () => {
    logout();
    window.location.reload();
  };

  if (loading) {
    return (
      <div className="account-page">
        <div className="loading">Loading...</div>
      </div>
    );
  }

  const expiryDate = plan?.exp ? new Date(plan.exp * 1000) : null;
  const daysUntilExpiry = expiryDate
    ? Math.ceil((expiryDate.getTime() - Date.now()) / (1000 * 60 * 60 * 24))
    : 0;

  return (
    <div className="account-page">
      <div className="container">
        <h1>Account Settings</h1>

        <div className="section">
          <h2>Profile</h2>
          <div className="info-row">
            <span className="label">Email:</span>
            <span className="value">{authState.email}</span>
          </div>
          <div className="info-row">
            <span className="label">Auth Mode:</span>
            <span className="value">{authState.mode === 'local' ? 'Local Dev' : 'Cloud'}</span>
          </div>
        </div>

        {plan && (
          <div className="section">
            <h2>Subscription</h2>
            <div className="plan-card">
              <div className="plan-header">
                <h3>{plan.plan} Plan</h3>
                {plan.plan !== 'FREE' && (
                  <span className="badge-active">Active</span>
                )}
              </div>

              <div className="limits">
                <div className="limit-item">
                  <span className="limit-label">Renders per day:</span>
                  <span className="limit-value">
                    {plan.limits.max_renders_per_day === -1
                      ? 'Unlimited'
                      : plan.limits.max_renders_per_day}
                  </span>
                </div>
                <div className="limit-item">
                  <span className="limit-label">Projects:</span>
                  <span className="limit-value">
                    {plan.limits.max_projects === -1 ? 'Unlimited' : plan.limits.max_projects}
                  </span>
                </div>
                <div className="limit-item">
                  <span className="limit-label">Export Quality:</span>
                  <span className="limit-value">{plan.limits.max_export_quality}</span>
                </div>
                <div className="limit-item">
                  <span className="limit-label">Seats:</span>
                  <span className="limit-value">{plan.seats}</span>
                </div>
              </div>

              {expiryDate && (
                <div className="expiry">
                  <p>
                    License expires on: <strong>{expiryDate.toLocaleDateString()}</strong>
                  </p>
                  {daysUntilExpiry <= 7 && (
                    <p className="warning">⚠️ Expires in {daysUntilExpiry} days</p>
                  )}
                </div>
              )}

              {authState.mode === 'cloud' && plan.plan !== 'FREE' && (
                <button className="btn-manage" onClick={handleManageBilling}>
                  Manage Billing
                </button>
              )}
            </div>
          </div>
        )}

        <div className="section">
          <button className="btn-logout" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </div>

      <style>{`
        .account-page {
          min-height: 100vh;
          background: #f5f5f5;
          padding: 40px 20px;
        }

        .container {
          max-width: 800px;
          margin: 0 auto;
        }

        h1 {
          color: #333;
          margin-bottom: 30px;
          font-size: 32px;
        }

        h2 {
          color: #555;
          font-size: 20px;
          margin-bottom: 15px;
        }

        .section {
          background: white;
          border-radius: 12px;
          padding: 30px;
          margin-bottom: 20px;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }

        .info-row {
          display: flex;
          justify-content: space-between;
          padding: 12px 0;
          border-bottom: 1px solid #f0f0f0;
        }

        .info-row:last-child {
          border-bottom: none;
        }

        .label {
          font-weight: 500;
          color: #666;
        }

        .value {
          color: #333;
        }

        .plan-card {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          border-radius: 12px;
          padding: 30px;
          color: white;
        }

        .plan-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 20px;
        }

        .plan-header h3 {
          margin: 0;
          font-size: 28px;
        }

        .badge-active {
          background: rgba(255, 255, 255, 0.3);
          padding: 5px 15px;
          border-radius: 20px;
          font-size: 14px;
        }

        .limits {
          margin: 20px 0;
        }

        .limit-item {
          display: flex;
          justify-content: space-between;
          padding: 10px 0;
          border-bottom: 1px solid rgba(255, 255, 255, 0.2);
        }

        .limit-item:last-child {
          border-bottom: none;
        }

        .limit-label {
          opacity: 0.9;
        }

        .limit-value {
          font-weight: 600;
        }

        .expiry {
          margin-top: 20px;
          padding-top: 20px;
          border-top: 1px solid rgba(255, 255, 255, 0.2);
        }

        .expiry p {
          margin: 5px 0;
        }

        .warning {
          color: #ffd700;
          font-weight: 600;
        }

        .btn-manage {
          width: 100%;
          padding: 14px;
          margin-top: 20px;
          background: white;
          color: #667eea;
          border: none;
          border-radius: 8px;
          font-size: 16px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.3s;
        }

        .btn-manage:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        }

        .btn-logout {
          padding: 12px 30px;
          background: #dc3545;
          color: white;
          border: none;
          border-radius: 8px;
          font-size: 16px;
          cursor: pointer;
          transition: all 0.3s;
        }

        .btn-logout:hover {
          background: #c82333;
        }

        .loading {
          text-align: center;
          padding: 40px;
          font-size: 18px;
          color: #666;
        }
      `}</style>
    </div>
  );
};
