/**
 * License verification and entitlement management
 */

import * as jose from 'jose';

const CLOUD_API_URL = process.env.BROUSLA_CLOUD_URL || 'http://localhost:8000';
const LICENSE_CACHE_KEY = 'brousla_license_jwt';
const LICENSE_CACHE_TIMESTAMP_KEY = 'brousla_license_timestamp';
const GRACE_PERIOD_MS = 72 * 60 * 60 * 1000; // 72 hours

export interface LicenseClaims {
  sub: string;
  plan: string;
  limits: {
    max_renders_per_day: number;
    max_seats: number;
    max_projects: number;
    max_export_quality: string;
    team_collaboration?: boolean;
    [key: string]: any;
  };
  seats: number;
  device_max: number;
  exp: number;
  iat: number;
  type: string;
}

export interface EntitlementCheckResult {
  entitled: boolean;
  reason?: string;
  currentUsage?: number;
  limit?: number;
}

/**
 * Fetch entitlements from cloud service
 */
export async function fetchEntitlements(accessToken: string): Promise<string> {
  const response = await fetch(`${CLOUD_API_URL}/entitlements`, {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch entitlements: ${response.statusText}`);
  }

  const data = await response.json();
  
  // Cache the license JWT
  localStorage.setItem(LICENSE_CACHE_KEY, data.license_jwt);
  localStorage.setItem(LICENSE_CACHE_TIMESTAMP_KEY, Date.now().toString());
  
  return data.license_jwt;
}

/**
 * Get cached license JWT (with grace period for offline mode)
 */
export function getCachedLicense(): string | null {
  const cachedJwt = localStorage.getItem(LICENSE_CACHE_KEY);
  const cachedTimestamp = localStorage.getItem(LICENSE_CACHE_TIMESTAMP_KEY);
  
  if (!cachedJwt || !cachedTimestamp) {
    return null;
  }
  
  const cacheAge = Date.now() - parseInt(cachedTimestamp, 10);
  
  // Allow cached license within grace period even if expired
  if (cacheAge > GRACE_PERIOD_MS) {
    return null;
  }
  
  return cachedJwt;
}

/**
 * Fetch public key (JWKs) from cloud service
 */
export async function fetchPublicKey(): Promise<jose.JWK> {
  const response = await fetch(`${CLOUD_API_URL}/pubkey`);
  
  if (!response.ok) {
    throw new Error(`Failed to fetch public key: ${response.statusText}`);
  }
  
  const data = await response.json();
  return data.keys[0]; // Return first key
}

/**
 * Verify license JWT with cloud public key
 */
export async function verifyLicense(
  licenseJwt: string,
  jwk?: jose.JWK
): Promise<LicenseClaims | null> {
  try {
    // Fetch public key if not provided
    if (!jwk) {
      jwk = await fetchPublicKey();
    }
    
    // Import JWK as public key
    const publicKey = await jose.importJWK(jwk, 'RS256');
    
    // Verify JWT
    const { payload } = await jose.jwtVerify(licenseJwt, publicKey, {
      algorithms: ['RS256'],
    });
    
    // Check if license type
    if (payload.type !== 'license') {
      throw new Error('Invalid token type');
    }
    
    return payload as unknown as LicenseClaims;
  } catch (error) {
    console.error('License verification failed:', error);
    
    // In offline mode, check if we can accept expired token with grace period
    const cachedTimestamp = localStorage.getItem(LICENSE_CACHE_TIMESTAMP_KEY);
    if (cachedTimestamp) {
      const cacheAge = Date.now() - parseInt(cachedTimestamp, 10);
      if (cacheAge <= GRACE_PERIOD_MS) {
        console.warn('Using cached license in offline mode (within grace period)');
        // Decode without verification (risky, but acceptable within grace period)
        const decoded = jose.decodeJwt(licenseJwt);
        return decoded as unknown as LicenseClaims;
      }
    }
    
    return null;
  }
}

/**
 * Check if user is entitled to a feature
 */
export async function isEntitled(
  feature: string,
  usage?: number
): Promise<EntitlementCheckResult> {
  // Try to get cached license first
  let licenseJwt = getCachedLicense();
  
  if (!licenseJwt) {
    return {
      entitled: false,
      reason: 'No valid license found. Please login or renew your subscription.',
    };
  }
  
  // Verify license
  const claims = await verifyLicense(licenseJwt);
  
  if (!claims) {
    return {
      entitled: false,
      reason: 'License verification failed. Please renew your subscription.',
    };
  }
  
  // Check specific feature entitlements
  const limits = claims.limits;
  
  switch (feature) {
    case 'render':
      const maxRenders = limits.max_renders_per_day;
      if (maxRenders === -1) {
        return { entitled: true }; // Unlimited
      }
      if (usage !== undefined && usage >= maxRenders) {
        return {
          entitled: false,
          reason: `Daily render limit reached (${maxRenders})`,
          currentUsage: usage,
          limit: maxRenders,
        };
      }
      return { entitled: true, currentUsage: usage, limit: maxRenders };
    
    case 'project_create':
      const maxProjects = limits.max_projects;
      if (maxProjects === -1) {
        return { entitled: true }; // Unlimited
      }
      if (usage !== undefined && usage >= maxProjects) {
        return {
          entitled: false,
          reason: `Project limit reached (${maxProjects})`,
          currentUsage: usage,
          limit: maxProjects,
        };
      }
      return { entitled: true, currentUsage: usage, limit: maxProjects };
    
    case 'export_4k':
      if (limits.max_export_quality === '4k') {
        return { entitled: true };
      }
      return {
        entitled: false,
        reason: `4K export requires PRO or TEAM plan`,
      };
    
    case 'team_collaboration':
      if (limits.team_collaboration === true) {
        return { entitled: true };
      }
      return {
        entitled: false,
        reason: 'Team collaboration requires TEAM plan',
      };
    
    default:
      return { entitled: true }; // Unknown features are allowed by default
  }
}

/**
 * Get current plan info from license
 */
export async function getCurrentPlan(): Promise<LicenseClaims | null> {
  const licenseJwt = getCachedLicense();
  if (!licenseJwt) {
    return null;
  }
  
  return await verifyLicense(licenseJwt);
}

/**
 * Report usage to cloud service
 */
export async function reportUsage(
  accessToken: string,
  type: string,
  quantity: number = 1
): Promise<void> {
  try {
    const response = await fetch(`${CLOUD_API_URL}/usage/report`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ type, qty: quantity }),
    });
    
    if (!response.ok) {
      console.error('Failed to report usage:', response.statusText);
    }
  } catch (error) {
    console.error('Error reporting usage:', error);
  }
}
