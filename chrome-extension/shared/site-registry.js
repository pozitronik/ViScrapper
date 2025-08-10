/**
 * Site Registry - Central registry for all supported sites
 * Single source of truth for site configuration and parser mapping
 */

class SiteRegistry {
  // Static registry storage
  static sites = new Map();
  
  /**
   * Register a site with its parser configuration
   * @param {Object} config - Site configuration
   * @param {string} config.domain - Primary domain pattern (e.g., 'calvinklein.us')
   * @param {string} config.siteId - Unique site identifier (e.g., 'calvinklein')
   * @param {string} config.siteName - Display name (e.g., 'Calvin Klein')
   * @param {Function} config.parserClass - Parser class constructor
   * @param {Array<string>} [config.urlPatterns] - Additional URL patterns to match
   * @param {Object} [config.metadata] - Additional metadata
   */
  static register(config) {
    const { domain, siteId, siteName, parserClass, urlPatterns = [], metadata = {} } = config;
    
    if (!domain || !siteId || !siteName || !parserClass) {
      console.error('SiteRegistry: Invalid registration config', config);
      return false;
    }
    
    // Store the configuration
    this.sites.set(domain, {
      domain,
      siteId,
      siteName,
      parserClass,
      urlPatterns: [domain, ...urlPatterns],
      metadata,
      // Factory function for creating parser instances
      createParser: () => new parserClass()
    });
    
    console.log(`SiteRegistry: Registered ${siteName} (${domain})`);
    return true;
  }
  
  /**
   * Get site configuration by URL
   * @param {string} url - URL to check
   * @returns {Object|null} Site configuration or null if not found
   */
  static getSiteByUrl(url) {
    if (!url) return null;
    
    // Check each registered site
    for (const [domain, siteConfig] of this.sites) {
      // Check primary domain
      if (url.includes(domain)) {
        return siteConfig;
      }
      
      // Check additional URL patterns
      if (siteConfig.urlPatterns) {
        for (const pattern of siteConfig.urlPatterns) {
          if (url.includes(pattern)) {
            return siteConfig;
          }
        }
      }
    }
    
    return null;
  }
  
  /**
   * Detect site from URL and return site info
   * @param {string} url - URL to check
   * @returns {Object} Site detection result
   */
  static detectSite(url) {
    const site = this.getSiteByUrl(url);
    
    if (site) {
      return {
        id: site.siteId,
        name: site.siteName,
        domain: site.domain,
        supported: true
      };
    }
    
    return {
      id: 'unsupported',
      name: 'VIParser',
      supported: false
    };
  }
  
  /**
   * Create parser for URL
   * @param {string} url - URL to create parser for
   * @returns {Object|null} Parser instance or null
   */
  static createParser(url) {
    const site = this.getSiteByUrl(url);
    
    if (site && site.createParser) {
      try {
        console.log(`SiteRegistry: Creating ${site.siteName} parser`);
        return site.createParser();
      } catch (error) {
        console.error(`SiteRegistry: Failed to create parser for ${site.siteName}:`, error);
        return null;
      }
    }
    
    console.log('SiteRegistry: No parser found for URL:', url);
    return null;
  }
  
  /**
   * Get all supported domains
   * @returns {Array<string>} List of supported domains
   */
  static getSupportedDomains() {
    return Array.from(this.sites.keys());
  }
  
  /**
   * Get all supported URL patterns (for manifest.json generation)
   * @returns {Array<string>} List of URL patterns
   */
  static getSupportedUrlPatterns() {
    const patterns = new Set();
    
    for (const site of this.sites.values()) {
      // Add manifest-style patterns
      patterns.add(`https://www.${site.domain}/*`);
      patterns.add(`https://${site.domain}/*`);
      
      // Add any additional patterns
      if (site.urlPatterns) {
        for (const pattern of site.urlPatterns) {
          if (!pattern.startsWith('http')) {
            patterns.add(`https://www.${pattern}/*`);
            patterns.add(`https://${pattern}/*`);
          } else {
            patterns.add(pattern);
          }
        }
      }
    }
    
    return Array.from(patterns);
  }
  
  /**
   * Get all site information
   * @returns {Array<Object>} Array of site configurations
   */
  static getAllSites() {
    return Array.from(this.sites.values()).map(site => ({
      domain: site.domain,
      siteId: site.siteId,
      siteName: site.siteName,
      urlPatterns: site.urlPatterns,
      metadata: site.metadata
    }));
  }
  
  /**
   * Check if URL is supported
   * @param {string} url - URL to check
   * @returns {boolean} True if supported
   */
  static isSupported(url) {
    return this.getSiteByUrl(url) !== null;
  }
  
  /**
   * Clear all registrations (mainly for testing)
   */
  static clear() {
    this.sites.clear();
    console.log('SiteRegistry: Cleared all registrations');
  }
}

// Make available globally
if (typeof window !== 'undefined') {
  window.SiteRegistry = SiteRegistry;
}

// Export for Node.js environment (testing)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = SiteRegistry;
}