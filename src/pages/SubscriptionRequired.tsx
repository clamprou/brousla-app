import React, { useState } from 'react';
import { getAuthState } from '../utils/auth';

const CLOUD_API_URL = process.env.BROUSLA_CLOUD_URL || 'http://localhost:8000';

export const SubscriptionRequired: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const authState = getAuthState();

  const handleUpgrade = async (plan: 'PRO' | 'TEAM') => {
    setLoading(true);
    try {
      const response = await fetch(`${CLOUD_API_URL}/billing/create-checkout-session`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authState.accessToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ plan }),
      });

      if (response.ok) {
        const data = await response.json();
        // Open Stripe Checkout in external browser
        window.open(data.url, '_blank');
      } else {
        alert('Failed to create checkout session');
      }
    } catch (error) {
      console.error('Error creating checkout session:', error);
      alert('An error occurred. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="subscription-required">
      <div className="content">
        <h1>🎨 Subscription Required</h1>
        <p className="subtitle">
          Upgrade to unlock unlimited creativity and premium features
        </p>

        <div className="plans">
          <div className="plan">
            <div className="plan-header">
              <h2>FREE</h2>
              <div className="price">$0</div>
            </div>
            <ul className="features">
              <li>✓ 10 renders per day</li>
              <li>✓ 3 projects</li>
              <li>✓ 720p export</li>
              <li>✓ 1 seat</li>
            </ul>
            <button className="btn-plan current" disabled>
              Current Plan
            </button>
          </div>

          <div className="plan featured">
            <div className="badge">POPULAR</div>
            <div className="plan-header">
              <h2>PRO</h2>
              <div className="price">
                $19<span>/month</span>
              </div>
            </div>
            <ul className="features">
              <li>✓ 100 renders per day</li>
              <li>✓ Unlimited projects</li>
              <li>✓ 4K export</li>
              <li>✓ 1 seat</li>
              <li>✓ Priority support</li>
            </ul>
            <button
              className="btn-plan"
              onClick={() => handleUpgrade('PRO')}
              disabled={loading}
            >
              {loading ? 'Loading...' : 'Upgrade to PRO'}
            </button>
          </div>

          <div className="plan">
            <div className="plan-header">
              <h2>TEAM</h2>
              <div className="price">
                $49<span>/month</span>
              </div>
            </div>
            <ul className="features">
              <li>✓ 500 renders per day</li>
              <li>✓ Unlimited projects</li>
              <li>✓ 4K export</li>
              <li>✓ 5 seats</li>
              <li>✓ Team collaboration</li>
              <li>✓ Priority support</li>
            </ul>
            <button
              className="btn-plan"
              onClick={() => handleUpgrade('TEAM')}
              disabled={loading}
            >
              {loading ? 'Loading...' : 'Upgrade to TEAM'}
            </button>
          </div>
        </div>

        <p className="note">
          💳 All payments are processed securely through Stripe.
          <br />
          Cancel anytime, no questions asked.
        </p>
      </div>

      <style>{`
        .subscription-required {
          min-height: 100vh;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          padding: 40px 20px;
          display: flex;
          justify-content: center;
          align-items: center;
        }

        .content {
          max-width: 1200px;
          width: 100%;
        }

        h1 {
          color: white;
          text-align: center;
          font-size: 42px;
          margin-bottom: 10px;
        }

        .subtitle {
          color: rgba(255, 255, 255, 0.9);
          text-align: center;
          font-size: 18px;
          margin-bottom: 40px;
        }

        .plans {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
          gap: 30px;
          margin-bottom: 30px;
        }

        .plan {
          background: white;
          border-radius: 12px;
          padding: 30px;
          position: relative;
          box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
          transition: transform 0.3s;
        }

        .plan:hover {
          transform: translateY(-5px);
        }

        .plan.featured {
          border: 3px solid #ffd700;
          transform: scale(1.05);
        }

        .badge {
          position: absolute;
          top: -10px;
          right: 20px;
          background: #ffd700;
          color: #333;
          padding: 5px 15px;
          border-radius: 20px;
          font-size: 12px;
          font-weight: bold;
        }

        .plan-header h2 {
          margin: 0 0 10px 0;
          font-size: 24px;
          color: #333;
        }

        .price {
          font-size: 36px;
          font-weight: bold;
          color: #667eea;
          margin-bottom: 20px;
        }

        .price span {
          font-size: 16px;
          color: #999;
          font-weight: normal;
        }

        .features {
          list-style: none;
          padding: 0;
          margin: 0 0 20px 0;
        }

        .features li {
          padding: 10px 0;
          color: #666;
          font-size: 14px;
        }

        .btn-plan {
          width: 100%;
          padding: 14px;
          border: none;
          border-radius: 8px;
          font-size: 16px;
          font-weight: 600;
          cursor: pointer;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          transition: all 0.3s;
        }

        .btn-plan:hover:not(:disabled) {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }

        .btn-plan.current {
          background: #e0e0e0;
          color: #999;
          cursor: not-allowed;
        }

        .btn-plan:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .note {
          text-align: center;
          color: rgba(255, 255, 255, 0.8);
          font-size: 14px;
          line-height: 1.6;
        }
      `}</style>
    </div>
  );
};
